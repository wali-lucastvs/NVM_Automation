"""Reusable AUTOSAR NvM configuration generator package."""

from .models import (
    GenerationRequest,
    NvMMemoryUsageSummary,
    build_argument_parser,
    default_input_dir,
    default_output_dir,
    ensure_workspace,
    detect_input_type,
    format_cli_command,
    generate_artifacts,
    get_workspace_layout,
    run_cli,
    summarize_memory_usage,
)
from .generator import NvMGenerator
from .models import NvMBlock, ParsedArxmlDocument
from .parser import NvMConfigParser

__all__ = [
    "GenerationRequest",
    "NvMMemoryUsageSummary",
    "NvMBlock",
    "NvMConfigParser",
    "NvMGenerator",
    "ParsedArxmlDocument",
    "build_argument_parser",
    "detect_input_type",
    "default_input_dir",
    "default_output_dir",
    "ensure_workspace",
    "format_cli_command",
    "generate_artifacts",
    "get_workspace_layout",
    "run_cli",
    "summarize_memory_usage",
]
