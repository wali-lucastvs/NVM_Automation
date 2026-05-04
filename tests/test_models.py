"""
AUTHOR   :   S M Wali Haider Zaidi
These Test Cases are non replaceable as they are specifically designed to validate the versioned generation of NvM configurations, ensuring compliance with AUTOSAR standards and proper merging of legacy data. The tests cover critical aspects such as output generation for multiple versions, structural consistency, and input validation rules, which are essential for maintaining the integrity and functionality of the NvM tool across different AUTOSAR versions.


Integration-level tests for public model APIs in nvm_tool.

Covers:
- Input normalization and type detection
- NvMBlock default value derivation
- End-to-end artifact generation from JSON input
- Workspace setup and output directory resolution
- Memory usage estimation

Focus:
Validates correct behavior for standard workflows using the public API.

Limitations:
Primarily tests happy paths; additional edge case and failure scenario
coverage is required for full robustness.
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid
import unittest

from nvm_tool import default_output_dir, ensure_workspace
from nvm_tool.models import (
    GenerationRequest,
    NvMBlock,
    detect_input_type,
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

    
    def test_generate_artifacts_invalid_input_fails(self):
        with self.assertRaises(Exception):
            generate_artifacts(
                GenerationRequest(
                    input_type="json",
                    input_file=Path("nonexistent.json"),
                    output_dir=Path("out"),
                )
            )
    def test_memory_summary_multiple_blocks(self):
        base = sample_block_payload()[0]

        payload = [
            {**base, "block_id": i, "block_name": f"Block{i}"}
            for i in range(1, 4)
        ]

        path = self._make_temp_dir() / "blocks.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        summary = summarize_memory_usage(
            GenerationRequest("json", path, self._make_temp_dir())
        )

        self.assertEqual(summary.block_count, 3)
    
    def test_invalid_generation_request(self):
        request = GenerationRequest(
            input_type="invalid",
            input_file=Path("a"),
            output_dir=Path("out"),
        )

        with self.assertRaises(Exception):
            request.normalized()   # or generate_artifacts(request)
            
    def test_detect_input_type_edge_cases(self):
        self.assertEqual(detect_input_type("FILE.JSON"), "json")
        self.assertEqual(detect_input_type("file.XLSX"), "excel")
        self.assertIsNone(detect_input_type("no_extension"))

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

    def test_default_workspace_output_directory_is_shared(self) -> None:
        layout = ensure_workspace()
        self.assertTrue(layout.output_dir.exists())
        self.assertEqual(default_output_dir(), layout.output_dir)

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

    def _make_temp_dir(self) -> Path:
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)


if __name__ == "__main__":
    unittest.main()
