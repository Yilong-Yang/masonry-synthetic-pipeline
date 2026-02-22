"""Geometry and sampling utilities used by the public RegularPattern workflow."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import polygonize


def round_to_n_sig_figs(number: float, n: int) -> float:
    """Round to `n` significant figures."""
    if number == 0:
        return 0.0
    # Convert significant-figure precision to decimal-place precision for round().
    digits = n - int(math.floor(math.log10(abs(number)))) - 1
    return round(number, digits)


def read_blocks(filename: str | Path) -> dict[str, list[list[float]]]:
    """Read block vertices from the input text format."""
    blocks: dict[str, list[list[float]]] = {}
    current_block: str | None = None

    with Path(filename).open("r", encoding="utf-8") as file_obj:
        for raw_line in file_obj:
            line = raw_line.strip()
            if not line:
                # Ignore empty separators.
                continue

            if line.startswith("Block"):
                # Start a new block section.
                current_block = line
                blocks[current_block] = []
                continue

            if current_block is None:
                raise ValueError("Found coordinates before any block header.")

            # Keep 4 significant figures to match original preprocessing behavior.
            values = [round_to_n_sig_figs(float(value.strip()), 4) for value in line.split(",")]
            if len(values) != 3:
                raise ValueError(f"Expected 3 coordinates per line, got {len(values)}: '{line}'")
            blocks[current_block].append(values)

    return blocks


def reorder_vertices(vertices: np.ndarray) -> np.ndarray:
    """Order polygon vertices counterclockwise around centroid."""
    vertices = np.asarray(vertices, dtype=float)
    center = vertices.mean(axis=0)
    # Sorting by angle around centroid gives a stable polygon ordering.
    angles = np.arctan2(vertices[:, 1] - center[1], vertices[:, 0] - center[0])
    return vertices[np.argsort(angles)]


def find_bounding_box(points: np.ndarray) -> np.ndarray:
    """Return bounding-box vertices in counterclockwise order."""
    points = points.reshape(-1, 2)
    min_x, min_y = np.min(points, axis=0)
    max_x, max_y = np.max(points, axis=0)
    # Return corners CCW, starting from lower-left.
    return np.asarray(
        [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
        ],
        dtype=float,
    )


def _edge_list_to_polygon_with_holes(edge_list: Iterable[Iterable[Iterable[float]]]) -> Polygon:
    """Build a polygon (with optional holes) from an edge list."""
    lines = []
    for edge in edge_list:
        edge_array = np.asarray(edge, dtype=float)
        if edge_array.shape != (2, 2):
            raise ValueError(f"Expected each edge to have shape (2, 2), got {edge_array.shape}.")
        lines.append(LineString(edge_array))

    # Reconstruct closed rings from potentially unordered edge segments.
    polygons = list(polygonize(lines))
    if not polygons:
        return Polygon()

    # Treat largest ring as exterior; contained rings become holes.
    outer = max(polygons, key=lambda poly: poly.area)
    holes = [
        list(poly.exterior.coords)
        for poly in polygons
        if poly != outer and outer.contains(poly.representative_point())
    ]

    polygon = Polygon(outer.exterior.coords, holes=holes)
    if isinstance(polygon, MultiPolygon):
        # Keep only dominant connected component.
        polygon = max(polygon.geoms, key=lambda poly: poly.area)
    if not polygon.is_valid:
        # buffer(0) is a standard topology fix for minor self-intersections.
        polygon = polygon.buffer(0)
        if isinstance(polygon, MultiPolygon):
            polygon = max(polygon.geoms, key=lambda poly: poly.area)
    return polygon


def _shrink_polygon(polygon: Polygon, distance: float) -> Polygon:
    """Shrink polygon inward by `distance`."""
    if distance < 0:
        raise ValueError("distance must be non-negative.")
    # Negative buffer creates a boundary clearance margin.
    shrunken = polygon.buffer(-distance)
    if isinstance(shrunken, MultiPolygon):
        shrunken = max(shrunken.geoms, key=lambda poly: poly.area)
    return shrunken if isinstance(shrunken, Polygon) and not shrunken.is_empty else Polygon()


def _sample_point_in_polygon(polygon: Polygon, rng: np.random.Generator) -> Point | None:
    """Sample a random point using rejection sampling within polygon bounds."""
    min_x, min_y, max_x, max_y = polygon.bounds
    for _ in range(500):
        candidate = Point(rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
        if polygon.contains(candidate):
            return candidate
    # Return None if sampling fails repeatedly (e.g., very thin polygon).
    return None


def generate_random_points(
    edge_list: np.ndarray,
    n: int,
    d: float,
    rng: np.random.Generator | None = None,
    candidates_per_iteration: int = 100,
) -> np.ndarray:
    """Generate up to `n` well-spaced points inside an edge-defined polygon."""
    if n <= 0:
        return np.empty((0, 2), dtype=float)
    if d < 0:
        raise ValueError("d must be non-negative.")
    if candidates_per_iteration <= 0:
        raise ValueError("candidates_per_iteration must be positive.")

    polygon = _edge_list_to_polygon_with_holes(edge_list)
    polygon = _shrink_polygon(polygon, distance=d)
    if polygon.is_empty:
        return np.empty((0, 2), dtype=float)

    rng = rng if rng is not None else np.random.default_rng()
    selected_points: list[Point] = []

    centroid = polygon.centroid
    # Start from a representative interior point to seed the spacing process.
    selected_points.append(centroid if polygon.contains(centroid) else polygon.representative_point())

    for _ in range(1, n):
        best_candidate = None
        best_min_distance = -1.0

        # Greedy farthest-point sampling: choose candidate maximizing distance to selected set.
        for _ in range(candidates_per_iteration):
            candidate = _sample_point_in_polygon(polygon, rng)
            if candidate is None:
                continue
            min_distance = min(candidate.distance(existing) for existing in selected_points)
            if min_distance > best_min_distance:
                best_min_distance = min_distance
                best_candidate = candidate

        if best_candidate is None:
            break
        selected_points.append(best_candidate)

    return np.asarray([(point.x, point.y) for point in selected_points], dtype=float)
