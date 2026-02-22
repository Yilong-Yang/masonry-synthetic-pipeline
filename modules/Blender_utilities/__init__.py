"""Blender utilities module.

This module contains Blender-side helper scripts for:
- applying element transforms from `.npz`
- joining collections with rebuilt modifiers
- grouped OBJ import to collections
- preserving object IDs as mesh attributes
"""

from __future__ import annotations

__all__ = [
    "AffineConfig",
    "CategoryIdConfig",
    "GroupImportConfig",
    "MergeConfig",
    "apply_affine_transforms",
    "assign_category_ids",
    "import_groups",
    "merge_collections",
]

try:  # pragma: no cover - requires Blender Python environment (`bpy`)
    from .TransformElement import AffineConfig, apply_affine_transforms
    from .SmartJoin import MergeConfig, merge_collections
    from .group_import_command import GroupImportConfig, import_groups
    from .preserve_obj_id import CategoryIdConfig, assign_category_ids
except ImportError:
    # Allow package metadata import outside Blender.
    pass
