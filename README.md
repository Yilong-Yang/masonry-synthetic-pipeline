# Masonry Synthetic Pipeline

This repository contains the implementation of the automated pipeline proposed in **_An Automated Pipeline for Synthetic Data Generation to Evaluate Segmentation and Deformation Monitoring Algorithms for Masonry Structures_**.

This repository is organized as a collection of independent modules.
Each module has its own code, data, and dependencies.

## Modules

- `modules/3DEC_modules`: 2D masonry mesh generation (bricks + mortar) from block geometry input.
- `modules/three_dec_generators`: 3DEC input script generation (`params.dat`, `block_creation.dat`, and `test.dat` workflow).
- `modules/Blender_input_module`: convert 3DEC gridpoint data to OBJ surfaces and 4x4 rigid transforms.
- `modules/Blender_utilities`: Blender-side utilities for transform application, smart join, grouped OBJ import, and ID preservation.

## Module Convention

Each module should be self-contained and include:

- implementation code
- module-specific `README.md`
- `requirements.txt`
- any required example data

## Current Module Usage

Regular pattern module:

```bash
cd modules/3DEC_modules
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

Blender input module:

```bash
cd modules/Blender_input_module
pip install -r requirements.txt
python ReadPrisms.py data/Gp_info.txt output/prisms
python FindTransformation.py data/Gp_info.txt output/AffineM_Regular1.npz
```

Blender utilities module:

```bash
cd modules/Blender_utilities
pip install -r requirements.txt
blender --python TransformElement.py
blender --python SmartJoin.py
```
