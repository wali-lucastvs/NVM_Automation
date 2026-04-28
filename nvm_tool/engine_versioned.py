from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree

from .rules import validate_blocks
from .generator import NvMGenerator
from .versioning import VersionProfile


def _build_validation_document(rendered: str) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.fromstring(rendered.encode("utf-8"), parser)


def generate(blocks: Iterable, output: Path, version: VersionProfile, logger: logging.Logger | None = None) -> Path:
    """Generate ARXML and C artifacts for the given AUTOSAR version.

    This function is bundle-aware (PyInstaller) and resolves templates/XSDs from sys._MEIPASS
    when present.
    """
    logger = logger or logging.getLogger("nvm_versioned_engine")

    # Ensure semantic rules pass
    validate_blocks(blocks)

    # Resolve template and xsd locations (bundle-aware)
    if getattr(sys, "_MEIPASS", None):
        bundle_root = Path(sys._MEIPASS)
        common_templates = bundle_root / "versions" / "common"
        version_folder = bundle_root / "versions" / version.key
    else:
        repo_root = Path(__file__).resolve().parent.parent
        common_templates = repo_root / "versions" / "common"
        version_folder = repo_root / "versions" / version.key

    loader_paths = []
    if common_templates.exists():
        loader_paths.append(str(common_templates))
    if version_folder.exists():
        loader_paths.append(str(version_folder))

    env = Environment(
        loader=FileSystemLoader(loader_paths or [str(version.folder / ".." / "common"), str(version.folder)]),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("template.arxml.jinja")
    rendered = template.render(namespace=version.namespace, xsd=Path(version.xsd).name, blocks=blocks, features=type("F", (), version.features))

    # Resolve XSD path
    if getattr(sys, "_MEIPASS", None):
        xsd_path = Path(sys._MEIPASS) / "versions" / version.key / Path(version.xsd).name
    else:
        xsd_path = Path(version.xsd)

    if not xsd_path.exists():
        raise FileNotFoundError(f"XSD for selected version not found: {xsd_path}")

    schema_doc = etree.parse(str(xsd_path))
    schema = etree.XMLSchema(schema_doc)

    try:
        validation_doc = _build_validation_document(rendered)
        schema.assertValid(validation_doc)
    except etree.DocumentInvalid as exc:
        raise RuntimeError(f"ARXML does not conform to XSD: {exc}") from exc

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Render C artifacts using existing generator helpers
    generator = NvMGenerator(blocks=blocks, previous_document=None, allow_update=False, logger=logger)
    header = generator.render_header(list(blocks))
    source = generator.render_source(list(blocks))

    header_file = out_dir / "NvM_Cfg.h"
    source_file = out_dir / "NvM_Cfg.c"
    arxml_file = out_dir / "NvM.arxml"

    header_file.write_text(header, encoding="utf-8", newline="\n")
    source_file.write_text(source, encoding="utf-8", newline="\n")
    arxml_file.write_text(rendered, encoding="utf-8", newline="\n")

    logger.info("Written versioned header to %s", header_file)
    logger.info("Written versioned source to %s", source_file)
    logger.info("Written versioned ARXML to %s", arxml_file)

    return arxml_file
