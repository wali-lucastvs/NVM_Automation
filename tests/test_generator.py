from __future__ import annotations

import unittest
from pathlib import Path
import uuid
from xml.etree import ElementTree as ET

from nvm_tool import NvMBlock, NvMConfigParser, NvMGenerator


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
        workspace = self._make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        parser = NvMConfigParser()
        previous_document = parser.parse_previous_arxml(previous_arxml_path)

        generator = NvMGenerator(blocks=[make_block("NewBlock", 5)], previous_document=previous_document)
        generator.generate(workspace)

        merged_content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, block_ids = self._extract_container_metadata(merged_content)
        self.assertEqual(short_names, ["LegacyBlock", "NewBlock"])
        self.assertEqual(block_ids, [10, 5])

    def test_duplicate_block_id_between_previous_arxml_and_new_input_is_rejected(self) -> None:
        workspace = self._make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        parser = NvMConfigParser()
        previous_document = parser.parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block ID 10"):
            NvMGenerator(
                blocks=[make_block("FreshBlock", 10)],
                previous_document=previous_document,
            ).generate(workspace)

    def test_duplicate_block_name_between_previous_arxml_and_new_input_is_rejected(self) -> None:
        workspace = self._make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        parser = NvMConfigParser()
        previous_document = parser.parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block name 'LegacyBlock'"):
            NvMGenerator(
                blocks=[make_block("LegacyBlock", 11)],
                previous_document=previous_document,
            ).generate(workspace)

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
