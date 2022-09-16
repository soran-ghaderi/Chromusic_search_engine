import pyrogram
from pydantic import Field
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup

from tase.db.arangodb import graph as graph_models
from tase.telegram.bots.bot_commands.base_command import BaseCommand
from tase.telegram.bots.bot_commands.bot_command_type import BotCommandType
from tase.telegram.bots.ui.inline_buttons import InlineButton
from tase.telegram.bots.ui.templates import BaseTemplate, HelpData
from tase.telegram.update_handlers.base import BaseHandler


class HelpCommand(BaseCommand):
    """
    Shows the help menu
    """

    command_type: BotCommandType = Field(default=BotCommandType.HELP)

    def command_function(
        self,
        client: pyrogram.Client,
        message: pyrogram.types.Message,
        handler: BaseHandler,
        db_from_user: graph_models.vertices.User,
        from_callback_query: bool,
    ) -> None:
        data = HelpData(
            support_channel_username="support_channel_username",
            url1="https://github.com/appheap/TASE",
            url2="https://github.com/appheap/TASE",
            lang_code=db_from_user.chosen_language_code,
        )

        markup = [
            [
                InlineButton.get_button("download_history").get_inline_keyboard_button(
                    db_from_user.chosen_language_code
                ),
                InlineButton.get_button("my_playlists").get_inline_keyboard_button(db_from_user.chosen_language_code),
            ],
            [
                InlineButton.get_button("back").get_inline_keyboard_button(db_from_user.chosen_language_code),
            ],
            [
                InlineButton.get_button("advertisement").get_inline_keyboard_button(db_from_user.chosen_language_code),
                InlineButton.get_button("help_catalog").get_inline_keyboard_button(db_from_user.chosen_language_code),
            ],
        ]
        markup = InlineKeyboardMarkup(markup)

        client.send_message(
            chat_id=message.from_user.id,
            text=BaseTemplate.registry.help_template.render(data),
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
