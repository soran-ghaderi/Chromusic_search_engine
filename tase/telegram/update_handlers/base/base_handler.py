import asyncio
import collections
from collections import defaultdict
from typing import Dict, List, Union, Deque, Tuple

import pyrogram
from pydantic import BaseModel
from pyrogram.enums import ParseMode

from tase.common.utils import _trans, async_timed
from tase.db.arangodb import graph as graph_models
from tase.db.arangodb.enums import TelegramAudioType, InteractionType, ChatType
from tase.db.arangodb.helpers import AudioKeyboardStatus
from tase.db.database_client import DatabaseClient
from tase.db.db_utils import get_telegram_message_media_type, parse_audio_key_from_message_id
from tase.db.elasticsearchdb import models as elasticsearch_models
from tase.my_logger import logger
from tase.telegram.client import TelegramClient
from .handler_metadata import HandlerMetadata


class BaseHandler(BaseModel):
    db: DatabaseClient
    telegram_client: TelegramClient

    class Config:
        arbitrary_types_allowed = True

    def init_handlers(self) -> List[HandlerMetadata]:
        raise NotImplementedError

    @async_timed()
    async def update_audio_cache(
        self,
        db_audios: Union[Deque[graph_models.vertices.Audio], Deque[elasticsearch_models.Audio]],
    ) -> Tuple[Dict[int, graph_models.vertices.Chat], Deque[str]]:
        """
        Update Audio file caches that are not been cached by this telegram client

        Parameters
        ----------
        db_audios : Union[Deque[graph_models.vertices.Audio], Deque[elasticsearch_models.Audio]]
            List of audios to be checked
        Returns
        -------
        A dictionary mapping from `chat_id` to a Chat object with list of invalid audios.
        """
        if not db_audios:
            return {}, collections.deque()

        chat_msg = defaultdict(collections.deque)
        chats_dict = {}
        invalid_audio_keys = collections.deque()

        def get_key(_db_audio) -> str:
            return _db_audio.key if isinstance(_db_audio, graph_models.vertices.Audio) else _db_audio.id

        cache_checks = await asyncio.gather(*(self.db.document.has_audio_by_key(self.telegram_client.telegram_id, get_key(db_audio)) for db_audio in db_audios))
        db_chats = await asyncio.gather(*(self.db.graph.get_chat_by_telegram_chat_id(db_audio.chat_id) for db_audio in db_audios))

        for cache_check, db_audio in zip(cache_checks, db_audios):
            if not cache_check and not isinstance(cache_check, BaseException):
                chat_msg[db_audio.chat_id].append(db_audio.message_id)

        for db_chat in db_chats:
            if db_chat and db_chat.chat_id not in chats_dict:
                chats_dict[db_chat.chat_id] = db_chat

        # todo: this approach is only for public channels, what about private channels?
        # todo: this might cause `floodwait` errors!, it should be avoided
        async def get_messages(
            chat_id: int,
            message_ids,
        ) -> Tuple[List[pyrogram.types.Message], int]:
            res = await self.telegram_client.get_messages(chat_id=chats_dict[chat_id].username, message_ids=message_ids)
            if not isinstance(res, KeyError):
                return res, chat_id
            else:
                # todo: this chat is no longer is public or available, update the databases accordingly
                for message_id in message_ids:
                    key = parse_audio_key_from_message_id(
                        message_id,
                        chat_id,
                    )
                    if key:
                        invalid_audio_keys.append(key)

                if len(invalid_audio_keys):
                    await asyncio.gather(*(self.db.mark_audio_as_deleted(key) for key in invalid_audio_keys))

                return [], chat_id

        messages_list = await asyncio.gather(*(get_messages(chat_id, message_ids) for chat_id, message_ids in chat_msg.items()))

        messages = [(message, chat_id) for sub_messages_list, chat_id in messages_list if sub_messages_list for message in sub_messages_list if message]
        if messages:
            await asyncio.gather(
                *(
                    self.db.update_or_create_audio(
                        message,
                        self.telegram_client.telegram_id,
                        chat_id,
                    )
                    for message, chat_id in messages
                )
            )

        return chats_dict, invalid_audio_keys

    @async_timed()
    async def download_audio(
        self,
        client: pyrogram.Client,
        from_user: graph_models.vertices.User,
        text: str,
        message: pyrogram.types.Message,
    ):
        if client is None or from_user is None or text is None or not len(text) or message is None:
            return

        valid = False
        # todo: handle errors for invalid messages
        hit_download_url = text.split("dl_")[1]
        audio_vertex = await self.db.graph.get_audio_from_hit_download_url(hit_download_url)

        if audio_vertex is not None:
            # todo: handle exceptions
            audio_doc, chat = await asyncio.gather(
                *(
                    self.db.document.get_audio_by_key(
                        self.telegram_client.telegram_id,
                        audio_vertex.key,
                    ),
                    self.db.graph.get_chat_by_telegram_chat_id(audio_vertex.chat_id),
                )
            )

            update_audio_task = None
            if audio_doc:
                file_id = audio_doc.file_id
            else:
                # fixme: find a better way of getting messages that have not been cached yet
                try:
                    if await self.telegram_client.peer_exists(audio_vertex.chat_id):
                        messages = await self.telegram_client.get_messages(audio_vertex.chat_id, [audio_vertex.message_id])
                    else:
                        messages = await self.telegram_client.get_messages(chat.username, [audio_vertex.message_id])
                except Exception as e:
                    logger.exception(e)
                    messages = None

                else:
                    if isinstance(messages, KeyError):
                        # todo: this chat is no longer is public or available, update the databases accordingly
                        await message.reply_text("The sender chat of the message containing this audio does not exist anymore, please try again!")
                        logger.error("The sender chat of the message containing this audio does not exist anymore, please try again!")
                        return

                if not messages:
                    # todo: could not get the audio from telegram servers, what to do now?
                    await message.reply_text(
                        _trans(
                            "An error occurred while processing the download URL for this audio",
                            from_user.chosen_language_code,
                        )
                    )
                    logger.error("could not get the audio from telegram servers, what to do now?")
                    return

                # update the audio in all databases
                update_audio_task = asyncio.create_task(
                    self.db.update_or_create_audio(
                        messages[0],
                        self.telegram_client.telegram_id,
                        audio_vertex.chat_id,
                    )
                )

                audio, audio_type = get_telegram_message_media_type(messages[0])
                if audio is None or audio_type == TelegramAudioType.NON_AUDIO:
                    # fixme: instead of raising an exception, it is better to mark the audio file in the
                    #  database as invalid and update related edges and vertices accordingly

                    if messages[0].empty:
                        await self.db.mark_audio_as_deleted(audio_vertex.key)
                    else:
                        await self.db.mark_audio_as_invalid(audio_vertex.key)

                    await message.reply_text("This message containing this audio does not exist anymore, please try again!")
                    # raise TelegramMessageWithNoAudio(audio_vertex.message_id, audio_vertex.chat_id)
                    return
                else:
                    file_id = audio.file_id

            from tase.telegram.bots.ui.templates import BaseTemplate
            from tase.telegram.bots.ui.templates import AudioCaptionData
            from tase.telegram.bots.ui.inline_buttons.common import get_audio_markup_keyboard

            text = BaseTemplate.registry.audio_caption_template.render(
                AudioCaptionData.parse_from_audio(
                    audio_vertex,
                    from_user,
                    chat,
                    bot_url=f"https://t.me/{(await self.telegram_client.get_me()).username}?start=dl_{hit_download_url}",
                    include_source=True,
                )
            )

            status = await AudioKeyboardStatus.get_status(
                self.db,
                from_user,
                hit_download_url=hit_download_url,
            )

            markup_keyboard = get_audio_markup_keyboard(
                (await self.telegram_client.get_me()).username,
                ChatType.BOT,
                from_user.chosen_language_code,
                hit_download_url,
                audio_vertex.valid_for_inline_search,
                status,
            )

            if audio_vertex.audio_type == TelegramAudioType.AUDIO_FILE:
                await message.reply_audio(
                    audio=file_id,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup_keyboard,
                )
            else:
                await message.reply_document(
                    document=file_id,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup_keyboard,
                )

            valid = True

            create_interaction = self.db.graph.create_interaction(
                hit_download_url,
                from_user,
                self.telegram_client.telegram_id,
                InteractionType.DOWNLOAD,
                ChatType.BOT,
            )
            if update_audio_task:
                await asyncio.gather(*(create_interaction, update_audio_task))
            else:
                await create_interaction

        if not valid:
            # todo: An Error occurred while processing this audio download url, why?
            logger.error(f"An error occurred while processing the download URL for this audio: {hit_download_url}")
            await message.reply_text(
                _trans(
                    "An error occurred while processing the download URL for this audio",
                    from_user.chosen_language_code,
                )
            )

    async def update_audio_keyboard_markup(
        self,
        client: pyrogram.Client,
        from_user: graph_models.vertices.User,
        telegram_chosen_inline_result: pyrogram.types.ChosenInlineResult,
        hit_download_url: str,
        chat_type: ChatType,
    ):
        retry_left = 5
        audio_vertex = None

        while retry_left:
            audio_vertex = await self.db.graph.get_audio_from_hit_download_url(hit_download_url)
            if not audio_vertex:
                # fixme: this should not happen
                logger.error("This should not happen")
                await asyncio.sleep(2)

            retry_left -= 1

        if not audio_vertex:
            logger.error("This should not happen at all!")
            # fixme: this should not happen at all!
            return

        from tase.telegram.bots.ui.inline_buttons.common import get_audio_markup_keyboard

        status = await AudioKeyboardStatus.get_status(
            self.db,
            from_user,
            audio_vertex_key=audio_vertex.key,
        )

        await client.edit_inline_reply_markup(
            telegram_chosen_inline_result.inline_message_id,
            reply_markup=get_audio_markup_keyboard(
                (await self.telegram_client.get_me()).username,
                chat_type,
                from_user.chosen_language_code,
                hit_download_url,
                audio_vertex.valid_for_inline_search,
                status,
            ),
        )
