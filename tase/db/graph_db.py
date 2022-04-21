from typing import Optional

import pyrogram
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.graph import Graph

from .graph_models.edges import FileRef, ArchivedAudio, SenderChat, LinkedChat, ContactOf, Creator, Downloaded, \
    DownloadedAudio, DownloadedFromBot
from .graph_models.vertices import Audio, Chat, File, User, Download
from ..my_logger import logger


class GraphDatabase:
    arango_client: 'ArangoClient'
    db: 'StandardDatabase'
    graph: 'Graph'

    def __init__(
            self,
            graph_db_config: dict,
    ):
        # Initialize the client for ArangoDB.
        self.arango_client = ArangoClient(hosts=graph_db_config.get('db_host_url'))
        sys_db = self.arango_client.db(
            '_system',
            username=graph_db_config.get('db_username'),
            password=graph_db_config.get('db_password')
        )

        if not sys_db.has_database(graph_db_config.get('db_name')):
            sys_db.create_database(
                graph_db_config.get('db_name'),
            )

        self.db = self.arango_client.db(
            graph_db_config.get('db_name'),
            username=graph_db_config.get('db_username'),
            password=graph_db_config.get('db_password')
        )

        if not self.db.has_graph(graph_db_config.get('graph_name')):
            self.graph = self.db.create_graph(graph_db_config.get('graph_name'))

            self.files = self.graph.create_vertex_collection(File._vertex_name)
            self.audios = self.graph.create_vertex_collection(Audio._vertex_name)
            self.chats = self.graph.create_vertex_collection(Chat._vertex_name)
            self.users = self.graph.create_vertex_collection(User._vertex_name)
            self.downloads = self.graph.create_vertex_collection(Download._vertex_name)

            self.archived_audio = self.graph.create_edge_definition(
                edge_collection=ArchivedAudio._collection_edge_name,
                from_vertex_collections=[Audio._vertex_name],
                to_vertex_collections=[Audio._vertex_name],
            )
            self.contact_of = self.graph.create_edge_definition(
                edge_collection=ContactOf._collection_edge_name,
                from_vertex_collections=[User._vertex_name],
                to_vertex_collections=[User._vertex_name],
            )
            self.creator = self.graph.create_edge_definition(
                edge_collection=Creator._collection_edge_name,
                from_vertex_collections=[Chat._vertex_name],
                to_vertex_collections=[User._vertex_name],
            )
            self.downloaded = self.graph.create_edge_definition(
                edge_collection=Downloaded._collection_edge_name,
                from_vertex_collections=[User._vertex_name],
                to_vertex_collections=[Download._vertex_name],
            )
            self.downloaded_audio = self.graph.create_edge_definition(
                edge_collection=DownloadedAudio._collection_edge_name,
                from_vertex_collections=[Download._vertex_name],
                to_vertex_collections=[Audio._vertex_name],
            )
            self.downloaded_from_bot = self.graph.create_edge_definition(
                edge_collection=DownloadedFromBot._collection_edge_name,
                from_vertex_collections=[Download._vertex_name],
                to_vertex_collections=[User._vertex_name],
            )
            self.file_ref = self.graph.create_edge_definition(
                edge_collection=FileRef._collection_edge_name,
                from_vertex_collections=[Audio._vertex_name],
                to_vertex_collections=[File._vertex_name],
            )
            self.linked_chat = self.graph.create_edge_definition(
                edge_collection=LinkedChat._collection_edge_name,
                from_vertex_collections=[Chat._vertex_name],
                to_vertex_collections=[Chat._vertex_name],
            )
            self.sender_chat = self.graph.create_edge_definition(
                edge_collection=SenderChat._collection_edge_name,
                from_vertex_collections=[Audio._vertex_name],
                to_vertex_collections=[Chat._vertex_name],
            )

        else:
            self.graph = self.db.graph(graph_db_config.get('graph_name'))

            self.files = self.graph.vertex_collection(File._vertex_name)
            self.audios = self.graph.vertex_collection(Audio._vertex_name)
            self.chats = self.graph.vertex_collection(Chat._vertex_name)
            self.users = self.graph.vertex_collection(User._vertex_name)
            self.downloads = self.graph.vertex_collection(Download._vertex_name)

            self.archived_audio = self.graph.edge_collection(ArchivedAudio._collection_edge_name)
            self.contact_of = self.graph.edge_collection(ContactOf._collection_edge_name)
            self.creator = self.graph.edge_collection(Creator._collection_edge_name)
            self.downloaded = self.graph.edge_collection(Downloaded._collection_edge_name)
            self.downloaded_audio = self.graph.edge_collection(DownloadedAudio._collection_edge_name)
            self.downloaded_from_bot = self.graph.edge_collection(DownloadedFromBot._collection_edge_name)
            self.file_ref = self.graph.edge_collection(FileRef._collection_edge_name)
            self.linked_chat = self.graph.edge_collection(LinkedChat._collection_edge_name)
            self.sender_chat = self.graph.edge_collection(SenderChat._collection_edge_name)

    def create_audio(self, message: 'pyrogram.types.Message') -> Optional['Audio']:
        if message is None or message.audio is None:
            return None

        if not self.audios.has(Audio.get_key(message)):
            audio = Audio.parse_from_message(message)
            if audio:
                metadata = self.audios.insert(audio.parse_for_graph())
                logger.info(metadata)
                audio.update_from_metadata(metadata)

                if self.files.has(audio.file_unique_id):
                    file = File.parse_from_graph(self.files.get(audio.file_unique_id))
                    if file:
                        file_ref = FileRef.parse_from_audio_and_file(audio, file)
                        if file_ref:
                            file_ref_metadata = self.file_ref.insert(file_ref.parse_for_graph())
                            file_ref.update_from_metadata(file_ref_metadata)
                        else:
                            pass
                else:
                    file = File.parse_from_audio(message.audio)
                    if file:
                        file_metadata = self.files.insert(file.parse_for_graph())
                        file.update_from_metadata(file_metadata)

                        if not self.file_ref.find({'_from': audio.id, '_to': file.id}):
                            file_ref = FileRef.parse_from_audio_and_file(audio, file)
                            if file_ref:
                                file_ref_metadata = self.file_ref.insert(file_ref.parse_for_graph())
                                file_ref.update_from_metadata(file_ref_metadata)
                        else:
                            pass
                    else:
                        pass

            logger.info(audio)