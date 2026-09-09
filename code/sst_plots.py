"""
sst_plots.py
Regenerates the manuscript's key simulation figures from the JSON/npz
results produced by the scripts above. Run after sst_dab_model.py,
sst_chb_model.py, sst_sim.py, sst_montecarlo.py, and sst_balancing.py.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

os.makedirs("../results/figs", exist_ok=True)


def fig_dab_power_transfer():
    with open("../results/sst_dab_results.json") as f:
        d = json.load(f)
    rows = d["sweep"]
    ds = [r["d"] for r in rows]
    an = [r["analytic_kW"] for r in rows]
    sw = [r["switched_kW"] for r in rows]
    plt.figure(figsize=(6, 4))
    plt.plot(ds, an, "o-", label="Analytic")
    plt.plot(ds, sw, "x--", label="Switched-model simulation")
    plt.axvline(0.35, color="gray", linestyle=":", label="Rated d=0.35")
    plt.xlabel("Duty / phase-shift ratio, d")
    plt.ylabel("Per-cell power transfer (kW)")
    plt.title("DAB power transfer: analytic vs. switched-model simulation")
    plt.legend()
    plt.tight_layout()
    plt.savefig("../results/figs/fig3_dab_power_transfer.png", dpi=150)
    plt.close()


def fig_chb_waveform():
    d = np.load("../results/sst_chb_waveform.npz")
    t_ms = d["t"] * 1000
    plt.figure(figsize=(7, 5))
    plt.subplot(2, 1, 1)
    plt.plot(t_ms, d["v_stack"] / 1000, label="CHB stack output (7-level)")
    plt.plot(t_ms, d["v_grid"] / 1000, "--", label="Grid phase voltage")
    plt.ylabel("Voltage (kV)")
    plt.legend()
    plt.title("CHB MV-side stack waveform and current spectrum")
    plt.subplot(2, 1, 2)
    freqs, amp = d["freqs"], d["amp"]
    mask = freqs < 3000
    plt.semilogy(freqs[mask], amp[mask] / amp.max() * 100 + 1e-6, ".")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("% of rated current")
    plt.tight_layout()
    plt.savefig("../results/figs/fig1_chb_waveform.png", dpi=150)
    plt.close()


def fig_ride_through():
    with open("../results/sst_sag_results.json") as f:
        rows = json.load(f)
    labels = [r["scenario"].split(",")[0] for r in rows]
    conv_dev = [min(r["conventional_unbuffered"]["max_dev_pct"], 25) for r in rows]
    matched_dev = [min(r["conventional_matched"]["max_dev_pct"], 25) for r in rows]
    sst_dev = [r["sst"]["max_dev_pct"] for r in rows]
    x = np.arange(len(labels))
    w = 0.25
    plt.figure(figsize=(8, 5))
    plt.bar(x - w, conv_dev, w, label="Conventional (unbuffered)")
    plt.bar(x, matched_dev, w, label="Conventional (matched)")
    plt.bar(x + w, sst_dev, w, label="SST")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Max LV-bus deviation (%, capped at 25 for display)")
    plt.title("MV-side disturbance-rejection comparison (Table 2)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("../results/figs/fig4_ride_through.png", dpi=150)
    plt.close()


def fig_montecarlo():
    with open("../results/sst_montecarlo_results.json") as f:
        d = json.load(f)
    labels = ["Conventional", "SST"]
    vals = [d["conv_trip_rate_pct"], d["sst_trip_rate_pct"]]
    paper_vals = [d["paper_reported"]["conv_trip_rate_pct"], d["paper_reported"]["sst_trip_rate_pct"]]
    x = np.arange(2)
    w = 0.35
    plt.figure(figsize=(5, 4))
    plt.bar(x - w / 2, vals, w, label="This implementation")
    plt.bar(x + w / 2, paper_vals, w, label="Paper")
    plt.xticks(x, labels)
    plt.ylabel("Trip rate (%)")
    plt.title("Monte Carlo sweep: trip rate comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig("../results/figs/fig9_montecarlo.png", dpi=150)
    plt.close()


def fig_balancing():
    with open("../results/sst_balancing_results.json") as f:
        d = json.load(f)
    print("Balancing summary (see console output of sst_balancing.py for full trace):")
    print(json.dumps(d["closed_loop"], indent=2))


def main():
    fig_dab_power_transfer()
    print("Wrote fig3_dab_power_transfer.png")
    if os.path.exists("../results/sst_chb_waveform.npz"):
        fig_chb_waveform()
        print("Wrote fig1_chb_waveform.png")
    if os.path.exists("../results/sst_sag_results.json"):
        fig_ride_through()
        print("Wrote fig4_ride_through.png")
    if os.path.exists("../results/sst_montecarlo_results.json"):
        fig_montecarlo()
        print("Wrote fig9_montecarlo.png")
    if os.path.exists("../results/sst_balancing_results.json"):
        fig_balancing()


if __name__ == "__main__":
    main()
