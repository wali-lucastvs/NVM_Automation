 from __future__ import annotations

import json
from pathlib import Path

from nvm_tool import default_output_dir, ensure_workspace
from nvm_tool.models import (
    GenerationRequest,
    NvMBlock,
    detect_input_type,
    generate_artifacts,
    summarize_memory_usage,
)
from tests.helpers import TempDirTestCase, base_block_record, sample_block_payload


class ModelRequestTests(TempDirTestCase):
    # TAG ID: MODEL_REQ_001
    # Why: Keeps CLI/API request normalization traceable for mixed-case input types.
    def test_MODEL_REQ_001_generation_request_normalizes_input_type(self) -> None:
        request = GenerationRequest(input_type=" JSON ", input_file=Path("blocks.json")).normalized()

        self.assertEqual(request.input_type, "json")

    # TAG ID: MODEL_REQ_002
    # Why: Unsupported request input types must fail before parsing starts.
    def test_MODEL_REQ_002_invalid_generation_request_fails(self) -> None:
        request = GenerationRequest(
            input_type="invalid",
            input_file=Path("a"),
            output_dir=Path("out"),
        )

        with self.assertRaises(Exception):
            request.normalized()


class ModelInputDetectionTests(TempDirTestCase):
    # TAG ID: MODEL_INPUT_001
    # Why: JSON and Excel suffix detection drives the public file selection workflow.
    def test_MODEL_INPUT_001_detect_input_type_supports_json_and_excel(self) -> None:
        self.assertEqual(detect_input_type("demo.json"), "json")
        self.assertEqual(detect_input_type("demo.xlsx"), "excel")
        self.assertEqual(detect_input_type("demo.xlsm"), "excel")
        self.assertIsNone(detect_input_type("demo.txt"))

    # TAG ID: MODEL_INPUT_002
    # Why: Case-insensitive suffix handling avoids rejecting valid user-selected files.
    def test_MODEL_INPUT_002_detect_input_type_handles_case_and_missing_extension(self) -> None:
        self.assertEqual(detect_input_type("FILE.JSON"), "json")
        self.assertEqual(detect_input_type("file.XLSX"), "excel")
        self.assertIsNone(detect_input_type("no_extension"))


class ModelBlockTests(TempDirTestCase):
    # TAG ID: MODEL_BLOCK_001
    # Why: Derived AUTOSAR defaults are used in generated ARXML when optional values are absent.
    def test_MODEL_BLOCK_001_nvm_block_defaults_are_derived(self) -> None:
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


class ModelValidationTests(TempDirTestCase):
    # TAG ID: VALIDATION_BLOCK_ID_001
    # Why: AUTOSAR reserves block ID 0, so accepting it would generate invalid configuration.
    def test_VALIDATION_BLOCK_ID_001_rejects_reserved_zero_block_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "block_id"):
            NvMBlock.from_mapping(base_block_record(block_id=0))

    # TAG ID: VALIDATION_BLOCK_ID_002
    # Why: Negative block IDs cannot be represented as valid NvM identifiers.
    def test_VALIDATION_BLOCK_ID_002_rejects_negative_block_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "block_id"):
            NvMBlock.from_mapping(base_block_record(block_id=-1))

    # TAG ID: VALIDATION_BLOCK_ID_003
    # Why: Generated C uses uint16_t block IDs, so values above 65535 must fail early.
    def test_VALIDATION_BLOCK_ID_003_rejects_block_id_above_uint16_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "65535"):
            NvMBlock.from_mapping(base_block_record(block_id=65536))

    # TAG ID: VALIDATION_BLOCK_SIZE_001
    # Why: A zero-length NvM block has no meaningful payload and should not generate artifacts.
    def test_VALIDATION_BLOCK_SIZE_001_rejects_zero_block_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "block_size"):
            NvMBlock.from_mapping(base_block_record(block_size=0))

    # TAG ID: VALIDATION_BLOCK_SIZE_002
    # Why: Negative sizes would produce invalid C declarations and ARXML values.
    def test_VALIDATION_BLOCK_SIZE_002_rejects_negative_block_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "block_size"):
            NvMBlock.from_mapping(base_block_record(block_size=-4))

    # TAG ID: VALIDATION_BLOCK_SIZE_003
    # Why: Device storage sizes are emitted as uint16_t values and must stay within range.
    def test_VALIDATION_BLOCK_SIZE_003_rejects_block_size_above_device_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "FEE"):
            NvMBlock.from_mapping(base_block_record(block_size=65536, device="FEE"))

    # TAG ID: VALIDATION_ENUM_001
    # Why: Unknown CRC modes would generate unsupported C enums and AUTOSAR values.
    def test_VALIDATION_ENUM_001_rejects_invalid_crc_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "crc_type"):
            NvMBlock.from_mapping(base_block_record(crc_type="CRC64"))

    # TAG ID: VALIDATION_ENUM_002
    # Why: Only known NvM storage backends can be rendered correctly.
    def test_VALIDATION_ENUM_002_rejects_invalid_device(self) -> None:
        with self.assertRaisesRegex(ValueError, "device"):
            NvMBlock.from_mapping(base_block_record(device="FLASH"))

    # TAG ID: VALIDATION_ENUM_003
    # Why: Management type controls NvM copy count and generated enum values.
    def test_VALIDATION_ENUM_003_rejects_invalid_block_management_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "block_management_type"):
            NvMBlock.from_mapping(base_block_record(block_management_type="MIRRORED"))

    # TAG ID: VALIDATION_RAM_NAME_001
    # Why: Empty RAM symbols would produce invalid external buffer declarations.
    def test_VALIDATION_RAM_NAME_001_rejects_empty_ram_block_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "ram_block_name"):
            NvMBlock.from_mapping(base_block_record(ram_block_name=""))

    # TAG ID: VALIDATION_RAM_NAME_002
    # Why: None must not silently become the string 'None' in generated C.
    def test_VALIDATION_RAM_NAME_002_rejects_none_ram_block_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "ram_block_name"):
            NvMBlock.from_mapping(base_block_record(ram_block_name=None))

    # TAG ID: VALIDATION_BLOCK_NAME_001
    # Why: Names with spaces are accepted but sanitized for AUTOSAR short names and C macros.
    def test_VALIDATION_BLOCK_NAME_001_sanitizes_block_names_with_spaces(self) -> None:
        block = NvMBlock.from_mapping(base_block_record(block_name="Door Lock", ram_block_name="Ram_DoorLock"))

        self.assertEqual(block.short_name, "Door_Lock")
        self.assertEqual(block.macro_token, "DOOR_LOCK")

    # TAG ID: VALIDATION_BLOCK_NAME_002
    # Why: Hyphenated names should map predictably to generated identifiers.
    def test_VALIDATION_BLOCK_NAME_002_sanitizes_block_names_with_hyphens(self) -> None:
        block = NvMBlock.from_mapping(base_block_record(block_name="Door-Lock", ram_block_name="Ram_DoorLock"))

        self.assertEqual(block.short_name, "Door_Lock")
        self.assertEqual(block.macro_token, "DOOR_LOCK")

    # TAG ID: VALIDATION_BLOCK_NAME_003
    # Why: Non-ASCII display names should not leak unsupported characters into generated symbols.
    def test_VALIDATION_BLOCK_NAME_003_sanitizes_non_ascii_block_names(self) -> None:
        block = NvMBlock.from_mapping(base_block_record(block_name="Blöck", ram_block_name="Ram_Block"))

        self.assertEqual(block.short_name, "Bl_ck")
        self.assertEqual(block.macro_token, "BL_CK")


class ModelMemorySummaryTests(TempDirTestCase):
    # TAG ID: MODEL_MEMORY_001
    # Why: Baseline memory accounting must include payload and CRC overhead.
    def test_MODEL_MEMORY_001_summarize_memory_usage_for_fresh_input(self) -> None:
        workspace = self.make_temp_dir()
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

    # TAG ID: MODEL_MEMORY_002
    # Why: Block count aggregation needs coverage for more than one input block.
    def test_MODEL_MEMORY_002_memory_summary_counts_multiple_blocks(self) -> None:
        base = sample_block_payload()[0]
        payload = [{**base, "block_id": i, "block_name": f"Block{i}"} for i in range(1, 4)]
        path = self.make_temp_dir() / "blocks.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        summary = summarize_memory_usage(
            GenerationRequest("json", path, self.make_temp_dir())
        )

        self.assertEqual(summary.block_count, 3)

    # TAG ID: MODEL_MEMORY_003
    # Why: EA storage accounting must be exercised separately from the FEE path.
    def test_MODEL_MEMORY_003_ea_device_memory_is_counted_separately(self) -> None:
        path = self.make_temp_dir() / "blocks.json"
        path.write_text(json.dumps([base_block_record(device="EA", block_size=10)]), encoding="utf-8")

        summary = summarize_memory_usage(GenerationRequest("json", path, self.make_temp_dir()))

        self.assertEqual(summary.ea_estimated_storage_bytes, 12)
        self.assertEqual(summary.fee_estimated_storage_bytes, 0)

    # TAG ID: MODEL_MEMORY_004
    # Why: Mixed devices must split estimated bytes correctly for capacity planning.
    def test_MODEL_MEMORY_004_mixed_ea_and_fee_blocks_split_storage_bytes(self) -> None:
        path = self.make_temp_dir() / "blocks.json"
        path.write_text(
            json.dumps(
                [
                    base_block_record(block_name="FeeBlock", block_id=2, block_size=10, device="FEE"),
                    base_block_record(block_name="EaBlock", block_id=3, block_size=20, device="EA"),
                ]
            ),
            encoding="utf-8",
        )

        summary = summarize_memory_usage(GenerationRequest("json", path, self.make_temp_dir()))

        self.assertEqual(summary.fee_estimated_storage_bytes, 12)
        self.assertEqual(summary.ea_estimated_storage_bytes, 22)

    # TAG ID: MODEL_MEMORY_005
    # Why: CRC32 consumes four bytes and must not be counted like CRC16.
    def test_MODEL_MEMORY_005_crc32_adds_four_bytes_compared_with_crc16(self) -> None:
        path = self.make_temp_dir() / "blocks.json"
        path.write_text(
            json.dumps(
                [
                    base_block_record(block_name="Crc16Block", block_id=2, block_size=10, crc_type="CRC16"),
                    base_block_record(block_name="Crc32Block", block_id=3, block_size=10, crc_type="CRC32"),
                ]
            ),
            encoding="utf-8",
        )

        summary = summarize_memory_usage(GenerationRequest("json", path, self.make_temp_dir()))

        self.assertEqual(summary.total_crc_bytes, 6)
        self.assertEqual(summary.total_estimated_storage_bytes, 26)


class WorkspaceTests(TempDirTestCase):
    # TAG ID: WORKSPACE_001
    # Why: The public workspace helper and output helper should resolve to the same directory.
    def test_WORKSPACE_001_default_workspace_output_directory_is_shared(self) -> None:
        layout = ensure_workspace()

        self.assertTrue(layout.output_dir.exists())
        self.assertEqual(default_output_dir(), layout.output_dir)


class ModelArtifactGenerationTests(TempDirTestCase):
    # TAG ID: GEN_ARTIFACT_001
    # Why: JSON artifact generation is the main public happy path.
    def test_GEN_ARTIFACT_001_generate_artifacts_from_json_creates_expected_files(self) -> None:
        workspace = self.make_temp_dir()
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
