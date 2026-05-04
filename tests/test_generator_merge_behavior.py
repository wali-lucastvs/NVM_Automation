from __future__ import annotations

import json

from nvm_tool import GenerationRequest, NvMConfigParser, NvMGenerator, detect_input_type, generate_artifacts
from tests.helpers import (
    TempDirTestCase,
    arxml_with_com_and_empty_nvm,
    base_arxml_with_block,
    base_block_record,
    extract_container_metadata,
    make_block,
    read_text,
    write_excel,
)


class NvMGeneratorArxmlMergeTests(TempDirTestCase):
    # TAG ID: GEN_MERGE_001
    # Why: Merge mode must preserve existing NvM containers while appending new blocks.
    def test_GEN_MERGE_001_previous_arxml_containers_are_preserved_and_new_blocks_appended(self) -> None:
        workspace = self.make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(previous_arxml_path)

        NvMGenerator(blocks=[make_block("NewBlock", 5)], previous_document=previous_document).generate(workspace)

        merged_content = read_text(workspace / "NvM.arxml")
        short_names, block_ids = extract_container_metadata(merged_content)
        self.assertCountEqual(short_names, ["LegacyBlock", "NewBlock"])
        self.assertCountEqual(block_ids, [10, 5])
        self.assertIn("Ram_NewBlock", merged_content)
        self.assertIn("NVM_CRC16", merged_content)

    # TAG ID: GEN_MERGE_002
    # Why: Appending more than one block protects against single-block-only merge logic.
    def test_GEN_MERGE_002_multiple_new_blocks_are_appended(self) -> None:
        workspace = self.make_temp_dir()
        previous_path = workspace / "NvM.arxml"
        previous_path.write_text(base_arxml_with_block("Legacy", 1), encoding="utf-8")
        previous_doc = NvMConfigParser().parse_previous_arxml(previous_path)

        NvMGenerator(
            blocks=[make_block("BlockA", 2), make_block("BlockB", 3)],
            previous_document=previous_doc,
        ).generate(workspace)

        content = read_text(workspace / "NvM.arxml")
        short_names, block_ids = extract_container_metadata(content)
        self.assertCountEqual(short_names, ["Legacy", "BlockA", "BlockB"])
        self.assertCountEqual(block_ids, [1, 2, 3])
        self.assertIn("Ram_BlockA", content)
        self.assertIn("Ram_BlockB", content)

    # TAG ID: GEN_MERGE_003
    # Why: Updating NvM must not remove unrelated AUTOSAR module configuration.
    def test_GEN_MERGE_003_non_nvm_containers_are_preserved(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(arxml_with_com_and_empty_nvm(), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator([make_block("A", 1)], previous_document=previous_document).generate(workspace)

        result = read_text(workspace / "NvM.arxml")
        self.assertIn("Com", result)
        self.assertIn("NvM", result)
        self.assertIn("Ram_A", result)

    # TAG ID: GEN_MERGE_004
    # Why: Legacy block ordering is important for reviewable generated ARXML diffs.
    def test_GEN_MERGE_004_legacy_blocks_appear_before_new_blocks_in_output(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("Legacy", 10), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator([make_block("NewBlock", 5)], previous_document=previous_document).generate(workspace)

        content = read_text(workspace / "NvM.arxml")
        self.assertLess(content.index("Legacy"), content.index("NewBlock"))

    # TAG ID: GEN_MERGE_005
    # Why: Write protection is a user-visible block safety flag.
    def test_GEN_MERGE_005_write_protected_block_is_merged_correctly(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("Legacy", 1), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator(
            [make_block("ProtectedBlock", 2, write_protection=True)],
            previous_document=previous_document,
        ).generate(workspace)

        short_names, block_ids = extract_container_metadata(read_text(workspace / "NvM.arxml"))
        self.assertIn("ProtectedBlock", short_names)
        self.assertIn(2, block_ids)

    # TAG ID: GEN_MERGE_006
    # Why: EA blocks use a different device enum and storage bucket than FEE blocks.
    def test_GEN_MERGE_006_ea_device_block_is_merged_correctly(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("FeeBlock", 1), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator([make_block("EaBlock", 2, device="EA")], previous_document=previous_document).generate(workspace)

        short_names, _ = extract_container_metadata(read_text(workspace / "NvM.arxml"))
        self.assertIn("EaBlock", short_names)

    # TAG ID: GEN_MERGE_007
    # Why: CRC32 generation must emit the correct AUTOSAR CRC enum.
    def test_GEN_MERGE_007_crc32_block_is_merged_correctly(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("Legacy", 1), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator([make_block("Crc32Block", 2, crc_type="CRC32")], previous_document=previous_document).generate(workspace)

        self.assertIn("NVM_CRC32", read_text(workspace / "NvM.arxml"))

    # TAG ID: GEN_MERGE_008
    # Why: Blocks without CRC omit CRC ARXML while keeping container structure valid.
    def test_GEN_MERGE_008_block_without_crc_is_merged_correctly(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("Legacy", 1), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(path)

        NvMGenerator([make_block("NoCrcBlock", 2, use_crc=False)], previous_document=previous_document).generate(workspace)

        short_names, _ = extract_container_metadata(read_text(workspace / "NvM.arxml"))
        self.assertIn("NoCrcBlock", short_names)

    # TAG ID: GEN_MERGE_009
    # Why: Repeated merge workflows must not duplicate already merged blocks.
    def test_GEN_MERGE_009_remerge_does_not_duplicate_blocks(self) -> None:
        workspace = self.make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(base_arxml_with_block("Legacy", 1), encoding="utf-8")

        previous_document = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("BlockA", 2)], previous_document=previous_document).generate(workspace)

        second_previous_document = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("BlockB", 3)], previous_document=second_previous_document).generate(workspace)

        short_names, block_ids = extract_container_metadata(read_text(workspace / "NvM.arxml"))
        self.assertEqual(len(short_names), len(set(short_names)))
        self.assertEqual(len(block_ids), len(set(block_ids)))
        self.assertCountEqual(short_names, ["Legacy", "BlockA", "BlockB"])

    # TAG ID: GEN_MERGE_010
    # Why: Duplicate new names would collide in generated ARXML SHORT-NAME values.
    def test_GEN_MERGE_010_duplicate_names_within_new_blocks_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            NvMGenerator(
                blocks=[make_block("SameName", 1), make_block("SameName", 2)]
            ).generate(self.make_temp_dir())

    # TAG ID: GEN_MERGE_011
    # Why: A new block must not reuse an existing block ID without explicit update mode.
    def test_GEN_MERGE_011_duplicate_block_id_between_previous_and_new_is_rejected(self) -> None:
        workspace = self.make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block ID 10"):
            NvMGenerator(
                blocks=[make_block("FreshBlock", 10)],
                previous_document=previous_document,
            ).generate(workspace)

    # TAG ID: GEN_MERGE_012
    # Why: A new block must not reuse an existing AUTOSAR short name.
    def test_GEN_MERGE_012_duplicate_block_name_between_previous_and_new_is_rejected(self) -> None:
        workspace = self.make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")
        previous_document = NvMConfigParser().parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block name 'LegacyBlock'"):
            NvMGenerator(
                blocks=[make_block("LegacyBlock", 11)],
                previous_document=previous_document,
            ).generate(workspace)


class NvMGeneratorArtifactTests(TempDirTestCase):
    # TAG ID: GEN_ARTIFACT_002
    # Why: REDUNDANT blocks affect NvM copy count and must generate complete artifacts.
    def test_GEN_ARTIFACT_002_redundant_block_generation_outputs_arxml_and_c_artifacts(self) -> None:
        output_dir = self.make_temp_dir()

        NvMGenerator([make_block("RedundantBlock", 8, block_management_type="REDUNDANT")]).generate(output_dir)

        arxml = read_text(output_dir / "NvM.arxml")
        source = read_text(output_dir / "NvM_Cfg.c")
        header = read_text(output_dir / "NvM_Cfg.h")
        self.assertIn("NVM_BLOCK_REDUNDANT", arxml)
        self.assertIn(".BlockManagementType = NVM_BLOCK_REDUNDANT", source)
        self.assertIn("#define NVM_BLOCK_ID_REDUNDANT_BLOCK (8u)", header)

    # TAG ID: GEN_ARTIFACT_003
    # Why: Existing output directories are common in reruns and should be overwritten deterministically.
    def test_GEN_ARTIFACT_003_existing_output_directory_is_overwritten(self) -> None:
        output_dir = self.make_temp_dir()
        stale_header = output_dir / "NvM_Cfg.h"
        stale_header.write_text("stale content", encoding="utf-8")

        NvMGenerator([make_block("OverwriteBlock", 9)]).generate(output_dir)

        self.assertNotIn("stale content", read_text(stale_header))
        self.assertIn("NVM_BLOCK_ID_OVERWRITE_BLOCK", read_text(stale_header))

    # TAG ID: GEN_ARTIFACT_004
    # Why: Generated C entries must contain block-specific fields, not just a table symbol.
    def test_GEN_ARTIFACT_004_c_file_contains_block_entry_fields(self) -> None:
        output_dir = self.make_temp_dir()

        NvMGenerator([make_block("ContentBlock", 14, device="EA", crc_type="CRC32")]).generate(output_dir)

        source = read_text(output_dir / "NvM_Cfg.c")
        self.assertIn("ContentBlock: block ID 14, EA, NATIVE, CRC32", source)
        self.assertIn(".BlockLength = 16u", source)
        self.assertIn(".BlockUseCrc = true", source)
        self.assertIn(".DeviceId = NVM_DEVICE_EA", source)

    # TAG ID: GEN_ARTIFACT_005
    # Why: Header macros should expose IDs, sizes, devices, and CRC choices for integrators.
    def test_GEN_ARTIFACT_005_header_contains_block_size_crc_and_device_macros(self) -> None:
        output_dir = self.make_temp_dir()

        NvMGenerator([make_block("MacroBlock", 15, device="EA", crc_type="CRC32")]).generate(output_dir)

        header = read_text(output_dir / "NvM_Cfg.h")
        self.assertIn("#define NVM_BLOCK_ID_MACRO_BLOCK (15u)", header)
        self.assertIn("#define NVM_BLOCK_SIZE_MACRO_BLOCK (16u)", header)
        self.assertIn("#define NVM_BLOCK_DEVICE_MACRO_BLOCK (NVM_DEVICE_EA)", header)
        self.assertIn("#define NVM_BLOCK_CRC_MACRO_BLOCK (NVM_CRC32)", header)

    # TAG ID: GEN_ARTIFACT_006
    # Why: Excel input must exercise the same public artifact path as JSON input.
    def test_GEN_ARTIFACT_006_excel_input_end_to_end_creates_artifacts(self) -> None:
        workspace = self.make_temp_dir()
        input_path = workspace / "blocks.xlsx"
        output_dir = workspace / "generated"
        write_excel(input_path, [base_block_record(block_name="ExcelBlock", block_id=16, ram_block_name="Ram_ExcelBlock")])

        generated_files = generate_artifacts(
            GenerationRequest(
                input_type=detect_input_type(input_path) or "",
                input_file=input_path,
                output_dir=output_dir,
            )
        )

        self.assertEqual(detect_input_type(input_path), "excel")
        for generated_file in generated_files:
            self.assertTrue(generated_file.exists(), generated_file)

    # TAG ID: GEN_ARTIFACT_007
    # Why: JSON generation into an existing directory should overwrite stale files.
    def test_GEN_ARTIFACT_007_generate_artifacts_overwrites_existing_directory_outputs(self) -> None:
        workspace = self.make_temp_dir()
        input_path = workspace / "blocks.json"
        output_dir = workspace / "generated"
        output_dir.mkdir()
        (output_dir / "NvM_Cfg.c").write_text("old source", encoding="utf-8")
        input_path.write_text(json.dumps([base_block_record(block_name="JsonBlock", block_id=17)]), encoding="utf-8")

        generate_artifacts(GenerationRequest("json", input_path, output_dir))

        self.assertNotIn("old source", read_text(output_dir / "NvM_Cfg.c"))
        self.assertIn("JsonBlock", read_text(output_dir / "NvM_Cfg.c"))
