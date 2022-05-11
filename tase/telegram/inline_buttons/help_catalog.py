import pyrogram

from .button import InlineButton
from ..telegram_client import TelegramClient

from ..handlers import BaseHandler
from ...db import DatabaseClient, graph_models
from ...utils import emoji


class HelpCatalogInlineButton(InlineButton):
    name = "help_catalog"
    text = f"Help | {emoji._exclamation_question_mark}"

    switch_inline_query_current_chat = f"#help_catalog"

    def on_inline_query(
            self,
            client: 'pyrogram.Client',
            inline_query: 'pyrogram.types.InlineQuery',
            handler: 'BaseHandler',
            db: 'DatabaseClient',
            telegram_client: 'TelegramClient',
            db_from_user: graph_models.vertices.User,
    ):
        pass
