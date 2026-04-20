from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Optional, Union
from xml.sax.saxutils import escape

from .models import NvMBlock


class NvMGenerator:
    """Generates NvM_Cfg.c, NvM_Cfg.h, and NvM.arxml from NvMBlock objects."""

    def __init__(
        self,
        blocks: Iterable[NvMBlock],
        logger: Optional[logging.Logger] = None,
        module_short_name: str = "NvM",
        config_short_name: str = "NvM_Config",
        schema_file: str = "AUTOSAR_00049.xsd",
    ) -> None:
        self.blocks = sorted(list(blocks), key=lambda block: block.block_id)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.module_short_name = module_short_name
        self.config_short_name = config_short_name
        self.schema_file = schema_file

    def generate(self, output_dir: Union[str, Path]) -> None:
        destination = Path(output_dir)
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"Output path must be a directory: {destination}")
        destination.mkdir(parents=True, exist_ok=True)

        files = {
            "NvM_Cfg.h": self.render_header(),
            "NvM_Cfg.c": self.render_source(),
            "NvM.arxml": self.render_arxml(),
        }

        for file_name, content in files.items():
            file_path = destination / file_name
            file_path.write_text(content, encoding="utf-8", newline="\n")
            self.logger.info("Generated %s", file_path)

        for block in self.blocks:
            self.logger.info(
                "Generated block '%s' (ID=%s, device=%s, management=%s).",
                block.block_name,
                block.block_id,
                block.device,
                block.block_management_type,
            )

    def render_header(self) -> str:
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
            "/* Number of generated NvM blocks. */",
            f"#define NVM_NUMBER_OF_BLOCKS ({len(self.blocks)}u)",
            "",
            "/* Symbolic block identifiers. */",
        ]

        for block in self.blocks:
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

    def render_source(self) -> str:
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

        for block in self.blocks:
            lines.append(f"extern uint8 {block.ram_block_name}[{block.block_size}u];")

        lines.extend(
            [
                "",
                "/*",
                " * NvM block descriptor table.",
                " * Each entry maps one logical NvM block to its RAM block and storage attributes.",
                " */",
                "const NvM_BlockDescriptorType NvM_BlockDescriptorTable[NVM_NUMBER_OF_BLOCKS] =",
                "{",
            ]
        )

        for index, block in enumerate(self.blocks):
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
                    "    }" + ("," if index < len(self.blocks) - 1 else ""),
                ]
            )

        lines.extend(["};"])
        return "\n".join(lines) + "\n"

    def render_arxml(self) -> str:
        namespace = "http://autosar.org/schema/r4.0"
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<AUTOSAR xmlns="{namespace}" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                f'xsi:schemaLocation="{namespace} {self.schema_file}">'
            ),
            "  <AR-PACKAGES>",
            "    <AR-PACKAGE>",
            f"      <SHORT-NAME>{escape(self.module_short_name)}</SHORT-NAME>",
            "      <ELEMENTS>",
            "        <ECUC-MODULE-CONFIGURATION-VALUES>",
            f"          <SHORT-NAME>{escape(self.config_short_name)}</SHORT-NAME>",
            '          <DEFINITION-REF DEST="ECUC-MODULE-DEF">/AUTOSAR/EcucDefs/NvM</DEFINITION-REF>',
            "          <CONTAINERS>",
        ]

        for block in self.blocks:
            lines.extend(self._render_block_container(block))

        lines.extend(
            [
                "          </CONTAINERS>",
                "        </ECUC-MODULE-CONFIGURATION-VALUES>",
                "      </ELEMENTS>",
                "    </AR-PACKAGE>",
                "  </AR-PACKAGES>",
                "</AUTOSAR>",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_block_container(self, block: NvMBlock) -> List[str]:
        lines = [
            "            <ECUC-CONTAINER-VALUE>",
            f"              <SHORT-NAME>{escape(block.short_name)}</SHORT-NAME>",
            (
                '              <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">'
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor"
                "</DEFINITION-REF>"
            ),
            "              <PARAMETER-VALUES>",
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramBlockIdentifier",
                block.block_id,
                "ECUC-INTEGER-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockLength",
                block.block_size,
                "ECUC-INTEGER-PARAM-DEF",
                indent="                ",
            ),
            *self._textual_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockManagementType",
                block.autosar_management_enum,
                "ECUC-ENUMERATION-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockUseCrc",
                block.autosar_use_crc_value,
                "ECUC-BOOLEAN-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockWriteProt",
                block.autosar_write_protection_value,
                "ECUC-BOOLEAN-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramDeviceId",
                block.effective_device_id,
                "ECUC-INTEGER-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockBaseNumber",
                block.effective_nv_block_base_number,
                "ECUC-INTEGER-PARAM-DEF",
                indent="                ",
            ),
            *self._numerical_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockNum",
                block.effective_nv_block_num,
                "ECUC-INTEGER-PARAM-DEF",
                indent="                ",
            ),
            *self._textual_param(
                "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMRamBlockDataAddress",
                block.ram_block_name,
                "ECUC-STRING-PARAM-DEF",
                indent="                ",
            ),
        ]

        if block.use_crc:
            lines.extend(
                self._textual_param(
                    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockCrcType",
                    block.autosar_crc_enum,
                    "ECUC-ENUMERATION-PARAM-DEF",
                    indent="                ",
                )
            )

        lines.extend(
            [
                "              </PARAMETER-VALUES>",
                "            </ECUC-CONTAINER-VALUE>",
            ]
        )
        return lines

    @staticmethod
    def _numerical_param(definition_ref: str, value: Union[int, str], dest: str, indent: str) -> List[str]:
        return [
            f"{indent}<ECUC-NUMERICAL-PARAM-VALUE>",
            f'{indent}  <DEFINITION-REF DEST="{dest}">{escape(definition_ref)}</DEFINITION-REF>',
            f"{indent}  <VALUE>{value}</VALUE>",
            f"{indent}</ECUC-NUMERICAL-PARAM-VALUE>",
        ]

    @staticmethod
    def _textual_param(definition_ref: str, value: str, dest: str, indent: str) -> List[str]:
        return [
            f"{indent}<ECUC-TEXTUAL-PARAM-VALUE>",
            f'{indent}  <DEFINITION-REF DEST="{dest}">{escape(definition_ref)}</DEFINITION-REF>',
            f"{indent}  <VALUE>{escape(value)}</VALUE>",
            f"{indent}</ECUC-TEXTUAL-PARAM-VALUE>",
        ]
