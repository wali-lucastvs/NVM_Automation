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
        description="Merge new NvM block input into a previous AUTOSAR NvM ARXML and generate C artifacts."
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
        required=True,
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
    
    input_path = args.input_file or args.input_file_alt
    if not input_path:
        logger.error("No input file provided.")
        return 1

    # Auto-detect logic for "Sample" folder workflow
    output_dir = args.output or input_path.parent
    prev_arxml = args.previous_arxml
    if not prev_arxml:
        potential_prev = input_path.parent / "NvM.arxml"
        if potential_prev.exists():
            prev_arxml = potential_prev
            logger.info("Auto-detected previous ARXML at: %s", prev_arxml)
        else:
            logger.error("No previous ARXML found. Use --previous-arxml to specify one.")
            return 1

    try:
        parser = NvMConfigParser(logger=logger)
        input_blocks = parser.parse_file(input_path)
        previous_document = parser.parse_previous_arxml(prev_arxml)

        generator = NvMGenerator(
            blocks=input_blocks,
            previous_document=previous_document,
            logger=logger,
        )
        generator.generate(output_dir)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error(str(exc))
        return 1
    except Exception:
        logger.exception("An unexpected error occurred during generation.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
