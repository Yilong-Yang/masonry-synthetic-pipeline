"""Generate block_creation.dat from user geometry lines.

Expected user input file:
- a .dat file containing geometry commands (typically `block create prism ... group '...'`)

Generated output:
- same geometry lines
- runtime-calculated BOT/TOP blocks
- runtime-calculated `fish def geo_params` section
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from const import BLOCK_DEFAULTS

NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
GROUP_PATTERN = re.compile(r"group\s+'([^']+)'", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate block_creation.dat from geometry-only input."
    )
    parser.add_argument(
        "--geometry-input",
        type=Path,
        required=True,
        help="Path to geometry-only .dat file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("block_creation.dat"),
        help="Output path. Default: block_creation.dat",
    )
    parser.add_argument(
        "--bottom-thickness",
        type=float,
        default=BLOCK_DEFAULTS.bottom_block_thickness,
        help=f"Bottom block thickness. Default: {BLOCK_DEFAULTS.bottom_block_thickness}",
    )
    parser.add_argument(
        "--top-thickness",
        type=float,
        default=BLOCK_DEFAULTS.top_block_thickness,
        help=f"Top block thickness. Default: {BLOCK_DEFAULTS.top_block_thickness}",
    )
    parser.add_argument(
        "--z-threshold",
        type=float,
        default=BLOCK_DEFAULTS.z_threshold,
        help=f"z threshold for geo_params. Default: {BLOCK_DEFAULTS.z_threshold}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )
    return parser.parse_args()


def fmt(value: float) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.12g}"


def extract_group(line: str) -> str | None:
    match = GROUP_PATTERN.search(line)
    return match.group(1) if match else None


def extract_numbers(line: str) -> list[float]:
    clean = GROUP_PATTERN.sub("", line)
    clean = re.sub(r"face-\d+", "", clean, flags=re.IGNORECASE)
    return [float(token) for token in NUMBER_PATTERN.findall(clean)]


def points_from_line(line: str, numbers: list[float]) -> list[tuple[float, float, float]]:
    if re.search(r"\bblock\s+create\s+brick\b", line, re.IGNORECASE) and len(numbers) >= 6:
        x_min, x_max, y_min, y_max, z_min, z_max = numbers[:6]
        return [
            (x_min, y_min, z_min),
            (x_min, y_min, z_max),
            (x_min, y_max, z_min),
            (x_min, y_max, z_max),
            (x_max, y_min, z_min),
            (x_max, y_min, z_max),
            (x_max, y_max, z_min),
            (x_max, y_max, z_max),
        ]
    if len(numbers) >= 3 and len(numbers) % 3 == 0:
        return [(numbers[i], numbers[i + 1], numbers[i + 2]) for i in range(0, len(numbers), 3)]
    return []


def parse_geometry_lines(text: str) -> tuple[list[str], list[tuple[float, float, float]], list[str]]:
    geometry_lines: list[str] = []
    points: list[tuple[float, float, float]] = []
    groups: list[str] = []
    seen_groups: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not re.search(r"\bblock\s+create\b", line, re.IGNORECASE):
            continue

        group = extract_group(line)
        if group is None:
            continue
        if group.upper() in {"BOT", "TOP"}:
            continue

        geometry_lines.append(line)
        if group not in seen_groups:
            groups.append(group)
            seen_groups.add(group)

        numbers = extract_numbers(line)
        points.extend(points_from_line(line, numbers))

    return geometry_lines, points, groups


def axis_limits(points: Iterable[tuple[float, float, float]]) -> tuple[float, float, float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def build_output(
    geometry_lines: list[str],
    groups: list[str],
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_min: float,
    z_max: float,
    bottom_thickness: float,
    top_thickness: float,
    z_threshold: float,
) -> str:
    top_contact_z = z_max
    bot_contact_z = z_min
    top_z = top_contact_z + top_thickness
    bot_bottom_z = bot_contact_z - bottom_thickness
    top_center_x = 0.5 * (x_min + x_max)
    top_center_y = 0.5 * (y_min + y_max)

    if groups:
        group_list_items = ", ".join(f"'{group}'" for group in groups)
    else:
        group_list_items = "'brick'"

    runtime_lines = [
        f"block create brick {fmt(x_min)} {fmt(x_max)} {fmt(y_min)} {fmt(y_max)} {fmt(bot_bottom_z)} {fmt(bot_contact_z)} group 'BOT' ; Needs to be changed during runtime",
        f"block create brick {fmt(x_min)} {fmt(x_max)} {fmt(y_min)} {fmt(y_max)} {fmt(top_contact_z)} {fmt(top_z)} group 'TOP' ; Needs to be changed during runtime",
        "fish def geo_params",
        f"    global top_contact_z = {fmt(top_contact_z)} ; Needs to be changed during runtime",
        f"    global bot_contact_z = {fmt(bot_contact_z)} ; Needs to be changed during runtime",
        f"    global top_z = {fmt(top_z)} ; Needs to be changed during runtime",
        f"    global z_threshold = {fmt(z_threshold)} ; Needs to be changed during runtime",
        f"    global top_center = vector({fmt(top_center_x)}, {fmt(top_center_y)}, {fmt(top_z)}) ; Needs to be changed during runtime",
        f"    global group_list = list.sequence({group_list_items}) ; Needs to be changed during runtime",
        "end",
        "[geo_params]",
    ]

    return "\n".join(geometry_lines + runtime_lines) + "\n"


def main() -> int:
    args = parse_args()
    if not args.geometry_input.is_file():
        raise FileNotFoundError(f"Geometry input not found: {args.geometry_input}")
    if args.output.exists() and not args.force:
        raise FileExistsError(f"{args.output} already exists. Use --force to overwrite.")

    input_text = args.geometry_input.read_text(encoding="utf-8")
    geometry_lines, points, groups = parse_geometry_lines(input_text)
    if not geometry_lines:
        raise ValueError("No geometry lines found. Provide lines with `block create ... group '...'`.")
    if not points:
        raise ValueError("Could not extract numeric coordinates from geometry lines.")

    x_min, x_max, y_min, y_max, z_min, z_max = axis_limits(points)
    output_text = build_output(
        geometry_lines=geometry_lines,
        groups=groups,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
        bottom_thickness=args.bottom_thickness,
        top_thickness=args.top_thickness,
        z_threshold=args.z_threshold,
    )
    args.output.write_text(output_text, encoding="utf-8")

    print(f"Generated: {args.output}")
    print(f"Geometry lines: {len(geometry_lines)}")
    print(f"Groups: {', '.join(groups) if groups else 'none'}")
    print(f"Extents x=[{fmt(x_min)}, {fmt(x_max)}], y=[{fmt(y_min)}, {fmt(y_max)}], z=[{fmt(z_min)}, {fmt(z_max)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
