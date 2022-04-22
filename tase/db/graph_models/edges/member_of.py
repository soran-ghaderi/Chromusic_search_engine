from typing import Optional

from .base_edge import BaseEdge
from ..vertices import User, Chat


class MemberOf(BaseEdge):
    """
    Connection from `User` to `Chat`.
    """

    _collection_edge_name = 'member_of'

    @staticmethod
    def parse_from_user_and_chat(user: 'User', chat: 'Chat') -> Optional['MemberOf']:
        if chat is None or user is None:
            return None

        key = f'{user.key}:{chat.key}'
        return MemberOf(
            key=key,
            from_node=user,
            to_node=chat,
        )