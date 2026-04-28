from __future__ import annotations

from typing import Iterable

from .models import NvMBlock


def validate_blocks(blocks: Iterable[NvMBlock]) -> None:
    """Run semantic validation rules on the block list."""
    seen_ids = set()
    seen_names = set()
    for block in blocks:
        if block.block_id in seen_ids:
            raise ValueError(f"Duplicate block_id detected in generated blocks: {block.block_id}")
        seen_ids.add(block.block_id)

        if block.short_name in seen_names:
            raise ValueError(f"Duplicate block SHORT-NAME detected: {block.short_name}")
        seen_names.add(block.short_name)

        # Example rule: dataset blocks must not have use_crc False
        if block.block_management_type == "DATASET" and not block.use_crc:
            raise ValueError(f"Dataset block '{block.block_name}' must enable CRC (use_crc=true).")
