"""Shared helpers for reading and processing 3DEC-style gridpoint tables."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Sequence

import numpy as np
import pandas as pd

REQUIRED_GRIDPOINT_COLUMNS = (
    "Block_ID",
    "Block_group",
    "Pos_x",
    "Pos_y",
    "Pos_z",
    "Disp_x",
    "Disp_y",
    "Disp_z",
)


def read_gridpoint_file(file_path: str | Path) -> pd.DataFrame:
    """Read a whitespace-delimited gridpoint file and validate required columns."""
    path = Path(file_path)
    dataframe = pd.read_csv(path, sep=r"\s+", engine="python")

    missing = [column for column in REQUIRED_GRIDPOINT_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(
            f"Missing required columns in {path}: {', '.join(missing)}"
        )
    return dataframe


def filter_plane(
    dataframe: pd.DataFrame,
    *,
    axis: str = "y",
    value: float = 0.0,
    tolerance: float = 1e-10,
) -> pd.DataFrame:
    """Filter rows where `Pos_<axis>` is within tolerance of value."""
    axis_normalized = axis.lower()
    if axis_normalized not in {"x", "y", "z"}:
        raise ValueError("axis must be one of: 'x', 'y', 'z'.")

    column = f"Pos_{axis_normalized}"
    return dataframe[np.abs(dataframe[column] - value) <= tolerance].copy()


def iter_element_dataframes(
    dataframe: pd.DataFrame,
    *,
    excluded_groups: Sequence[str] = (),
) -> Iterator[tuple[str, int, pd.DataFrame]]:
    """Yield `(block_group, block_id, element_df)` tuples."""
    excluded = set(excluded_groups)

    for group_name in sorted(dataframe["Block_group"].dropna().unique().tolist()):
        if group_name in excluded:
            continue
        group_df = dataframe[dataframe["Block_group"] == group_name]
        for block_id in sorted(group_df["Block_ID"].unique().tolist()):
            element_df = group_df[group_df["Block_ID"] == block_id]
            yield str(group_name), int(block_id), element_df


def compute_positions(
    element_df: pd.DataFrame,
    *,
    scale: float = 1e-3,
) -> tuple[np.ndarray, np.ndarray]:
    """Return undeformed and deformed XYZ arrays for one element."""
    point_coords = element_df[["Pos_x", "Pos_y", "Pos_z"]].to_numpy(dtype=float) * scale
    point_disp = element_df[["Disp_x", "Disp_y", "Disp_z"]].to_numpy(dtype=float) * scale
    return point_coords, point_coords + point_disp

