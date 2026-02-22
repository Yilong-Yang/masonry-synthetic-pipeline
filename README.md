# Masonry Synthetic Pipeline

This repository is organized as a collection of independent modules.
Each module has its own code, data, and dependencies.

## Modules

- `modules/regular_pattern`: 2D masonry mesh generation (bricks + mortar) from block geometry input.

## Module Convention

Each module should be self-contained and include:

- implementation code
- module-specific `README.md`
- `requirements.txt`
- any required example data

## Current Module Usage

```bash
cd modules/regular_pattern
pip install -r requirements.txt
python RegularPattern.py --no-gui
```
