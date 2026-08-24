"""
monte_carlo.py
--------------
Monte Carlo simulation of the waste dump Factor of Safety.

Each geotechnical input is treated as a random variable with a distribution
reflecting typical field/lab variability for mine waste rock:

    cohesion (c')        ~ Normal, truncated at 0        (kPa)
    friction angle (phi') ~ Normal, truncated to (20, 45) (deg)
    unit weight (gamma)   ~ Normal, truncated at 15       (kN/m^3)
    depth (z)             ~ Uniform                       (m)   -- geometric/operational variable
    slope angle (beta)    ~ Uniform                       (deg) -- geometric/operational variable
    pore pressure ratio r_u ~ Lognormal-like (Normal trunc [0,0.5])

The simulation reports:
    - mean, std, and percentiles of FS
    - probability of failure Pf = P(FS < 1)
    - reliability index (Hasofer-Lind style, mean/std approximation)
"""

import numpy as np
import pandas as pd
from core import factor_of_safety_vectorized

RNG_SEED = 42


def default_distributions() -> dict:
    """Distribution parameters (mean, std, and hard physical bounds) for each variable."""
    return {
        "cohesion_kPa":       {"mean": 15.0, "std": 4.0, "bounds": (0.0, None)},
        "friction_angle_deg": {"mean": 35.0, "std": 3.0, "bounds": (20.0, 45.0)},
        "unit_weight_kNm3":   {"mean": 20.0, "std": 1.0, "bounds": (16.0, 24.0)},
        "depth_m":            {"mean": 15.0, "std": 3.0, "bounds": (5.0, 30.0)},
        "slope_angle_deg":    {"mean": 28.0, "std": 2.0, "bounds": (18.0, 37.0)},
        "ru":                 {"mean": 0.15, "std": 0.08, "bounds": (0.0, 0.5)},
    }


def _sample_truncated_normal(rng, mean, std, lo, hi, size):
    samples = rng.normal(mean, std, size)
    if lo is not None:
        samples = np.clip(samples, lo, None)
    if hi is not None:
        samples = np.clip(samples, None, hi)
    return samples


def run_simulation(n_trials: int = 100_000, seed: int = RNG_SEED, dists: dict = None) -> pd.DataFrame:
    """Draw n_trials samples for every input, compute FS for each, return a DataFrame."""
    rng = np.random.default_rng(seed)
    dists = dists or default_distributions()

    samples = {}
    for name, d in dists.items():
        lo, hi = d["bounds"]
        samples[name] = _sample_truncated_normal(rng, d["mean"], d["std"], lo, hi, n_trials)

    fs = factor_of_safety_vectorized(
        cohesion_kPa=samples["cohesion_kPa"],
        friction_angle_deg=samples["friction_angle_deg"],
        unit_weight_kNm3=samples["unit_weight_kNm3"],
        depth_m=samples["depth_m"],
        slope_angle_deg=samples["slope_angle_deg"],
        ru=samples["ru"],
    )

    df = pd.DataFrame(samples)
    df["FS"] = fs
    return df


def summarize(df: pd.DataFrame) -> dict:
    fs = df["FS"].values
    pf = float(np.mean(fs < 1.0))
    mean_fs = float(np.mean(fs))
    std_fs = float(np.std(fs, ddof=1))
    reliability_index = (mean_fs - 1.0) / std_fs if std_fs > 0 else np.inf

    percentiles = {p: float(np.percentile(fs, p)) for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]}

    return {
        "n_trials": len(fs),
        "mean_FS": mean_fs,
        "std_FS": std_fs,
        "min_FS": float(np.min(fs)),
        "max_FS": float(np.max(fs)),
        "probability_of_failure": pf,
        "reliability_index_beta": reliability_index,
        "percentiles": percentiles,
    }


def convergence_curve(df: pd.DataFrame, checkpoints=None) -> pd.DataFrame:
    """Running estimate of Pf as a function of number of trials, to show MC convergence."""
    fs = df["FS"].values
    n = len(fs)
    if checkpoints is None:
        checkpoints = np.unique(np.logspace(2, np.log10(n), 60).astype(int))
    running_pf = []
    for c in checkpoints:
        running_pf.append(np.mean(fs[:c] < 1.0))
    return pd.DataFrame({"n_trials": checkpoints, "running_Pf": running_pf})


if __name__ == "__main__":
    df = run_simulation(100_000)
    stats = summarize(df)
    print(f"Trials: {stats['n_trials']:,}")
    print(f"Mean FS: {stats['mean_FS']:.3f}  |  Std FS: {stats['std_FS']:.3f}")
    print(f"Probability of failure (FS<1): {stats['probability_of_failure']*100:.2f}%")
    print(f"Reliability index (beta): {stats['reliability_index_beta']:.3f}")
    print("Percentiles:", {k: round(v, 3) for k, v in stats["percentiles"].items()})
