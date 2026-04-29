from __future__ import annotations

import json
from pathlib import Path
import uuid
import unittest

from nvm_tool.parser import NvMConfigParser


class ParserTests(unittest.TestCase):
    def test_parse_json_input_returns_sorted_blocks(self) -> None:
        workspace = self._make_temp_dir()
        input_path = workspace / "blocks.json"
        input_path.write_text(
            json.dumps(
                [
                    {
                        "block_name": "Second",
                        "block_id": 9,
                        "block_size": 8,
                        "ram_block_name": "Ram_Second",
                        "device": "FEE",
                        "block_management_type": "NATIVE",
                        "use_crc": True,
                        "crc_type": "CRC16",
                        "write_protection": False,
                    },
                    {
                        "block_name": "First",
                        "block_id": 3,
                        "block_size": 4,
                        "ram_block_name": "Ram_First",
                        "device": "EA",
                        "block_management_type": "REDUNDANT",
                        "use_crc": True,
                        "crc_type": "CRC32",
                        "write_protection": True,
                    },
                ]
            ),
            encoding="utf-8",
        )

        blocks = NvMConfigParser().parse_input_file("json", input_path)
        self.assertEqual([block.block_id for block in blocks], [3, 9])

    def test_parse_previous_arxml_reads_existing_blocks(self) -> None:
        workspace = self._make_temp_dir()
        arxml_path = workspace / "NvM.arxml"
        arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        document = NvMConfigParser().parse_previous_arxml(arxml_path)

        self.assertEqual(document.namespace, "http://autosar.org/schema/r4.0")
        self.assertEqual(len(document.blocks), 1)
        self.assertEqual(document.blocks[0].block_id, 10)
        self.assertEqual(document.blocks[0].short_name, "LegacyBlock")

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
