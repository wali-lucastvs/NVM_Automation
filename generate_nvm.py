from __future__ import annotations

import argparse
import logging
from pathlib import Path

from nvm_tool import NvMConfigParser, NvMGenerator


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate AUTOSAR NvM configuration files from JSON or Excel input."
    )
    parser.add_argument("input", type=Path, help="Path to the JSON or Excel input file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory where NvM_Cfg.c, NvM_Cfg.h, and NvM.arxml are written.",
    )
    parser.add_argument(
        "--module-short-name",
        default="NvM",
        help="AUTOSAR package short name for the NvM module.",
    )
    parser.add_argument(
        "--config-short-name",
        default="NvM_Config",
        help="AUTOSAR ECUC module configuration short name.",
    )
    parser.add_argument(
        "--schema-file",
        default="AUTOSAR_00049.xsd",
        help="Schema file name written into the ARXML xsi:schemaLocation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging while parsing and generating files.",
    )
    return parser


def main() -> int:
    argument_parser = build_argument_parser()
    args = argument_parser.parse_args()

    configure_logging(args.verbose)
    logger = logging.getLogger("nvm_generator")

    parser = NvMConfigParser(logger=logger)
    blocks = parser.parse_file(args.input)

    generator = NvMGenerator(
        blocks=blocks,
        logger=logger,
        module_short_name=args.module_short_name,
        config_short_name=args.config_short_name,
        schema_file=args.schema_file,
    )
    generator.generate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
