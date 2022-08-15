from .inline_button import InlineButton
from tase.utils import _trans, emoji


class AdvertisementInlineButton(InlineButton):
    name = "advertisement"

    s_advertisement = _trans("Advertisement")
    text = f"{s_advertisement} | {emoji._chart_increasing}{emoji._bar_chart}"
    url = "https://t.me/advertisement_channel_username"