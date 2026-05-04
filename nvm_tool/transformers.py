from __future__ import annotations

from typing import Any, Iterable, Mapping

from .models import NvMBlock


class NvMBlockTransformer:
    """Translate external input records into the internal NvMBlock model."""

    @staticmethod
    def from_input_record(record: Mapping[str, Any]) -> NvMBlock:
        return NvMBlock.from_mapping(record)

    @classmethod
    def from_input_records(cls, records: Iterable[Mapping[str, Any]]) -> list[NvMBlock]:
        return [cls.from_input_record(record) for record in records]

    @staticmethod
    def from_arxml_container(
        short_name: str,
        parameter_values: Mapping[str, str],
    ) -> NvMBlock:
        return NvMBlock.from_arxml_values(short_name, parameter_values)
