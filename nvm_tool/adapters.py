from __future__ import annotations

from typing import Iterable
from xml.etree import ElementTree as ET

from .config import VersionProfile
from .models import (
    AUTOSAR_XSI_NAMESPACE,
    NVM_BLOCK_CONTAINER_DEFINITION_REF,
    NVM_BLOCK_CRC_TYPE_DEFINITION_REF,
    NVM_MODULE_DEFINITION_REF,
    NvMBlock,
    ParameterDefinition,
)


FEATURES = {
    "4.0.2": {
        "crc": True,
        "dataset_blocks": True,
        "nv_block_base_number": True,
        "short_name_required": True,
    },
    "4.2.2": {
        "crc": True,
        "dataset_blocks": True,
        "nv_block_base_number": True,
        "short_name_required": True,
    },
    "4.3.0": {
        "crc": True,
        "dataset_blocks": True,
        "nv_block_base_number": True,
        "short_name_required": True,
    },
}


class NvMVersionAdapter:
    """Build version-specific AUTOSAR NvM ARXML using a shared internal model."""

    def __init__(self, profile: VersionProfile) -> None:
        self.profile = profile

    @property
    def version(self) -> str:
        return self.profile.version

    @property
    def namespace(self) -> str:
        return self.profile.namespace

    @property
    def feature_flags(self) -> dict:
        merged = dict(FEATURES.get(self.version, {}))
        merged.update(self.profile.features)
        if "nvm_crc_support" in merged and "crc" not in merged:
            merged["crc"] = merged["nvm_crc_support"]
        return merged

    def build_document(self, blocks: Iterable[NvMBlock]) -> ET.ElementTree:
        root = ET.Element(self._tag("AUTOSAR"))
        root.set(f"{{{AUTOSAR_XSI_NAMESPACE}}}schemaLocation", self.schema_location)

        ar_packages = ET.SubElement(root, self._tag("AR-PACKAGES"))
        ar_package = ET.SubElement(ar_packages, self._tag("AR-PACKAGE"))
        ET.SubElement(ar_package, self._tag("SHORT-NAME")).text = "NvM"
        elements = ET.SubElement(ar_package, self._tag("ELEMENTS"))

        module_configuration = ET.SubElement(
            elements,
            self._tag("ECUC-MODULE-CONFIGURATION-VALUES"),
        )

        definition_ref = ET.SubElement(module_configuration, self._tag("DEFINITION-REF"))
        definition_ref.set("DEST", "ECUC-MODULE-DEF")
        definition_ref.text = NVM_MODULE_DEFINITION_REF

        containers = ET.SubElement(module_configuration, self._tag("CONTAINERS"))
        for block in blocks:
            self.validate_block(block)
            containers.append(self.generate_block(block))

        tree = ET.ElementTree(root)
        return tree

    @property
    def schema_location(self) -> str:
        return f"{self.namespace} {self.profile.xsd_name}"

    def validate_block(self, block: NvMBlock) -> None:
        if self.feature_flags.get("short_name_required", True) and not block.short_name:
            raise ValueError(f"{block.block_name}: SHORT-NAME is required for AUTOSAR {self.version}.")

        if (
            not self.feature_flags.get("dataset_blocks", True)
            and block.block_management_type == "DATASET"
        ):
            raise ValueError(
                f"{block.block_name}: DATASET blocks are not supported in AUTOSAR {self.version}."
            )

    def generate_block(self, block: NvMBlock) -> ET.Element:
        container = ET.Element(self._tag("ECUC-CONTAINER-VALUE"))
        ET.SubElement(container, self._tag("SHORT-NAME")).text = block.short_name

        definition_ref = ET.SubElement(container, self._tag("DEFINITION-REF"))
        definition_ref.set("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        definition_ref.text = NVM_BLOCK_CONTAINER_DEFINITION_REF

        parameter_values = ET.SubElement(container, self._tag("PARAMETER-VALUES"))
        parameter_map = block.autosar_parameter_values()
        for definition in self.parameter_definitions(block):
            value = parameter_map.get(definition.definition_ref)
            if value is None:
                continue
            parameter = ET.SubElement(
                parameter_values,
                self._tag(self._parameter_tag_name(definition)),
            )
            self._write_parameter_value(parameter, definition, value)

        return container

    def parameter_definitions(self, block: NvMBlock) -> Iterable[ParameterDefinition]:
        for definition in NvMBlock.STANDARD_PARAMETER_DEFINITIONS:
            if definition.definition_ref == NVM_BLOCK_CRC_TYPE_DEFINITION_REF:
                if not self.feature_flags.get("crc", False) or not block.use_crc:
                    continue
            yield definition

    def _write_parameter_value(
        self,
        parameter_element: ET.Element,
        definition: ParameterDefinition,
        value: str,
    ) -> None:
        definition_ref = ET.SubElement(parameter_element, self._tag("DEFINITION-REF"))
        definition_ref.set("DEST", definition.dest)
        definition_ref.text = definition.definition_ref
        value_element = ET.SubElement(parameter_element, self._tag("VALUE"))
        value_element.text = value

    def _parameter_tag_name(self, definition: ParameterDefinition) -> str:
        if definition.value_kind == "numerical":
            return "ECUC-NUMERICAL-PARAM-VALUE"
        return "ECUC-TEXTUAL-PARAM-VALUE"

    def _tag(self, local_name: str) -> str:
        return f"{{{self.namespace}}}{local_name}"


class NvM_v402_Adapter(NvMVersionAdapter):
    """Preserve the current 4.0.2 NvM block structure."""


class NvM_v422_Adapter(NvMVersionAdapter):
    """4.2.2 adapter with mandatory SHORT-NAME and feature-driven CRC emission."""


class NvM_v430_Adapter(NvMVersionAdapter):
    """4.3.0 adapter reusing the common R4.x ECUC layout."""


VERSION_REGISTRY = {
    "4.0.2": NvM_v402_Adapter,
    "4.2.2": NvM_v422_Adapter,
    "4.3.0": NvM_v430_Adapter,
}


def get_version_adapter(profile: VersionProfile) -> NvMVersionAdapter:
    adapter_cls = VERSION_REGISTRY.get(profile.version)
    if adapter_cls is None:
        return NvMVersionAdapter(profile)
    return adapter_cls(profile)


def register_adapter(version: str, adapter_cls: type[NvMVersionAdapter]) -> None:
    VERSION_REGISTRY[version] = adapter_cls
