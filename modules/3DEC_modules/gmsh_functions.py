"""Gmsh helper functions used by the public RegularPattern workflow."""

from __future__ import annotations

from typing import Iterable

import gmsh
import numpy as np


def set_points_color(point_tags: Iterable[int], r: int, g: int, b: int) -> None:
    """Apply a display color to a collection of point entities."""
    for tag in point_tags:
        gmsh.model.setColor([(0, int(tag))], r, g, b)


def create_points(points: np.ndarray, mesh_size: float) -> list[int]:
    """Create OCC points and return their tags."""
    point_tags: list[int] = []
    for vertex in np.asarray(points, dtype=float):
        x, y = vertex
        point_tag = gmsh.model.occ.addPoint(float(x), float(y), 0.0, meshSize=mesh_size)
        point_tags.append(point_tag)
    # OCC entities are not visible to the model API until synchronize() is called.
    gmsh.model.occ.synchronize()
    return point_tags


def create_2d_polygon(vertices: np.ndarray, mesh_size: float) -> dict[str, int | list[int]]:
    """Create points, boundary lines, loop, and planar surface for a polygon."""
    vertices = np.asarray(vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 2:
        raise ValueError("vertices must have shape (N, 2).")
    if len(vertices) < 3:
        raise ValueError("At least 3 vertices are required to create a polygon.")

    point_tags: list[int] = []
    for x, y in vertices:
        point_tags.append(gmsh.model.occ.addPoint(float(x), float(y), 0.0, meshSize=mesh_size))

    line_tags: list[int] = []
    for i in range(len(point_tags)):
        # Connect each vertex to the next, wrapping around at the end.
        line_tags.append(gmsh.model.occ.addLine(point_tags[i], point_tags[(i + 1) % len(point_tags)]))

    curve_loop_tag = gmsh.model.occ.addCurveLoop(line_tags)
    surface_tag = gmsh.model.occ.addPlaneSurface([curve_loop_tag])
    gmsh.model.occ.synchronize()

    return {
        "point": point_tags,
        "line": line_tags,
        "curve loop": curve_loop_tag,
        "surface": surface_tag,
    }


def read_polygon(region_entity: Iterable[tuple[int, int]]) -> np.ndarray:
    """Read boundary edges of a region as a (num_edges, 2, 2) array."""
    edge_list = []
    line_entities = gmsh.model.getBoundary(list(region_entity), oriented=True)
    for line_dim, line_tag in line_entities:
        if line_dim != 1:
            raise ValueError("Expected boundary entities of dimension 1.")

        point_entities = gmsh.model.getBoundary([(line_dim, line_tag)], oriented=True)
        if len(point_entities) != 2:
            raise ValueError("Each boundary line should have exactly two boundary points.")

        point_coords = []
        for point_dim, point_tag in point_entities:
            if point_dim != 0:
                raise ValueError("Expected boundary entities of dimension 0 for points.")
            # With oriented boundaries, point tags can be signed; geometry lookup needs absolute tag.
            x, y, *_ = gmsh.model.getValue(point_dim, abs(point_tag), [])
            point_coords.append([float(x), float(y)])

        if line_tag < 0:
            # Reverse endpoint order when edge orientation is negative.
            point_coords.reverse()
        edge_list.append(point_coords)

    return np.asarray(edge_list, dtype=float)
