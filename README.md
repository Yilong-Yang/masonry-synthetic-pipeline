# Masonry Synthetic Pipeline

This repository is organized as a collection of independent modules.
Each module has its own code, data, and dependencies.

## Modules

- `modules/regular_pattern`: 2D masonry mesh generation (bricks + mortar) from block geometry input.
- `modules/three_dec_generators`: 3DEC input script generation (`params.dat`, `block_creation.dat`, and `test.dat` workflow).

## Module Convention

Each module should be self-contained and include:

- implementation code
- module-specific `README.md`
- `requirements.txt`
- any required example data

## Current Module Usage

Regular pattern module:

```bash
cd modules/regular_pattern
pip install -r requirements.txt
python RegularPattern.py --no-gui
```

3DEC generators module:

```bash
cd modules/three_dec_generators
pip install -r requirements.txt
python BlockCreationGen.py --geometry-input data/geometry_input.dat --output block_creation.dat --force
python ParamsGen.py --interactive --output params.dat --force
```
