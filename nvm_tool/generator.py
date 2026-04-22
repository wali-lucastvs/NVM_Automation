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
    """Generates NvM configuration artifacts and optionally merges into an existing ARXML."""

    def __init__(
        self,
        blocks: Iterable[NvMBlock],
        previous_document: Optional[ParsedArxmlDocument] = None,
        allow_update: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.blocks = sorted(list(blocks), key=lambda block: block.block_id)
        self.previous_document = previous_document
        self.allow_update = allow_update
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def generate(self, output_dir: Union[str, Path]) -> None:
        destination = Path(output_dir)
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"Output path must be a directory: {destination}")
        destination.mkdir(parents=True, exist_ok=True)

        if self.previous_document is not None:
            merged_blocks, merged_arxml = self._merge_blocks_into_previous_arxml()
        else:
            merged_blocks, merged_arxml = self._generate_fresh_arxml()
        
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
                "Output block '%s' (ID=%s, device=%s, management=%s).",
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
            '#include <stdint.h> /* For uint8_t, uint16_t */',
            '#include <stdbool.h> /* For bool, true, false */',
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
            "    uint16_t BlockId;",
            "    uint16_t BlockLength;",
            "    uint8_t* RamBlockDataAddress;",
            "    NvM_DeviceType DeviceId;",
            "    NvM_BlockManagementTypeType BlockManagementType;",
            "    bool BlockUseCrc;",
            "    NvM_CrcType BlockCrcType;",
            "    bool WriteProtection;",
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
            lines.append(f"extern uint8_t {block.ram_block_name}[{block.block_size}u];")

        lines.extend(
            [
                "",
                "/*",
                " * Merged NvM block descriptor table.",
                " * Existing blocks from the previous ARXML are preserved and new blocks are appended.",
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

    def _generate_fresh_arxml(self) -> Tuple[List[NvMBlock], str]:
        """Generate a fresh ARXML from input blocks without merging."""
        namespace = "http://autosar.org/schema/r4.0"
        
        # Create root element
        root = ET.Element(self._tag("AUTOSAR", namespace))
        root.set(self._tag("schemaLocation", "http://www.w3.org/2001/XMLSchema-instance"), 
                 "http://autosar.org/schema/r4.0 AUTOSAR_4-0-2.xsd")
        
        # Create ARPackages element
        ar_packages = ET.SubElement(root, self._tag("AR-PACKAGES", namespace))
        
        # Create NvM module configuration
        module_config = ET.SubElement(ar_packages, self._tag("AR-PACKAGE", namespace))
        ET.SubElement(module_config, self._tag("SHORT-NAME", namespace)).text = "NvM"
        nvm_values = ET.SubElement(module_config, self._tag("ELEMENTS", namespace))
        
        module_configuration = ET.SubElement(
            nvm_values,
            self._tag("ECUC-MODULE-CONFIGURATION-VALUES", namespace)
        )
        
        definition_ref = ET.SubElement(module_configuration, self._tag("DEFINITION-REF", namespace))
        definition_ref.set("DEST", "ECUC-MODULE-DEF")
        definition_ref.text = NVM_MODULE_DEFINITION_REF
        
        # Create CONTAINERS element
        containers_element = ET.SubElement(module_configuration, self._tag("CONTAINERS", namespace))
        
        # Add all input blocks
        for block in self.blocks:
            self.logger.info("Adding NvM block ID %s to fresh ARXML.", block.block_id)
            containers_element.append(self._build_block_container(block, namespace))
        
        merged_blocks = list(self.blocks)
        self._validate_merged_short_names(merged_blocks)
        
        # Register namespaces and convert to string
        ET.register_namespace("", namespace)
        ET.register_namespace("xsi", AUTOSAR_XSI_NAMESPACE)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        return merged_blocks, ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"

    def _merge_blocks_into_previous_arxml(self) -> Tuple[List[NvMBlock], str]:
        root = deepcopy(self.previous_document.root)
        module_configuration = self._find_nvm_module_configuration(root)
        containers_element = self._ensure_direct_child(
            module_configuration,
            "CONTAINERS",
            self.previous_document.namespace,
        )
        self._index_block_containers(containers_element)

        merged_blocks_by_id: Dict[int, NvMBlock] = {
            block.block_id: block for block in self.previous_document.blocks
        }

        for block in self.blocks:
            existing_id_location = self.previous_document.block_id_locations.get(block.block_id)
            existing_name_location = self.previous_document.short_name_locations.get(block.short_name)
            
            if existing_id_location is not None or existing_name_location is not None:
                if not self.allow_update:
                    raise ValueError(
                        f"Duplicate block ID {block.block_id} or name '{block.short_name}' found. "
                        f"Use --allow-update flag to modify existing blocks."
                    )
                
                # Update mode: find and replace the existing container
                self.logger.info("Updating existing NvM block ID %s in ARXML.", block.block_id)
                
                # Find the container element to replace
                container_to_replace = None
                for container in containers_element:
                    if self._local_name(container.tag) != "ECUC-CONTAINER-VALUE":
                        continue
                    extracted_id = self._extract_block_id(container)
                    if extracted_id == block.block_id:
                        container_to_replace = container
                        break
                
                if container_to_replace is not None:
                    # Replace the old container with the new one
                    container_index = list(containers_element).index(container_to_replace)
                    containers_element.remove(container_to_replace)
                    containers_element.insert(container_index, self._build_block_container(block, self.previous_document.namespace))
                    merged_blocks_by_id[block.block_id] = block
                else:
                    raise ValueError(f"Could not find existing block container for ID {block.block_id} to update.")
            else:
                self.logger.info("Appending new NvM block ID %s to previous ARXML.", block.block_id)
                containers_element.append(
                    self._build_block_container(block, self.previous_document.namespace)
                )
                merged_blocks_by_id[block.block_id] = block

        merged_blocks = sorted(merged_blocks_by_id.values(), key=lambda item: item.block_id)
        self._validate_merged_short_names(merged_blocks)

        ET.register_namespace("", self.previous_document.namespace)
        ET.register_namespace("xsi", AUTOSAR_XSI_NAMESPACE)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        return merged_blocks, ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"

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
