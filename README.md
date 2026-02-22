# Public Release: RegularPattern

This folder is a self-contained, publication-ready version of the original
`RegularPattern.py` workflow. Original project scripts remain unchanged.

## Contents

- `RegularPattern.py`: main entry point.
- `functions.py`: geometry parsing and seed-point generation helpers.
- `gmsh_functions.py`: Gmsh geometry/mesh utility functions.
- `const.py`: shared plotting colors.
- `data/Wallet_example.txt`: example input data file.

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From this folder:

```bash
python RegularPattern.py
```

Common options:

```bash
python RegularPattern.py --no-gui --mesh-size 0.004 --seed-count 40 --random-seed 42
```

To skip writing output:

```bash
python RegularPattern.py --no-write
```
