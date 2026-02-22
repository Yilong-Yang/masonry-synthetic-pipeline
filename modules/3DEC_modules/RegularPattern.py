"""Generate a 2D masonry mesh (bricks + mortar) from block geometry input.

This script is a publication-ready rewrite of the original `RegularPattern.py`.
It keeps the same meshing intent while adding:
1. Argument parsing for reproducible runs.
2. Type hints and explicit validation.
3. Clear separation of setup, geometry construction, and meshing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import gmsh
import numpy as np

from const import color_dict
from functions import (
    find_bounding_box,
    generate_random_points,
    read_blocks,
    reorder_vertices,
)
from gmsh_functions import create_2d_polygon, create_points, read_polygon, set_points_color

SURFACE_DIM = 2
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class MeshConfig:
    input_file: Path
    output_file: Path | None
    mesh_size: float
    seed_count: int
    mesh_algorithm: int
    random_seed: int | None
    show_gui: bool


def _resolve_path(path_value: Path) -> Path:
    """Resolve relative paths against this script directory."""
    return path_value if path_value.is_absolute() else (SCRIPT_DIR / path_value)


def _parse_args(argv: Sequence[str]) -> MeshConfig:
    parser = argparse.ArgumentParser(
        description="Create a regular masonry mesh with brick and mortar regions."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/Wallet_example.txt"),
        help="Input block geometry file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/Wallet_example.msh"),
        help="Output mesh file path.",
    )
    parser.add_argument(
        "--mesh-size",
        type=float,
        default=0.005,
        help="Target mesh size for generated points and surfaces.",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=10,
        help="Base number of seed points used to control mesh density and randomness.",
    )
    parser.add_argument(
        "--mesh-algorithm",
        type=int,
        default=5,
        help="Gmsh 2D mesh algorithm index.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic point generation.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable the Gmsh FLTK viewer.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing mesh output to disk.",
    )
    parser.add_argument("-nopopup", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    if args.mesh_size <= 0:
        raise ValueError("--mesh-size must be positive.")
    if args.seed_count <= 0:
        raise ValueError("--seed-count must be a positive integer.")

    return MeshConfig(
        input_file=_resolve_path(args.input),
        output_file=None if args.no_write else _resolve_path(args.output),
        mesh_size=args.mesh_size,
        seed_count=args.seed_count,
        mesh_algorithm=args.mesh_algorithm,
        random_seed=args.random_seed,
        show_gui=not (args.no_gui or args.nopopup),
    )


def _load_blocks_as_2d_vertices(input_file: Path) -> np.ndarray:
    """Load 3D blocks and project to the X-Z plane used for 2D meshing."""
    blocks = read_blocks(input_file)
    blocks_np = np.asarray(list(blocks.values()), dtype=float)
    # Keep X and Z coordinates from the source geometry.
    blocks_np = blocks_np[:, :, [0, 2]]
    # Remove duplicate vertices per block, then enforce consistent ordering.
    blocks_np = np.unique(blocks_np, axis=1)
    return np.asarray([reorder_vertices(vertices) for vertices in blocks_np], dtype=float)


def _embed_random_points(
    surface_tag: int,
    seed_count: int,
    min_distance_to_boundary: float,
    mesh_size: float,
    rng: np.random.Generator,
) -> None:
    """Generate and embed interior seed points into one surface."""
    polygon_edges = read_polygon([(SURFACE_DIM, surface_tag)])
    random_points = generate_random_points(
        polygon_edges,
        n=seed_count,
        d=min_distance_to_boundary,
        rng=rng,
    )
    if random_points.size == 0:
        return

    random_tags = create_points(random_points, mesh_size=mesh_size)
    gmsh.model.mesh.embed(0, random_tags, SURFACE_DIM, surface_tag)
    set_points_color(random_tags, *color_dict["red"])


def build_mesh(config: MeshConfig) -> None:
    """Build and optionally save the masonry mesh."""
    block_vertices = _load_blocks_as_2d_vertices(config.input_file)
    wall_vertices = find_bounding_box(block_vertices)
    rng = np.random.default_rng(config.random_seed)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("Geometry.PointSize", 6)
        gmsh.option.setNumber("Mesh.PointSize", 8)

        wall_tags = create_2d_polygon(wall_vertices, config.mesh_size)
        block_tags = []
        for index, block in enumerate(block_vertices, start=1):
            tags = create_2d_polygon(block, config.mesh_size)
            block_tags.append(tags)
            physical_tag = gmsh.model.addPhysicalGroup(SURFACE_DIM, [tags["surface"]])
            gmsh.model.setPhysicalName(SURFACE_DIM, physical_tag, f"Brick_{index:03d}")

        wall_entity = [(SURFACE_DIM, wall_tags["surface"])]
        brick_entities = [(SURFACE_DIM, tags["surface"]) for tags in block_tags]
        # Mortar is defined as the wall area minus all brick areas.
        cut_result = gmsh.model.occ.cut(wall_entity, brick_entities, removeTool=False)
        gmsh.model.occ.synchronize()

        remaining_entities = cut_result[0]
        if not remaining_entities:
            raise RuntimeError("Boolean cut produced no remaining mortar surface.")
        mortar_surface_tag = remaining_entities[0][1]

        mortar_group_tag = gmsh.model.addPhysicalGroup(SURFACE_DIM, [mortar_surface_tag])
        gmsh.model.setPhysicalName(SURFACE_DIM, mortar_group_tag, "Mortar")

        # Place fewer seeds in bricks, more in mortar to stabilize grading across joints.
        for tags in block_tags:
            _embed_random_points(
                surface_tag=tags["surface"],
                seed_count=max(1, config.seed_count // 2),
                min_distance_to_boundary=config.mesh_size,
                mesh_size=config.mesh_size,
                rng=rng,
            )

        _embed_random_points(
            surface_tag=mortar_surface_tag,
            seed_count=config.seed_count * 4,
            min_distance_to_boundary=config.mesh_size / 2.0,
            mesh_size=config.mesh_size,
            rng=rng,
        )

        gmsh.model.setColor(brick_entities, *color_dict["grey"])
        gmsh.model.setColor(remaining_entities, *color_dict["grey_green"])

        gmsh.option.setNumber("Mesh.Algorithm", config.mesh_algorithm)
        gmsh.model.mesh.generate(SURFACE_DIM)

        if config.output_file is not None:
            config.output_file.parent.mkdir(parents=True, exist_ok=True)
            gmsh.write(str(config.output_file))

        if config.show_gui:
            gmsh.fltk.run()
    finally:
        gmsh.finalize()


def main(argv: Sequence[str] | None = None) -> None:
    config = _parse_args(argv if argv is not None else [])
    build_mesh(config)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
