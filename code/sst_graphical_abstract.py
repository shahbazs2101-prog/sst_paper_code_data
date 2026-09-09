"""
sst_graphical_abstract.py
Regenerates the manuscript's graphical abstract: a compact visual summary
of the three-stage SST vs conventional interface, the efficiency trade-off,
and the ride-through/Monte Carlo headline numbers.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os


def main():
    with open("../results/sst_losses_results.json") as f:
        losses = json.load(f)
    with open("../results/sst_montecarlo_results.json") as f:
        mc = json.load(f)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # Panel 1: efficiency
    ax = axes[0]
    labels = ["Conventional", "SST"]
    vals = [losses["final_operating_point"]["conventional_eff_pct"],
            losses["final_operating_point"]["full_SST_eff_pct"]]
    ax.bar(labels, vals, color=["#888888", "#2b6cb0"])
    ax.set_ylabel("Efficiency (%)")
    ax.set_ylim(90, 100)
    ax.set_title("Efficiency trade-off")

    # Panel 2: ride-through trip rate
    ax = axes[1]
    vals2 = [mc["conv_trip_rate_pct"], mc["sst_trip_rate_pct"]]
    ax.bar(labels, vals2, color=["#888888", "#2b6cb0"])
    ax.set_ylabel("Monte Carlo trip rate (%)")
    ax.set_title("Disturbance resilience\n(500 randomized trials)")

    # Panel 3: architecture schematic (simple boxes)
    ax = axes[2]
    ax.axis("off")
    ax.set_title("Three-stage SST")
    boxes = [("MV\nCHB", 0.05), ("DAB\n(isolation)", 0.4), ("LV\ninverter", 0.75)]
    for label, x in boxes:
        ax.add_patch(plt.Rectangle((x, 0.35), 0.2, 0.3, fill=True,
                                     color="#2b6cb0", alpha=0.7))
        ax.text(x + 0.1, 0.5, label, ha="center", va="center", color="white", fontsize=9)
    ax.annotate("", xy=(0.4, 0.5), xytext=(0.25, 0.5),
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("", xy=(0.75, 0.5), xytext=(0.6, 0.5),
                arrowprops=dict(arrowstyle="->"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    plt.suptitle("SST vs. Conventional Interface for a PV-BESS Microgrid", fontsize=13)
    plt.tight_layout()
    os.makedirs("../results/figs", exist_ok=True)
    plt.savefig("../results/figs/graphical_abstract.png", dpi=150)
    plt.close()
    print("Wrote graphical_abstract.png")


if __name__ == "__main__":
    main()
