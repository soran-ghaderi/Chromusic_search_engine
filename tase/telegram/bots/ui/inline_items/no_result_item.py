from typing import Optional

import pyrogram.types
from pyrogram.enums import ParseMode
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent

from tase.db import graph_models
from tase.utils import _trans, emoji
from .base_inline_item import BaseInlineItem


class NoResultItem(BaseInlineItem):
    @classmethod
    def get_item(
        cls,
        db_from_user: graph_models.vertices.User,
    ) -> Optional["pyrogram.types.InlineQueryResult"]:
        if db_from_user is None:
            return None

        return InlineQueryResultArticle(
            title=_trans("No Results Were Found", db_from_user.chosen_language_code),
            description=_trans("No results were found", db_from_user.chosen_language_code),
            input_message_content=InputTextMessageContent(
                message_text=emoji.high_voltage,
                parse_mode=ParseMode.HTML,
            ),
        )