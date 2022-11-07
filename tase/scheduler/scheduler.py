import asyncio
import pickle
from multiprocessing import Process
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from apscheduler.schedulers.background import BackgroundScheduler
from decouple import config

from tase import task_globals
from tase.common.utils import sync_exception_handler, async_exception_handler
from tase.configs import TASEConfig
from tase.db import DatabaseClient
from tase.db.arangodb.enums import RabbitMQTaskType
from tase.my_logger import logger
from tase.rabbimq_consumer import RabbitMQConsumer


class SchedulerWorkerProcess(Process):
    def __init__(
        self,
        config: TASEConfig,
    ):
        super().__init__()

        self.daemon = True
        self.name = "SchedulerWorkerProcess"
        self.config = config
        self.db: Optional[DatabaseClient] = None
        self.consumer = None

    def run(self) -> None:
        logger.info("SchedulerWorkerProcess started ....")

        self.db = DatabaseClient(
            self.config.elastic_config,
            self.config.arango_db_config,
        )

        self.consumer = SchedulerJobConsumer(
            db=self.db,
        )

        asyncio.run(self.consumer.init_consumer())
        await asyncio.Future()


class SchedulerJobConsumer(RabbitMQConsumer):
    scheduler: Optional[BackgroundScheduler]

    class Config:
        arbitrary_types_allowed = True

    async def init_consumer(self) -> AbstractRobustConnection:
        logger.info("scheduler task consumer started...")
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        connection = await aio_pika.connect_robust(
            login=config("RABBITMQ_DEFAULT_USER"),
            password=config("RABBITMQ_DEFAULT_PASS"),
        )
        self.connection = connection

        # Creating channel
        channel = await connection.channel()

        # Maximum message count which will be processing at the same time.
        await channel.set_qos(prefetch_count=1)

        rabbitmq_worker_command_queue = await channel.declare_queue(
            "scheduler_command_queue",
            auto_delete=True,
            exclusive=True,
        )

        await rabbitmq_worker_command_queue.bind(
            task_globals.rabbitmq_worker_command_exchange.name,
            routing_key="scheduler_command_queue",
            robust=True,
        )
        await rabbitmq_worker_command_queue.consume(self.on_job)

        ###############################################################

        scheduler_queue = await channel.declare_queue(
            task_globals.scheduler_queue_name,
            auto_delete=True,
            exclusive=True,
        )

        await scheduler_queue.bind(
            task_globals.scheduler_exchange.name,
            routing_key=task_globals.scheduler_queue_name,
            robust=True,
        )
        await scheduler_queue.consume(self.on_job_scheduled)

        return connection

    @sync_exception_handler
    async def on_job(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
    ):
        async with message.process():
            from tase.task_distribution import BaseTask

            body = pickle.loads(message.body)

            if isinstance(body, BaseTask):
                logger.info(f"Scheduler got a new task: {body.type.value} @ {0}")
                if body.type != RabbitMQTaskType.UNKNOWN:
                    # await body.run(self.db, None)
                    asyncio.create_task(body.run(self, self.db, None))
            else:
                # todo: unknown type for body detected, what now?
                raise TypeError(f"Unknown type for `body`: {type(body)}")

    @sync_exception_handler
    def job_runner(
        self,
        *args,
        **kwargs,
    ) -> None:
        """
        This method serves as a workaround for BaseJob derivative classes to be run

        Parameters
        ----------
        args : tuple
            A list of arguments provided as input to the job. The first argument is a subclass of
            `BaseJob<tase.telegram.jobs.BaseJob>`
        kwargs : dict
            A dictionary containing other keyword arguments passed to this function.

        Returns
        -------
        None
        """
        args[0].run(self, self.db)

    @async_exception_handler()
    async def on_job_scheduled(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        """
        This method is executed when a new Job is fetched from RabbitMQ exchange and schedules the job on the
        global scheduler

        Parameters
        ----------
        message : aio_pika.abc.AbstractIncomingMessage
            Object containing information about this message
        """
        from tase.scheduler.jobs import BaseJob

        job: BaseJob = pickle.loads(message.body)
        logger.info(f"scheduler_task_consumer_on_job : {job.type.value}")

        if self.connection is None and self.scheduler.running():
            logger.info("Shutting down scheduler...")
            self.scheduler.shutdown()
            return

        if job.type != RabbitMQTaskType.UNKNOWN:
            self.scheduler.add_job(
                self.job_runner,
                trigger=job.trigger,
                args=[
                    job,
                ],
            )
