"""
sensitivity.py
--------------
One-at-a-time (OAT) sensitivity analysis of the waste dump Factor of Safety.

Each geotechnical/geometric parameter is varied individually over a realistic
+/- range around the baseline while all other parameters are held fixed.
This identifies which parameters the dump's stability is most sensitive to,
and produces the data behind a tornado diagram.
"""

import numpy as np
import pandas as pd
from core import SlopeParameters, factor_of_safety, BASELINE

# Realistic operating ranges for each parameter (min, max), independent of the
# distributions used later for Monte Carlo -- these are the OAT sweep bounds.
PARAM_RANGES = {
    "cohesion_kPa":       (5.0, 25.0),
    "friction_angle_deg": (28.0, 40.0),
    "unit_weight_kNm3":   (18.0, 22.0),
    "depth_m":            (8.0, 25.0),
    "slope_angle_deg":    (22.0, 34.0),
    "ru":                 (0.0, 0.35),
}

PARAM_LABELS = {
    "cohesion_kPa":       "Cohesion, c' (kPa)",
    "friction_angle_deg": "Friction angle, \u03c6' (\u00b0)",
    "unit_weight_kNm3":   "Unit weight, \u03b3 (kN/m\u00b3)",
    "depth_m":            "Depth to slip surface, z (m)",
    "slope_angle_deg":    "Slope angle, \u03b2 (\u00b0)",
    "ru":                 "Pore pressure ratio, r_u",
}

N_STEPS = 25


def sweep_parameter(param_name: str, baseline: SlopeParameters = BASELINE) -> pd.DataFrame:
    """Vary a single parameter across its realistic range; hold all others at baseline."""
    lo, hi = PARAM_RANGES[param_name]
    values = np.linspace(lo, hi, N_STEPS)
    fs_values = []
    for v in values:
        p = baseline.clone(**{param_name: v})
        fs_values.append(factor_of_safety(p))
    return pd.DataFrame({param_name: values, "FS": fs_values})


def run_all_sweeps(baseline: SlopeParameters = BASELINE) -> dict:
    """Return {param_name: DataFrame(value, FS)} for every parameter."""
    return {name: sweep_parameter(name, baseline) for name in PARAM_RANGES}


def tornado_data(baseline: SlopeParameters = BASELINE) -> pd.DataFrame:
    """
    For each parameter, compute FS at the low and high end of its realistic range
    (others held at baseline) -- the standard input to a tornado diagram.
    """
    base_fs = factor_of_safety(baseline)
    rows = []
    for name, (lo, hi) in PARAM_RANGES.items():
        fs_lo = factor_of_safety(baseline.clone(**{name: lo}))
        fs_hi = factor_of_safety(baseline.clone(**{name: hi}))
        swing = abs(fs_hi - fs_lo)
        rows.append({
            "parameter": PARAM_LABELS[name],
            "param_key": name,
            "low_value": lo,
            "high_value": hi,
            "FS_at_low": fs_lo,
            "FS_at_high": fs_hi,
            "baseline_FS": base_fs,
            "swing": swing,
        })
    df = pd.DataFrame(rows).sort_values("swing", ascending=True).reset_index(drop=True)
    return df


if __name__ == "__main__":
    print("Baseline FS:", round(factor_of_safety(BASELINE), 3))
    print("\nTornado data (sorted by influence):")
    print(tornado_data().to_string(index=False))
