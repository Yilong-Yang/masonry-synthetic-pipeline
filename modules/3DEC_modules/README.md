# Module: 3DEC_modules

This module is a self-contained, publication-ready package with:

- mesh generation from block geometry (`RegularPattern.py`)
- 3DEC command export from generated mesh (`ThreeDecCommand.py`)

## Contents

- `RegularPattern.py`: generates a 2D masonry mesh (bricks + mortar).
- `ThreeDecCommand.py`: converts `.msh` into 3DEC prism and loading-block commands.
- `functions.py`: geometry parsing and seed-point generation helpers.
- `gmsh_functions.py`: Gmsh geometry/mesh utility functions.
- `const.py`: shared plotting colors.
- `data/Wallet_example.txt`: example geometry input.
- `data/Wallet_example.msh`: example mesh input/output.

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From this folder, generate mesh:

```bash
python RegularPattern.py
```

Common mesh options:

```bash
python RegularPattern.py --no-gui --mesh-size 0.004 --seed-count 40 --random-seed 42
```

To skip writing output:

```bash
python RegularPattern.py --no-write
```

Export to 3DEC commands:

```bash
python ThreeDecCommand.py
```

Common 3DEC export options:

```bash
python ThreeDecCommand.py --input data/Wallet_example.msh --output data/threedec/Wallet_example.dat --extrusion 0.065 --scale 1000
```

If the mesh does not contain a dedicated mortar cell block:

```bash
python ThreeDecCommand.py --no-mortar
```

