"""Simple generator for params.dat.

Usage:
    python ParamsGen.py
    python ParamsGen.py --interactive
    python ParamsGen.py --output my_params.dat --force
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from const import DEFAULTS, ParamsConfig


PARAMS_TEMPLATE = """fish def params
    ; All units are compatible with millimeters
    global mesh_size = {mesh_size} ; mm
    global gravity_const = {gravity_const} ; mm/s^2

    global density = {density} ; kg/mm^3
    ; parameters of the bonding
    global E = {E}  ; elasticity in kg mm^-1 s^-2, or kPa
    global G = E/3 ; shear elasticity
    global joint_spacing = {joint_spacing} ; mm
    global K_n = E/joint_spacing
    global K_s = G/joint_spacing
    global t_strength = {t_strength} ; tensile strength in kg mm^-1 s^-2
    global c_strength = {c_strength} ; kg mm^-1 s^-2
    global friction_angle = {friction_angle}
    global cohesion = {cohesion} ; in kg mm^-1 s^-2
    global cohesion_res = {cohesion_res}

    ; parameters of potential crack surfaces (b-bricks)
    global s_factor = {s_factor}
    global E_b = E*s_factor ; strong brick and weak bond
    global G_b = E_b / 3
    global K_n_b = E_b / joint_spacing ; same joint spacing is used
    global K_s_b = G_b / joint_spacing
    global t_strength_b = {t_strength_b} ; in kg mm^-1 s^-2, or kPa
    global c_strength_b = {c_strength_b} ; in kg mm^-1 s^-2, or kPa
    global friction_angle_b = {friction_angle_b}
    global cohesion_b = {cohesion_b} ; in kg mm^-1 s^-2
    global cohesion_res_b = {cohesion_res_b}

    ; empirical relationships
    ; bond
    global G_t = t_strength*0.029e-3 * 1e3 ; energy release rate in kg s^-1
    global G_s = G_t*10
    global G_c = c_strength*1.6e-3 * 1e3
    ; potential crack surfaces - bricks
    global G_t_b = t_strength_b * 0.029e-3 * 1e3
    global G_s_b = G_t_b * 10
    global G_c_b = c_strength_b * 1.6e-3 * 1e3

    ; loading params
    global cycle_n = {cycle_n}
    global velocity = {velocity}
    global loading_group = '{loading_group}'
    global amp = {amp}
    global v_pressure = {v_pressure} ; in kg mm^-1 s^-2, or MPa
end
[params]
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate params.dat from const.py values.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("params.dat"),
        help="Output file path. Default: params.dat",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for values before writing params.dat.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )
    return parser.parse_args()


def format_num(value: float) -> str:
    return f"{value:.12g}"


def prompt_float(label: str, current: float) -> float:
    raw = input(f"{label} [{current}]: ").strip()
    if not raw:
        return current
    return float(raw)


def prompt_int(label: str, current: int) -> int:
    raw = input(f"{label} [{current}]: ").strip()
    if not raw:
        return current
    return int(raw)


def prompt_str(label: str, current: str) -> str:
    raw = input(f"{label} [{current}]: ").strip()
    return raw if raw else current


def maybe_prompt_user(config: ParamsConfig, interactive: bool) -> ParamsConfig:
    if not interactive:
        return config

    print("Press Enter to keep the default value.")
    return ParamsConfig(
        mesh_size=prompt_float("mesh_size (mm)", config.mesh_size),
        gravity_const=prompt_float("gravity_const (mm/s^2)", config.gravity_const),
        density=prompt_float("density (kg/mm^3)", config.density),
        E=prompt_float("E (kPa)", config.E),
        joint_spacing=prompt_float("joint_spacing (mm)", config.joint_spacing),
        t_strength=prompt_float("t_strength", config.t_strength),
        c_strength=prompt_float("c_strength", config.c_strength),
        friction_angle=prompt_float("friction_angle", config.friction_angle),
        cohesion=prompt_float("cohesion", config.cohesion),
        cohesion_res=prompt_float("cohesion_res", config.cohesion_res),
        s_factor=prompt_float("s_factor", config.s_factor),
        t_strength_b=prompt_float("t_strength_b", config.t_strength_b),
        c_strength_b=prompt_float("c_strength_b", config.c_strength_b),
        friction_angle_b=prompt_float("friction_angle_b", config.friction_angle_b),
        cohesion_b=prompt_float("cohesion_b", config.cohesion_b),
        cohesion_res_b=prompt_float("cohesion_res_b", config.cohesion_res_b),
        cycle_n=prompt_int("cycle_n", config.cycle_n),
        velocity=prompt_float("velocity", config.velocity),
        loading_group=prompt_str("loading_group", config.loading_group),
        amp=prompt_float("amp", config.amp),
        v_pressure=prompt_float("v_pressure", config.v_pressure),
    )


def render_params(config: ParamsConfig) -> str:
    values = asdict(config)
    for key, value in list(values.items()):
        if isinstance(value, float):
            values[key] = format_num(value)
    return PARAMS_TEMPLATE.format(**values)


def write_output(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Use --force to overwrite.")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    config = maybe_prompt_user(DEFAULTS, args.interactive)
    output = render_params(config)
    write_output(args.output, output, args.force)
    print(f"Generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
