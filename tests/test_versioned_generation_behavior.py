from __future__ import annotations

import xml.etree.ElementTree as ET

from nvm_tool.config import load_version_profile
from nvm_tool.generator import NvMGenerator, generate
from nvm_tool.parser import NvMConfigParser
from tests.helpers import (
    TempDirTestCase,
    arxml_with_com_and_empty_nvm,
    base_arxml_with_block,
    dataset_block_payload,
    normalized_xml_shape,
    read_text,
    versioned_block_payload,
)


class VersionProfileTests(TempDirTestCase):
    # TAG ID: VERSION_PROFILE_001
    # Why: Unknown version keys should fail clearly instead of falling back silently.
    def test_VERSION_PROFILE_001_unknown_version_fails(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_version_profile("Autosar_9_9_9")

    # TAG ID: VERSION_PROFILE_002
    # Why: Human-friendly aliases and folder keys must resolve to the same profile.
    def test_VERSION_PROFILE_002_version_aliases_are_consistent(self) -> None:
        self.assertEqual(
            load_version_profile("4.2.2"),
            load_version_profile("Autosar_4_2_2"),
        )


class VersionedGenerationTests(TempDirTestCase):
    # TAG ID: VERSION_GEN_001
    # Why: Supported AUTOSAR versions must generate ARXML, C, and header outputs.
    def test_VERSION_GEN_001_selected_versions_generate_expected_outputs(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        expectations = {
            "4.0.2": "http://autosar.org/schema/r4.0",
            "Autosar_4_1_1": "http://autosar.org/schema/r4.1",
            "4.3.0": "http://autosar.org/schema/r4.3",
        }

        for version_key, namespace in expectations.items():
            with self.subTest(version=version_key):
                output_dir = self.make_temp_dir()
                arxml_path = generate(
                    blocks,
                    output_dir,
                    load_version_profile(version_key),
                    versioned=True,
                )

                self.assertEqual(arxml_path.resolve(), (output_dir / "NvM.arxml").resolve())
                self.assertTrue((output_dir / "NvM_Cfg.c").exists())
                self.assertTrue((output_dir / "NvM_Cfg.h").exists())

                arxml_text = read_text(output_dir / "NvM.arxml")
                header_text = read_text(output_dir / "NvM_Cfg.h")
                source_text = read_text(output_dir / "NvM_Cfg.c")
                root = ET.fromstring(arxml_text)

                self.assertTrue(root.tag.startswith(f"{{{namespace}}}"))
                self.assertIn("NVM_NUMBER_OF_BLOCKS (1u)", header_text)
                self.assertIn("NvM_BlockDescriptorTable", source_text)

    # TAG ID: VERSION_GEN_002
    # Why: Versioned merge must include both legacy and newly supplied blocks.
    def test_VERSION_GEN_002_previous_arxml_merge_preserves_legacy_and_new_blocks(self) -> None:
        parser = NvMConfigParser()
        legacy_blocks = parser.parse_input_file(
            "json",
            self.write_json(
                [
                    {
                        "block_name": "LegacyBlock",
                        "block_id": 10,
                        "block_size": 8,
                        "ram_block_name": "Ram_LegacyBlock",
                        "device": "FEE",
                        "block_management_type": "NATIVE",
                        "use_crc": True,
                        "crc_type": "CRC16",
                        "write_protection": False,
                    }
                ]
            ),
        )
        previous_dir = self.make_temp_dir()
        NvMGenerator(legacy_blocks).generate(previous_dir)
        previous_document = parser.parse_previous_arxml(previous_dir / "NvM.arxml")
        new_blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        output_dir = self.make_temp_dir()

        generate(
            new_blocks,
            output_dir,
            load_version_profile("Autosar_4_2_2"),
            previous_document=previous_document,
            versioned=True,
        )

        arxml_text = read_text(output_dir / "NvM.arxml")
        header_text = read_text(output_dir / "NvM_Cfg.h")
        self.assertIn("LegacyBlock", arxml_text)
        self.assertIn("VersionedBlock", arxml_text)
        self.assertIn("NVM_NUMBER_OF_BLOCKS (2u)", header_text)

    # TAG ID: VERSION_GEN_003
    # Why: AUTOSAR 4.0.2 versioned output should preserve the legacy structure shape.
    def test_VERSION_GEN_003_structure_is_preserved_for_autosar_402(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        legacy_dir = self.make_temp_dir()
        versioned_dir = self.make_temp_dir()

        NvMGenerator(blocks).generate(legacy_dir)
        generate(
            blocks,
            versioned_dir,
            load_version_profile("4.0.2"),
            versioned=True,
        )

        legacy_tree = ET.fromstring(read_text(legacy_dir / "NvM.arxml"))
        versioned_tree = ET.fromstring(read_text(versioned_dir / "NvM.arxml"))
        self.assertEqual(normalized_xml_shape(legacy_tree), normalized_xml_shape(versioned_tree))

    # TAG ID: VERSION_GEN_004
    # Why: Empty generation is useful for template validation and should report zero blocks.
    def test_VERSION_GEN_004_empty_blocks_generate_zero_block_header(self) -> None:
        output_dir = self.make_temp_dir()

        generate([], output_dir, load_version_profile("4.0.2"), versioned=True)

        self.assertIn("NVM_NUMBER_OF_BLOCKS (0u)", read_text(output_dir / "NvM_Cfg.h"))

    # TAG ID: VERSION_GEN_005
    # Why: AUTOSAR 4.2.2 output must use the configured 4.2 namespace.
    def test_VERSION_GEN_005_autosar_422_namespace_is_rendered(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        output_dir = self.make_temp_dir()

        generate(blocks, output_dir, load_version_profile("4.2.2"), versioned=True)

        root = ET.fromstring(read_text(output_dir / "NvM.arxml"))
        self.assertTrue(root.tag.startswith("{http://autosar.org/schema/r4.2}"))

    # TAG ID: VERSION_GEN_006
    # Why: Versioned merge output should keep legacy blocks before newly generated blocks.
    def test_VERSION_GEN_006_legacy_blocks_appear_before_new_blocks(self) -> None:
        parser = NvMConfigParser()
        previous_dir = self.make_temp_dir()
        previous_path = previous_dir / "NvM.arxml"
        previous_path.write_text(base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")
        previous_document = parser.parse_previous_arxml(previous_path)
        new_blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        output_dir = self.make_temp_dir()

        generate(
            new_blocks,
            output_dir,
            load_version_profile("4.2.2"),
            previous_document=previous_document,
            versioned=True,
        )

        arxml = read_text(output_dir / "NvM.arxml")
        self.assertLess(arxml.index("LegacyBlock"), arxml.index("VersionedBlock"))

    # TAG ID: VERSION_GEN_007
    # Why: Versioned output must not discard unrelated AUTOSAR containers from previous ARXML.
    def test_VERSION_GEN_007_non_nvm_container_is_preserved_in_versioned_output(self) -> None:
        parser = NvMConfigParser()
        previous_path = self.make_temp_dir() / "NvM.arxml"
        previous_path.write_text(arxml_with_com_and_empty_nvm(), encoding="utf-8")
        previous_document = parser.parse_previous_arxml(previous_path)
        blocks = parser.parse_input_file("json", self.write_json(versioned_block_payload()))
        output_dir = self.make_temp_dir()

        generate(
            blocks,
            output_dir,
            load_version_profile("4.2.2"),
            previous_document=previous_document,
            versioned=True,
        )

        arxml = read_text(output_dir / "NvM.arxml")
        self.assertIn("<SHORT-NAME>Com</SHORT-NAME>", arxml)
        self.assertIn("<SHORT-NAME>NvM</SHORT-NAME>", arxml)


class VersionedValidationTests(TempDirTestCase):
    # TAG ID: VALIDATION_001
    # Why: DATASET blocks rely on CRC for valid versioned generation.
    def test_VALIDATION_001_dataset_without_crc_fails(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self.write_json(dataset_block_payload(use_crc=False)))

        with self.assertRaises(ValueError):
            generate(blocks, self.make_temp_dir(), load_version_profile("4.0.2"), versioned=True)

    # TAG ID: VALIDATION_002
    # Why: DATASET blocks with CRC enabled are the intended success path.
    def test_VALIDATION_002_dataset_block_with_crc_passes_versioned_generate(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self.write_json(dataset_block_payload(use_crc=True)))
        output_dir = self.make_temp_dir()

        generate(
            blocks,
            output_dir,
            load_version_profile("4.0.2"),
            versioned=True,
        )

        self.assertIn("DatasetBlock", read_text(output_dir / "NvM.arxml"))
        self.assertIn("NVM_NUMBER_OF_BLOCKS (1u)", read_text(output_dir / "NvM_Cfg.h"))

    # TAG ID: VALIDATION_003
    # Why: Missing input files should fail before artifact paths are reported.
    def test_VALIDATION_003_generate_artifacts_invalid_input_fails(self) -> None:
        from pathlib import Path

        from nvm_tool.models import GenerationRequest, generate_artifacts

        with self.assertRaises(Exception):
            generate_artifacts(
                GenerationRequest(
                    input_type="json",
                    input_file=Path("nonexistent.json"),
                    output_dir=Path("out"),
                )
            )
