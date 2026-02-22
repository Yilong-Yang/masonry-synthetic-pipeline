# Module: Blender Utilities

This module provides Blender-side utilities for common masonry data workflows:

- apply per-element affine transforms from `.npz` to scene objects (`TransformElement.py`)
- smart join of two collections while preserving split displacement control (`SmartJoin.py`)
- grouped OBJ import from directory trees (`group_import_command.py`)
- preserve object IDs into mesh face attributes (`preserve_obj_id.py`)

## Files

- `TransformElement.py`: apply 4x4 transforms from `.npz` to objects.
- `SmartJoin.py`: merge two collections and rebuild Subsurf/Displace modifiers.
- `group_import_command.py`: import OBJ groups by folder into dedicated collections.
- `preserve_obj_id.py`: assign trailing name IDs to face-level int attributes.

## Dependencies

Install from this module directory:

```bash
pip install -r requirements.txt
```

Notes:
- Scripts run inside Blender and use `bpy`.
- `bpy` and `mathutils` come from Blender, not from pip.

## Usage

From repository root:

```bash
cd modules/Blender_utilities
```

Run with Blender (recommended):

```bash
blender --python TransformElement.py
blender --python SmartJoin.py
blender --python group_import_command.py
blender --python preserve_obj_id.py
```

Or run from Blender GUI:

1. Open Blender and switch to the **Scripting** workspace.
2. Open one script from this module.
3. Update the configuration values in `main()` (paths, collection names, etc.).
4. Click **Run Script**.

## Python API

```python
from pathlib import Path

from Blender_utilities.TransformElement import AffineConfig, apply_affine_transforms
from Blender_utilities.SmartJoin import MergeConfig, merge_collections
from Blender_utilities.group_import_command import GroupImportConfig, import_groups
from Blender_utilities.preserve_obj_id import CategoryIdConfig, assign_category_ids

apply_affine_transforms(
    AffineConfig(matrix_npz_path=Path(r"C:\path\to\AffineM2.npz"))
)

merge_collections(
    MergeConfig(collection_a_name="Collection1", collection_b_name="Collection2")
)

import_groups(
    GroupImportConfig(root_directory=Path(r"C:\path\to\obj_root_directory"))
)

assign_category_ids(
    CategoryIdConfig(attribute_name="category_id", selected_objects_only=False)
)
```
