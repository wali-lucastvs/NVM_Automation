from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from .generator import NvMGenerator
from .parser import NvMConfigParser
from .workspace import default_output_dir


@dataclass(frozen=True)
class GenerationRequest:
    input_type: str
    input_file: Path
    output_dir: Path = field(default_factory=default_output_dir)
    previous_arxml: Optional[Path] = None
    verbose: bool = False
    allow_update: bool = False

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
    return parser


def generate_artifacts(
    request: GenerationRequest,
    log_handler: Optional[logging.Handler] = None,
) -> list[Path]:
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
        "generate_nvm.py",
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
    if normalized_request.verbose:
        parts.append("--verbose")
    return " ".join(_quote_for_powershell(part) for part in parts)


def _quote_for_powershell(value: str) -> str:
    if not value:
        return '""'
    if any(character.isspace() for character in value):
        return '"' + value.replace('"', '`"') + '"'
    return value


def _crc_bytes_for_block(block) -> int:
    if not block.use_crc:
        return 0
    return {
        "CRC8": 1,
        "CRC16": 2,
        "CRC32": 4,
    }[block.crc_type]
