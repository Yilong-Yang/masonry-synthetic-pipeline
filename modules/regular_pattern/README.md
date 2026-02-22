# Module: Regular Pattern

This module generates a 2D masonry mesh (bricks and mortar) from block geometry
input and writes a Gmsh `.msh` file.

## Files

- `RegularPattern.py`: main entry point.
- `functions.py`: geometry parsing and random seed-point generation.
- `gmsh_functions.py`: Gmsh geometry and mesh helper functions.
- `const.py`: color constants for visualization.
- `data/Wallet_example.txt`: example input file.
- `data/Wallet_example.msh`: example output mesh.

## Dependencies

Install from this module directory:

```bash
pip install -r requirements.txt
```

## Usage

From repository root:

```bash
cd modules/regular_pattern
python RegularPattern.py
```

Typical non-GUI run:

```bash
python RegularPattern.py --no-gui --mesh-size 0.004 --seed-count 40 --random-seed 42
```

Skip writing output:

```bash
python RegularPattern.py --no-write
```
