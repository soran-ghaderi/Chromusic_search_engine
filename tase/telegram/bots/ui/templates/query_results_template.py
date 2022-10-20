import textwrap
from datetime import timedelta, datetime
from typing import Dict, List

from jinja2 import Template

from tase.common.preprocessing import clean_audio_item_text
from tase.common.utils import _trans
from tase.db.arangodb import graph as graph_models
from tase.db.elasticsearchdb import models as elasticsearch_models
from .base_template import BaseTemplate, BaseTemplateData


class QueryResultsTemplate(BaseTemplate):
    name = "query_results_template"

    template = Template(
        "<b>{{emoji._search_emoji}} {{s_search_results_for}} {{query}}</b>"
        "{{c_new_line}}"
        "{{emoji._checkmark_emoji}} {{s_better_results}}"
        "{{c_new_line}}"
        "{{c_new_line}}"
        "{{c_new_line}}"
        "{% for item in items %}"
        "{{c_dir}}<b>{{item.index}}. {{c_dir}}{{emoji._headphone_emoji}} </b><b>{{item.name}}</b>"
        "{{c_new_line}}"
        "{{c_dir}}      {{emoji._floppy_emoji}} {{item.file_size}} {{s_MB}} | {{c_dir}}{{emoji._clock_emoji}} {{item.time}}{{c_dir}} | {{emoji._cd}} {{item.quality_string}}"
        "{{c_new_line}}"
        "{{c_dir}}       {{s_download}} /dl_{{item.url}}"
        "{{c_new_line}}"
        "{{c_dir}}{{item.sep}}"
        "{{c_new_line}}"
        "{{c_new_line}}"
        "{% endfor %}"
    )


class QueryResultsData(BaseTemplateData):
    query: str
    items: list[dict]

    s_search_results_for: str = _trans("Search results for:")
    s_better_results: str = _trans("Better results are at the bottom of the list")
    s_download: str = _trans("Download:")
    s_MB: str = _trans("MB")

    @classmethod
    def process_item(
        cls,
        index: int,
        es_audio_doc: elasticsearch_models.Audio,
        hit: graph_models.vertices.Hit,
    ) -> Dict[str, str]:
        duration = timedelta(seconds=es_audio_doc.duration if es_audio_doc.duration else 0)
        d = datetime(1, 1, 1) + duration
        _performer = clean_audio_item_text(es_audio_doc.raw_performer)
        _title = clean_audio_item_text(es_audio_doc.raw_title)
        _file_name = clean_audio_item_text(
            es_audio_doc.raw_file_name,
            is_file_name=True,
            remove_file_extension_=True,
        )
        if _title is None:
            _title = ""
        if _performer is None:
            _performer = ""
        if _file_name is None:
            _file_name = ""

        if len(_title) >= 2 and len(_performer) >= 2:
            name = f"{_performer} - {_title}"
        elif len(_performer) >= 2:
            name = f"{_performer} - {_file_name}"
        elif len(_title) >= 2:
            name = _title
        else:
            name = _file_name

        return {
            "index": f"{index + 1:02}",
            "name": textwrap.shorten(name, width=35, placeholder="..."),
            "file_size": round(es_audio_doc.file_size / 1_048_576, 1),
            "time": f"{str(d.hour) + ':' if d.hour > 0 else ''}{d.minute:02}:{d.second:02}" if duration else "",
            "url": hit.download_url,
            "sep": f"{40 * '-' if index != 0 else ''}",
            "quality_string": es_audio_doc.estimated_bit_rate_type.get_bit_rate_string(),
        }

    @classmethod
    def parse_from_query(
        cls,
        query: str,
        lang_code: str,
        es_audio_docs: List[elasticsearch_models.Audio],
        hits: List[graph_models.vertices.Hit],
    ):
        items = [
            cls.process_item(index, es_audio_doc, db_hit)
            for index, (es_audio_doc, db_hit) in reversed(
                list(
                    enumerate(
                        # filter(
                        #     lambda args: args[0].title is not None,
                        #     zip(db_audio_docs, hits),
                        # )
                        zip(es_audio_docs, hits),
                    )
                )
            )
        ]

        return QueryResultsData(
            query=query,
            items=items,
            lang_code=lang_code,
        )
