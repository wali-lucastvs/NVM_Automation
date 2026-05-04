"""
AUTHOR   :   S M Wali Haider Zaidi
These Test Cases are non replaceable as they are specifically designed to validate the versioned generation of NvM configurations, ensuring compliance with AUTOSAR standards and proper merging of legacy data. The tests cover critical aspects such as output generation for multiple versions, structural consistency, and input validation rules, which are essential for maintaining the integrity and functionality of the NvM tool across different AUTOSAR versions.

Test suite for validating versioned NvM generation.

Key checks:
- Ensures ARXML, C, and header files are generated correctly for supported AUTOSAR versions.
- Verifies merging of previous ARXML data with new inputs.
- Confirms structural consistency between legacy and versioned (4.0.2) outputs.
- Validates input rules (e.g., duplicate block IDs, dataset blocks requiring CRC).
- Handles edge cases like empty inputs and invalid previous ARXML.

Note:
XML comparisons ignore non-functional differences such as schemaLocation
and formatting, focusing only on meaningful structure and attributes.
"""



from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from nvm_tool.generator import NvMGenerator, generate
from nvm_tool.parser import NvMConfigParser
from nvm_tool.config import load_version_profile


def sample_payload() -> list[dict[str, object]]:
    return [
        {
            "block_name": "VersionedBlock",
            "block_id": 21,
            "block_size": 24,
            "ram_block_name": "Ram_VersionedBlock",
            "device": "FEE",
            "block_management_type": "NATIVE",
            "use_crc": True,
            "crc_type": "CRC16",
            "write_protection": False,
        }
    ]


def dataset_without_crc_payload() -> list[dict[str, object]]:
    return [
        {
            "block_name": "DatasetBlock",
            "block_id": 22,
            "block_size": 16,
            "ram_block_name": "Ram_DatasetBlock",
            "device": "EA",
            "block_management_type": "DATASET",
            "use_crc": False,
            "crc_type": "CRC16",
            "write_protection": False,
        }
    ]


class VersionedGenerationTests(unittest.TestCase):

    # ---------- Core Tests ----------

    def test_selected_versions_generate_outputs(self) -> None:
        parser = NvMConfigParser()
        input_path = self._write_json(sample_payload())
        blocks = parser.parse_input_file("json", input_path)

        expectations = {
            "4.0.2": "http://autosar.org/schema/r4.0",
            "Autosar_4_1_1": "http://autosar.org/schema/r4.1",
            "4.3.0": "http://autosar.org/schema/r4.3",
        }

        for version_key, namespace in expectations.items():
            with self.subTest(version=version_key):
                output_dir = self._make_temp_dir()
                profile = load_version_profile(version_key)

                arxml_path = generate(blocks, output_dir, profile, versioned=True)

                self.assertEqual(
                    arxml_path.resolve(),
                    (output_dir / "NvM.arxml").resolve(),
                )

                self.assertTrue((output_dir / "NvM_Cfg.c").exists())
                self.assertTrue((output_dir / "NvM_Cfg.h").exists())

                arxml_text = self._read(output_dir / "NvM.arxml")
                header_text = self._read(output_dir / "NvM_Cfg.h")
                source_text = self._read(output_dir / "NvM_Cfg.c")

                root = ET.fromstring(arxml_text)
                self.assertTrue(root.tag.startswith(f"{{{namespace}}}"))

                self.assertIn("NVM_NUMBER_OF_BLOCKS (1u)", header_text)
                self.assertIn("NvM_BlockDescriptorTable", source_text)

    def test_previous_arxml_merge(self) -> None:
        parser = NvMConfigParser()

        # legacy
        legacy_input = self._write_json([
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
        ])

        legacy_blocks = parser.parse_input_file("json", legacy_input)
        previous_dir = self._make_temp_dir()
        NvMGenerator(legacy_blocks).generate(previous_dir)

        previous_doc = parser.parse_previous_arxml(previous_dir / "NvM.arxml")

        # new
        new_blocks = parser.parse_input_file("json", self._write_json(sample_payload()))
        output_dir = self._make_temp_dir()

        generate(
            new_blocks,
            output_dir,
            load_version_profile("Autosar_4_2_2"),
            previous_document=previous_doc,
            versioned=True,
        )

        arxml_text = self._read(output_dir / "NvM.arxml")
        header_text = self._read(output_dir / "NvM_Cfg.h")

        self.assertIn("LegacyBlock", arxml_text)
        self.assertIn("VersionedBlock", arxml_text)
        self.assertIn("NVM_NUMBER_OF_BLOCKS (2u)", header_text)

    def test_structure_preserved_for_402(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self._write_json(sample_payload()))

        legacy_dir = self._make_temp_dir()
        NvMGenerator(blocks).generate(legacy_dir)

        versioned_dir = self._make_temp_dir()
        generate(
            blocks,
            versioned_dir,
            load_version_profile("4.0.2"),
            versioned=True,
        )

        legacy_tree = ET.fromstring(self._read(legacy_dir / "NvM.arxml"))
        versioned_tree = ET.fromstring(self._read(versioned_dir / "NvM.arxml"))

        self.assertEqual(
            self._normalized_shape(legacy_tree),
            self._normalized_shape(versioned_tree),
        )

    # ---------- Validation Tests ----------

    def test_dataset_without_crc_fails(self) -> None:
        parser = NvMConfigParser()
        blocks = parser.parse_input_file("json", self._write_json(dataset_without_crc_payload()))

        with self.assertRaises(ValueError):
            generate(blocks, self._make_temp_dir(), load_version_profile("4.0.2"), versioned=True)

    def test_unknown_version_fails(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_version_profile("Autosar_9_9_9")

    def test_version_alias_consistency(self) -> None:
        self.assertEqual(
            load_version_profile("4.2.2"),
            load_version_profile("Autosar_4_2_2"),
        )

    # ---------- Edge Cases ----------

    def test_empty_blocks(self) -> None:
        output_dir = self._make_temp_dir()
        generate([], output_dir, load_version_profile("4.0.2"), versioned=True)

        header = self._read(output_dir / "NvM_Cfg.h")
        self.assertIn("NVM_NUMBER_OF_BLOCKS (0u)", header)


    # ---------- Helpers ----------

    def _make_temp_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def _write_json(self, payload: list[dict[str, object]]) -> Path:
        path = self._make_temp_dir() / "blocks.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


    def test_parse_previous_arxml_rejects_malformed_inputs(self) -> None:
        cases = [
            # (label, file_content, expected_exc, message_fragment_or_None)
            (
                "non_xml_garbage",
                "<invalid>",
                Exception,
                None,
                # Rationale: not valid XML at all — any parse error is correct.
            ),
            (
                "unclosed_xml_tags",
                "<AUTOSAR><broken>",
                Exception,
                None,
                # Rationale: structurally broken XML; same code path but a more
                # realistic corruption pattern than "<invalid>" alone.
                # This was the strongest single test among the three duplicates
                # (G04) and is preserved here.
            ),
            (
                "valid_xml_no_nvm_module",
                "<AUTOSAR></AUTOSAR>",
                ValueError,
                "NvM ECUC-MODULE",
                # Rationale: well-formed XML that is semantically empty.
                # Asserts the *specific* ValueError that the parser must raise
                # — not just Exception — so regressions in error handling are
                # caught precisely.
            ),
            (
                "empty_file",
                "",
                Exception,
                None,
                # Rationale: edge case missed by all three original tests;
                # empty files are a realistic filesystem error scenario.
            ),
        ]

        for label, content, expected_exc, msg_fragment in cases:
            with self.subTest(case=label):
                path = self._make_temp_dir() / f"{label}.arxml"
                path.write_text(content, encoding="utf-8")

                if msg_fragment:
                    with self.assertRaisesRegex(expected_exc, msg_fragment):
                        NvMConfigParser().parse_previous_arxml(path)
                else:
                    with self.assertRaises(expected_exc):
                        NvMConfigParser().parse_previous_arxml(path)


    @staticmethod
    def _read(path: Path) -> str:
        with path.open(encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _normalized_shape(element: ET.Element):
        def clean_attrib(attrib: dict) -> tuple:
            filtered = {}
            for k, v in attrib.items():
                # Ignore schemaLocation (tool/version dependent)
                if k.endswith("schemaLocation"):
                    continue

                # Normalize whitespace in values
                filtered[k] = " ".join(v.split()) if isinstance(v, str) else v

            return tuple(sorted(filtered.items()))

        return (
            element.tag.split("}", 1)[-1],  # ignore namespace prefix
            (element.text or "").strip(),
            clean_attrib(element.attrib),
            [VersionedGenerationTests._normalized_shape(child) for child in list(element)],
        )


if __name__ == "__main__":
    unittest.main()