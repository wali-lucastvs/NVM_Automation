from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Union, Tuple
from xml.etree import ElementTree as ET

from .models import (
    NvMBlock, 
    ParsedArxmlDocument, 
    AUTOSAR_NAMESPACE, 
    NVM_MODULE_DEFINITION_REF,
    NVM_BLOCK_CONTAINER_DEFINITION_REF
)


class NvMConfigParser:
    """Parses JSON or Excel NvM block input into NvMBlock objects."""

    REQUIRED_FIELDS = {
        "block_name",
        "block_id",
        "block_size",
        "ram_block_name",
        "device",
        "block_management_type",
        "use_crc",
        "crc_type",
        "write_protection",
    }

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def parse_input_file(self, input_type: str, input_path: Path) -> List[NvMBlock]:
        """Wrapper to match the expected API in generate_nvm.py."""
        return self.parse_file(input_path)

    def parse_previous_arxml(self, arxml_path: Path) -> ParsedArxmlDocument:
        """Parses an existing ARXML to extract current NvM configurations."""
        if not arxml_path.exists():
            raise FileNotFoundError(f"Previous ARXML not found: {arxml_path}")

        tree = ET.parse(arxml_path)
        root = tree.getroot()
        
        # Handle Namespaces
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0].strip("{")
        
        ns = {"ns": namespace} if namespace else {}

        # Find NvM Module Configuration
        module_conf = None
        for elem in root.iter(f"{{{namespace}}}ECUC-MODULE-CONFIGURATION-VALUES" if namespace else "ECUC-MODULE-CONFIGURATION-VALUES"):
            def_ref = elem.find(f"{{{namespace}}}DEFINITION-REF" if namespace else "DEFINITION-REF")
            if def_ref is not None and def_ref.text == NVM_MODULE_DEFINITION_REF:
                module_conf = elem
                break

        if module_conf is None:
            raise ValueError(f"Could not find NvM configuration in {arxml_path}")

        containers_element = module_conf.find(f"{{{namespace}}}CONTAINERS" if namespace else "CONTAINERS")
        
        blocks = []
        if containers_element is not None:
            for container in containers_element.findall(f"{{{namespace}}}ECUC-CONTAINER-VALUE" if namespace else "ECUC-CONTAINER-VALUE"):
                def_ref = container.find(f"{{{namespace}}}DEFINITION-REF" if namespace else "DEFINITION-REF")
                if def_ref is not None and def_ref.text == NVM_BLOCK_CONTAINER_DEFINITION_REF:
                    short_name = container.find(f"{{{namespace}}}SHORT-NAME" if namespace else "SHORT-NAME").text
                    
                    params = {}
                    param_values = container.find(f"{{{namespace}}}PARAMETER-VALUES" if namespace else "PARAMETER-VALUES")
                    if param_values is not None:
                        for param in param_values:
                            p_def = param.find(f"{{{namespace}}}DEFINITION-REF" if namespace else "DEFINITION-REF").text
                            p_val = param.find(f"{{{namespace}}}VALUE" if namespace else "VALUE").text
                            params[p_def] = p_val
                    
                    try:
                        blocks.append(NvMBlock.from_arxml_values(short_name, params))
                    except Exception as e:
                        self.logger.warning("Skipping block '%s' in previous ARXML: %s", short_name, e)

        return ParsedArxmlDocument(
            tree=tree,
            root=root,
            namespace=namespace,
            module_configuration=module_conf,
            containers_element=containers_element,
            blocks=blocks
        )

    def parse_file(self, input_path: Union[str, Path]) -> List[NvMBlock]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        if path.is_dir():
            raise ValueError(f"Input path must be a file, not a directory: {path}")

        if path.suffix.lower() == ".json":
            records = self._read_json(path)
        elif path.suffix.lower() in {".xlsx", ".xlsm"}:
            records = self._read_excel(path)
        else:
            raise ValueError("Unsupported input file. Use .json, .xlsx, or .xlsm.")

        blocks = [self._record_to_block(record, index) for index, record in enumerate(records, start=1)]
        self._validate_unique_ids(blocks)
        self._validate_unique_generated_names(blocks)

        for block in blocks:
            if block.block_id < 2:
                self.logger.warning(
                    "Block '%s' uses block_id=%s. AUTOSAR typically reserves 0 and 1.",
                    block.block_name,
                    block.block_id,
                )

        sorted_blocks = sorted(blocks, key=lambda block: block.block_id)
        self.logger.info("Parsed %d NvM block(s) from %s.", len(sorted_blocks), path)
        return sorted_blocks

    def _record_to_block(self, record: Dict[str, Any], index: int) -> NvMBlock:
        missing = sorted(self.REQUIRED_FIELDS - set(record))
        if missing:
            raise ValueError(f"Record {index} is missing required fields: {', '.join(missing)}")

        try:
            return NvMBlock.from_mapping(record)
        except Exception as exc:  # noqa: BLE001 - keep parser error messages user friendly
            raise ValueError(f"Invalid NvM block in record {index}: {exc}") from exc

    def _read_json(self, path: Path) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}, column {exc.colno}."
            ) from exc

        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("blocks"), list):
            records = payload["blocks"]
        else:
            raise ValueError("JSON input must be a list of blocks or an object with a 'blocks' list.")

        if not records:
            raise ValueError("Input does not contain any NvM blocks.")

        normalized_records: List[Dict[str, Any]] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, Mapping):
                raise ValueError(f"Record {index} must be a JSON object.")
            normalized_records.append(dict(record))

        return normalized_records

    def _read_excel(self, path: Path) -> List[Dict[str, Any]]:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError(
                "Excel input requires openpyxl. Install it with 'pip install openpyxl'."
            ) from exc

        workbook = load_workbook(filename=path, read_only=True, data_only=True)
        try:
            worksheet = workbook.active
            rows = worksheet.iter_rows(values_only=True)

            try:
                headers = next(rows)
            except StopIteration as exc:
                raise ValueError("Excel input is empty.") from exc

            normalized_headers = [self._normalize_header(header) for header in headers]
            missing = sorted(self.REQUIRED_FIELDS - set(normalized_headers))
            if missing:
                raise ValueError(
                    "Excel header row is missing required columns: " + ", ".join(missing)
                )

            duplicate_headers = self._find_duplicate_headers(normalized_headers)
            if duplicate_headers:
                raise ValueError(
                    "Excel header row contains duplicate columns after normalization: "
                    + ", ".join(duplicate_headers)
                )

            records: List[Dict[str, Any]] = []
            for row in rows:
                if row is None or all(cell in (None, "") for cell in row):
                    continue

                record = {
                    normalized_headers[position]: cell
                    for position, cell in enumerate(row)
                    if position < len(normalized_headers) and normalized_headers[position]
                }
                records.append(record)

            if not records:
                raise ValueError("Excel input does not contain any NvM blocks.")

            return records
        finally:
            workbook.close()

    def _validate_unique_ids(self, blocks: List[NvMBlock]) -> None:
        seen: Dict[int, str] = {}
        for block in blocks:
            existing = seen.get(block.block_id)
            if existing is not None:
                raise ValueError(
                    f"Duplicate block_id {block.block_id} found for '{existing}' and '{block.block_name}'."
                )
            seen[block.block_id] = block.block_name

    def _validate_unique_generated_names(self, blocks: List[NvMBlock]) -> None:
        self._validate_unique_strings(
            blocks,
            lambda block: block.block_id_macro,
            "generated block ID macro",
        )
        self._validate_unique_strings(
            blocks,
            lambda block: block.short_name,
            "generated AUTOSAR short name",
        )

    @staticmethod
    def _validate_unique_strings(
        blocks: List[NvMBlock],
        selector: Callable[[NvMBlock], str],
        label: str,
    ) -> None:
        seen: Dict[str, str] = {}
        for block in blocks:
            value = selector(block)
            existing = seen.get(value)
            if existing is not None:
                raise ValueError(
                    f"Block names '{existing}' and '{block.block_name}' collide on the {label} "
                    f"'{value}'. Rename one of the blocks."
                )
            seen[value] = block.block_name

    @staticmethod
    def _find_duplicate_headers(headers: List[str]) -> List[str]:
        seen = set()
        duplicates = set()
        for header in headers:
            if not header:
                continue
            if header in seen:
                duplicates.add(header)
            seen.add(header)
        return sorted(duplicates)

    @staticmethod
    def _normalize_header(header: Any) -> str:
        if header is None:
            return ""
        normalized = str(header).strip().lower().replace(" ", "_").replace("-", "_")
        return normalized
