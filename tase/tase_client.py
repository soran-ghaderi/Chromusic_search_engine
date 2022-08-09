import json
import multiprocessing as mp
from typing import List, Optional

from decouple import config

from tase.configs import TASEConfig
from tase.db.database_client import DatabaseClient
from tase.scheduler import SchedulerWorkerProcess
from tase.telegram.client import TelegramClient
from tase.telegram.client.client_manager import ClientManager


class TASE:
    clients: List["TelegramClient"]
    tase_config: Optional[TASEConfig]

    def __init__(
        self,
    ):
        self.clients = []
        self.client_managers: List[ClientManager] = []
        self.tase_config = None
        self.database_client = None

    def init_telegram_clients(self):
        mgr = mp.Manager()
        task_queues = mgr.dict()
        scheduler = None

        debug = config(
            "DEBUG",
            cast=bool,
            default=True,
        )

        tase_config_file_name = (
            config("TASE_CONFIG_FILE_NAME_DEBUG") if debug else config("TASE_CONFIG_FILE_NAME_PRODUCTION")
        )

        if tase_config_file_name is not None:
            with open(f"../{tase_config_file_name}", "r") as f:
                tase_config = TASEConfig.parse_obj(json.loads("".join(f.readlines())))  # todo: any improvement?

            self.tase_config = tase_config
            if tase_config is not None:
                self.database_client = DatabaseClient(
                    elasticsearch_config=tase_config.elastic_config,
                    arangodb_config=tase_config.arango_db_config,
                )

                for client_config in tase_config.clients_config:
                    tg_client = TelegramClient._parse(
                        client_config,
                        tase_config.pyrogram_config.workdir,
                    )
                    client_manager = ClientManager(
                        telegram_client_name=tg_client.name,
                        telegram_client=tg_client,
                        task_queues=task_queues,
                        database_client=self.database_client,
                    )
                    client_manager.start()
                    self.clients.append(tg_client)
                    self.client_managers.append(client_manager)

                scheduler = SchedulerWorkerProcess(
                    0,
                    self.database_client,
                    task_queues,
                )
                scheduler.start()

                # todo: do initial job scheduling in a proper way
                publish_job_to_scheduler(IndexChannelsJob())
                publish_job_to_scheduler(ExtractUsernamesJob())

            else:
                # todo: raise error (config file is invalid)
                pass

        else:
            # todo: raise error (empty config file path)
            pass

        for client_mgr in self.client_managers:
            client_mgr.join()

        if scheduler:
            scheduler.join()

    def connect_clients(self):
        for client in self.clients:
            client.start()


if __name__ == "__main__":
    tase = TASE()
    tase.init_telegram_clients()
