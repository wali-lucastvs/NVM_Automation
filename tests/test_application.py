from __future__ import annotations

import json
from pathlib import Path
import uuid
import unittest

from nvm_tool import (
    GenerationRequest,
    build_argument_parser,
    default_output_dir,
    detect_input_type,
    ensure_workspace,
    format_cli_command,
    generate_artifacts,
    summarize_memory_usage,
)


def sample_block_payload() -> list[dict[str, object]]:
    return [
        {
            "block_name": "GuiBlock",
            "block_id": 7,
            "block_size": 32,
            "ram_block_name": "Ram_GuiBlock",
            "device": "FEE",
            "block_management_type": "NATIVE",
            "use_crc": True,
            "crc_type": "CRC16",
            "write_protection": False,
        }
    ]


class ApplicationTests(unittest.TestCase):
    def test_generate_artifacts_from_json_creates_expected_files(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        output_dir = workspace / "generated"
        input_path.write_text(json.dumps(sample_block_payload()), encoding="utf-8")

        generated_files = generate_artifacts(
            GenerationRequest(
                input_type="json",
                input_file=input_path,
                output_dir=output_dir,
            )
        )

        self.assertEqual(
            generated_files,
            [
                output_dir / "NvM_Cfg.c",
                output_dir / "NvM_Cfg.h",
                output_dir / "NvM.arxml",
            ],
        )
        for file_path in generated_files:
            self.assertTrue(file_path.exists(), file_path)

    def test_allow_update_without_previous_arxml_is_rejected(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        input_path.write_text(json.dumps(sample_block_payload()), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "--allow-update requires --previous-arxml"):
            generate_artifacts(
                GenerationRequest(
                    input_type="json",
                    input_file=input_path,
                    allow_update=True,
                )
            )

    def test_detect_input_type_supports_json_and_excel(self) -> None:
        self.assertEqual(detect_input_type("demo.json"), "json")
        self.assertEqual(detect_input_type("demo.xlsx"), "excel")
        self.assertEqual(detect_input_type("demo.xlsm"), "excel")
        self.assertIsNone(detect_input_type("demo.txt"))

    def test_format_cli_command_includes_merge_and_verbose_flags(self) -> None:
        command = format_cli_command(
            GenerationRequest(
                input_type="excel",
                input_file=Path(r"C:\input files\NvM.xlsx"),
                previous_arxml=Path(r"C:\base\NvM.arxml"),
                output_dir=Path(r"C:\output folder"),
                verbose=True,
                allow_update=True,
            )
        )

        self.assertIn("generate_nvm.py", command)
        self.assertIn("--input-type excel", command)
        self.assertIn("--previous-arxml", command)
        self.assertIn("--allow-update", command)
        self.assertIn("--verbose", command)

    def test_cli_defaults_to_shared_workspace_output_directory(self) -> None:
        layout = ensure_workspace()
        parsed_args = build_argument_parser().parse_args(
            [
                "--input-type",
                "json",
                "--input-file",
                str(layout.input_dir / "nvm_blocks.json"),
            ]
        )

        self.assertEqual(parsed_args.output, default_output_dir())
        self.assertEqual(parsed_args.output, layout.output_dir)

    def test_summarize_memory_usage_for_fresh_input(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        input_path.write_text(json.dumps(sample_block_payload()), encoding="utf-8")

        summary = summarize_memory_usage(
            GenerationRequest(
                input_type="json",
                input_file=input_path,
                output_dir=workspace / "generated",
            )
        )

        self.assertEqual(summary.block_count, 1)
        self.assertEqual(summary.total_payload_bytes, 32)
        self.assertEqual(summary.total_crc_bytes, 2)
        self.assertEqual(summary.total_estimated_storage_bytes, 34)
        self.assertEqual(summary.fee_estimated_storage_bytes, 34)
        self.assertEqual(summary.ea_estimated_storage_bytes, 0)

    def test_summarize_memory_usage_for_merge_includes_previous_blocks(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        previous_arxml_path = workspace / "NvM.arxml"
        input_path.write_text(json.dumps(sample_block_payload()), encoding="utf-8")
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        summary = summarize_memory_usage(
            GenerationRequest(
                input_type="json",
                input_file=input_path,
                previous_arxml=previous_arxml_path,
                output_dir=workspace / "generated",
            )
        )

        self.assertEqual(summary.block_count, 2)
        self.assertEqual(summary.total_payload_bytes, 40)
        self.assertEqual(summary.total_crc_bytes, 4)
        self.assertEqual(summary.total_estimated_storage_bytes, 44)

    def test_summarize_memory_usage_for_update_replaces_existing_block(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        previous_arxml_path = workspace / "NvM.arxml"
        input_path.write_text(json.dumps(sample_block_payload()), encoding="utf-8")
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 7), encoding="utf-8")

        summary = summarize_memory_usage(
            GenerationRequest(
                input_type="json",
                input_file=input_path,
                previous_arxml=previous_arxml_path,
                output_dir=workspace / "generated",
                allow_update=True,
            )
        )

        self.assertEqual(summary.block_count, 1)
        self.assertEqual(summary.total_payload_bytes, 32)
        self.assertEqual(summary.total_crc_bytes, 2)
        self.assertEqual(summary.total_estimated_storage_bytes, 34)

    @staticmethod
    def _make_temp_dir() -> Path:
        temp_path = Path(__file__).resolve().parent / "_tmp" / uuid.uuid4().hex
        temp_path.mkdir(parents=True, exist_ok=False)
        return temp_path

    @staticmethod
    def _base_arxml_with_block(short_name: str, block_id: int) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <ELEMENTS>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>NvM</SHORT-NAME>
          <DEFINITION-REF DEST="ECUC-MODULE-DEF">/AUTOSAR/EcucDefs/NvM</DEFINITION-REF>
          <CONTAINERS>
            <ECUC-CONTAINER-VALUE>
              <SHORT-NAME>{short_name}</SHORT-NAME>
              <DEFINITION-REF DEST="ECUC-PARAM-CONF-CONTAINER-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor</DEFINITION-REF>
              <PARAMETER-VALUES>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramBlockIdentifier</DEFINITION-REF>
                  <VALUE>{block_id}</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockLength</DEFINITION-REF>
                  <VALUE>8</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-TEXTUAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-ENUMERATION-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockManagementType</DEFINITION-REF>
                  <VALUE>NVM_BLOCK_NATIVE</VALUE>
                </ECUC-TEXTUAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-BOOLEAN-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockUseCrc</DEFINITION-REF>
                  <VALUE>1</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-BOOLEAN-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockWriteProt</DEFINITION-REF>
                  <VALUE>0</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramDeviceId</DEFINITION-REF>
                  <VALUE>0</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockBaseNumber</DEFINITION-REF>
                  <VALUE>{block_id}</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-INTEGER-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockNum</DEFINITION-REF>
                  <VALUE>1</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>
                <ECUC-TEXTUAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-STRING-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMRamBlockDataAddress</DEFINITION-REF>
                  <VALUE>Ram_{short_name}</VALUE>
                </ECUC-TEXTUAL-PARAM-VALUE>
                <ECUC-TEXTUAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-ENUMERATION-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockCrcType</DEFINITION-REF>
                  <VALUE>NVM_CRC16</VALUE>
                </ECUC-TEXTUAL-PARAM-VALUE>
              </PARAMETER-VALUES>
            </ECUC-CONTAINER-VALUE>
          </CONTAINERS>
        </ECUC-MODULE-CONFIGURATION-VALUES>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
"""


if __name__ == "__main__":
    unittest.main()
