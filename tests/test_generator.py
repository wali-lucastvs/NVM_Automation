"""
AUTHOR   :   S M Wali Haider Zaidi
These Test Cases are non replaceable as they are specifically designed to validate the versioned generation of NvM configurations, ensuring compliance with AUTOSAR standards and proper merging of legacy data. The tests cover critical aspects such as output generation for multiple versions, structural consistency, and input validation rules, which are essential for maintaining the integrity and functionality of the NvM tool across different AUTOSAR versions.


Tests for NvM ARXML merge behavior.

Covers:
- Merging previous ARXML with new NvM blocks
- Preservation of existing containers (NvM and non-NvM)
- Appending new block descriptors (single and multiple)
- Detection of duplicate block IDs and names across sources
- Write protection flag handling
- EA and FEE device types in merge
- CRC32 block type in merge
- Blocks with use_crc=False
- Re-merge safety (merging an already-merged file)
- Block ordering after merge
- Duplicate block names within new blocks only

Focus:
Ensures correctness of merge logic and AUTOSAR NvM constraints.
"""


from __future__ import annotations

import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from nvm_tool import NvMBlock, NvMConfigParser, NvMGenerator


def make_block(
    name: str,
    block_id: int,
    device: str = "FEE",
    use_crc: bool = True,
    crc_type: str = "CRC16",
    write_protection: bool = False,
    block_management_type: str = "NATIVE",
) -> NvMBlock:
    return NvMBlock.from_mapping(
        {
            "block_name": name,
            "block_id": block_id,
            "block_size": 16,
            "ram_block_name": f"Ram_{name}",
            "device": device,
            "block_management_type": block_management_type,
            "use_crc": use_crc,
            "crc_type": crc_type,
            "write_protection": write_protection,
        }
    )


class NvMGeneratorArxmlMergeTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # Happy path: core merge
    # ------------------------------------------------------------------

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
        self.assertCountEqual(short_names, ["LegacyBlock", "NewBlock"])
        self.assertCountEqual(block_ids, [10, 5])
        self.assertIn("Ram_NewBlock", merged_content)
        self.assertIn("NVM_CRC16", merged_content)

    def test_multiple_new_blocks_appended(self) -> None:
        """FIX: was using weak assertIn — now uses _extract_container_metadata for proper validation."""
        workspace = self._make_temp_dir()
        previous_path = workspace / "NvM.arxml"
        previous_path.write_text(self._base_arxml_with_block("Legacy", 1), encoding="utf-8")

        parser = NvMConfigParser()
        previous_doc = parser.parse_previous_arxml(previous_path)

        generator = NvMGenerator(
            blocks=[make_block("BlockA", 2), make_block("BlockB", 3)],
            previous_document=previous_doc,
        )
        generator.generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, block_ids = self._extract_container_metadata(content)

        self.assertCountEqual(short_names, ["Legacy", "BlockA", "BlockB"])
        self.assertCountEqual(block_ids, [1, 2, 3])
        self.assertIn("Ram_BlockA", content)
        self.assertIn("Ram_BlockB", content)

    # ------------------------------------------------------------------
    # Empty / minimal ARXML
    # ------------------------------------------------------------------

    def test_empty_previous_arxml_valid_nvm(self) -> None:
        path = self._make_temp_dir() / "NvM.arxml"
        path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <ELEMENTS>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>NvM</SHORT-NAME>
          <DEFINITION-REF DEST="ECUC-MODULE-DEF">/AUTOSAR/EcucDefs/NvM</DEFINITION-REF>
          <CONTAINERS/>
        </ECUC-MODULE-CONFIGURATION-VALUES>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
""", encoding="utf-8")

        parser = NvMConfigParser()
        prev = parser.parse_previous_arxml(path)
        self.assertEqual(prev.blocks, [])

    # ------------------------------------------------------------------
    # Error cases: bad ARXML input
    # ------------------------------------------------------------------


    def test_arxml_without_nvm_module_fails(self) -> None:
        path = self._make_temp_dir() / "empty.arxml"
        path.write_text("<AUTOSAR></AUTOSAR>", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "NvM ECUC-MODULE"):
            NvMConfigParser().parse_previous_arxml(path)

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------


    def test_duplicate_names_within_new_blocks(self) -> None:
        """NEW: duplicate name within new blocks only — was missing."""
        with self.assertRaises(ValueError):
            NvMGenerator(
                blocks=[make_block("SameName", 1), make_block("SameName", 2)]
            ).generate(self._make_temp_dir())

    def test_duplicate_block_id_between_previous_and_new_is_rejected(self) -> None:
        workspace = self._make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        previous_document = NvMConfigParser().parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block ID 10"):
            NvMGenerator(
                blocks=[make_block("FreshBlock", 10)],
                previous_document=previous_document,
            ).generate(workspace)

    def test_duplicate_block_name_between_previous_and_new_is_rejected(self) -> None:
        workspace = self._make_temp_dir()
        previous_arxml_path = workspace / "NvM.arxml"
        previous_arxml_path.write_text(self._base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        previous_document = NvMConfigParser().parse_previous_arxml(previous_arxml_path)

        with self.assertRaisesRegex(ValueError, "Duplicate block name 'LegacyBlock'"):
            NvMGenerator(
                blocks=[make_block("LegacyBlock", 11)],
                previous_document=previous_document,
            ).generate(workspace)

    # ------------------------------------------------------------------
    # Non-NvM container preservation
    # ------------------------------------------------------------------

    def test_non_nvm_containers_are_preserved(self) -> None:
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <ELEMENTS>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>Com</SHORT-NAME>
        </ECUC-MODULE-CONFIGURATION-VALUES>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>NvM</SHORT-NAME>
          <DEFINITION-REF DEST="ECUC-MODULE-DEF">/AUTOSAR/EcucDefs/NvM</DEFINITION-REF>
          <CONTAINERS/>
        </ECUC-MODULE-CONFIGURATION-VALUES>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
""", encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("A", 1)], previous_document=prev).generate(workspace)

        result = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        self.assertIn("Com", result)
        self.assertIn("NvM", result)
        self.assertIn("Ram_A", result)

    # ------------------------------------------------------------------
    # NEW: Block ordering
    # ------------------------------------------------------------------

    def test_legacy_blocks_appear_before_new_blocks_in_output(self) -> None:
        """NEW: legacy blocks must come before newly appended blocks."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("Legacy", 10), encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("NewBlock", 5)], previous_document=prev).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        legacy_pos = content.index("Legacy")
        new_pos = content.index("NewBlock")
        self.assertLess(legacy_pos, new_pos, "Legacy block should appear before new block in output")

    # ------------------------------------------------------------------
    # NEW: Write protection flag
    # ------------------------------------------------------------------

    def test_write_protected_block_is_merged_correctly(self) -> None:
        """NEW: write_protection=True was never tested in merge path."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("Legacy", 1), encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator(
            [make_block("ProtectedBlock", 2, write_protection=True)],
            previous_document=prev,
        ).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, block_ids = self._extract_container_metadata(content)
        self.assertIn("ProtectedBlock", short_names)
        self.assertIn(2, block_ids)

    # ------------------------------------------------------------------
    # NEW: EA device type
    # ------------------------------------------------------------------

    def test_ea_device_block_is_merged_correctly(self) -> None:
        """NEW: all previous tests used FEE — EA device path was untested."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("FeeBlock", 1), encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator(
            [make_block("EaBlock", 2, device="EA")],
            previous_document=prev,
        ).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, _ = self._extract_container_metadata(content)
        self.assertIn("EaBlock", short_names)

    # ------------------------------------------------------------------
    # NEW: CRC32 block type
    # ------------------------------------------------------------------

    def test_crc32_block_is_merged_correctly(self) -> None:
        """NEW: only CRC16 was tested before — CRC32 path was missing."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("Legacy", 1), encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator(
            [make_block("Crc32Block", 2, crc_type="CRC32")],
            previous_document=prev,
        ).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        self.assertIn("NVM_CRC32", content)

    # ------------------------------------------------------------------
    # NEW: use_crc=False
    # ------------------------------------------------------------------

    def test_block_without_crc_is_merged_correctly(self) -> None:
        """NEW: use_crc=False path was never tested — could break XML structure."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("Legacy", 1), encoding="utf-8")

        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator(
            [make_block("NoCrcBlock", 2, use_crc=False)],
            previous_document=prev,
        ).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, _ = self._extract_container_metadata(content)
        self.assertIn("NoCrcBlock", short_names)

    # ------------------------------------------------------------------
    # NEW: Re-merge safety
    # ------------------------------------------------------------------

    def test_remerge_does_not_duplicate_blocks(self) -> None:
        """NEW: merging an already-merged file must not produce duplicate blocks."""
        workspace = self._make_temp_dir()
        path = workspace / "NvM.arxml"
        path.write_text(self._base_arxml_with_block("Legacy", 1), encoding="utf-8")

        # First merge
        prev = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("BlockA", 2)], previous_document=prev).generate(workspace)

        # Second merge using the already-merged output as input
        prev2 = NvMConfigParser().parse_previous_arxml(path)
        NvMGenerator([make_block("BlockB", 3)], previous_document=prev2).generate(workspace)

        content = (workspace / "NvM.arxml").read_text(encoding="utf-8")
        short_names, block_ids = self._extract_container_metadata(content)

        # No duplicates
        self.assertEqual(len(short_names), len(set(short_names)), "Duplicate block names found after re-merge")
        self.assertEqual(len(block_ids), len(set(block_ids)), "Duplicate block IDs found after re-merge")
        self.assertCountEqual(short_names, ["Legacy", "BlockA", "BlockB"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_temp_dir(self) -> Path:
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

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
