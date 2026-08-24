"""
make_plots.py
-------------
Generates all figures used in the report / Excel workbook:
  1. sensitivity_lines.png   - FS vs each parameter (OAT sweep), small multiples
  2. tornado.png             - tornado diagram of parameter influence on FS
  3. mc_histogram.png        - Monte Carlo FS distribution with Pf shaded
  4. mc_convergence.png      - running estimate of Pf vs number of trials
  5. slope_schematic.png     - simple labeled schematic of the infinite-slope model
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from core import BASELINE, factor_of_safety
from sensitivity import run_all_sweeps, tornado_data, PARAM_LABELS
from monte_carlo import run_simulation, summarize, convergence_curve
from optimization import sweep_slope_angle, recommended_angles, TARGET_PF

OUT = "../figures"

plt.rcParams.update({
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.facecolor": "white",
})


def plot_sensitivity_lines():
    sweeps = run_all_sweeps()
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    axes = axes.flatten()
    for ax, (name, df) in zip(axes, sweeps.items()):
        ax.plot(df[name], df["FS"], color="#2b6cb0", linewidth=2)
        ax.axhline(1.0, color="crimson", linestyle="--", linewidth=1, label="FS = 1.0 (failure)")
        baseline_val = getattr(BASELINE, name)
        ax.axvline(baseline_val, color="gray", linestyle=":", linewidth=1)
        ax.set_xlabel(PARAM_LABELS[name])
        ax.set_ylabel("Factor of Safety")
        ax.set_title(PARAM_LABELS[name], fontsize=10)
    axes[0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Sensitivity of Factor of Safety to Individual Parameters\n(all other parameters held at baseline)",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(f"{OUT}/sensitivity_lines.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_tornado():
    df = tornado_data()
    base_fs = df["baseline_FS"].iloc[0]
    fig, ax = plt.subplots(figsize=(9, 5.5))

    y_pos = np.arange(len(df))
    left = np.minimum(df["FS_at_low"], df["FS_at_high"])
    width = np.abs(df["FS_at_high"] - df["FS_at_low"])

    colors = ["#c53030" if lo > hi else "#2b6cb0" for lo, hi in zip(df["FS_at_low"], df["FS_at_high"])]
    ax.barh(y_pos, width, left=left, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)

    for i, (lo, hi) in enumerate(zip(df["FS_at_low"], df["FS_at_high"])):
        ax.text(lo - 0.02, i, f"{lo:.2f}", va="center", ha="right", fontsize=8)
        ax.text(hi + 0.02, i, f"{hi:.2f}", va="center", ha="left", fontsize=8)

    ax.axvline(base_fs, color="black", linewidth=1.5, label=f"Baseline FS = {base_fs:.2f}")
    ax.axvline(1.0, color="crimson", linestyle="--", linewidth=1.2, label="FS = 1.0 (failure)")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["parameter"])
    ax.set_xlabel("Factor of Safety")
    ax.set_title("Tornado Diagram - Parameter Influence on Factor of Safety\n(bars = FS range across each parameter's realistic operating range)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/tornado.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_mc_histogram(df_mc):
    stats = summarize(df_mc)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fs = df_mc["FS"].values
    counts, bins, patches_ = ax.hist(fs, bins=120, color="#2b6cb0", alpha=0.75, edgecolor="none")

    for i, b in enumerate(bins[:-1]):
        if b < 1.0:
            patches_[i].set_facecolor("#c53030")

    ax.axvline(1.0, color="black", linestyle="--", linewidth=1.5, label="FS = 1.0 (failure)")
    ax.axvline(stats["mean_FS"], color="darkgreen", linewidth=1.5, label=f"Mean FS = {stats['mean_FS']:.2f}")
    ax.set_xlabel("Factor of Safety")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Monte Carlo Simulation of Factor of Safety (n = {stats['n_trials']:,})\n"
                 f"Probability of Failure P(FS<1) = {stats['probability_of_failure']*100:.1f}%   |   "
                 f"Reliability Index \u03b2 = {stats['reliability_index_beta']:.2f}")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/mc_histogram.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_mc_convergence(df_mc):
    conv = convergence_curve(df_mc)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(conv["n_trials"], conv["running_Pf"] * 100, color="#2b6cb0", linewidth=1.8)
    final_pf = conv["running_Pf"].iloc[-1] * 100
    ax.axhline(final_pf, color="crimson", linestyle="--", linewidth=1, label=f"Converged Pf = {final_pf:.1f}%")
    ax.set_xscale("log")
    ax.set_xlabel("Number of Monte Carlo trials (log scale)")
    ax.set_ylabel("Running estimate of Pf (%)")
    ax.set_title("Monte Carlo Convergence of Probability of Failure")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/mc_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_slope_schematic():
    """Simple labeled schematic of the infinite-slope failure model."""
    fig, ax = plt.subplots(figsize=(8, 5))
    beta_deg = BASELINE.slope_angle_deg
    beta = np.radians(beta_deg)

    x0, x1 = 0, 10
    y0 = 0
    y1 = y0 + (x1 - x0) * np.tan(beta)

    # Slope face
    ax.plot([x0, x1], [y0 + 3, y1 + 3], color="saddlebrown", linewidth=3)
    # Ground behind crest / toe extension for context
    ax.plot([x1, x1 + 2], [y1 + 3, y1 + 3], color="saddlebrown", linewidth=3)
    ax.plot([x0 - 2, x0], [y0 + 3, y0 + 3], color="saddlebrown", linewidth=3)

    # Fill body (waste dump)
    poly = patches.Polygon(
        [(x0 - 2, 0), (x0 - 2, y0 + 3), (x1, y1 + 3), (x1 + 2, y1 + 3), (x1 + 2, 0)],
        closed=True, facecolor="#d9c7a3", edgecolor="none", zorder=0,
    )
    ax.add_patch(poly)

    # Failure plane parallel to slope face, at depth z
    z_scale = 1.4  # visual scaling only
    ax.plot([x0 - 2, x1 + 2], [0 + 3 - z_scale, y1 + 3 - z_scale * np.cos(beta)],
            color="crimson", linewidth=2, linestyle="--")
    ax.annotate("Potential failure plane\n(parallel to slope face, depth z)",
                xy=((x0 + x1) / 2, (y0 + y1) / 2 + 3 - z_scale * 1.1),
                xytext=(3.5, -1.8), color="crimson", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="crimson"))

    # Slope angle annotation
    ax.annotate("", xy=(x0 + 2, y0 + 3 + 2 * np.tan(beta)), xytext=(x0 + 2, y0 + 3),
                arrowprops=dict(arrowstyle="-", color="black", linewidth=0.8))
    ax.text(x0 + 2.3, y0 + 4.9, f"\u03b2 = {beta_deg:.0f}\u00b0", fontsize=10)

    ax.annotate("Slope face (\u03b2)", xy=((x0 + x1) / 2, (y0 + y1) / 2 + 3), xytext=(5, 7.3),
                fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.text(x0 - 1.8, 0.3, "Foundation", fontsize=9, style="italic", color="dimgray")
    ax.text(2.0, 2.0, "Waste rock dump\n(c\u2019, \u03c6\u2019, \u03b3)", fontsize=9, ha="center")

    ax.set_xlim(x0 - 3, x1 + 3)
    ax.set_ylim(-1, y1 + 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Infinite-Slope Model Schematic - Mine Waste Rock Dump", fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{OUT}/slope_schematic.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_risk_optimization(df_sweep):
    rec = recommended_angles(df_sweep)
    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    ax1.plot(df_sweep["slope_angle_deg"], df_sweep["probability_of_failure"] * 100,
             color="#2b6cb0", linewidth=2, marker="o", markersize=3, label="Probability of failure, Pf")
    ax1.set_xlabel("Overall slope (face) angle, \u03b2 (\u00b0)")
    ax1.set_ylabel("Probability of failure, Pf (%)")
    ax1.set_title("Risk-Based Optimization of Dump Slope Angle\n(Monte Carlo Pf vs. design slope angle)")

    colors = ["#38a169", "#d69e2e", "#dd6b20", "#c53030"]
    for (_, row), c in zip(rec.iterrows(), colors):
        if row["recommended_slope_angle_deg"] is not None:
            ax1.axvline(row["recommended_slope_angle_deg"], color=c, linestyle=":", linewidth=1.3,
                        label=f"Pf \u2264 {row['target_Pf']*100:.0f}% \u2192 \u03b2 \u2264 {row['recommended_slope_angle_deg']:.0f}\u00b0")

    ax1.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/risk_optimization.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)

    print("Baseline FS:", round(factor_of_safety(BASELINE), 3))

    plot_slope_schematic()
    print("Saved slope_schematic.png")

    plot_sensitivity_lines()
    print("Saved sensitivity_lines.png")

    plot_tornado()
    print("Saved tornado.png")

    df_mc = run_simulation(100_000)
    df_mc.to_parquet(f"{OUT}/mc_results.parquet") if False else None  # skip; kept lightweight

    plot_mc_histogram(df_mc)
    print("Saved mc_histogram.png")

    plot_mc_convergence(df_mc)
    print("Saved mc_convergence.png")

    df_sweep = sweep_slope_angle()
    plot_risk_optimization(df_sweep)
    print("Saved risk_optimization.png")
