from __future__ import annotations
from collections import defaultdict
from typing import List

import arrow
import emoji
import pyrogram
from pyrogram.types import InlineQueryResultCachedAudio, InlineKeyboardMarkup, InlineKeyboardButton, \
    InlineQueryResultArticle, InputMessageContent, InputTextMessageContent

from tase.db import elasticsearch_models
from tase.my_logger import logger
from tase.telegram.handlers import BaseHandler, HandlerMetadata
from tase.utils import get_timestamp
from pyrogram import handlers


class InlineQueryHandler(BaseHandler):

    def init_handlers(self) -> List[HandlerMetadata]:
        return [
            HandlerMetadata(
                cls=handlers.InlineQueryHandler,
                callback=self.on_inline_query,
            )
        ]

    def on_inline_query(self, client: 'pyrogram.Client', inline_query: 'pyrogram.types.InlineQuery'):
        logger.debug(f"on_inline_query: {inline_query}")
        query_date = get_timestamp(arrow.utcnow())

        found_any = True
        from_ = 0
        results = []

        if inline_query.query is None or not len(inline_query.query):
            # todo: query is empty
            found_any = False
        else:
            if inline_query.offset is not None and len(inline_query.offset):
                from_ = int(inline_query.offset)

            db_docs, query_metadata = self.db.search_audio(inline_query.query, from_, size=10)

            if not db_docs or not len(db_docs) or not len(query_metadata):
                found_any = False

            db_docs: List['elasticsearch_models.Audio'] = db_docs

            db_inline_query = self.db.get_or_create_inline_query(
                self.telegram_client.telegram_id,
                inline_query,
                query_date=query_date,
                query_metadata=query_metadata,
                audio_docs=db_docs,
            )

            chat_msg = defaultdict(list)
            for db_audio in db_docs:
                chat_msg[db_audio.chat_id].append(db_audio.message_id)

            for chat_id, message_ids in chat_msg.items():
                db_chat = self.db.get_chat_by_chat_id(chat_id)
                messages = self.telegram_client._client.get_messages(chat_id=db_chat.username, message_ids=message_ids)
                for message in messages:
                    self.db.update_or_create_audio(
                        message,
                        self.telegram_client.telegram_id,
                    )

            for db_audio in db_docs:
                db_audio_doc = self.db.get_audio_file_from_cache(db_audio, self.telegram_client.telegram_id)

                #  todo: Some audios have null titles, solution?
                if not db_audio_doc or not db_audio.title:
                    continue

                results.append(
                    InlineQueryResultCachedAudio(
                        audio_file_id=db_audio_doc.file_id,
                        id=f'{inline_query.id}->{db_audio.id}',
                        caption=db_audio.message_caption,
                    )
                )

        if found_any:
            try:
                next_offset = str(from_ + len(results) - 1) if (len(results) - 1) else None
                inline_query.answer(results, cache_time=1, next_offset=next_offset)
            except Exception as e:
                logger.exception(e)
        else:
            # todo: No results matching the query found, what now?
            inline_query.answer(
                [
                    InlineQueryResultArticle(
                        title="No Results were found",
                        description="description",
                        input_message_content=InputTextMessageContent(
                            message_text="message",
                        )
                    )
                ]
            )