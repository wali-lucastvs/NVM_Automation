from __future__ import annotations

import argparse
import logging
from pathlib import Path

from nvm_tool import NvMConfigParser
from nvm_tool.versioning import load_version_profile
from nvm_tool.engine_versioned import generate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate NvM ARXML for a selected AUTOSAR version.")
    p.add_argument("--input-type", required=True, choices=("json", "excel"))
    p.add_argument("--input-file", required=True, type=Path)
    p.add_argument("--autosar-version", required=True, help="Version folder name, e.g. Autosar_4_0_2")
    p.add_argument("--output", type=Path, default=Path("workspace/output"))
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--previous-arxml", type=Path, default=None)
    p.add_argument("--allow-update", action="store_true")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("generate_nvm_versioned")

    profile = load_version_profile(args.autosar_version)

    cfg_parser = NvMConfigParser(logger=logger)
    blocks = cfg_parser.parse_input_file(args.input_type, args.input_file)

    previous_doc = None
    if args.previous_arxml:
        previous_doc = cfg_parser.parse_previous_arxml(args.previous_arxml)

    try:
        out = generate(
            blocks,
            args.output,
            profile,
            previous_document=previous_doc,
            allow_update=args.allow_update,
            logger=logger,
        )
        logger.info("Generation successful: %s", out)
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
