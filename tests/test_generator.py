from __future__ import annotations

import unittest
from pathlib import Path
import uuid
from xml.etree import ElementTree as ET

from nvm_tool import NvMBlock, NvMGenerator


def make_block(name: str, block_id: int) -> NvMBlock:
    return NvMBlock.from_mapping(
        {
            "block_name": name,
            "block_id": block_id,
            "block_size": 16,
            "ram_block_name": f"Ram_{name}",
            "device": "FEE",
            "block_management_type": "NATIVE",
            "use_crc": True,
            "crc_type": "CRC16",
            "write_protection": False,
        }
    )


class NvMGeneratorArxmlMergeTests(unittest.TestCase):
    def test_previous_arxml_containers_are_preserved_and_new_blocks_are_appended(self) -> None:
        temp_path = self._make_temp_dir()
        previous_arxml = temp_path / "previous.arxml"
        previous_arxml.write_text(
            NvMGenerator(blocks=[make_block("ExistingBlock", 2)]).render_arxml(),
            encoding="utf-8",
        )

        merged_arxml = NvMGenerator(
            blocks=[make_block("NewBlock", 5)],
            previous_arxml=previous_arxml,
        ).render_arxml()

        short_names, block_ids = self._extract_container_metadata(merged_arxml)
        self.assertEqual(short_names, ["ExistingBlock", "NewBlock"])
        self.assertEqual(block_ids, [2, 5])

    def test_previous_arxml_duplicate_block_id_is_rejected(self) -> None:
        temp_path = self._make_temp_dir()
        previous_arxml = temp_path / "previous.arxml"
        previous_arxml.write_text(
            NvMGenerator(blocks=[make_block("ExistingBlock", 2)]).render_arxml(),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "block_id '2'"):
            NvMGenerator(
                blocks=[make_block("NewBlock", 2)],
                previous_arxml=previous_arxml,
            ).render_arxml()

    @staticmethod
    def _make_temp_dir() -> Path:
        temp_path = Path(__file__).resolve().parent / "_tmp" / uuid.uuid4().hex
        temp_path.mkdir(parents=True, exist_ok=False)
        return temp_path

    @staticmethod
    def _extract_container_metadata(arxml_text: str) -> tuple[list[str], list[int]]:
        root = ET.fromstring(arxml_text)
        short_names: list[str] = []
        block_ids: list[int] = []

        for container in root.iter():
            if container.tag.split("}", 1)[-1] != "ECUC-CONTAINER-VALUE":
                continue

            definition_ref = None
            short_name = None
            block_id = None

            for child in container:
                local_name = child.tag.split("}", 1)[-1]
                if local_name == "SHORT-NAME":
                    short_name = child.text
                elif local_name == "DEFINITION-REF":
                    definition_ref = child.text
                elif local_name == "PARAMETER-VALUES":
                    for parameter in child:
                        parameter_definition = None
                        parameter_value = None
                        for parameter_child in parameter:
                            parameter_child_name = parameter_child.tag.split("}", 1)[-1]
                            if parameter_child_name == "DEFINITION-REF":
                                parameter_definition = parameter_child.text
                            elif parameter_child_name == "VALUE":
                                parameter_value = parameter_child.text
                        if (
                            parameter_definition
                            == "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramBlockIdentifier"
                        ):
                            block_id = int(parameter_value)

            if definition_ref == "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor":
                short_names.append(short_name)
                block_ids.append(block_id)

        return short_names, block_ids


if __name__ == "__main__":
    unittest.main()
