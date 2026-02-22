# Module: 3DEC Generators

This module generates 3DEC input scripts for masonry simulations:

- `ParamsGen.py`: generates `params.dat`
- `BlockCreationGen.py`: generates `block_creation.dat` from user geometry lines

The module also includes:

- `test.dat`: driver template that calls `params.dat` and `block_creation.dat`
- `data/params.dat`: example expected output from `ParamsGen.py`
- `data/block_creation.dat`: example expected output from `BlockCreationGen.py`
- `data/geometry_input.dat`: example geometry-only input for `BlockCreationGen.py`

## Files

- `ParamsGen.py`: params generator entry point.
- `BlockCreationGen.py`: block creation generator entry point.
- `const.py`: editable default values for both generators.
- `test.dat`: example 3DEC driver script.
- `data/params.dat`: example generated params script.
- `data/block_creation.dat`: example generated block creation script.
- `data/geometry_input.dat`: example input geometry lines.

## Dependencies

Install from this module directory:

```bash
pip install -r requirements.txt
```

## Usage

From repository root:

```bash
cd modules/three_dec_generators
```

Generate params with defaults:

```bash
python ParamsGen.py --output params.dat --force
```

Interactive params generation:

```bash
python ParamsGen.py --interactive --output params.dat --force
```

Generate block creation from geometry lines:

```bash
python BlockCreationGen.py --geometry-input data/geometry_input.dat --output block_creation.dat --force
```

Optional runtime overrides:

```bash
python BlockCreationGen.py --geometry-input data/geometry_input.dat --output block_creation.dat --bottom-thickness 150 --top-thickness 150 --z-threshold 0.001 --force
```

## Recommended Workflow

1. Prepare user geometry lines (`block create ... group '...'`) in a `.dat` file.
2. Run `BlockCreationGen.py` to generate `block_creation.dat`.
3. Run `ParamsGen.py` to generate `params.dat`.
4. Run `test.dat` in 3DEC.
