from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import yaml

from .versioning import canonical_version_label, normalize_version_key


@dataclass(frozen=True)
class WorkspaceLayout:
    application_root: Path
    workspace_root: Path
    input_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class VersionProfile:
    key: str
    version: str
    namespace: str
    xsd: str
    features: dict
    folder: Path

    @property
    def xsd_name(self) -> str:
        return Path(self.xsd).name


@dataclass(frozen=True)
class AppConfig:
    workspace: WorkspaceLayout
    version: VersionProfile | None = None


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_workspace_layout(base_dir: str | Path | None = None) -> WorkspaceLayout:
    # Prefer the current working directory (the opened project folder) by default so
    # CLI and GUI use: <current working dir>/workspace/output instead of the packaged
    # application's installation folder. A caller can still override base_dir.
    application_root = Path(base_dir).resolve() if base_dir is not None else Path.cwd()
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


def load_version_profile(key: str, versions_dir: str | Path | None = None) -> VersionProfile:
    root = Path(versions_dir).resolve() if versions_dir is not None else get_application_root() / "versions"
    resolved_key = normalize_version_key(key)
    folder = root / resolved_key
    if not folder.exists():
        raise FileNotFoundError(f"Version folder not found: {folder}")

    cfg_path = folder / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing config.yaml in version folder: {folder}")

    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    schema_path = folder / "schema.xsd"
    if not schema_path.exists():
        schema_path = folder / cfg.get("xsd")

    return VersionProfile(
        key=resolved_key,
        version=canonical_version_label(key if key.count(".") == 2 else resolved_key),
        namespace=cfg.get("namespace", "http://autosar.org/schema/r4.0"),
        xsd=str(schema_path),
        features=cfg.get("features", {}),
        folder=folder,
    )


def load_config(
    version_key: str | None = None,
    base_dir: str | Path | None = None,
) -> AppConfig:
    workspace = get_workspace_layout(base_dir)
    version = load_version_profile(version_key) if version_key else None
    return AppConfig(workspace=workspace, version=version)
