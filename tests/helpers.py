from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from nvm_tool import NvMBlock


class TempDirTestCase(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def write_json(self, payload: list[dict[str, object]]) -> Path:
        path = self.make_temp_dir() / "blocks.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


def sample_block_payload() -> list[dict[str, object]]:
    return [base_block_record()]


def base_block_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "block_name": "GuiBlock",
        "block_id": 7,
        "block_size": 32,
        "ram_block_name": "Ram_GuiBlock",
        "device": "FEE",
        "block_management_type": "NATIVE",
        "use_crc": True,
        "crc_type": "CRC16",
        "write_protection": False,
    }
    record.update(overrides)
    return record


def versioned_block_payload() -> list[dict[str, object]]:
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


def dataset_block_payload(use_crc: bool = True) -> list[dict[str, object]]:
    return [
        {
            "block_name": "DatasetBlock",
            "block_id": 22,
            "block_size": 16,
            "ram_block_name": "Ram_DatasetBlock",
            "device": "EA",
            "block_management_type": "DATASET",
            "use_crc": use_crc,
            "crc_type": "CRC16",
            "write_protection": False,
        }
    ]


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


def base_arxml_with_block(short_name: str, block_id: int) -> str:
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


def empty_nvm_arxml() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
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
"""


def arxml_with_com_and_empty_nvm() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
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
"""


def arxml_with_direct_write_protection(short_name: str, block_id: int) -> str:
    return base_arxml_with_block(short_name, block_id).replace(
        """                <ECUC-NUMERICAL-PARAM-VALUE>
                  <DEFINITION-REF DEST="ECUC-BOOLEAN-PARAM-DEF">/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockWriteProt</DEFINITION-REF>
                  <VALUE>0</VALUE>
                </ECUC-NUMERICAL-PARAM-VALUE>""",
        "<WRITE-PROTECTION>true</WRITE-PROTECTION>",
    )


def arxml_with_multiple_packages() -> str:
    first = base_arxml_with_block("FirstPackageBlock", 3)
    second = """<?xml version="1.0" encoding="utf-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>ComPackage</SHORT-NAME>
      <ELEMENTS>
        <ECUC-MODULE-CONFIGURATION-VALUES>
          <SHORT-NAME>Com</SHORT-NAME>
        </ECUC-MODULE-CONFIGURATION-VALUES>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
"""
    first_root = ET.fromstring(first)
    second_root = ET.fromstring(second)
    first_packages = next(e for e in first_root.iter() if e.tag.split("}", 1)[-1] == "AR-PACKAGES")
    second_package = next(e for e in second_root.iter() if e.tag.split("}", 1)[-1] == "AR-PACKAGE")
    first_packages.append(second_package)
    tree = ET.ElementTree(first_root)
    ET.indent(tree, space="  ")
    return ET.tostring(first_root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"


def write_excel(path: Path, rows: list[dict[str, object]]) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    headers = list(base_block_record().keys())
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header) for header in headers])
    workbook.save(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_container_metadata(arxml_text: str) -> tuple[list[str], list[int]]:
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
                block_id = _extract_block_id(child)

        if definition_ref == "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor":
            short_names.append(short_name or "")
            if block_id is not None:
                block_ids.append(block_id)

    return short_names, block_ids


def normalized_xml_shape(element: ET.Element):
    def clean_attrib(attrib: dict) -> tuple:
        filtered = {}
        for key, value in attrib.items():
            if key.endswith("schemaLocation"):
                continue
            filtered[key] = " ".join(value.split()) if isinstance(value, str) else value
        return tuple(sorted(filtered.items()))

    return (
        element.tag.split("}", 1)[-1],
        (element.text or "").strip(),
        clean_attrib(element.attrib),
        [normalized_xml_shape(child) for child in list(element)],
    )


def _extract_block_id(parameter_values: ET.Element) -> int | None:
    for parameter in parameter_values:
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
            return int(parameter_value or 0)

    return None
