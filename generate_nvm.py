from __future__ import annotations

import sys
from nvm_tool.application import build_argument_parser, run_cli


def main() -> int:
    argument_parser = build_argument_parser()
    if len(sys.argv) == 1:
        argument_parser.print_help()
        return 0

    return run_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
