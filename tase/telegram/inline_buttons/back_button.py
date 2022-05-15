import pyrogram

from ..telegram_client import TelegramClient
from .button import InlineButton
# from ..handlers import BaseHandler
from ...db import DatabaseClient, graph_models
from ...utils import emoji, _trans


class BackInlineButton(InlineButton):
    name = "back"

    s_back = _trans("Back")
    text = f"{s_back} | {emoji._BACK_arrow}"
    callback_data = "back->back"

    def on_callback_query(
            self,
            client: 'pyrogram.Client',
            callback_query: 'pyrogram.types.CallbackQuery',
            handler: 'BaseHandler',
            db: 'DatabaseClient',
            telegram_client: 'TelegramClient',
            db_from_user: graph_models.vertices.User
    ):
        callback_query.message.delete()