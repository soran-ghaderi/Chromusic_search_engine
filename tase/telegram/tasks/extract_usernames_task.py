import random
import time
from typing import List, Optional, Union

import pyrogram
from kombu.mixins import ConsumerProducerMixin
from pydantic import Field
from pyrogram.errors import UsernameNotOccupied, FloodWait

from tase.common.utils import datetime_to_timestamp, prettify, find_telegram_usernames
from tase.db import DatabaseClient
from tase.db.arangodb.enums import MentionSource, RabbitMQTaskType
from tase.db.arangodb.graph.vertices import Chat
from tase.db.arangodb.helpers import UsernameExtractorMetadata
from tase.my_logger import logger
from tase.task_distribution import BaseTask, TargetWorkerType
from tase.telegram.client import TelegramClient


class ExtractUsernamesTask(BaseTask):
    target_worker_type = TargetWorkerType.ANY_TELEGRAM_CLIENTS_CONSUMER_WORK
    type = RabbitMQTaskType.EXTRACT_USERNAMES_TASK

    db: Optional[DatabaseClient] = Field(default=None)
    chat: Optional[Chat] = Field(default=None)

    chat_username: Optional[str]
    metadata: Optional[UsernameExtractorMetadata]

    def run(
        self,
        consumer_producer: ConsumerProducerMixin,
        db: DatabaseClient,
        telegram_client: TelegramClient = None,
    ):
        self.task_in_worker(db)

        chat_key = self.kwargs.get("chat_key", None)
        if chat_key is None:
            channel_username: str = self.kwargs.get("channel_username", None)
            if channel_username is None:
                self.task_failed(db)
                return

            self.chat_username = channel_username.lower()
            chat_id = channel_username
            title = channel_username

        else:
            chat: Chat = db.graph.get_chat_by_key(chat_key)
            if chat is None:
                self.task_failed(db)
                return

            self.chat_username = chat.username.lower() if chat.username else None
            chat_id = chat.username if chat.username else chat.invite_link
            title = chat.title

        try:
            tg_chat = telegram_client.get_chat(chat_id)
        except ValueError as e:
            # In case the chat invite link points to a chat that this telegram client hasn't joined yet.
            # todo: fix this
            logger.exception(e)
            self.task_failed(db)
        except KeyError as e:
            self.task_failed(db)
            logger.exception(e)
        except FloodWait as e:
            self.task_failed(db)
            logger.exception(e)

            sleep_time = e.value + random.randint(1, 10)
            logger.info(f"Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            logger.info(f"Waking up after sleeping for {sleep_time} seconds...")
        except UsernameNotOccupied as e:
            self.task_failed(db)
        except Exception as e:
            logger.exception(e)
            self.task_failed(db)
        else:
            chat = db.graph.update_or_create_chat(tg_chat)

            if chat.username_extractor_metadata is None:
                self.metadata: UsernameExtractorMetadata = UsernameExtractorMetadata()
            else:
                self.metadata = chat.username_extractor_metadata.copy()

            if self.metadata is None:
                self.task_failed(db)
                return
            self.metadata.reset_counters()

            self.chat = chat
            self.db = db

            if chat:
                for message in telegram_client.iter_messages(
                    chat_id=chat_id,
                    offset_id=self.metadata.last_message_offset_id,
                    only_newer_messages=True,
                ):
                    message: pyrogram.types.Message = message

                    self.metadata.message_count += 1

                    self.find_usernames_in_text(
                        message.text if message.text else message.caption,
                        True,
                        message,
                        MentionSource.MESSAGE_TEXT,
                    )

                    if message.forward_from_chat and message.forward_from_chat.username:
                        # fixme: it's a public channel or a public supergroup or a user or a bot
                        self.find_usernames_in_text(
                            message.forward_from_chat.username,
                            True,
                            message,
                            MentionSource.FORWARDED_CHAT_USERNAME,
                        )

                        # check the forwarded chat's description/bio for usernames
                        self.find_usernames_in_text(
                            [
                                message.forward_from_chat.description,
                                message.forward_from_chat.bio,
                            ],
                            True,
                            message,
                            MentionSource.FORWARDED_CHAT_DESCRIPTION,
                        )

                    if message.audio:
                        self.find_usernames_in_text(
                            [
                                message.audio.title,
                                message.audio.performer,
                                message.audio.file_name,
                            ],
                            False,
                            message,
                            [
                                MentionSource.AUDIO_TITLE,
                                MentionSource.AUDIO_PERFORMER,
                                MentionSource.AUDIO_FILE_NAME,
                            ],
                        )

                    if message.id > self.metadata.last_message_offset_id:
                        self.metadata.last_message_offset_id = message.id
                        self.metadata.last_message_offset_date = datetime_to_timestamp(message.date)

                logger.info(f"Finished extracting usernames from chat: {title}")

                # check gathered usernames if they match the current policy of indexing and them to the Database
                logger.info(f"Metadata: {prettify(self.metadata)}")
                self.chat.update_username_extractor_metadata(self.metadata)

                self.task_done(db)
            else:
                self.task_failed(db)
                logger.error(f"Error occurred: {title}")
        finally:
            # wait for a while before starting to extract usernames from another channel
            time.sleep(random.randint(10, 20))

    def find_usernames_in_text(
        self,
        text: Union[str, List[Union[str, None]]],
        is_direct_mention: bool,
        message: pyrogram.types.Message,
        mention_source: Union[MentionSource, List[MentionSource]],
    ) -> None:
        if message is None or mention_source is None:
            return None

        def find(text_: str, mention_source_: MentionSource):
            for username, match_start in find_telegram_usernames(text_):
                self.add_username(
                    username,
                    is_direct_mention,
                    message,
                    mention_source_,
                    match_start,
                )

        if not isinstance(text, str) and isinstance(text, List):
            if isinstance(mention_source, List):
                if len(mention_source) != len(text):
                    raise Exception(f"mention_source and text must of the the same size: {len(mention_source)} != " f"{len(text)}")
                for text__, mention_source_ in zip(text, mention_source):
                    if text__ is not None and mention_source_ is not None:
                        find(text__, mention_source_)
            else:
                for text__ in text:
                    if text__ is not None:
                        find(text__, mention_source)

        else:
            if text is not None:
                find(text, mention_source)

    def add_username(
        self,
        username: str,
        is_direct_mention: bool,
        message: pyrogram.types.Message,
        mention_source: MentionSource,
        mention_start_index: int,
    ) -> None:
        if username is None or not len(username) or is_direct_mention is None or message is None or mention_source is None or mention_start_index is None:
            return

        username = username.lower()

        # todo: this is not a valid username, it's an invite link for a private supergroup / channel.
        if username in ("joinchat",):
            return

        if self.chat_username:
            if username == self.chat_username:
                if is_direct_mention:
                    self.metadata.direct_self_mention_count += 1
                else:
                    self.metadata.indirect_self_mention_count += 1
            else:
                if is_direct_mention:
                    self.metadata.direct_raw_mention_count += 1
                else:
                    self.metadata.indirect_raw_mention_count += 1
        else:
            if is_direct_mention:
                self.metadata.direct_raw_mention_count += 1
            else:
                self.metadata.indirect_raw_mention_count += 1

        mentioned_at = datetime_to_timestamp(message.date)
        username_vertex = self.db.graph.get_or_create_username(
            username,
            self.chat,
            is_direct_mention,
            mentioned_at,
            mention_source,
            mention_start_index,
            message.id,
        )

    class Config:
        arbitrary_types_allowed = True
