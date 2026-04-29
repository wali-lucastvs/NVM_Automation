from __future__ import annotations

import json
from pathlib import Path
import uuid
import unittest

from nvm_tool import default_output_dir, ensure_workspace
from nvm_tool.models import (
    GenerationRequest,
    NvMBlock,
    build_argument_parser,
    detect_input_type,
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


class ModelSurfaceTests(unittest.TestCase):
    def test_generation_request_normalizes_input_type(self) -> None:
        request = GenerationRequest(input_type=" JSON ", input_file=Path("blocks.json")).normalized()
        self.assertEqual(request.input_type, "json")

    def test_detect_input_type_supports_json_and_excel(self) -> None:
        self.assertEqual(detect_input_type("demo.json"), "json")
        self.assertEqual(detect_input_type("demo.xlsx"), "excel")
        self.assertEqual(detect_input_type("demo.xlsm"), "excel")
        self.assertIsNone(detect_input_type("demo.txt"))

    def test_format_cli_command_uses_unified_entry_point(self) -> None:
        command = format_cli_command(
            GenerationRequest(
                input_type="json",
                input_file=Path(r"C:\input files\NvM.json"),
                output_dir=Path(r"C:\output folder"),
                verbose=True,
            )
        )

        self.assertIn("main.py", command)
        self.assertIn("generate", command)
        self.assertIn("--verbose", command)

    def test_nvm_block_defaults_are_derived(self) -> None:
        block = NvMBlock.from_mapping(
            {
                "block_name": "ModelBlock",
                "block_id": 7,
                "block_size": 8,
                "ram_block_name": "Ram_ModelBlock",
                "device": "FEE",
                "block_management_type": "NATIVE",
                "use_crc": True,
                "crc_type": "CRC16",
                "write_protection": False,
            }
        )

        self.assertEqual(block.effective_device_id, 0)
        self.assertEqual(block.effective_nv_block_base_number, 7)
        self.assertEqual(block.effective_nv_block_num, 1)

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

    @staticmethod
    def _make_temp_dir() -> Path:
        temp_path = Path(__file__).resolve().parent / "_tmp" / uuid.uuid4().hex
        temp_path.mkdir(parents=True, exist_ok=False)
        return temp_path


if __name__ == "__main__":
    unittest.main()
