"""Export prism-plane geometry from a gridpoint table to OBJ files.

This module is a publish-ready rewrite of `Blender/ReadPrisms.py`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

try:
    from ._gridpoint_io import compute_positions, filter_plane, iter_element_dataframes, read_gridpoint_file
except ImportError:  # pragma: no cover - supports direct script usage
    from _gridpoint_io import compute_positions, filter_plane, iter_element_dataframes, read_gridpoint_file  # type: ignore


def write_obj(
    vertices: np.ndarray | Sequence[Sequence[float]],
    filename: str | Path,
    *,
    decimal_places: int = 6,
    object_name: str = "surface",
) -> Path:
    """Write one polygon object to an OBJ file.

    Args:
        vertices: Array-like with shape `(n, 3)` and `n >= 3`.
        filename: Output OBJ path.
        decimal_places: Decimal precision for vertex coordinates.
        object_name: Prefix used in OBJ group line.

    Returns:
        Output path.
    """
    points = np.asarray(vertices, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("vertices must be a 2D array-like with shape (n, 3).")
    if points.shape[0] < 3:
        raise ValueError("at least 3 vertices are required to write an OBJ face.")

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = f"{{:.{decimal_places}f}}"
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Polygonal plane\n")
        for x, y, z in points:
            handle.write(f"v {fmt.format(x)} {fmt.format(y)} {fmt.format(z)}\n")
        handle.write("\n")
        handle.write(f"g {object_name}1\n")
        face = " ".join(str(index) for index in range(1, points.shape[0] + 1))
        handle.write(f"f {face}\n")

    return output_path


def map_block_group_name(block_group_name: str) -> str:
    """Map block-group names to output folder categories."""
    if block_group_name in {"brick1", "mortar"}:
        return "mortar"
    return "brick"


def block_group_name_convert(bg_name: str) -> str:
    """Compatibility wrapper for the legacy function name."""
    return map_block_group_name(bg_name)


def export_prisms_from_gridpoints(
    file_path: str | Path,
    output_base: str | Path,
    *,
    plane_axis: str = "y",
    plane_value: float = 0.0,
    plane_tolerance: float = 1e-10,
    scale: float = 1e-3,
    excluded_groups: Sequence[str] = ("TOP", "BOT"),
    group_mapper: Callable[[str], str] = map_block_group_name,
    decimal_places: int = 6,
) -> dict[str, int]:
    """Export undeformed/deformed prism-plane OBJ files.

    Folder layout:
    - `<output_base>/undeformed/<mapped_group>/element<ID>.obj`
    - `<output_base>/deformed/<mapped_group>/element<ID>.obj`
    """
    dataframe = read_gridpoint_file(file_path)
    plane_df = filter_plane(
        dataframe,
        axis=plane_axis,
        value=plane_value,
        tolerance=plane_tolerance,
    )

    output_root = Path(output_base)
    counts = {"elements": 0, "undeformed_files": 0, "deformed_files": 0}

    for group_name, block_id, element_df in iter_element_dataframes(
        plane_df,
        excluded_groups=excluded_groups,
    ):
        undeformed, deformed = compute_positions(element_df, scale=scale)
        mapped_group = group_mapper(group_name)

        undeformed_path = output_root / "undeformed" / mapped_group / f"element{block_id}.obj"
        deformed_path = output_root / "deformed" / mapped_group / f"element{block_id}.obj"

        write_obj(
            undeformed,
            undeformed_path,
            decimal_places=decimal_places,
            object_name="surface",
        )
        write_obj(
            deformed,
            deformed_path,
            decimal_places=decimal_places,
            object_name="surface",
        )

        counts["elements"] += 1
        counts["undeformed_files"] += 1
        counts["deformed_files"] += 1

    return counts


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export prism plane OBJ files from a gridpoint table.")
    parser.add_argument("input_file", help="Path to the gridpoint text file.")
    parser.add_argument("output_base", help="Base folder for OBJ outputs.")
    parser.add_argument("--plane-axis", default="y", choices=["x", "y", "z"], help="Plane axis for filtering.")
    parser.add_argument("--plane-value", type=float, default=0.0, help="Target value for plane filtering.")
    parser.add_argument("--plane-tolerance", type=float, default=1e-10, help="Tolerance for plane filtering.")
    parser.add_argument("--scale", type=float, default=1e-3, help="Position/displacement scale factor.")
    parser.add_argument("--decimal-places", type=int, default=6, help="OBJ coordinate precision.")
    parser.add_argument(
        "--exclude-group",
        action="append",
        default=["TOP", "BOT"],
        help="Block group to exclude (repeatable).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    result = export_prisms_from_gridpoints(
        file_path=args.input_file,
        output_base=args.output_base,
        plane_axis=args.plane_axis,
        plane_value=args.plane_value,
        plane_tolerance=args.plane_tolerance,
        scale=args.scale,
        excluded_groups=tuple(args.exclude_group),
        decimal_places=args.decimal_places,
    )

    print(
        f"Export complete: {result['elements']} elements, "
        f"{result['undeformed_files']} undeformed files, "
        f"{result['deformed_files']} deformed files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

