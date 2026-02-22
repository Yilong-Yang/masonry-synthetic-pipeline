"""Compute rigid transforms from undeformed to deformed gridpoint planes.

This module is a publish-ready rewrite of `Blender/FindTransformation.py`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    from ._gridpoint_io import compute_positions, filter_plane, iter_element_dataframes, read_gridpoint_file
except ImportError:  # pragma: no cover - supports direct script usage
    from _gridpoint_io import compute_positions, filter_plane, iter_element_dataframes, read_gridpoint_file  # type: ignore


def compute_rigid_transform_4x4(
    p_orig: np.ndarray | Sequence[Sequence[float]],
    p_transformed: np.ndarray | Sequence[Sequence[float]],
) -> np.ndarray:
    """Compute a 4x4 rigid transform with the Kabsch algorithm.

    Args:
        p_orig: Source points with shape `(n, 3)`.
        p_transformed: Target points with shape `(n, 3)`.

    Returns:
        A `(4, 4)` transform matrix containing rotation and translation only.
    """
    p = np.asarray(p_orig, dtype=float)
    q = np.asarray(p_transformed, dtype=float)

    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("p_orig must be a 2D array-like with shape (n, 3).")
    if q.ndim != 2 or q.shape[1] != 3:
        raise ValueError("p_transformed must be a 2D array-like with shape (n, 3).")
    if p.shape != q.shape:
        raise ValueError(f"Point arrays must have identical shape, got {p.shape} and {q.shape}.")
    if p.shape[0] < 3:
        raise ValueError("At least 3 non-collinear points are required.")

    centroid_p = np.mean(p, axis=0)
    centroid_q = np.mean(q, axis=0)

    p_centered = p - centroid_p
    q_centered = q - centroid_q

    covariance = p_centered.T @ q_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T

    # Reflection correction to enforce a proper rotation matrix.
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T

    translation = centroid_q - rotation @ centroid_p

    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    return transform


def apply_transform(
    transform_matrix: np.ndarray | Sequence[Sequence[float]],
    points: np.ndarray | Sequence[Sequence[float]],
) -> np.ndarray:
    """Apply a 4x4 affine transform to `(n, 3)` points."""
    t = np.asarray(transform_matrix, dtype=float)
    p = np.asarray(points, dtype=float)

    if t.shape != (4, 4):
        raise ValueError("transform_matrix must have shape (4, 4).")
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("points must be a 2D array-like with shape (n, 3).")

    p_hom = np.hstack([p, np.ones((p.shape[0], 1), dtype=float)])
    q_hom = (t @ p_hom.T).T
    return q_hom[:, :3]


def validate_affine_matrix_4x4(
    t_matrix: np.ndarray | Sequence[Sequence[float]],
    p_orig: np.ndarray | Sequence[Sequence[float]],
    p_transformed: np.ndarray | Sequence[Sequence[float]],
    *,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate a transform by comparing transformed points with expected points.

    Returns:
        errors: Euclidean distance per point.
        transformed_points: Computed transformed points.
    """
    q_expected = np.asarray(p_transformed, dtype=float)
    q_computed = apply_transform(t_matrix, p_orig)

    if q_expected.shape != q_computed.shape:
        raise ValueError(
            f"Expected and computed points must have the same shape, got "
            f"{q_expected.shape} and {q_computed.shape}."
        )

    errors = np.linalg.norm(q_computed - q_expected, axis=1)

    if verbose:
        for index, error in enumerate(errors):
            print(
                f"Point {index}: Expected={q_expected[index]}, "
                f"Computed={q_computed[index]}, Error={error:.6f}"
            )

    return errors, q_computed


def build_transform_dict_from_gridpoints(
    file_path: str | Path,
    *,
    plane_axis: str = "y",
    plane_value: float = 0.0,
    plane_tolerance: float = 1e-10,
    scale: float = 1e-3,
    excluded_groups: Sequence[str] = (),
) -> dict[str, np.ndarray]:
    """Build per-element rigid transforms from a gridpoint table."""
    dataframe = read_gridpoint_file(file_path)
    plane_df = filter_plane(
        dataframe,
        axis=plane_axis,
        value=plane_value,
        tolerance=plane_tolerance,
    )

    matrix_dict: dict[str, np.ndarray] = {}
    for group_name, block_id, element_df in iter_element_dataframes(
        plane_df,
        excluded_groups=excluded_groups,
    ):
        del group_name  # group is not required for output keys
        point_coords, deformed_points = compute_positions(element_df, scale=scale)
        matrix_dict[str(block_id)] = compute_rigid_transform_4x4(point_coords, deformed_points)

    return matrix_dict


def save_transform_dict_npz(
    matrix_dict: dict[str, np.ndarray],
    output_file: str | Path,
) -> Path:
    """Save transform dictionary to `.npz` file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, **matrix_dict)
    return output_path


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute rigid transforms from a gridpoint text file.")
    parser.add_argument("input_file", help="Path to the gridpoint text file.")
    parser.add_argument("output_file", help="Path to the output .npz file.")
    parser.add_argument("--plane-axis", default="y", choices=["x", "y", "z"], help="Plane axis for filtering.")
    parser.add_argument("--plane-value", type=float, default=0.0, help="Target value for plane filtering.")
    parser.add_argument("--plane-tolerance", type=float, default=1e-10, help="Tolerance for plane filtering.")
    parser.add_argument("--scale", type=float, default=1e-3, help="Position/displacement scale factor.")
    parser.add_argument(
        "--exclude-group",
        action="append",
        default=[],
        help="Block group to exclude (repeatable).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    transforms = build_transform_dict_from_gridpoints(
        file_path=args.input_file,
        plane_axis=args.plane_axis,
        plane_value=args.plane_value,
        plane_tolerance=args.plane_tolerance,
        scale=args.scale,
        excluded_groups=tuple(args.exclude_group),
    )
    output_path = save_transform_dict_npz(transforms, args.output_file)
    print(f"Saved {len(transforms)} transforms to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

