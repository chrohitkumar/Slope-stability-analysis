"""
optimization.py
----------------
Risk-based optimization of the dump slope angle.

Rather than designing to a single deterministic FS target, this sweeps the
overall slope (face) angle, re-runs the full Monte Carlo simulation at each
angle (holding all other input distributions fixed), and reports probability
of failure Pf(beta). This lets the dump be designed to a *risk* target
(e.g., Pf <= 5%) instead of only a deterministic FS target, and quantifies
the trade-off between steeper slopes (less waste footprint / haul distance)
and higher probability of instability.
"""

import numpy as np
import pandas as pd
from monte_carlo import default_distributions, run_simulation, summarize

BETA_RANGE = np.arange(20.0, 35.01, 1.0)   # slope angles to evaluate (deg)
N_TRIALS_PER_ANGLE = 20_000                 # lighter than the headline run, still stable
TARGET_PF = [0.20, 0.10, 0.05, 0.01]        # common risk targets (20%, 10%, 5%, 1%)


def sweep_slope_angle(n_trials: int = N_TRIALS_PER_ANGLE, seed_base: int = 1000) -> pd.DataFrame:
    """Run a full MC simulation at each candidate slope angle; angle held fixed (not random) so
    the sweep isolates the design lever from the other, uncontrollable geotechnical uncertainty."""
    rows = []
    for i, beta in enumerate(BETA_RANGE):
        dists = default_distributions()
        # Slope angle fixed at this candidate value (deterministic design lever),
        # so replace its distribution with a near-zero-variance one at 'beta'.
        dists["slope_angle_deg"] = {"mean": beta, "std": 1e-6, "bounds": (beta - 1e-3, beta + 1e-3)}
        df = run_simulation(n_trials=n_trials, seed=seed_base + i, dists=dists)
        stats = summarize(df)
        rows.append({
            "slope_angle_deg": beta,
            "mean_FS": stats["mean_FS"],
            "std_FS": stats["std_FS"],
            "probability_of_failure": stats["probability_of_failure"],
            "reliability_index_beta": stats["reliability_index_beta"],
        })
    return pd.DataFrame(rows)


def recommended_angles(df: pd.DataFrame, targets=TARGET_PF) -> pd.DataFrame:
    """For each target Pf, find the steepest evaluated angle whose Pf is <= target."""
    rows = []
    for t in targets:
        feasible = df[df["probability_of_failure"] <= t]
        if feasible.empty:
            rows.append({"target_Pf": t, "recommended_slope_angle_deg": None, "achieved_Pf": None})
        else:
            best = feasible.loc[feasible["slope_angle_deg"].idxmax()]
            rows.append({
                "target_Pf": t,
                "recommended_slope_angle_deg": best["slope_angle_deg"],
                "achieved_Pf": best["probability_of_failure"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = sweep_slope_angle()
    print(df.to_string(index=False))
    print("\nRecommended angles for common risk targets:")
    print(recommended_angles(df).to_string(index=False))
