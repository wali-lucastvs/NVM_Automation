from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from nvm_tool import NvMConfigParser, NvMGenerator


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate AUTOSAR NvM configuration artifacts from JSON or Excel input, optionally merging with a previous NvM.arxml file."
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
        default=Path("output"),
        help="Directory where NvM_Cfg.c, NvM_Cfg.h, and the merged NvM.arxml are written.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging while parsing and generating files.",
    )
    return parser


def main() -> int:
    argument_parser = build_argument_parser()
    if len(sys.argv) == 1:
        argument_parser.print_help()
        return 0

    args = argument_parser.parse_args()
    configure_logging(args.verbose)
    logger = logging.getLogger("nvm_generator")

    try:
        parser = NvMConfigParser(logger=logger)
        input_blocks = parser.parse_input_file(args.input_type, args.input_file)
        previous_document = None
        if args.previous_arxml:
            previous_document = parser.parse_previous_arxml(args.previous_arxml)

        generator = NvMGenerator(
            blocks=input_blocks,
            previous_document=previous_document,
            logger=logger,
        )
        generator.generate(args.output)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error(str(exc))
        return 1
    except Exception:
        logger.exception("An unexpected error occurred during generation.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
