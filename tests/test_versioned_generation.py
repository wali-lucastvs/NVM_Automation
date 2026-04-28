from __future__ import annotations

import json
from pathlib import Path
import uuid
import unittest

from nvm_tool.generator import NvMGenerator
from nvm_tool.parser import NvMConfigParser
from nvm_tool.versioning import load_version_profile
from nvm_tool.engine_versioned import generate


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
    def test_selected_versions_generate_arxml_c_and_h(self) -> None:
        parser = NvMConfigParser()
        input_path = self._write_json(sample_payload())
        blocks = parser.parse_input_file("json", input_path)

        expectations = {
            "Autosar_4_0_2": "http://autosar.org/schema/r4.0",
            "Autosar_4_1_1": "http://autosar.org/schema/r4.1",
            "Autosar_4_3_0": "http://autosar.org/schema/r4.3",
        }

        for version_key, namespace in expectations.items():
            with self.subTest(version=version_key):
                output_dir = self._make_temp_dir()
                profile = load_version_profile(version_key)
                arxml_path = generate(blocks, output_dir, profile)

                self.assertEqual(arxml_path, output_dir / "NvM.arxml")
                self.assertTrue((output_dir / "NvM.arxml").exists())
                self.assertTrue((output_dir / "NvM_Cfg.c").exists())
                self.assertTrue((output_dir / "NvM_Cfg.h").exists())

                arxml_text = (output_dir / "NvM.arxml").read_text(encoding="utf-8")
                header_text = (output_dir / "NvM_Cfg.h").read_text(encoding="utf-8")
                source_text = (output_dir / "NvM_Cfg.c").read_text(encoding="utf-8")

                self.assertIn(f'xmlns="{namespace}"', arxml_text)
                self.assertIn("NVM_NUMBER_OF_BLOCKS (1u)", header_text)
                self.assertIn("NvM_BlockDescriptorTable", source_text)

    def test_previous_arxml_merge_is_applied_before_versioned_output(self) -> None:
        parser = NvMConfigParser()
        input_path = self._write_json(sample_payload())
        previous_dir = self._make_temp_dir()
        previous_output = previous_dir / "legacy"
        previous_output.mkdir(parents=True, exist_ok=True)

        legacy_input = previous_dir / "legacy_blocks.json"
        legacy_input.write_text(
            json.dumps(
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
            encoding="utf-8",
        )
        legacy_blocks = parser.parse_input_file("json", legacy_input)
        NvMGenerator(legacy_blocks).generate(previous_output)
        previous_document = parser.parse_previous_arxml(previous_output / "NvM.arxml")

        new_blocks = parser.parse_input_file("json", input_path)
        output_dir = self._make_temp_dir()
        generate(
            new_blocks,
            output_dir,
            load_version_profile("Autosar_4_2_2"),
            previous_document=previous_document,
        )

        arxml_text = (output_dir / "NvM.arxml").read_text(encoding="utf-8")
        header_text = (output_dir / "NvM_Cfg.h").read_text(encoding="utf-8")
        self.assertIn("LegacyBlock", arxml_text)
        self.assertIn("VersionedBlock", arxml_text)
        self.assertIn("NVM_NUMBER_OF_BLOCKS (2u)", header_text)

    def test_dataset_blocks_without_crc_are_rejected(self) -> None:
        parser = NvMConfigParser()
        input_path = self._write_json(dataset_without_crc_payload())
        blocks = parser.parse_input_file("json", input_path)

        with self.assertRaisesRegex(ValueError, "must enable CRC"):
            generate(blocks, self._make_temp_dir(), load_version_profile("Autosar_4_0_2"))

    def test_unknown_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Version folder not found"):
            load_version_profile("Autosar_9_9_9")

    @staticmethod
    def _make_temp_dir() -> Path:
        temp_path = Path(__file__).resolve().parent / "_tmp" / uuid.uuid4().hex
        temp_path.mkdir(parents=True, exist_ok=False)
        return temp_path

    def _write_json(self, payload: list[dict[str, object]]) -> Path:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        return input_path


if __name__ == "__main__":
    unittest.main()
