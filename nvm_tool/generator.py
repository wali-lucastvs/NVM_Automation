from __future__ import annotations

from copy import deepcopy
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
from xml.etree import ElementTree as ET

from .models import (
    AUTOSAR_XSI_NAMESPACE,
    NVM_BLOCK_CONTAINER_DEFINITION_REF,
    NVM_BLOCK_CRC_TYPE_DEFINITION_REF,
    NVM_MODULE_DEFINITION_REF,
    NvMBlock,
    ParsedArxmlDocument,
)


class NvMGenerator:
    """Merges NvM block definitions into an existing ARXML and generates C artifacts."""

    def __init__(
        self,
        blocks: Iterable[NvMBlock],
        previous_document: ParsedArxmlDocument,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.blocks = sorted(list(blocks), key=lambda block: block.block_id)
        self.previous_document = previous_document
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def generate(self, output_dir: Union[str, Path]) -> None:
        destination = Path(output_dir)
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"Output path must be a directory: {destination}")
        destination.mkdir(parents=True, exist_ok=True)

        merged_blocks, merged_arxml = self._merge_blocks_into_previous_arxml()
        files = {
            "NvM_Cfg.h": self.render_header(merged_blocks),
            "NvM_Cfg.c": self.render_source(merged_blocks),
            "NvM.arxml": merged_arxml,
        }

        for file_name, content in files.items():
            file_path = destination / file_name
            file_path.write_text(content, encoding="utf-8", newline="\n")
            self.logger.info("Generated %s", file_path)

        for block in merged_blocks:
            self.logger.info(
                "Merged block '%s' (ID=%s, device=%s, management=%s).",
                block.block_name,
                block.block_id,
                block.device,
                block.block_management_type,
            )

    def render_header(self, blocks: List[NvMBlock]) -> str:
        lines = [
            "/*",
            " * NvM_Cfg.h",
            " * Auto-generated NvM configuration header.",
            " * Integrate the generated types with your platform Std_Types.h if needed.",
            " */",
            "",
            "#ifndef NVM_CFG_H",
            "#define NVM_CFG_H",
            "",
            '#include "Std_Types.h"',
            "",
            "#ifdef __cplusplus",
            'extern "C" {',
            "#endif",
            "",
            "typedef enum",
            "{",
            "    NVM_DEVICE_FEE = 0,",
            "    NVM_DEVICE_EA = 1",
            "} NvM_DeviceType;",
            "",
            "typedef enum",
            "{",
            "    NVM_BLOCK_NATIVE = 0,",
            "    NVM_BLOCK_REDUNDANT = 1,",
            "    NVM_BLOCK_DATASET = 2",
            "} NvM_BlockManagementTypeType;",
            "",
            "typedef enum",
            "{",
            "    NVM_CRC_NONE = 0,",
            "    NVM_CRC8 = 1,",
            "    NVM_CRC16 = 2,",
            "    NVM_CRC32 = 3",
            "} NvM_CrcType;",
            "",
            "typedef struct",
            "{",
            "    uint16 BlockId;",
            "    uint16 BlockLength;",
            "    uint8* RamBlockDataAddress;",
            "    NvM_DeviceType DeviceId;",
            "    NvM_BlockManagementTypeType BlockManagementType;",
            "    boolean BlockUseCrc;",
            "    NvM_CrcType BlockCrcType;",
            "    boolean WriteProtection;",
            "} NvM_BlockDescriptorType;",
            "",
            "/* Number of merged NvM blocks. */",
            f"#define NVM_NUMBER_OF_BLOCKS ({len(blocks)}u)",
            "",
            "/* Symbolic block identifiers. */",
        ]

        for block in blocks:
            lines.append(f"#define {block.block_id_macro} ({block.block_id}u)")

        lines.extend(
            [
                "",
                "extern const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS];",
                "",
                "#ifdef __cplusplus",
                "}",
                "#endif",
                "",
                "#endif /* NVM_CFG_H */",
            ]
        )
        return "\n".join(lines) + "\n"

    def render_source(self, blocks: List[NvMBlock]) -> str:
        lines = [
            "/*",
            " * NvM_Cfg.c",
            " * Auto-generated NvM configuration source.",
            " */",
            "",
            '#include "NvM_Cfg.h"',
            "",
            "/* External RAM block buffers configured for permanent RAM usage. */",
        ]

        for block in blocks:
            lines.append(f"extern uint8 {block.ram_block_name}[{block.block_size}u];")

        lines.extend(
            [
                "",
                "/*",
                " * Merged NvM block descriptor table.",
                " * Existing blocks from the previous ARXML are preserved unless updated by the new input.",
                " */",
                "const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS] =",
                "{",
            ]
        )

        for index, block in enumerate(blocks):
            use_crc_literal, write_protection_literal = block.bool_c_literal
            lines.extend(
                [
                    f"    /* {block.block_name}: block ID {block.block_id}, {block.device}, "
                    f"{block.block_management_type}, "
                    f"{block.crc_type if block.use_crc else 'NO_CRC'} */",
                    "    {",
                    f"        .BlockId = {block.block_id_macro},",
                    f"        .BlockLength = {block.block_size}u,",
                    f"        .RamBlockDataAddress = {block.ram_block_name},",
                    f"        .DeviceId = {block.device_enum},",
                    f"        .BlockManagementType = {block.management_enum},",
                    f"        .BlockUseCrc = {use_crc_literal},",
                    f"        .BlockCrcType = {block.crc_enum},",
                    f"        .WriteProtection = {write_protection_literal}",
                    "    }" + ("," if index < len(blocks) - 1 else ""),
                ]
            )

        lines.extend(["};"])
        return "\n".join(lines) + "\n"

    def _merge_blocks_into_previous_arxml(self) -> Tuple[List[NvMBlock], str]:
        root = deepcopy(self.previous_document.root)
        module_configuration = self._find_nvm_module_configuration(root)
        containers_element = self._ensure_direct_child(
            module_configuration,
            "CONTAINERS",
            self.previous_document.namespace,
        )
        existing_containers = self._index_block_containers(containers_element)

        merged_blocks_by_id: Dict[int, NvMBlock] = {
            block.block_id: block for block in self.previous_document.blocks
        }
        short_name_to_id: Dict[str, int] = {
            block.short_name: block.block_id for block in self.previous_document.blocks
        }

        for block in self.blocks:
            existing_block_id = short_name_to_id.get(block.short_name)
            if existing_block_id is not None and existing_block_id != block.block_id:
                raise ValueError(
                    f"Cannot merge block '{block.block_name}' because ARXML SHORT-NAME "
                    f"'{block.short_name}' already belongs to block_id {existing_block_id}."
                )

            if block.block_id in existing_containers:
                self.logger.info("Updating existing NvM block ID %s in previous ARXML.", block.block_id)
                self._update_block_container(
                    existing_containers[block.block_id],
                    block,
                    self.previous_document.namespace,
                )
            else:
                self.logger.info("Appending new NvM block ID %s to previous ARXML.", block.block_id)
                containers_element.append(
                    self._build_block_container(block, self.previous_document.namespace)
                )

            merged_blocks_by_id[block.block_id] = block
            short_name_to_id[block.short_name] = block.block_id

        merged_blocks = sorted(merged_blocks_by_id.values(), key=lambda item: item.block_id)
        self._validate_merged_short_names(merged_blocks)

        ET.register_namespace("", self.previous_document.namespace)
        ET.register_namespace("xsi", AUTOSAR_XSI_NAMESPACE)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        return merged_blocks, ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"

    def _update_block_container(
        self,
        container: ET.Element,
        block: NvMBlock,
        namespace: str,
    ) -> None:
        short_name_element = self._ensure_direct_child(container, "SHORT-NAME", namespace)
        short_name_element.text = block.short_name

        definition_ref = self._ensure_direct_child(container, "DEFINITION-REF", namespace)
        definition_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        definition_ref.text = NVM_BLOCK_CONTAINER_DEFINITION_REF

        parameter_values = self._ensure_direct_child(container, "PARAMETER-VALUES", namespace)
        parameter_elements = self._index_parameter_elements(parameter_values, block.short_name)
        desired_values = block.autosar_parameter_values()

        for definition in NvMBlock.STANDARD_PARAMETER_DEFINITIONS:
            if definition.definition_ref == NVM_BLOCK_CRC_TYPE_DEFINITION_REF and not block.use_crc:
                self._remove_parameter(parameter_values, parameter_elements, definition.definition_ref)
                continue

            value = desired_values.get(definition.definition_ref)
            if value is None:
                continue
            parameter_element = parameter_elements.get(definition.definition_ref)
            if parameter_element is None:
                parameter_element = ET.SubElement(
                    parameter_values,
                    self._tag(
                        "ECUC-NUMERICAL-PARAM-VALUE"
                        if definition.value_kind == "numerical"
                        else "ECUC-TEXTUAL-PARAM-VALUE",
                        namespace,
                    ),
                )
                parameter_elements[definition.definition_ref] = parameter_element
            self._write_parameter_value(parameter_element, definition, value, namespace)

    def _build_block_container(self, block: NvMBlock, namespace: str) -> ET.Element:
        container = ET.Element(self._tag("ECUC-CONTAINER-VALUE", namespace))
        ET.SubElement(container, self._tag("SHORT-NAME", namespace)).text = block.short_name

        definition_ref = ET.SubElement(container, self._tag("DEFINITION-REF", namespace))
        definition_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        definition_ref.text = NVM_BLOCK_CONTAINER_DEFINITION_REF

        parameter_values = ET.SubElement(container, self._tag("PARAMETER-VALUES", namespace))
        for definition in NvMBlock.STANDARD_PARAMETER_DEFINITIONS:
            if definition.definition_ref == NVM_BLOCK_CRC_TYPE_DEFINITION_REF and not block.use_crc:
                continue

            parameter_element = ET.SubElement(
                parameter_values,
                self._tag(
                    "ECUC-NUMERICAL-PARAM-VALUE"
                    if definition.value_kind == "numerical"
                    else "ECUC-TEXTUAL-PARAM-VALUE",
                    namespace,
                ),
            )
            self._write_parameter_value(
                parameter_element,
                definition,
                block.autosar_parameter_values()[definition.definition_ref],
                namespace,
            )
        return container

    def _write_parameter_value(
        self,
        parameter_element: ET.Element,
        definition,
        value: str,
        namespace: str,
    ) -> None:
        parameter_element.tag = self._tag(
            "ECUC-NUMERICAL-PARAM-VALUE"
            if definition.value_kind == "numerical"
            else "ECUC-TEXTUAL-PARAM-VALUE",
            namespace,
        )
        definition_ref = self._ensure_direct_child(parameter_element, "DEFINITION-REF", namespace)
        definition_ref.set("DEST", definition.dest)
        definition_ref.text = definition.definition_ref
        value_element = self._ensure_direct_child(parameter_element, "VALUE", namespace)
        value_element.text = value

    def _index_block_containers(self, containers_element: ET.Element) -> Dict[int, ET.Element]:
        indexed_containers: Dict[int, ET.Element] = {}
        for container in containers_element:
            if self._local_name(container.tag) != "ECUC-CONTAINER-VALUE":
                continue
            definition_ref = self._find_direct_child(container, "DEFINITION-REF")
            if definition_ref is None:
                continue
            if (definition_ref.text or "").strip() != NVM_BLOCK_CONTAINER_DEFINITION_REF:
                continue
            block_id = self._extract_block_id(container)
            if block_id in indexed_containers:
                raise ValueError(
                    f"Previous ARXML contains duplicate NvM block containers for block_id {block_id}."
                )
            indexed_containers[block_id] = container
        return indexed_containers

    def _extract_block_id(self, container: ET.Element) -> int:
        short_name = self._container_name(container)
        parameter_values = self._find_direct_child(container, "PARAMETER-VALUES")
        if parameter_values is None:
            raise ValueError(f"Previous ARXML block '{short_name}' is missing PARAMETER-VALUES.")

        for parameter in parameter_values:
            definition_ref = self._find_direct_child(parameter, "DEFINITION-REF")
            value_element = self._find_direct_child(parameter, "VALUE")
            if definition_ref is None or value_element is None:
                continue
            if (definition_ref.text or "").strip() == NvMBlock.STANDARD_PARAMETER_DEFINITIONS[0].definition_ref:
                try:
                    return int((value_element.text or "").strip())
                except ValueError as exc:
                    raise ValueError(
                        f"Previous ARXML block '{short_name}' has a non-integer NvMNvramBlockIdentifier."
                    ) from exc

        raise ValueError(
            f"Previous ARXML block '{short_name}' is missing NvMNvramBlockIdentifier."
        )

    def _index_parameter_elements(
        self,
        parameter_values: ET.Element,
        short_name: str,
    ) -> Dict[str, ET.Element]:
        indexed_parameters: Dict[str, ET.Element] = {}
        for parameter in parameter_values:
            definition_ref = self._find_direct_child(parameter, "DEFINITION-REF")
            if definition_ref is None:
                continue
            definition_ref_text = (definition_ref.text or "").strip()
            if not definition_ref_text:
                continue
            if definition_ref_text in indexed_parameters:
                raise ValueError(
                    f"Previous ARXML block '{short_name}' contains duplicate parameter "
                    f"'{definition_ref_text}'."
                )
            indexed_parameters[definition_ref_text] = parameter
        return indexed_parameters

    @staticmethod
    def _remove_parameter(
        parameter_values: ET.Element,
        parameter_elements: Dict[str, ET.Element],
        definition_ref: str,
    ) -> None:
        parameter_element = parameter_elements.pop(definition_ref, None)
        if parameter_element is not None:
            parameter_values.remove(parameter_element)

    @staticmethod
    def _validate_merged_short_names(blocks: List[NvMBlock]) -> None:
        seen: Dict[str, int] = {}
        for block in blocks:
            existing_block_id = seen.get(block.short_name)
            if existing_block_id is not None and existing_block_id != block.block_id:
                raise ValueError(
                    f"Merged ARXML contains duplicate SHORT-NAME '{block.short_name}' for "
                    f"block_id {existing_block_id} and {block.block_id}."
                )
            seen[block.short_name] = block.block_id

    def _find_nvm_module_configuration(self, root: ET.Element) -> ET.Element:
        matches: List[ET.Element] = []
        for element in root.iter():
            if self._local_name(element.tag) != "ECUC-MODULE-CONFIGURATION-VALUES":
                continue
            definition_ref = self._find_direct_child(element, "DEFINITION-REF")
            if definition_ref is None:
                continue
            if (definition_ref.text or "").strip() == NVM_MODULE_DEFINITION_REF:
                matches.append(element)

        if not matches:
            raise ValueError("Previous ARXML no longer contains an NvM ECUC-MODULE-CONFIGURATION-VALUES node.")
        if len(matches) > 1:
            raise ValueError("Previous ARXML contains multiple NvM ECUC-MODULE-CONFIGURATION-VALUES nodes.")
        return matches[0]

    def _container_name(self, container: ET.Element) -> str:
        short_name_element = self._find_direct_child(container, "SHORT-NAME")
        return (short_name_element.text or "").strip() if short_name_element is not None else "<unknown>"

    @staticmethod
    def _find_direct_child(parent: ET.Element, local_name: str) -> Optional[ET.Element]:
        for child in parent:
            if NvMGenerator._local_name(child.tag) == local_name:
                return child
        return None

    def _ensure_direct_child(
        self,
        parent: ET.Element,
        local_name: str,
        namespace: str,
    ) -> ET.Element:
        existing = self._find_direct_child(parent, local_name)
        if existing is not None:
            return existing
        return ET.SubElement(parent, self._tag(local_name, namespace))

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}", 1)[-1]

    @staticmethod
    def _tag(local_name: str, namespace: str) -> str:
        return f"{{{namespace}}}{local_name}"
