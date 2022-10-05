from __future__ import annotations

import uuid
from typing import Optional

from pydantic import Field

from .base_document import BaseDocument
from ..enums import RabbitMQTaskStatus, RabbitMQTaskType


class RabbitMQTask(BaseDocument):
    _collection_name = "doc_rabbitmq_tasks"
    schema_version = 1

    type: RabbitMQTaskType = Field(default=RabbitMQTaskType.UNKNOWN)
    status: RabbitMQTaskStatus = Field(default=RabbitMQTaskStatus.CREATED)
    state_dict: dict = Field(default=dict())

    @classmethod
    def parse(
        cls,
        task_type: RabbitMQTaskType,
        state_dict: dict = None,
    ) -> Optional[RabbitMQTask]:
        if task_type is None:
            return None

        bot_task = RabbitMQTask(
            key=str(uuid.uuid4()),
            type=task_type,
        )
        if state_dict is not None and len(state_dict):
            bot_task.state_dict = state_dict

        return bot_task

    def update_status(
        self,
        status: RabbitMQTaskStatus,
    ) -> bool:
        """
        Update `status` of the task.

        Parameters
        ----------
        status : RabbitMQTaskStatus
            New status of the task

        Returns
        -------
        bool
            Whether the update was successful or not
        """
        if status is None:
            return False

        self_copy = self.copy(deep=True)
        self_copy.status = status
        return self.update(self_copy, reserve_non_updatable_fields=True)

    def update_task_state_dict(
        self,
        new_task_state: dict,
    ) -> bool:
        """
        Update the task extra parameters dictionary.

        Parameters
        ----------
        new_task_state : dict
            Dictionary of the new extra parameters

        Returns
        -------
        bool
            Whether the update was successful or not
        """
        if new_task_state is None:
            return False

        self_copy = self.copy(deep=True)
        self_copy.state_dict = new_task_state
        return self.update(self_copy, reserve_non_updatable_fields=True)


class RabbitMQTaskMethods:
    _get_active_rabbitmq_task_query = (
        "for doc_task in @rabbitmq_tasks"
        "   sort doc_task.modified_at desc"
        "   filter doc_task.type == '@type' and doc_task.status in @status_list and doc_task.state_dict != null"
        "   filter @input_attr_list all in attributes(doc_task.state_dict) and @input_value_list all in values(doc_task.state_dict)"
        "   limit 1"
        "   return doc_task"
    )

    _cancel_recent_rabbitmq_tasks_query = (
        "for doc_task in @rabbitmq_tasks"
        "   sort doc_task.modified_at desc"
        "   filter doc_task.type == @type and doc_task.status in @status_list"
        "   update doc_task with {"
        "       status: @new_status"
        "   } in @rabbitmq_tasks options {mergeObjects: true}"
        "   return NEW"
    )

    def get_rabbitmq_task_by_key(
        self,
        key: str,
    ) -> Optional[RabbitMQTask]:
        """
        Get `a RabbitMQTask` by its `key`

        Parameters
        ----------
        key : str
            Key of the task to get

        Returns
        -------
        RabbitMQTask, optional
            Task if it exists in the database, otherwise, return None

        """
        if key is None:
            return None

        return RabbitMQTask.get(key)

    def create_rabbitmq_task(
        self,
        task_type: RabbitMQTaskType,
        state_dict: dict = None,
        cancel_active_tasks: bool = False,
    ) -> Optional[RabbitMQTask]:
        """
        Create a `RabbitMQTask` document in the ArangoDB.

        Parameters
        ----------
        task_type : BotTaskType
            Type of the task
        state_dict : dict
            Extra data passed to the BotTask
        cancel_active_tasks : bool, default : False
            Whether to cancel recent tasks of the user before creating a new one

        Returns
        -------
        BotTask, optional
            BotTask document if the creation was successful, otherwise, return None
        """
        if cancel_active_tasks:
            self.cancel_active_rabbitmq_tasks(
                task_type,
            )

        task, successful = RabbitMQTask.insert(
            RabbitMQTask.parse(
                task_type,
                state_dict,
            )
        )
        if task and successful:
            return task

        return None

    def get_active_rabbitmq_task(
        self,
        task_type: RabbitMQTaskType,
        state_dict: dict = None,
    ) -> Optional[RabbitMQTask]:
        if task_type is None or task_type == RabbitMQTaskType.UNKNOWN:
            return None

        if state_dict is None:
            state_dict = {}

        cursor = RabbitMQTask.execute_query(
            self._get_active_rabbitmq_task_query,
            bind_vars={
                "rabbitmq_tasks": RabbitMQTask._collection_name,
                "type": task_type.value,
                "status_list": [
                    RabbitMQTaskStatus.CREATED.value,
                    RabbitMQTaskStatus.IN_QUEUE.value,
                    RabbitMQTaskStatus.IN_WORKER.value,
                ],
                "input_attr_list": list(state_dict.keys()),
                "input_value_list": list(state_dict.values()),
            },
        )
        if cursor is not None and len(cursor):
            return RabbitMQTask.from_collection(cursor.pop())

        return None

    def cancel_active_rabbitmq_tasks(
        self,
        task_type: RabbitMQTaskType,
    ) -> bool:
        """
        Cancel the RabbitMQ tasks with specified `task_type` that their status are `created`, `in_queue`, or `in_worker`.

        Parameters
        ----------
        task_type : BotTaskType
            Type of the BotTask to cancel

        Returns
        -------
        bool
            Whether the cancellation was successful or not.
        """
        if task_type is None or task_type == RabbitMQTaskType.UNKNOWN:
            return False

        cursor = RabbitMQTask.execute_query(
            self._cancel_recent_rabbitmq_tasks_query,
            bind_vars={
                "doc_bot_tasks": RabbitMQTask._collection_name,
                "type": task_type.value,
                "status_list": [
                    RabbitMQTaskStatus.CREATED.value,
                    RabbitMQTaskStatus.IN_QUEUE.value,
                    RabbitMQTaskStatus.IN_WORKER.value,
                ],
                "new_status": RabbitMQTaskStatus.CANCELED.value,
            },
        )
        if cursor is not None:
            return True
        else:
            return False
