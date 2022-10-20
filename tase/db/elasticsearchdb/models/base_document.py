from __future__ import annotations

import time
from enum import Enum
from typing import Optional, Tuple, TypeVar, Dict, Any, Type, List

import elasticsearch
from elastic_transport import ObjectApiResponse
from elasticsearch import ConflictError, Elasticsearch, NotFoundError
from pydantic import BaseModel, Field, ValidationError

from tase.common.utils import get_now_timestamp
from tase.db.arangodb.helpers import ElasticQueryMetadata
from tase.db.helpers import SearchMetaData
from tase.my_logger import logger

TBaseDocument = TypeVar("TBaseDocument", bound="BaseDocument")


class ToDocumentBaseProcessor(BaseModel):
    @classmethod
    def process(
        cls,
        document: TBaseDocument,
        attr_value_dict: Dict[str, Any],
    ) -> None:
        """
        Execute some operations on the attribute value dictionary.

        Parameters
        ----------
        document : TBaseDocument
            Document this processing is done for
        attr_value_dict : dict
            Attribute value mapping dictionary to be processed

        Raises
        ------
        Exception
            if there was any error with processing
        """
        raise NotImplementedError


class FromDocumentBaseProcessor(BaseModel):
    @classmethod
    def process(
        cls,
        document_class: Type[TBaseDocument],
        body: dict,
        response: Optional[ObjectApiResponse],
        hit: Optional[dict],
    ) -> None:
        """
        Execute some operations on the attribute value dictionary.

        Parameters
        ----------
        document_class : Type[TBaseDocument]
            Class of this document. (It's not an instance of the class)
        body : dict
            Dictionary to put the new attributes into
        response : ObjectApiResponse, optional
            Attribute value mapping dictionary to be processed
        hit : dict, optional
            Hit dictionary from the search

        Raises
        ------
        Exception
            if there was any error with processing
        """
        raise NotImplementedError


##########################################################################################
class ToDocumentAttributeMapper(ToDocumentBaseProcessor):
    """
    Prepare the attribute value mapping to be saved into the database.
    """

    @classmethod
    def process(
        cls,
        document: TBaseDocument,
        attr_value_dict: Dict[str, Any],
    ) -> None:
        for obj_attr in document._to_db_mapping:
            del attr_value_dict[obj_attr]


class ToDocumentEnumConverter(ToDocumentBaseProcessor):
    """
    Convert enum types to their values because `Enum` types cannot be directly saved into ElasticSearch.

    """

    @classmethod
    def process(
        cls,
        document: TBaseDocument,
        attr_value_dict: Dict[str, Any],
    ) -> None:
        for attr_name, attr_value in attr_value_dict.copy().items():
            attr_value = getattr(document, attr_name, None)
            if attr_value:
                if isinstance(attr_value, Enum):
                    attr_value_dict[attr_name] = attr_value.value


class FromDocumentAttributeMapper(FromDocumentBaseProcessor):
    """
    Prepare the attribute value mapping from graph to be converted into a python object.
    """

    @classmethod
    def process(
        cls,
        document_class: Type[TBaseDocument],
        body: dict,
        response: Optional[ObjectApiResponse],
        hit: Optional[dict],
    ) -> None:
        if body is None or (response is None and hit is None):
            return

        if response is not None:
            body.update(**response.body["_source"])
            body.update({"id": response.body["_id"]})
        else:
            body.update(**hit["_source"])
            body.update({"id": hit["_id"]})


##########################################################################################


class BaseDocument(BaseModel):
    schema_version: int = Field(default=1)

    _es: Optional[Elasticsearch]

    _index_name = "base_index_name"
    _mappings = {}

    _to_db_mapping = ("id", "search_metadata")
    _search_fields: List[str] = []

    _to_index_base_processors: Optional[Tuple[ToDocumentBaseProcessor]] = (
        ToDocumentEnumConverter,
        ToDocumentAttributeMapper,
    )
    _to_index_extra_processors: Optional[Tuple[ToDocumentBaseProcessor]] = None

    _from_index_base_processors: Optional[Tuple[FromDocumentBaseProcessor]] = (FromDocumentAttributeMapper,)
    _from_index_extra_processors: Optional[Tuple[FromDocumentBaseProcessor]] = None

    _base_do_not_update_fields: Optional[Tuple[str]] = ("created_at",)
    _extra_do_not_update_fields: Optional[Tuple[str]] = None

    id: Optional[str]

    created_at: int = Field(default_factory=get_now_timestamp)
    modified_at: int = Field(default_factory=get_now_timestamp)

    search_metadata: Optional[SearchMetaData]

    def to_index(self) -> Tuple[Optional[str], Optional[dict]]:
        """
        Convert the object to a dictionary to be saved into the ElasticSearch.

        Returns
        -------
        tuple
            Tuple of the document ID and dictionary mapping attribute names to attribute values

        """
        attr_value_dict = self.dict()

        for attrib_processor in self._to_index_base_processors:
            try:
                attrib_processor.process(self, attr_value_dict)
            except Exception as e:
                return None, None

        if self._to_index_extra_processors is not None:
            for doc_processor in self._to_index_extra_processors:
                try:
                    doc_processor.process(self, attr_value_dict)
                except Exception as e:
                    return None, None

        return self.id, attr_value_dict

    @classmethod
    def from_index(
        cls,
        response: Optional[ObjectApiResponse] = None,
        hit: Optional[dict] = None,
        rank: Optional[int] = None,
    ) -> Optional[TBaseDocument]:
        """
        Convert a database document dictionary to be converted into a python object.

        Parameters
        ----------
        doc : dict
            Dictionary mapping attribute names to attribute values
        response : ObjectApiResponse, optional
            Attribute value mapping dictionary to be processed
        hit : dict, optional
            Hit dictionary from the search
        rank : int, optional
            Rank of the hit in the query

        Returns
        -------
        TBaseDocument, optional
            Python object converted from the database document dictionary

        Raises
        ------
        ValueError
            If `response` or `hit` parameter is not passed to this function or both of them are None
        """
        is_hit = False
        if response is not None:
            if not len(response.body):
                return None
        elif hit is not None:
            if not len(hit) or not len(hit["_source"]) or rank is None:
                return None

            is_hit = True
        else:
            raise ValueError("either `response` or `hit` parameter must be passed to this method")

        body = dict()
        for doc_processor in cls._from_index_base_processors:
            try:
                doc_processor.process(cls, body, response, hit)
            except Exception as e:
                return None

        if cls._from_index_extra_processors is not None:
            for doc_processor in cls._from_index_extra_processors:
                try:
                    doc_processor.process(cls, body, response, hit)
                except Exception as e:
                    return None

        try:
            obj = cls(**body)
        except ValidationError as e:
            # Attribute value mapping cannot be validated, and it cannot be converted to a python object
            logger.debug(e.json())
        except Exception as e:
            # todo: check if this happens
            logger.exception(e)
        else:
            if is_hit:
                obj.search_metadata = SearchMetaData(
                    rank=rank,
                    score=hit.get("_score", None) or 0.0,
                )
            return obj

        return None

    def _update_non_updatable_fields(
        self,
        old_doc: TBaseDocument,
    ) -> TBaseDocument:
        """
        Update the non-updatable field values of a document from an old document

        Parameters
        ----------
        old_doc : TBaseDocument
            Document to update the fields from

        Returns
        -------
        TBaseDocument
            Updated document

        """
        for field_name in self._base_do_not_update_fields:
            setattr(self, field_name, getattr(old_doc, field_name, None))

        if self._extra_do_not_update_fields is not None:
            for field_name in self._extra_do_not_update_fields:
                setattr(self, field_name, getattr(old_doc, field_name, None))

        return self

    @classmethod
    def has_index(
        cls,
    ) -> bool:
        """
        Check if an index exists in the ElasticSearch.

        Returns
        -------
        bool
            Whether the Index exists in the ElasticSearch or not

        """
        index_exists = False
        try:
            cls._es.indices.get(index=cls._index_name)
            index_exists = True
        except NotFoundError as e:
            index_exists = False
        except Exception as e:
            index_exists = False
            logger.exception(e)
        return index_exists

    @classmethod
    def create_index(
        cls,
    ) -> bool:
        """
        Create the index in the ElasticSearch

        Returns
        -------
        bool
            Whether the index was created or not
        """
        try:
            cls._es.indices.create(
                index=cls._index_name,
                mappings=cls._mappings,
            )
        except Exception as e:
            raise e
        else:
            return True

    @classmethod
    def get(
        cls,
        doc_id: str,
    ) -> Optional[TBaseDocument]:
        """
        Get a document in a collection by its `ID`

        Parameters
        ----------
        doc_id : str
            ID of the document in the index

        Returns
        -------
        TBaseDocument, optional
            Document matching the specified `ID` if it exists in the index, otherwise return `None`

        """
        obj = None
        try:
            response = cls._es.get(
                index=cls._index_name,
                id=doc_id,
            )
            obj = cls.from_index(response=response)
        except NotFoundError as e:
            # audio does not exist in the index
            pass
        except ValueError as e:
            # happen when the `hit` is None
            pass
        except Exception as e:
            logger.exception(f"{cls.__name__} : {e}")
        return obj

    @classmethod
    def create(
        cls: Type[TBaseDocument],
        document: TBaseDocument,
    ) -> Tuple[Optional[TBaseDocument], bool]:
        """
        Insert an object into the ElasticSearch

        Parameters
        ----------
        document : TBaseDocument
            Object to inserted into the ElasticSearch

        Returns
        -------
        tuple
            Document object with returned metadata from ElasticSearch and `True` if the operation was successful,
            otherwise return `None` and `False`.
        """
        if document is None:
            return None, False

        if not isinstance(document, BaseDocument):
            raise Exception(f"`document` is not an instance of {BaseDocument.__class__.__name__} class")

        successful = False
        try:
            id, doc = document.to_index()
            if id and doc:
                response = cls._es.create(
                    index=cls._index_name,
                    id=id,
                    document=doc,
                )
                successful = True
        except ConflictError as e:
            # Exception representing a 409 status code. Document exists in the index
            logger.exception(f"{cls.__name__} : {e}")
        except Exception as e:
            logger.exception(f"{cls.__name__} : {e}")

        return document, successful

    def update(
        self,
        document: TBaseDocument,
        reserve_non_updatable_fields: bool = True,
        retry_on_failure: bool = True,
        run_depth: int = 1,
    ) -> bool:
        """
        Update a document in the database

        Parameters
        ----------
        document : TBaseDocument
            Document used for updating the old document in the database
        reserve_non_updatable_fields : bool, default: True
            Whether to keep the non-updatable fields from the old document or not
        retry_on_failure : bool, default : True
            Whether to retry the operation if it fails due to `revision` mismatch
        run_depth : int
            Depth of running the function. stop and return False after 10 runs.

        Returns
        -------
        bool
            Whether the update was successful or not

        """
        if document is None:
            return False

        if not isinstance(document, BaseDocument):
            raise Exception(f"`document` is not an instance of {BaseDocument.__class__.__name__} class")

        if retry_on_failure and run_depth > 10:
            logger.error(f"{self.__class__.__name__}: `{self.id}` : failed after 10 retries")
            # stop if the update is retried for 10 times
            return False

        successful = False
        try:
            if reserve_non_updatable_fields:
                id, doc = document._update_non_updatable_fields(self).to_index()
            else:
                id, doc = document.to_index()

            if id and doc:
                doc["modified_at"] = get_now_timestamp()

                response = self._es.update(
                    index=self._index_name,
                    id=id,
                    doc=doc,
                )
                self.__dict__.update(document.__dict__)
        except elasticsearch.ConflictError as e:
            logger.error(f"{self.__class__.__name__}: `{self.id}` : elasticsearch.ConflictError")
            if retry_on_failure:
                logger.error(f"Retry #{run_depth}")
                # todo: sleep for a while before retrying
                time.sleep(run_depth * 20 / 1000)

                latest_doc = self.get(self.id)
                if latest_doc is not None:
                    successful = latest_doc.update(
                        document,
                        reserve_non_updatable_fields=reserve_non_updatable_fields,
                        retry_on_failure=retry_on_failure,
                        run_depth=run_depth + 1,
                    )
                    if successful:
                        self.__dict__.update(latest_doc.__dict__)
        except Exception as e:
            logger.exception(f"{self.__class__.__name__} : {e}")
        else:
            successful = True

        return successful

    @classmethod
    def search(
        cls,
        query: str,
        from_: int = 0,
        size: int = 10,
        filter_by_valid_for_inline_search: Optional[bool] = True,
    ) -> Tuple[Optional[List[TBaseDocument]], Optional[ElasticQueryMetadata]]:
        """
        Search among the documents with the given query

        Parameters
        ----------
        query : str
            Query string to search for
        from_ : int, default : 0
            Number of documents to skip in the query
        size : int, default : 50
            Number of documents to return
        filter_by_valid_for_inline_search : bool, default: True
            Whether to filter documents by the validity to be shown in inline search of telegram


        Returns
        -------
        tuple
            List of documents matching the query alongside the query metadata

        """
        if query is None or from_ is None or size is None:
            return None, None

        db_docs = []
        try:
            res: ObjectApiResponse = cls._es.search(
                index=cls._index_name,
                from_=from_,
                size=size,
                query=cls.get_query(query, filter_by_valid_for_inline_search),
                sort=cls.get_sort(),
            )

            hits = res.body["hits"]["hits"]

            duration = res.meta.duration
            total_hits = res.body["hits"]["total"]["value"] or 0
            total_rel = res.body["hits"]["total"]["relation"]
            max_score = res.body["hits"]["max_score"] or 0

            query_metadata = {
                "duration": duration,
                "total_hits": total_hits,
                "total_rel": total_rel,
                "max_score": max_score,
            }

            query_metadata = ElasticQueryMetadata.parse(query_metadata)

            for index, hit in enumerate(hits, start=1):
                try:
                    db_doc = cls.from_index(
                        hit=hit,
                        rank=len(hits) - index + 1,
                    )
                except ValueError:
                    # fixme: happens when the `hit` is None
                    pass
                else:
                    db_docs.append(db_doc)

        except Exception as e:
            logger.exception(e)

        else:
            return db_docs, query_metadata

        return None, None

    @classmethod
    def get_query(
        cls,
        query: Optional[str],
        filter_by_valid_for_inline_search: Optional[bool] = True,
    ) -> dict:
        """
        Get the query for this index

        Parameters
        ----------
        query : str, optional
            Query string to search for
        filter_by_valid_for_inline_search : bool, default : True
            Whether to filter documents by the validity to be shown in inline search of telegram

        Returns
        -------
        dict
            Dictionary defining how the query should be made

        """
        return {
            "multi_match": {
                "query": query,
                "fuzziness": "AUTO",
                "type": "best_fields",
                "minimum_should_match": "60%",
                "fields": cls._search_fields,
            },
        }

    @classmethod
    def get_sort(cls) -> Optional[dict]:
        """
        Get sort dictionary for this query

        Returns
        -------
        dict, optional
            Dictionary defining how the query results should be sorted
        """
        return None

    ######################################################################
    @classmethod
    def parse(
        cls: Type[TBaseDocument],
        *args,
        **kwargs,
    ) -> Optional[TBaseDocument]:
        """
        Parse a subclass of `BaseDocument` document from given arguments and keyword arguments

        Parameters
        ----------
        args : tuple
            List of arguments
        kwargs : dict, optional
            Dictionary of keyword arguments

        Returns
        -------
        TBaseDocument, optional
            Document object if parsing was successful, otherwise, return `None`.

        Raises
        ------
        NotImplementedError
            If the `class` calling this or any of superclasses haven't implemented this method.
        """
        raise NotImplementedError

    @classmethod
    def parse_id(
        cls: Type[TBaseDocument],
        *args,
        **kwargs,
    ) -> Optional[str]:
        """
        Parse an ID from the given arguments and keyword arguments

        Parameters
        ----------
        args : tuple
            List of arguments
        kwargs : dict, optional
            List of keyword arguments

        Returns
        -------
        str, optional
            ID string if parsing was successful, otherwise, return `None`.

        Raises
        ------
        NotImplementedError
            If the `class` calling this or any of superclasses haven't implemented this method.
        """
        raise NotImplementedError
