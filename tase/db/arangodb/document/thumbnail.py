from __future__ import annotations

from typing import Optional

import pyrogram

from aioarango.models import PersistentIndex
from tase.my_logger import logger
from .base_document import BaseDocument
from ...db_utils import parse_thumbnail_document_key


class Thumbnail(BaseDocument):
    """
    Represents the information about the thumbnail of an audio file.

    Attributes
    ----------
    telegram_client_id : int
        ID of the telegram client that uploaded this thumbnail photo.
    thumbnail_file_unique_id : str
        File unique ID of the original thumbnail.
    photo_file_unique_id : str
        File unique ID of the uploaded photo.
    photo_file_id : str
        ID of the uploaded thumbnail which is used for accessing it on telegram servers.
    archive_chat_id : int
        ID of the chat where the photo was uploaded.
    archive_message_id : int
        ID of the message which the photo belongs to.
    """

    __collection_name__ = "doc_thumbnails"
    schema_version = 1
    __indexes__ = [
        PersistentIndex(
            custom_version=1,
            name="telegram_client_id",
            fields=[
                "telegram_client_id",
            ],
        ),
        PersistentIndex(
            custom_version=1,
            name="thumbnail_file_unique_id",
            fields=[
                "thumbnail_file_unique_id",
            ],
        ),
        PersistentIndex(
            custom_version=1,
            name="photo_file_unique_id",
            fields=[
                "photo_file_unique_id",
            ],
        ),
        PersistentIndex(
            custom_version=1,
            name="photo_file_id",
            fields=[
                "photo_file_id",
            ],
        ),
        PersistentIndex(
            custom_version=1,
            name="archive_chat_id",
            fields=[
                "archive_chat_id",
            ],
        ),
        PersistentIndex(
            custom_version=1,
            name="archive_message_id",
            fields=[
                "archive_message_id",
            ],
        ),
    ]

    telegram_client_id: int

    thumbnail_file_unique_id: str
    photo_file_unique_id: str
    photo_file_id: str

    # These attributes show the uploaded photo message information.
    archive_chat_id: int
    archive_message_id: int

    @classmethod
    def parse_key(
        cls,
        telegram_client_id: int,
        telegram_uploaded_photo_message: pyrogram.types.Message,
    ) -> Optional[str]:
        if telegram_client_id is None or not telegram_uploaded_photo_message:
            return None

        return parse_thumbnail_document_key(
            telegram_client_id,
            telegram_uploaded_photo_message.chat.id,
            telegram_uploaded_photo_message.id,
        )

    @classmethod
    def parse(
        cls,
        telegram_client_id: int,
        thumbnail_file_unique_id: str,
        telegram_uploaded_photo_message: pyrogram.types.Message,
    ) -> Optional[Thumbnail]:
        if telegram_client_id is None or not thumbnail_file_unique_id or not telegram_uploaded_photo_message or not telegram_uploaded_photo_message.photo:
            return None

        photo = telegram_uploaded_photo_message.photo

        key = cls.parse_key(telegram_client_id, telegram_uploaded_photo_message)
        if not key:
            return None

        return Thumbnail(
            key=key,
            telegram_client_id=telegram_client_id,
            photo_file_unique_id=photo.file_unique_id,
            thumbnail_file_unique_id=thumbnail_file_unique_id,
            photo_file_id=photo.file_id,
            archive_chat_id=telegram_uploaded_photo_message.chat.id,
            archive_message_id=telegram_uploaded_photo_message.id,
        )


class ThumbnailMethods:
    async def create_thumbnail_document(
        self,
        telegram_client_id: int,
        thumbnail_file_unique_id: str,
        telegram_uploaded_photo_message: pyrogram.types.Message,
    ) -> Optional[Thumbnail]:
        """
        Create a thumbnail from the given arguments.

        Parameters
        ----------
        telegram_client_id : int
            ID of the telegram client uploading this thumbnail.
        thumbnail_file_unique_id : str
            File unique ID of the telegram thumbnail object to use for creating the thumbnail object.
        telegram_uploaded_photo_message : pyrogram.types.Message
            Telegram message to use for creating the thumbnail object.

        Returns
        -------
        Thumbnail, optional
            Created Thumbnail document if the operation was successful, otherwise return `None`.
        """
        try:
            thumbnail, successful = await Thumbnail.insert(
                Thumbnail.parse(
                    telegram_client_id=telegram_client_id,
                    thumbnail_file_unique_id=thumbnail_file_unique_id,
                    telegram_uploaded_photo_message=telegram_uploaded_photo_message,
                )
            )
        except Exception as e:
            logger.exception(e)
        else:
            if thumbnail and successful:
                return thumbnail

        return None

    async def get_or_create_thumbnail_document(
        self,
        telegram_client_id: int,
        thumbnail_file_unique_id: str,
        telegram_uploaded_photo_message: pyrogram.types.Message,
    ) -> Optional[Thumbnail]:
        """
        Get a thumbnail from the given arguments if it exists in the database, otherwise create it.

        Parameters
        ----------
        telegram_client_id : int
            ID of the telegram client uploading this thumbnail.
        thumbnail_file_unique_id : str
            File unique ID of the telegram thumbnail object to use for creating the thumbnail object.
        telegram_uploaded_photo_message : pyrogram.types.Message
            Telegram message to use for creating or getting the thumbnail object.

        Returns
        -------
        Thumbnail, optional
            Thumbnail document if the operation was successful, otherwise return `None`.
        """
        thumbnail = await Thumbnail.get(Thumbnail.parse_key(telegram_client_id, telegram_uploaded_photo_message))
        if not thumbnail:
            thumbnail = await self.create_thumbnail_document(
                telegram_client_id=telegram_client_id,
                thumbnail_file_unique_id=thumbnail_file_unique_id,
                telegram_uploaded_photo_message=telegram_uploaded_photo_message,
            )

        return thumbnail
