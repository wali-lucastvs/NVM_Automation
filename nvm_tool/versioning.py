from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import yaml


@dataclass
class VersionProfile:
    key: str
    namespace: str
    xsd: str
    features: dict
    folder: Path


def load_version_profile(key: str) -> VersionProfile:
    # Resolve versions directory relative to the package. When bundled with
    # PyInstaller, data is extracted to sys._MEIPASS, so prefer that when present.
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        root = Path(sys._MEIPASS)
    else:
        root = Path(__file__).resolve().parent.parent
    versions_dir = root / "versions"
    folder_name = key
    folder = versions_dir / folder_name
    if not folder.exists():
        raise FileNotFoundError(f"Version folder not found: {folder}")

    cfg_path = folder / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing config.yaml in version folder: {folder}")

    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    return VersionProfile(
        key=key,
        namespace=cfg.get("namespace", "http://autosar.org/schema/r4.0"),
        xsd=str(folder / cfg.get("xsd")),
        features=cfg.get("features", {}),
        folder=folder,
    )
