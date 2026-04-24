"""Reusable AUTOSAR NvM configuration generator package."""

from .application import (
    GenerationRequest,
    build_argument_parser,
    detect_input_type,
    format_cli_command,
    generate_artifacts,
    run_cli,
)
from .generator import NvMGenerator
from .models import NvMBlock, ParsedArxmlDocument
from .parser import NvMConfigParser

__all__ = [
    "GenerationRequest",
    "NvMBlock",
    "NvMConfigParser",
    "NvMGenerator",
    "ParsedArxmlDocument",
    "build_argument_parser",
    "detect_input_type",
    "format_cli_command",
    "generate_artifacts",
    "run_cli",
]
