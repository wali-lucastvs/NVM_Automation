from __future__ import annotations


VERSION_ALIASES = {
    "4.0.1": "Autosar_4_0_1",
    "4.0.2": "Autosar_4_0_2",
    "4.0.3": "Autosar_4_0_3",
    "4.1.1": "Autosar_4_1_1",
    "4.1.2": "Autosar_4_1_2",
    "4.1.3": "Autosar_4_1_3",
    "4.2.1": "Autosar_4_2_1",
    "4.2.2": "Autosar_4_2_2",
    "4.3.0": "Autosar_4_3_0",
}


def normalize_version_key(version: str) -> str:
    return VERSION_ALIASES.get(version, version)


def canonical_version_label(version_key: str) -> str:
    if version_key.count(".") == 2:
        return version_key
    return version_key.replace("Autosar_", "").replace("_", ".")
