from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from nvm_tool import GenerationRequest, default_output_dir, generate_artifacts


def _add_common_generate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input-type", required=True, choices=("json", "excel"))
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--previous-arxml", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=default_output_dir())
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--allow-update", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AUTOSAR NvM automation entry point.")
    parser.add_argument("--gui", action="store_true", help="Launch a GUI instead of the CLI generator.")
    parser.add_argument(
        "--versioned",
        action="store_true",
        help="Use the versioned generator or versioned GUI flow.",
    )

    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Run standard generation.")
    _add_common_generate_arguments(generate_parser)
    generate_parser.add_argument("--autosar-version", required=False)

    generate_versioned_parser = subparsers.add_parser(
        "generate-versioned",
        help="Run versioned generation.",
    )
    _add_common_generate_arguments(generate_versioned_parser)
    generate_versioned_parser.add_argument("--autosar-version", required=True)

    subparsers.add_parser("gui", help="Launch the main desktop GUI.")
    subparsers.add_parser("gui-versioned", help="Launch the lightweight versioned GUI.")
    return parser


def _resolve_command(args: argparse.Namespace) -> str | None:
    if args.command:
        return args.command
    if args.gui and args.versioned:
        return "gui-versioned"
    if args.gui:
        return "gui"
    if args.versioned:
        return "generate-versioned"
    return None


def _run_generate_command(args: argparse.Namespace, *, require_version: bool) -> int:
    autosar_version = args.autosar_version
    if require_version and not autosar_version:
        raise ValueError("--autosar-version is required for versioned generation.")

    generate_artifacts(
        GenerationRequest(
            input_type=args.input_type,
            input_file=args.input_file,
            previous_arxml=args.previous_arxml,
            output_dir=args.output,
            verbose=args.verbose,
            allow_update=args.allow_update,
            autosar_version=autosar_version,
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = _resolve_command(args)

    if command is None:
        parser.print_help()
        return 0

    if command == "gui":
        from nvm_gui import main as gui_main

        gui_main()
        return 0

    if command == "gui-versioned":
        from nvm_gui_versioned import main as gui_versioned_main

        gui_versioned_main()
        return 0

    try:
        if command == "generate-versioned":
            return _run_generate_command(args, require_version=True)
        if command == "generate":
            return _run_generate_command(args, require_version=False)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(exc)
        return 1

    parser.error(f"Unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
