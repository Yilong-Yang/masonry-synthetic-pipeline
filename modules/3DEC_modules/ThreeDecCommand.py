"""Convert a 2D Gmsh mesh into 3DEC block creation commands.

This script is a publication-ready rewrite of `ThreeDecCommand.py`.
It converts triangular surface cells into extruded prism blocks and writes
auxiliary TOP/BOT loading blocks plus a FISH helper definition.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import meshio
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ExportConfig:
    input_mesh: Path
    output_dat: Path
    extrusion: float
    scale: float
    has_mortar: bool
    mortar_index: int
    group_prefix: str
    mortar_group_name: str


def _resolve_path(path_value: Path) -> Path:
    """Resolve relative paths against this script directory."""
    return path_value if path_value.is_absolute() else (SCRIPT_DIR / path_value)


def _format_number(value: float) -> str:
    """Format with 6 significant digits to keep command files compact."""
    return f"{value:.6g}"


def _format_group_list(group_names: Sequence[str]) -> str:
    return ", ".join(f"'{name}'" for name in group_names)


def _make_brick_command(block_limits: np.ndarray, group_name: str) -> str:
    """Create a 3DEC brick command from axis-aligned min/max limits."""
    coords = " ".join(_format_number(value) for pair in block_limits for value in pair)
    return f"block create brick {coords} group '{group_name}'"


def _make_prism_command(face1: np.ndarray, face2: np.ndarray, group_name: str) -> str:
    """Create a 3DEC prism command from two 3-point faces."""
    face1 = np.asarray(face1, dtype=float)
    face2 = np.asarray(face2, dtype=float)
    if face1.shape != (3, 3) or face2.shape != (3, 3):
        raise ValueError("face1 and face2 must each have shape (3, 3).")
    face1_coords = " ".join(f"{x:.6f}" for x in face1.flatten())
    face2_coords = " ".join(f"{x:.6f}" for x in face2.flatten())
    return f"block create prism face-1 {face1_coords} face-2 {face2_coords} group '{group_name}'"


def _compute_enclosure(points_xyz: np.ndarray, scale: float, extrusion: float) -> dict[str, tuple[float, float]]:
    """Compute scaled enclosure bounds in the legacy axis convention.

    Axis mapping follows the original script behavior:
    - source X -> 3DEC X
    - source Y -> 3DEC Z
    - source Z -> 3DEC Y
    """
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise ValueError("points_xyz must have shape (N, 3).")

    scaled = points_xyz * scale
    mins = scaled.min(axis=0)
    maxs = scaled.max(axis=0)

    return {
        "x": (mins[0], maxs[0]),
        "z": (mins[1], maxs[1]),
        "y": (mins[2], maxs[2] + extrusion * scale),
    }


def _compute_loading_blocks(
    enclosure: dict[str, tuple[float, float]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create BOT/TOP loading block limits and top-center location."""
    z_min, z_max = enclosure["z"]
    loading_thickness = 0.05 * (z_max - z_min)

    x_min, x_max = enclosure["x"]
    y_min, y_max = enclosure["y"]

    top_block = np.asarray(
        [
            [x_min, x_max],
            [y_min, y_max],
            [z_max, z_max + loading_thickness],
        ],
        dtype=float,
    )
    bot_block = np.asarray(
        [
            [x_min, x_max],
            [y_min, y_max],
            [z_min - loading_thickness, z_min],
        ],
        dtype=float,
    )
    top_center = np.asarray(
        [
            np.mean(top_block[0]),
            np.mean(top_block[1]),
            top_block[2, 1],
        ],
        dtype=float,
    )
    return bot_block, top_block, top_center


def _group_names(
    num_cell_blocks: int,
    has_mortar: bool,
    mortar_index: int,
    group_prefix: str,
    mortar_group_name: str,
) -> list[str]:
    """Assign group names per mesh cell block."""
    if num_cell_blocks <= 0:
        raise ValueError("Mesh contains no cell blocks.")

    if has_mortar:
        names = [group_prefix for _ in range(num_cell_blocks)]
        normalized_idx = mortar_index if mortar_index >= 0 else num_cell_blocks + mortar_index
        if normalized_idx < 0 or normalized_idx >= num_cell_blocks:
            raise ValueError(
                f"mortar_index={mortar_index} is out of range for {num_cell_blocks} cell blocks."
            )
        names[normalized_idx] = mortar_group_name
        return names

    return [f"{group_prefix}{i}" for i in range(num_cell_blocks)]


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _mesh_to_prism_commands(mesh: meshio.Mesh, config: ExportConfig) -> tuple[list[str], list[str]]:
    """Convert triangular cells to prism commands and return commands + group names."""
    points = np.asarray(mesh.points, dtype=float)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("Mesh points must have at least 3 coordinates per point.")
    points = points[:, :3]

    groups = _group_names(
        num_cell_blocks=len(mesh.cells),
        has_mortar=config.has_mortar,
        mortar_index=config.mortar_index,
        group_prefix=config.group_prefix,
        mortar_group_name=config.mortar_group_name,
    )

    commands: list[str] = []
    for cell_block, group_name in zip(mesh.cells, groups):
        connectivity = np.asarray(cell_block.data, dtype=int)
        if connectivity.ndim != 2 or connectivity.shape[1] != 3:
            raise ValueError(
                f"Cell block '{cell_block.type}' must be triangular (shape (N, 3)); "
                f"got {connectivity.shape}."
            )

        for triangle_indices in connectivity:
            # Reorder axes to preserve original command convention: (x, z, y).
            triangle = points[triangle_indices].copy()
            triangle[:, [1, 2]] = triangle[:, [2, 1]]

            # Extrude each triangle into a prism with thickness along local Y.
            face1 = triangle.copy()
            face2 = triangle.copy()
            face1[:, 1] = 0.0
            face2[:, 1] = config.extrusion
            face1 *= config.scale
            face2 *= config.scale

            commands.append(_make_prism_command(face1, face2, group_name))

    return commands, groups


def _geo_params_command(top_block: np.ndarray, bot_block: np.ndarray, top_center: np.ndarray, groups: list[str]) -> str:
    """Build FISH helper function that stores shared geometry parameters."""
    unique_groups = _unique_preserve_order(groups)
    return (
        "fish def geo_params\n"
        f"    global top_contact_z = {_format_number(top_block[2, 0])}\n"
        f"    global bot_contact_z = {_format_number(bot_block[2, 1])}\n"
        f"    global top_z = {_format_number(top_block[2, 1])}\n"
        "    global z_threshold = 0.001\n"
        f"    global top_center = vector({_format_number(top_center[0])}, {_format_number(top_center[1])}, {_format_number(top_center[2])})\n"
        f"    global group_list = list.sequence({_format_group_list(unique_groups)})\n"
        "end\n"
        "[geo_params]"
    )


def _parse_args(argv: Sequence[str]) -> ExportConfig:
    parser = argparse.ArgumentParser(
        description="Export a Gmsh mesh into 3DEC prism/block command format."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/Wallet_example.msh"),
        help="Input Gmsh mesh file (.msh).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/threedec/Wallet_example.dat"),
        help="Output 3DEC command file path.",
    )
    parser.add_argument(
        "--extrusion",
        type=float,
        default=0.065,
        help="Extrusion thickness for each triangular prism.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1e3,
        help="Uniform scale factor applied before writing commands.",
    )
    parser.add_argument(
        "--no-mortar",
        action="store_true",
        help="Disable mortar labeling; all cell blocks become uniquely named brick groups.",
    )
    parser.add_argument(
        "--mortar-index",
        type=int,
        default=-1,
        help="Cell-block index used as mortar group when mortar mode is enabled (default: last).",
    )
    parser.add_argument(
        "--group-prefix",
        type=str,
        default="brick",
        help="Base name for brick groups.",
    )
    parser.add_argument(
        "--mortar-group-name",
        type=str,
        default="mortar",
        help="Group name assigned to the mortar block.",
    )

    args = parser.parse_args(argv)

    if args.extrusion <= 0:
        raise ValueError("--extrusion must be positive.")
    if args.scale <= 0:
        raise ValueError("--scale must be positive.")

    return ExportConfig(
        input_mesh=_resolve_path(args.input),
        output_dat=_resolve_path(args.output),
        extrusion=args.extrusion,
        scale=args.scale,
        has_mortar=not args.no_mortar,
        mortar_index=args.mortar_index,
        group_prefix=args.group_prefix,
        mortar_group_name=args.mortar_group_name,
    )


def export_threedec_commands(config: ExportConfig) -> Path:
    """Read mesh, generate command text, and write output file."""
    mesh = meshio.read(str(config.input_mesh))
    points = np.asarray(mesh.points, dtype=float)[:, :3]
    enclosure = _compute_enclosure(points_xyz=points, scale=config.scale, extrusion=config.extrusion)
    bot_block, top_block, top_center = _compute_loading_blocks(enclosure)

    prism_commands, groups = _mesh_to_prism_commands(mesh, config)
    output_lines = []
    output_lines.extend(prism_commands)
    output_lines.append(_make_brick_command(bot_block, "BOT"))
    output_lines.append(_make_brick_command(top_block, "TOP"))
    output_lines.append(_geo_params_command(top_block, bot_block, top_center, groups))

    config.output_dat.parent.mkdir(parents=True, exist_ok=True)
    with config.output_dat.open("w", encoding="utf-8", newline="\n") as file_obj:
        file_obj.write("\n".join(output_lines))
        file_obj.write("\n")

    return config.output_dat


def main(argv: Sequence[str] | None = None) -> None:
    config = _parse_args(argv if argv is not None else [])
    export_threedec_commands(config)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
