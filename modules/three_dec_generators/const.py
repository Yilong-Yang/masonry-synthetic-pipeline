"""User-editable defaults for script generators."""

from dataclasses import dataclass


@dataclass
class ParamsConfig:
    # Units compatible with millimeters.
    mesh_size: float = 0.05e3
    gravity_const: float = 9.81e3

    density: float = 1805e-9

    # Bonding parameters.
    E: float = 2.746e9 * 3 * 1e-3
    joint_spacing: float = 70.5e-3 * 1e3
    t_strength: float = 0.33e6 * 0.05 * 1e-3
    c_strength: float = 5.93e6 * 1e-3
    friction_angle: float = 23.0
    cohesion: float = 0.14e6 * 1e-3
    cohesion_res: float = 0.0

    # Potential crack surface (b-brick) parameters.
    s_factor: float = 7.0
    t_strength_b: float = 2.74e6 * 1e-3
    c_strength_b: float = 5.93e6 * 1e-3
    friction_angle_b: float = 45.0
    cohesion_b: float = 2 * 2.74e6 * 1e-3
    cohesion_res_b: float = 0.0

    # Loading parameters.
    cycle_n: int = 101
    velocity: float = 0.01 * 1e3
    loading_group: str = "TOP"
    amp: float = 5.39e-3 * 1e3
    v_pressure: float = -0.5e6 * 1e-3


DEFAULTS = ParamsConfig()


@dataclass
class BlockRuntimeConfig:
    # Thickness of the base/top rigid blocks added around the geometry.
    bottom_block_thickness: float = 150.0
    top_block_thickness: float = 150.0

    # Tolerance used in range filtering in test.dat.
    z_threshold: float = 0.001


BLOCK_DEFAULTS = BlockRuntimeConfig()
