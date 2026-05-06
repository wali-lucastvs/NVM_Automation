from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from lxml import etree

from .config import VersionProfile


class ArxmlValidator:
    """Optional XSD-backed validation entry point for generated ARXML."""

    def validate(
        self,
        xml_text: str,
        version: VersionProfile,
    ) -> None:
        xsd_path = Path(version.xsd)
        if not xsd_path.exists():
            raise FileNotFoundError(f"XSD for selected version not found: {xsd_path}")

        schema_doc = etree.parse(str(xsd_path))
        schema = etree.XMLSchema(schema_doc)
        validation_doc = self._build_validation_document(xml_text)

        schema_root = schema_doc.getroot()
        if not schema_root.get("targetNamespace"):
            validation_doc = self._strip_namespaces_for_validation(validation_doc)

        try:
            schema.assertValid(validation_doc)
        except etree.DocumentInvalid as exc:
            raise RuntimeError(f"ARXML does not conform to XSD: {exc}") from exc

    @staticmethod
    def _build_validation_document(rendered: str) -> etree._ElementTree:
        parser = etree.XMLParser(remove_blank_text=True)
        return etree.fromstring(rendered.encode("utf-8"), parser)

    @staticmethod
    def _strip_namespaces_for_validation(document: etree._ElementTree) -> etree._ElementTree:
        normalized = deepcopy(document)
        for element in normalized.iter():
            if isinstance(element.tag, str) and element.tag.startswith("{"):
                element.tag = element.tag.split("}", 1)[1]
            element.attrib.clear()
        etree.cleanup_namespaces(normalized)
        return normalized
