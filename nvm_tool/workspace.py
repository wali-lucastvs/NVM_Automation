from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class WorkspaceLayout:
    application_root: Path
    workspace_root: Path
    input_dir: Path
    output_dir: Path


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        # When bundled by PyInstaller, data files are extracted to sys._MEIPASS.
        # Prefer that location if available so bundled data (versions/, workspace/) is found.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_workspace_layout(base_dir: str | Path | None = None) -> WorkspaceLayout:
    application_root = Path(base_dir).resolve() if base_dir is not None else get_application_root()
    workspace_root = application_root / "workspace"
    return WorkspaceLayout(
        application_root=application_root,
        workspace_root=workspace_root,
        input_dir=workspace_root / "input",
        output_dir=workspace_root / "output",
    )


def ensure_workspace(base_dir: str | Path | None = None) -> WorkspaceLayout:
    layout = get_workspace_layout(base_dir)
    layout.input_dir.mkdir(parents=True, exist_ok=True)
    layout.output_dir.mkdir(parents=True, exist_ok=True)
    return layout


def default_input_dir() -> Path:
    return get_workspace_layout().input_dir


def default_output_dir() -> Path:
    return get_workspace_layout().output_dir
