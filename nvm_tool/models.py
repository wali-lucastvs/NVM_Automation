from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Any, Mapping, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET


AUTOSAR_NAMESPACE = "http://autosar.org/schema/r4.0"
AUTOSAR_XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

NVM_MODULE_DEFINITION_REF = "/AUTOSAR/EcucDefs/NvM"
NVM_BLOCK_CONTAINER_DEFINITION_REF = "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor"
NVM_BLOCK_ID_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramBlockIdentifier"
)
NVM_BLOCK_LENGTH_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockLength"
)
NVM_BLOCK_MANAGEMENT_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockManagementType"
)
NVM_BLOCK_USE_CRC_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockUseCrc"
)
NVM_BLOCK_WRITE_PROT_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockWriteProt"
)
NVM_BLOCK_DEVICE_ID_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvramDeviceId"
)
NVM_BLOCK_BASE_NUMBER_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockBaseNumber"
)
NVM_BLOCK_NUM_DEFINITION_REF = "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMNvBlockNum"
NVM_BLOCK_RAM_ADDRESS_DEFINITION_REF = (
    "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMRamBlockDataAddress"
)
NVM_BLOCK_CRC_TYPE_DEFINITION_REF = "/AUTOSAR/EcucDefs/NvM/NvMBlockDescriptor/NvMBlockCrcType"

_C_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INTEGER_STRING_PATTERN = re.compile(r"^[+-]?\d+$")


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


def _as_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer value.")

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer value.")

    if isinstance(value, str):
        normalized = value.strip()
        if _INTEGER_STRING_PATTERN.match(normalized):
            return int(normalized)

    raise ValueError(f"{field_name} must be an integer value.")


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    definition_ref: str
    dest: str
    value_kind: str


@dataclass
class ParsedArxmlDocument:
    tree: ET.ElementTree
    root: ET.Element
    namespace: str
    module_configuration: ET.Element
    containers_element: Optional[ET.Element]
    blocks: list["NvMBlock"]
    block_id_locations: dict[int, str]
    short_name_locations: dict[str, str]


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
    short_name_override: Optional[str] = None

    ALLOWED_DEVICES = {"FEE", "EA"}
    ALLOWED_BLOCK_MANAGEMENT_TYPES = {"NATIVE", "REDUNDANT", "DATASET"}
    ALLOWED_CRC_TYPES = {"CRC8", "CRC16", "CRC32"}
    DEFAULT_DEVICE_IDS = {"FEE": 0, "EA": 1}
    DEFAULT_NV_BLOCK_NUM = {"NATIVE": 1, "REDUNDANT": 2, "DATASET": 2}
    DEVICE_ID_TO_NAME = {0: "FEE", 1: "EA"}
    AUTOSAR_MANAGEMENT_TO_INTERNAL = {
        "NVM_BLOCK_NATIVE": "NATIVE",
        "NVM_BLOCK_REDUNDANT": "REDUNDANT",
        "NVM_BLOCK_DATASET": "DATASET",
    }
    AUTOSAR_CRC_TO_INTERNAL = {
        "NVM_CRC8": "CRC8",
        "NVM_CRC16": "CRC16",
        "NVM_CRC32": "CRC32",
    }
    STANDARD_PARAMETER_DEFINITIONS = (
        ParameterDefinition(
            "block_id",
            NVM_BLOCK_ID_DEFINITION_REF,
            "ECUC-INTEGER-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "block_size",
            NVM_BLOCK_LENGTH_DEFINITION_REF,
            "ECUC-INTEGER-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "block_management_type",
            NVM_BLOCK_MANAGEMENT_DEFINITION_REF,
            "ECUC-ENUMERATION-PARAM-DEF",
            "textual",
        ),
        ParameterDefinition(
            "use_crc",
            NVM_BLOCK_USE_CRC_DEFINITION_REF,
            "ECUC-BOOLEAN-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "write_protection",
            NVM_BLOCK_WRITE_PROT_DEFINITION_REF,
            "ECUC-BOOLEAN-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "device_id",
            NVM_BLOCK_DEVICE_ID_DEFINITION_REF,
            "ECUC-INTEGER-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "nv_block_base_number",
            NVM_BLOCK_BASE_NUMBER_DEFINITION_REF,
            "ECUC-INTEGER-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "nv_block_num",
            NVM_BLOCK_NUM_DEFINITION_REF,
            "ECUC-INTEGER-PARAM-DEF",
            "numerical",
        ),
        ParameterDefinition(
            "ram_block_name",
            NVM_BLOCK_RAM_ADDRESS_DEFINITION_REF,
            "ECUC-STRING-PARAM-DEF",
            "textual",
        ),
        ParameterDefinition(
            "crc_type",
            NVM_BLOCK_CRC_TYPE_DEFINITION_REF,
            "ECUC-ENUMERATION-PARAM-DEF",
            "textual",
        ),
    )

    def __post_init__(self) -> None:
        normalized_device = self.device.strip().upper()
        normalized_management = self.block_management_type.strip().upper()
        normalized_crc = self.crc_type.strip().upper()
        normalized_block_name = self.block_name.strip()
        normalized_ram_name = self.ram_block_name.strip()
        normalized_short_name_override = (
            self.short_name_override.strip() if self.short_name_override is not None else None
        )

        object.__setattr__(self, "block_name", normalized_block_name)
        object.__setattr__(self, "ram_block_name", normalized_ram_name)
        object.__setattr__(self, "device", normalized_device)
        object.__setattr__(self, "block_management_type", normalized_management)
        object.__setattr__(self, "short_name_override", normalized_short_name_override)

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

        if normalized_short_name_override is not None and not normalized_short_name_override:
            raise ValueError(f"{self.block_name}: short_name_override must not be empty.")

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "NvMBlock":
        """Build an NvMBlock from parsed JSON or Excel input."""

        return cls(
            block_name=str(record["block_name"]),
            block_id=_as_int(record["block_id"], "block_id"),
            block_size=_as_int(record["block_size"], "block_size"),
            ram_block_name=str(record["ram_block_name"]),
            device=str(record["device"]),
            block_management_type=str(record["block_management_type"]),
            use_crc=_as_bool(record["use_crc"], "use_crc"),
            crc_type=str(record.get("crc_type", "CRC16")),
            write_protection=_as_bool(record["write_protection"], "write_protection"),
            device_id=(
                _as_int(record["device_id"], "device_id")
                if record.get("device_id") not in (None, "")
                else None
            ),
            nv_block_base_number=(
                _as_int(record["nv_block_base_number"], "nv_block_base_number")
                if record.get("nv_block_base_number") not in (None, "")
                else None
            ),
            nv_block_num=(
                _as_int(record["nv_block_num"], "nv_block_num")
                if record.get("nv_block_num") not in (None, "")
                else None
            ),
        )

    @classmethod
    def from_arxml_values(
        cls,
        short_name: str,
        parameter_values: Mapping[str, str],
    ) -> "NvMBlock":
        """Build an NvMBlock from a previous ARXML container."""

        block_id = _as_int(
            parameter_values[NVM_BLOCK_ID_DEFINITION_REF],
            "NvMNvramBlockIdentifier",
        )
        block_size = _as_int(
            parameter_values[NVM_BLOCK_LENGTH_DEFINITION_REF],
            "NvMNvBlockLength",
        )
        device_id = _as_int(
            parameter_values[NVM_BLOCK_DEVICE_ID_DEFINITION_REF],
            "NvMNvramDeviceId",
        )
        device = cls.DEVICE_ID_TO_NAME.get(device_id)
        if device is None:
            raise ValueError(
                f"{short_name}: NvMNvramDeviceId={device_id} is unsupported. "
                "Only device IDs 0 (FEE) and 1 (EA) are supported."
            )

        management_value = parameter_values[NVM_BLOCK_MANAGEMENT_DEFINITION_REF].strip().upper()
        management_type = cls.AUTOSAR_MANAGEMENT_TO_INTERNAL.get(management_value)
        if management_type is None:
            raise ValueError(
                f"{short_name}: unsupported NvMBlockManagementType '{management_value}'."
            )

        use_crc = _as_bool(
            parameter_values[NVM_BLOCK_USE_CRC_DEFINITION_REF],
            "NvMBlockUseCrc",
        )
        write_protection = _as_bool(
            parameter_values[NVM_BLOCK_WRITE_PROT_DEFINITION_REF],
            "NvMBlockWriteProt",
        )
        crc_type = "CRC16"
        if use_crc:
            raw_crc_type = parameter_values.get(NVM_BLOCK_CRC_TYPE_DEFINITION_REF)
            if raw_crc_type is None:
                raise ValueError(f"{short_name}: missing NvMBlockCrcType while NvMBlockUseCrc=1.")
            normalized_crc_type = raw_crc_type.strip().upper()
            crc_type = cls.AUTOSAR_CRC_TO_INTERNAL.get(normalized_crc_type, "")
            if not crc_type:
                raise ValueError(f"{short_name}: unsupported NvMBlockCrcType '{raw_crc_type}'.")

        return cls(
            block_name=short_name,
            short_name_override=short_name,
            block_id=block_id,
            block_size=block_size,
            ram_block_name=parameter_values[NVM_BLOCK_RAM_ADDRESS_DEFINITION_REF],
            device=device,
            block_management_type=management_type,
            use_crc=use_crc,
            crc_type=crc_type,
            write_protection=write_protection,
            device_id=device_id,
            nv_block_base_number=_as_int(
                parameter_values[NVM_BLOCK_BASE_NUMBER_DEFINITION_REF],
                "NvMNvBlockBaseNumber",
            ),
            nv_block_num=_as_int(
                parameter_values[NVM_BLOCK_NUM_DEFINITION_REF],
                "NvMNvBlockNum",
            ),
        )

    @property
    def short_name(self) -> str:
        if self.short_name_override:
            return self.short_name_override
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
        return ("true" if self.use_crc else "false", "true" if self.write_protection else "false")

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

    def autosar_parameter_values(self) -> dict[str, str]:
        values = {
            NVM_BLOCK_ID_DEFINITION_REF: str(self.block_id),
            NVM_BLOCK_LENGTH_DEFINITION_REF: str(self.block_size),
            NVM_BLOCK_MANAGEMENT_DEFINITION_REF: self.autosar_management_enum,
            NVM_BLOCK_USE_CRC_DEFINITION_REF: self.autosar_use_crc_value,
            NVM_BLOCK_WRITE_PROT_DEFINITION_REF: self.autosar_write_protection_value,
            NVM_BLOCK_DEVICE_ID_DEFINITION_REF: str(self.effective_device_id),
            NVM_BLOCK_BASE_NUMBER_DEFINITION_REF: str(self.effective_nv_block_base_number),
            NVM_BLOCK_NUM_DEFINITION_REF: str(self.effective_nv_block_num),
            NVM_BLOCK_RAM_ADDRESS_DEFINITION_REF: self.ram_block_name,
        }
        if self.use_crc:
            values[NVM_BLOCK_CRC_TYPE_DEFINITION_REF] = self.autosar_crc_enum
        return values


@dataclass(frozen=True)
class GenerationRequest:
    input_type: str
    input_file: Path
    output_dir: Path = field(default_factory=lambda: default_output_dir())
    previous_arxml: Optional[Path] = None
    verbose: bool = False
    allow_update: bool = False
    autosar_version: Optional[str] = None

    def normalized(self) -> "GenerationRequest":
        normalized_input_type = self.input_type.strip().lower()
        if normalized_input_type not in {"json", "excel"}:
            raise ValueError("Unsupported input type. Use 'json' or 'excel'.")
        if self.allow_update and self.previous_arxml is None:
            raise ValueError("--allow-update requires --previous-arxml.")

        return GenerationRequest(
            input_type=normalized_input_type,
            input_file=Path(self.input_file),
            output_dir=Path(self.output_dir),
            previous_arxml=Path(self.previous_arxml) if self.previous_arxml is not None else None,
            verbose=self.verbose,
            allow_update=self.allow_update,
            autosar_version=self.autosar_version,
        )


@dataclass(frozen=True)
class NvMMemoryUsageSummary:
    block_count: int
    total_payload_bytes: int
    total_estimated_storage_bytes: int
    total_crc_bytes: int
    fee_estimated_storage_bytes: int
    ea_estimated_storage_bytes: int


def configure_logger(
    verbose: bool,
    handler: Optional[logging.Handler] = None,
) -> logging.Logger:
    logger = logging.getLogger("nvm_generator")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    effective_handler = handler or logging.StreamHandler()
    effective_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    effective_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(effective_handler)
    return logger


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate AUTOSAR NvM configuration artifacts from JSON or Excel input, "
            "optionally merging with a previous NvM.arxml file."
        )
    )
    parser.add_argument(
        "--input-type",
        required=True,
        choices=("json", "excel"),
        help="Select the primary input source format.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        type=Path,
        help="Path to the JSON or Excel NvM block input file.",
    )
    parser.add_argument(
        "--previous-arxml",
        required=False,
        type=Path,
        help="Path to the previous NvM.arxml file used as the merge base.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_dir(),
        help="Directory where NvM_Cfg.c, NvM_Cfg.h, and NvM.arxml are written.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging while parsing and generating files.",
    )
    parser.add_argument(
        "--allow-update",
        action="store_true",
        help="Allow updating existing blocks with the same ID or name instead of rejecting them.",
    )
    parser.add_argument(
        "--autosar-version",
        required=False,
        help="Target AUTOSAR version (e.g., Autosar_4_0_2).",
    )
    return parser


def generate_artifacts(
    request: GenerationRequest,
    log_handler: Optional[logging.Handler] = None,
) -> list[Path]:
    from .generator import NvMGenerator, generate
    from .parser import NvMConfigParser

    normalized_request = request.normalized()
    logger = configure_logger(normalized_request.verbose, handler=log_handler)

    parser = NvMConfigParser(logger=logger)
    input_blocks = parser.parse_input_file(
        normalized_request.input_type,
        normalized_request.input_file,
    )

    previous_document = None
    if normalized_request.previous_arxml:
        previous_document = parser.parse_previous_arxml(normalized_request.previous_arxml)

    if normalized_request.autosar_version:
        from .config import load_version_profile

        profile = load_version_profile(normalized_request.autosar_version)
        generate(
            blocks=input_blocks,
            output=normalized_request.output_dir,
            version=profile,
            previous_document=previous_document,
            allow_update=normalized_request.allow_update,
            logger=logger,
            versioned=True,
        )
    else:
        generator = NvMGenerator(
            blocks=input_blocks,
            previous_document=previous_document,
            allow_update=normalized_request.allow_update,
            logger=logger,
        )
        generator.generate(normalized_request.output_dir)

    return [
        normalized_request.output_dir / "NvM_Cfg.c",
        normalized_request.output_dir / "NvM_Cfg.h",
        normalized_request.output_dir / "NvM.arxml",
    ]


def summarize_memory_usage(request: GenerationRequest) -> NvMMemoryUsageSummary:
    from .generator import NvMGenerator
    from .parser import NvMConfigParser

    normalized_request = request.normalized()
    logger = logging.getLogger("nvm_generator.summary")
    parser = NvMConfigParser(logger=logger)
    input_blocks = parser.parse_input_file(
        normalized_request.input_type,
        normalized_request.input_file,
    )

    previous_document = None
    if normalized_request.previous_arxml:
        previous_document = parser.parse_previous_arxml(normalized_request.previous_arxml)

    generator = NvMGenerator(
        blocks=input_blocks,
        previous_document=previous_document,
        allow_update=normalized_request.allow_update,
        logger=logger,
    )
    effective_blocks = generator.resolve_blocks()

    total_payload_bytes = 0
    total_estimated_storage_bytes = 0
    total_crc_bytes = 0
    fee_estimated_storage_bytes = 0
    ea_estimated_storage_bytes = 0

    for block in effective_blocks:
        block_copies = block.effective_nv_block_num
        payload_bytes = block.block_size
        crc_bytes = _crc_bytes_for_block(block)
        estimated_storage_bytes = (payload_bytes + crc_bytes) * block_copies

        total_payload_bytes += payload_bytes
        total_crc_bytes += crc_bytes * block_copies
        total_estimated_storage_bytes += estimated_storage_bytes

        if block.device == "FEE":
            fee_estimated_storage_bytes += estimated_storage_bytes
        elif block.device == "EA":
            ea_estimated_storage_bytes += estimated_storage_bytes

    return NvMMemoryUsageSummary(
        block_count=len(effective_blocks),
        total_payload_bytes=total_payload_bytes,
        total_estimated_storage_bytes=total_estimated_storage_bytes,
        total_crc_bytes=total_crc_bytes,
        fee_estimated_storage_bytes=fee_estimated_storage_bytes,
        ea_estimated_storage_bytes=ea_estimated_storage_bytes,
    )


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    argument_parser = build_argument_parser()
    if argv is not None and len(argv) == 0:
        argument_parser.print_help()
        return 0

    args = argument_parser.parse_args(argv)

    try:
        generate_artifacts(
            GenerationRequest(
                input_type=args.input_type,
                input_file=args.input_file,
                previous_arxml=args.previous_arxml,
                output_dir=args.output,
                verbose=args.verbose,
                allow_update=args.allow_update,
                autosar_version=args.autosar_version,
            )
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger = configure_logger(args.verbose)
        logger.error(str(exc))
        return 1
    except Exception:
        logger = configure_logger(args.verbose)
        logger.exception("An unexpected error occurred during generation.")
        return 1

    return 0


def detect_input_type(input_file: str | Path) -> Optional[str]:
    suffix = Path(input_file).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".xlsx", ".xlsm"}:
        return "excel"
    return None


def format_cli_command(request: GenerationRequest) -> str:
    normalized_request = request.normalized()
    parts = [
        "python",
        "main.py",
        "generate",
        "--input-type",
        normalized_request.input_type,
        "--input-file",
        str(normalized_request.input_file),
        "--output",
        str(normalized_request.output_dir),
    ]
    if normalized_request.previous_arxml is not None:
        parts.extend(["--previous-arxml", str(normalized_request.previous_arxml)])
    if normalized_request.allow_update:
        parts.append("--allow-update")
    if normalized_request.autosar_version:
        parts.extend(["--autosar-version", normalized_request.autosar_version])
    if normalized_request.verbose:
        parts.append("--verbose")
    return " ".join(_quote_for_powershell(part) for part in parts)


def _quote_for_powershell(value: str) -> str:
    if not value:
        return '""'
    if any(character.isspace() for character in value):
        return '"' + value.replace('"', '`"') + '"'
    return value


def _crc_bytes_for_block(block: NvMBlock) -> int:
    if not block.use_crc:
        return 0
    return {
        "CRC8": 1,
        "CRC16": 2,
        "CRC32": 4,
    }[block.crc_type]


def get_application_root() -> Path:
    from .config import get_application_root as _get_application_root

    return _get_application_root()


def get_workspace_layout(base_dir: str | Path | None = None):
    from .config import get_workspace_layout as _get_workspace_layout

    return _get_workspace_layout(base_dir)


def ensure_workspace(base_dir: str | Path | None = None):
    from .config import ensure_workspace as _ensure_workspace

    return _ensure_workspace(base_dir)


def default_input_dir() -> Path:
    from .config import default_input_dir as _default_input_dir

    return _default_input_dir()


def default_output_dir() -> Path:
    from .config import default_output_dir as _default_output_dir

    return _default_output_dir()
