"""
core.py
-------
Deterministic Factor-of-Safety (FS) model for an open-pit mine waste rock dump.

Model: infinite-slope method with seepage parallel to the slope face and a
pore-water pressure ratio r_u (Bishop & Morgenstern, 1960), which is the
standard first-pass tool for planar/near-surface failures in engineered
waste dumps (as opposed to deep-seated rotational failures, which need a
circular/Bishop's Simplified slice analysis).

    FS = [c' + (gamma * z * cos^2(beta) - r_u * gamma * z) * tan(phi')]
         ---------------------------------------------------------------
                        gamma * z * sin(beta) * cos(beta)

where
    c'     : effective cohesion of dump material          (kPa)
    phi'   : effective friction angle of dump material     (degrees)
    gamma  : bulk unit weight of dump material             (kN/m^3)
    z      : vertical depth to the potential failure plane (m)
    beta   : slope (face) angle                            (degrees)
    r_u    : pore-water pressure ratio, u / (gamma * z)    (0-1, dimensionless)

FS < 1.0  -> unstable
FS = 1.0  -> at limiting equilibrium
FS > 1.0  -> stable (typical regulatory targets: 1.3 static, 1.0-1.1 pseudo-static)
"""

from dataclasses import dataclass, replace
import numpy as np


@dataclass
class SlopeParameters:
    """Baseline geotechnical and geometric parameters for the waste dump."""
    cohesion_kPa: float = 15.0          # c'
    friction_angle_deg: float = 35.0    # phi'
    unit_weight_kNm3: float = 20.0      # gamma
    depth_m: float = 15.0               # z  (vertical depth to slip surface)
    slope_angle_deg: float = 28.0       # beta (overall face angle)
    ru: float = 0.15                    # pore pressure ratio

    def clone(self, **changes) -> "SlopeParameters":
        return replace(self, **changes)


def factor_of_safety(p: SlopeParameters) -> float:
    """Compute FS for a single set of parameters (infinite slope, r_u method)."""
    beta = np.radians(p.slope_angle_deg)
    phi = np.radians(p.friction_angle_deg)

    normal_stress = p.unit_weight_kNm3 * p.depth_m * np.cos(beta) ** 2
    pore_pressure = p.ru * p.unit_weight_kNm3 * p.depth_m
    driving_stress = p.unit_weight_kNm3 * p.depth_m * np.sin(beta) * np.cos(beta)

    resisting = p.cohesion_kPa + (normal_stress - pore_pressure) * np.tan(phi)

    if driving_stress <= 0:
        return np.inf
    return resisting / driving_stress


def factor_of_safety_vectorized(
    cohesion_kPa, friction_angle_deg, unit_weight_kNm3, depth_m, slope_angle_deg, ru
) -> np.ndarray:
    """Vectorized FS calculation for Monte Carlo arrays (all inputs same shape or broadcastable)."""
    beta = np.radians(slope_angle_deg)
    phi = np.radians(friction_angle_deg)

    normal_stress = unit_weight_kNm3 * depth_m * np.cos(beta) ** 2
    pore_pressure = ru * unit_weight_kNm3 * depth_m
    driving_stress = unit_weight_kNm3 * depth_m * np.sin(beta) * np.cos(beta)

    resisting = cohesion_kPa + (normal_stress - pore_pressure) * np.tan(phi)

    with np.errstate(divide="ignore", invalid="ignore"):
        fs = np.where(driving_stress > 0, resisting / driving_stress, np.inf)
    return fs


BASELINE = SlopeParameters()

if __name__ == "__main__":
    fs = factor_of_safety(BASELINE)
    print(f"Baseline Factor of Safety = {fs:.3f}")
