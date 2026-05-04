from __future__ import annotations

import json

from nvm_tool.parser import NvMConfigParser
from tests.helpers import (
    TempDirTestCase,
    arxml_with_direct_write_protection,
    arxml_with_multiple_packages,
    base_arxml_with_block,
    empty_nvm_arxml,
)


class ParserJsonInputTests(TempDirTestCase):
    # TAG ID: PARSER_JSON_001
    # Why: Parser output ordering determines deterministic generated artifacts.
    def test_PARSER_JSON_001_parse_json_input_returns_sorted_blocks(self) -> None:
        workspace = self.make_temp_dir()
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

        self.assertEqual([(b.block_id, b.block_name) for b in blocks], [(3, "First"), (9, "Second")])

    # TAG ID: PARSER_JSON_002
    # Why: Missing required fields should fail at parse time with a clear error.
    def test_PARSER_JSON_002_missing_required_field_fails(self) -> None:
        path = self.make_temp_dir() / "bad.json"
        path.write_text(json.dumps([{"block_name": "A"}]), encoding="utf-8")

        with self.assertRaises(Exception):
            NvMConfigParser().parse_input_file("json", path)

    # TAG ID: PARSER_JSON_003
    # Why: Empty input files should not produce empty but valid-looking configurations.
    def test_PARSER_JSON_003_empty_input_fails(self) -> None:
        path = self.make_temp_dir() / "empty.json"
        path.write_text("[]", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "NvM blocks"):
            NvMConfigParser().parse_input_file("json", path)


class ParserArxmlInputTests(TempDirTestCase):
    # TAG ID: PARSER_ARXML_001
    # Why: Existing NvM blocks must be recovered accurately for merge/update workflows.
    def test_PARSER_ARXML_001_parse_previous_arxml_reads_existing_blocks(self) -> None:
        workspace = self.make_temp_dir()
        arxml_path = workspace / "NvM.arxml"
        arxml_path.write_text(base_arxml_with_block("LegacyBlock", 10), encoding="utf-8")

        document = NvMConfigParser().parse_previous_arxml(arxml_path)

        self.assertTrue(document.namespace.startswith("http://autosar.org/schema/"))
        block = document.blocks[0]
        self.assertEqual(block.block_size, 8)
        self.assertTrue(block.use_crc)
        self.assertEqual(block.crc_type, "CRC16")
        self.assertEqual(block.ram_block_name, "Ram_LegacyBlock")

    # TAG ID: PARSER_ARXML_002
    # Why: Empty NvM modules are valid starting points for update flows.
    def test_PARSER_ARXML_002_empty_previous_arxml_with_nvm_module_is_valid(self) -> None:
        path = self.make_temp_dir() / "NvM.arxml"
        path.write_text(empty_nvm_arxml(), encoding="utf-8")

        previous_document = NvMConfigParser().parse_previous_arxml(path)

        self.assertEqual(previous_document.blocks, [])

    # TAG ID: PARSER_ARXML_003
    # Why: Semantically empty ARXML should fail instead of silently dropping previous data.
    def test_PARSER_ARXML_003_arxml_without_nvm_module_fails(self) -> None:
        path = self.make_temp_dir() / "empty.arxml"
        path.write_text("<AUTOSAR></AUTOSAR>", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "NvM ECUC-MODULE"):
            NvMConfigParser().parse_previous_arxml(path)

    # TAG ID: PARSER_ARXML_004
    # Why: Malformed ARXML cases should be rejected consistently and precisely.
    def test_PARSER_ARXML_004_malformed_inputs_are_rejected(self) -> None:
        cases = [
            ("non_xml_garbage", "<invalid>", Exception, None),
            ("unclosed_xml_tags", "<AUTOSAR><broken>", Exception, None),
            ("valid_xml_no_nvm_module", "<AUTOSAR></AUTOSAR>", ValueError, "NvM ECUC-MODULE"),
            ("empty_file", "", Exception, None),
        ]

        for label, content, expected_exc, msg_fragment in cases:
            with self.subTest(case=label):
                path = self.make_temp_dir() / f"{label}.arxml"
                path.write_text(content, encoding="utf-8")

                if msg_fragment:
                    with self.assertRaisesRegex(expected_exc, msg_fragment):
                        NvMConfigParser().parse_previous_arxml(path)
                else:
                    with self.assertRaises(expected_exc):
                        NvMConfigParser().parse_previous_arxml(path)

    # TAG ID: PARSER_ARXML_005
    # Why: Some legacy ARXML exports represent write protection as a direct tag.
    def test_PARSER_ARXML_005_direct_write_protection_tag_maps_to_boolean(self) -> None:
        path = self.make_temp_dir() / "NvM.arxml"
        path.write_text(arxml_with_direct_write_protection("ProtectedLegacy", 12), encoding="utf-8")

        document = NvMConfigParser().parse_previous_arxml(path)

        self.assertTrue(document.blocks[0].write_protection)

    # TAG ID: PARSER_ARXML_006
    # Why: Real AUTOSAR files can contain several AR-PACKAGE nodes around the NvM package.
    def test_PARSER_ARXML_006_multiple_ar_packages_do_not_hide_nvm_blocks(self) -> None:
        path = self.make_temp_dir() / "NvM.arxml"
        path.write_text(arxml_with_multiple_packages(), encoding="utf-8")

        document = NvMConfigParser().parse_previous_arxml(path)

        self.assertEqual([block.block_name for block in document.blocks], ["FirstPackageBlock"])
