"""Apply affine transforms to Blender objects from a NumPy ``.npz`` file.

Expected ``.npz`` format:
- Each key is an element identifier (for example ``"42"``).
- Each value is a ``4 x 4`` transform matrix.

Object names are resolved with ``object_name_template`` where ``{element_id}``
is replaced with each key from the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import bpy
import mathutils
import numpy as np


@dataclass(frozen=True)
class AffineConfig:
    """Runtime configuration for affine transform import."""

    matrix_npz_path: Path
    object_name_template: str = "element{element_id}"
    transpose_matrix: bool = False


def _build_world_matrix(raw_matrix: np.ndarray, transpose: bool) -> mathutils.Matrix:
    """Convert a raw ``4 x 4`` matrix array into Blender's ``matrix_world``."""
    matrix = raw_matrix.astype(np.float32, copy=False)
    if matrix.shape != (4, 4):
        raise ValueError(f"Expected a 4x4 matrix, received shape {matrix.shape}.")

    if transpose:
        matrix = matrix.T

    world_matrix = mathutils.Matrix(matrix.tolist())
    if world_matrix.size != 4:
        raise ValueError("Failed to build a valid 4x4 Blender matrix.")
    return world_matrix


def apply_affine_transforms(config: AffineConfig) -> Tuple[int, int, int]:
    """Apply all transforms from ``config.matrix_npz_path``.

    Returns:
        Tuple ``(applied_count, missing_object_count, invalid_matrix_count)``.
    """
    matrix_path = config.matrix_npz_path.expanduser().resolve()
    if not matrix_path.exists():
        raise FileNotFoundError(f"Matrix file not found: {matrix_path}")

    applied_count = 0
    missing_object_count = 0
    invalid_matrix_count = 0

    with np.load(str(matrix_path)) as matrix_data:
        for element_id in matrix_data.files:
            object_name = config.object_name_template.format(element_id=element_id)
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                print(f"[WARN] Object '{object_name}' not found. Skipping.")
                missing_object_count += 1
                continue

            try:
                obj.matrix_world = _build_world_matrix(
                    matrix_data[element_id],
                    transpose=config.transpose_matrix,
                )
            except ValueError as error:
                print(f"[WARN] Invalid matrix for '{object_name}': {error}")
                invalid_matrix_count += 1
                continue

            applied_count += 1

    print(
        "[DONE] Applied transforms: "
        f"{applied_count}, missing objects: {missing_object_count}, "
        f"invalid matrices: {invalid_matrix_count}"
    )
    return applied_count, missing_object_count, invalid_matrix_count


def main() -> None:
    config = AffineConfig(
        matrix_npz_path=Path(r"C:\path\to\AffineM2.npz"),
        object_name_template="element{element_id}",
        transpose_matrix=False,
    )
    apply_affine_transforms(config)


if __name__ == "__main__":
    main()
