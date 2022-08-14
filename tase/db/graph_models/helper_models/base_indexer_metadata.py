from pydantic import BaseModel, Field


class BaseIndexerMetadata(BaseModel):
    """
    This class is used to store indexer metadata and is not vertex by itself
    """

    score: float = Field(default=0.0)
    last_message_offset_id: int = Field(default=1)
    last_message_offset_date: int = Field(default=0)
    message_count: int = Field(default=0)

    def reset_counters(self):
        self.message_count = 0

    def update_score(self):
        raise NotImplementedError

    def update_metadata(self, metadata: "BaseIndexerMetadata") -> "BaseIndexerMetadata":
        if metadata is None or not isinstance(metadata, BaseIndexerMetadata):
            return self

        self.message_count += metadata.message_count

        if self.last_message_offset_id < metadata.last_message_offset_id:
            self.last_message_offset_id = metadata.last_message_offset_id
            self.last_message_offset_date = metadata.last_message_offset_date

        return self
