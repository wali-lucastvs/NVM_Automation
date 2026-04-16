from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Optional, Tuple


_C_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _normalize_short_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", value.strip())
    if not sanitized:
        raise ValueError("NvM block name must not be empty.")
    if sanitized[0].isdigit():
        sanitized = f"NvM_{sanitized}"
    return sanitized


def _to_macro_token(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value.strip())
    token = re.sub(r"[^A-Za-z0-9_]", "_", value).upper()
    token = re.sub(r"_+", "_", token).strip("_")
    if not token:
        raise ValueError("Unable to derive a symbolic name from block_name.")
    if token[0].isdigit():
        token = f"BLOCK_{token}"
    return token


def _as_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError(f"{field_name} must be a boolean-compatible value.")

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False

    raise ValueError(f"{field_name} must be a boolean-compatible value.")


@dataclass(frozen=True)
class NvMBlock:
    """Structured representation of a single AUTOSAR NvM block."""

    block_name: str
    block_id: int
    block_size: int
    ram_block_name: str
    device: str
    block_management_type: str
    use_crc: bool
    crc_type: str
    write_protection: bool
    device_id: Optional[int] = None
    nv_block_base_number: Optional[int] = None
    nv_block_num: Optional[int] = None

    ALLOWED_DEVICES = {"FEE", "EA"}
    ALLOWED_BLOCK_MANAGEMENT_TYPES = {"NATIVE", "REDUNDANT", "DATASET"}
    ALLOWED_CRC_TYPES = {"CRC8", "CRC16", "CRC32"}
    DEFAULT_DEVICE_IDS = {"FEE": 0, "EA": 1}
    DEFAULT_NV_BLOCK_NUM = {"NATIVE": 1, "REDUNDANT": 2, "DATASET": 2}

    def __post_init__(self) -> None:
        normalized_device = self.device.strip().upper()
        normalized_management = self.block_management_type.strip().upper()
        normalized_crc = self.crc_type.strip().upper()
        normalized_block_name = self.block_name.strip()
        normalized_ram_name = self.ram_block_name.strip()

        object.__setattr__(self, "block_name", normalized_block_name)
        object.__setattr__(self, "ram_block_name", normalized_ram_name)
        object.__setattr__(self, "device", normalized_device)
        object.__setattr__(self, "block_management_type", normalized_management)

        if normalized_device not in self.ALLOWED_DEVICES:
            raise ValueError(
                f"{self.block_name}: device must be one of {sorted(self.ALLOWED_DEVICES)}."
            )

        if normalized_management not in self.ALLOWED_BLOCK_MANAGEMENT_TYPES:
            raise ValueError(
                f"{self.block_name}: block_management_type must be one of "
                f"{sorted(self.ALLOWED_BLOCK_MANAGEMENT_TYPES)}."
            )

        if self.block_id <= 0:
            raise ValueError(f"{self.block_name}: block_id must be greater than 0.")

        if self.block_size <= 0:
            raise ValueError(f"{self.block_name}: block_size must be greater than 0.")

        if not normalized_block_name:
            raise ValueError("block_name must not be empty.")

        if not normalized_ram_name:
            raise ValueError(f"{self.block_name}: ram_block_name must not be empty.")

        if not _C_IDENTIFIER_PATTERN.match(normalized_ram_name):
            raise ValueError(
                f"{self.block_name}: ram_block_name must be a valid C identifier."
            )

        if self.use_crc:
            if normalized_crc not in self.ALLOWED_CRC_TYPES:
                raise ValueError(
                    f"{self.block_name}: crc_type must be one of "
                    f"{sorted(self.ALLOWED_CRC_TYPES)} when use_crc is true."
                )
            object.__setattr__(self, "crc_type", normalized_crc)
        else:
            object.__setattr__(self, "crc_type", "NONE")

        if self.device_id is not None and self.device_id < 0:
            raise ValueError(f"{self.block_name}: device_id must be >= 0.")

        if self.nv_block_base_number is not None and self.nv_block_base_number <= 0:
            raise ValueError(f"{self.block_name}: nv_block_base_number must be > 0.")

        if self.nv_block_num is not None and self.nv_block_num <= 0:
            raise ValueError(f"{self.block_name}: nv_block_num must be > 0.")

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "NvMBlock":
        """Build an NvMBlock from a parser record."""

        return cls(
            block_name=str(record["block_name"]),
            block_id=int(record["block_id"]),
            block_size=int(record["block_size"]),
            ram_block_name=str(record["ram_block_name"]),
            device=str(record["device"]),
            block_management_type=str(record["block_management_type"]),
            use_crc=_as_bool(record["use_crc"], "use_crc"),
            crc_type=str(record.get("crc_type", "CRC16")),
            write_protection=_as_bool(record["write_protection"], "write_protection"),
            device_id=(
                int(record["device_id"]) if record.get("device_id") not in (None, "") else None
            ),
            nv_block_base_number=(
                int(record["nv_block_base_number"])
                if record.get("nv_block_base_number") not in (None, "")
                else None
            ),
            nv_block_num=(
                int(record["nv_block_num"]) if record.get("nv_block_num") not in (None, "") else None
            ),
        )

    @property
    def short_name(self) -> str:
        return _normalize_short_name(self.block_name)

    @property
    def macro_token(self) -> str:
        return _to_macro_token(self.block_name)

    @property
    def block_id_macro(self) -> str:
        return f"NVM_BLOCK_ID_{self.macro_token}"

    @property
    def device_enum(self) -> str:
        return f"NVM_DEVICE_{self.device}"

    @property
    def management_enum(self) -> str:
        return f"NVM_BLOCK_{self.block_management_type}"

    @property
    def autosar_management_enum(self) -> str:
        return f"NVM_BLOCK_{self.block_management_type}"

    @property
    def crc_enum(self) -> str:
        if not self.use_crc:
            return "NVM_CRC_NONE"
        return f"NVM_{self.crc_type}"

    @property
    def autosar_crc_enum(self) -> str:
        return f"NVM_{self.crc_type}"

    @property
    def bool_c_literal(self) -> Tuple[str, str]:
        return ("TRUE" if self.use_crc else "FALSE", "TRUE" if self.write_protection else "FALSE")

    @property
    def autosar_use_crc_value(self) -> str:
        return "1" if self.use_crc else "0"

    @property
    def autosar_write_protection_value(self) -> str:
        return "1" if self.write_protection else "0"

    @property
    def effective_device_id(self) -> int:
        if self.device_id is not None:
            return self.device_id
        return self.DEFAULT_DEVICE_IDS[self.device]

    @property
    def effective_nv_block_base_number(self) -> int:
        if self.nv_block_base_number is not None:
            return self.nv_block_base_number
        return self.block_id

    @property
    def effective_nv_block_num(self) -> int:
        if self.nv_block_num is not None:
            return self.nv_block_num
        return self.DEFAULT_NV_BLOCK_NUM[self.block_management_type]
