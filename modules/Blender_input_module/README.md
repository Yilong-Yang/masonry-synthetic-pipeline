# Module: Blender Input Module

This module provides utilities for converting 3DEC-style gridpoint outputs into:

- per-element OBJ prism-plane files (`ReadPrisms.py`)
- per-element 4x4 rigid transformation matrices (`FindTransformation.py`)

## Files

- `ReadPrisms.py`: exports undeformed and deformed OBJ files from gridpoint input.
- `FindTransformation.py`: computes rigid transforms using the Kabsch algorithm and saves `.npz`.
- `_gridpoint_io.py`: shared parsing and filtering utilities.
- `data/Gp_info.txt`: demo gridpoint data.

## Dependencies

Install from this module directory:

```bash
pip install -r requirements.txt
```

## Usage

From repository root:

```bash
cd modules/Blender_input_module
```

Export OBJ files:

```bash
python ReadPrisms.py data/Gp_info.txt output/prisms
```

Compute rigid transforms:

```bash
python FindTransformation.py data/Gp_info.txt output/AffineM_Regular1.npz
```

## Python API

```python
from Blender_input_module.ReadPrisms import export_prisms_from_gridpoints
from Blender_input_module.FindTransformation import (
    build_transform_dict_from_gridpoints,
    save_transform_dict_npz,
)

stats = export_prisms_from_gridpoints("data/Gp_info.txt", "output/prisms")
transforms = build_transform_dict_from_gridpoints("data/Gp_info.txt")
save_transform_dict_npz(transforms, "output/AffineM_Regular1.npz")
```