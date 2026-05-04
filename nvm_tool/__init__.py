"""Reusable AUTOSAR NvM configuration generator package."""

from .models import (
    GenerationRequest,
    NvMMemoryUsageSummary,
    default_input_dir,
    default_output_dir,
    ensure_workspace,
    detect_input_type,
    generate_artifacts,
    get_workspace_layout,
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
    "detect_input_type",
    "default_input_dir",
    "default_output_dir",
    "ensure_workspace",
    "generate_artifacts",
    "get_workspace_layout",
    "summarize_memory_usage",
]
