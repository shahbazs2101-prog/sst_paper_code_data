"""
sst_balancing.py
Section 7 -- Closed-loop active cell balancing.

9-cell fleet, each with an independently drawn power-sharing mismatch up to
+/-3% of Pcell_rated (16.667 kW). Open-loop: cells drift apart under their
own C*V*dV/dt energy balance. Closed-loop: decentralized, saturated PI
controller per cell regulates its own link voltage against the fixed
3300V setpoint (no inter-cell communication), duty-trim realized through
the DAB's own SPS power-transfer sensitivity.
"""
import json
import numpy as np

N_cells = 9
C_cell = 2000e-6
V1_nom = 3300.0
Pcell_rated = 16667.0
Pmax = 0.30 * Pcell_rated  # 5.0 kW saturation

# 2 Hz target bandwidth PI gains (verified exact match to paper: 82.9, 104.2)
f_bw = 2.0
Kp = 2 * np.pi * f_bw * C_cell * V1_nom
Ki = Kp * (2 * np.pi * f_bw) / 10.0

# DAB duty-power sensitivity at d0=0.35 (Section 4.2/7 design values)
n, V1, V2, fs, Lk = 4.0, 3300.0, 800.0, 10e3, 7.207e-3
d0 = 0.35
dP_dd = n * V1 * V2 * (1 - 2 * d0) / (2 * fs * Lk)  # ~22.0 kW per unit d


def simulate_fleet(mismatches, closed_loop, dt=1e-3, t_total=25.0):
    """mismatches: array of N_cells fractional power mismatches (e.g. 0.03
    for +3%). Returns (t, V1_trace [n_cells x n_steps])."""
    n_steps = int(t_total / dt)
    t = np.arange(n_steps) * dt
    V = np.full(N_cells, V1_nom)
    integ = np.zeros(N_cells)
    trace = np.zeros((N_cells, n_steps))
    trace[:, 0] = V

    P_mismatch = mismatches * Pcell_rated  # W, constant per-cell power imbalance

    for k in range(1, n_steps):
        if closed_loop:
            e = V - V1_nom
            p_unsat = Kp * e + Ki * integ
            p_corr = np.clip(p_unsat, -Pmax, Pmax)
            # conditional anti-windup: only integrate if not pushing further into saturation
            saturating = (p_unsat > Pmax) | (p_unsat < -Pmax)
            would_worsen = ((p_unsat > Pmax) & (e > 0)) | ((p_unsat < -Pmax) & (e < 0))
            integ = integ + np.where(would_worsen, 0.0, e) * dt
            # the correction OPPOSES the mismatch that's driving V away from setpoint
            P_net = P_mismatch - p_corr
        else:
            P_net = P_mismatch

        dVdt = P_net / (C_cell * V)
        V = V + dVdt * dt
        trace[:, k] = V

    return t, trace


def main():
    rng = np.random.default_rng(11)
    mismatches = rng.uniform(-0.03, 0.03, size=N_cells)
    print(f"Drawn per-cell mismatches (%): {np.round(mismatches * 100, 2)}")

    # --- open loop ---
    t_ol, trace_ol = simulate_fleet(mismatches, closed_loop=False, dt=2e-3, t_total=25.0)
    dev_ol = np.max(np.abs(trace_ol - V1_nom), axis=0) / V1_nom * 100.0
    idx_15 = np.argmax(dev_ol >= 15.0) if np.any(dev_ol >= 15.0) else -1
    t_to_15pct = t_ol[idx_15] if idx_15 > 0 else None
    print(f"Open loop: worst-cell reaches 15% deviation at t={t_to_15pct} "
          f"(paper: 6.4s)" if t_to_15pct else "Open loop: never reaches 15% in window")

    # --- closed loop ---
    t_cl, trace_cl = simulate_fleet(mismatches, closed_loop=True, dt=1e-3, t_total=3.0)
    dev_cl = np.max(np.abs(trace_cl - V1_nom), axis=0) / V1_nom * 100.0
    peak_dev = np.max(dev_cl)
    t_peak = t_cl[np.argmax(dev_cl)]
    peak_idx = np.argmax(dev_cl)
    below_05 = np.where(dev_cl[peak_idx:] < 0.5)[0]
    below_005 = np.where(dev_cl[peak_idx:] < 0.05)[0]
    t_settle_05 = t_cl[peak_idx + below_05[0]] if len(below_05) else None
    t_settle_005 = t_cl[peak_idx + below_005[0]] if len(below_005) else None
    final_dev = dev_cl[-1]

    print(f"\nClosed loop: peak deviation={peak_dev:.3f}% at t={t_peak:.3f}s "
          f"(paper: 0.14% @ 0.21s)")
    print(f"Final deviation (t={t_cl[-1]:.0f}s): {final_dev:.4f}% (paper: 0.00%)")
    print(f"Time to settle <0.5%: {t_settle_05} (paper: 0.00s)")
    print(f"Time to settle <0.05%: {t_settle_005} (paper: 1.05s)")

    results = {
        "mismatches_pct": (mismatches * 100).tolist(),
        "open_loop": {"t_to_15pct_s": float(t_to_15pct) if t_to_15pct else None},
        "closed_loop": {
            "peak_dev_pct": float(peak_dev), "t_peak_s": float(t_peak),
            "final_dev_pct": float(final_dev),
            "t_settle_0.5pct_s": float(t_settle_05) if t_settle_05 is not None else None,
            "t_settle_0.05pct_s": float(t_settle_005) if t_settle_005 is not None else None,
        },
        "gains": {"Kp": Kp, "Ki": Ki, "Pmax_W": Pmax, "dP_dd_per_unit_d": dP_dd},
        "paper_reported": {
            "open_loop_t_to_15pct_s": 6.4,
            "closed_loop_peak_dev_pct": 0.14, "closed_loop_t_peak_s": 0.21,
            "closed_loop_t_settle_0.05pct_s": 1.05,
        },
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_balancing_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
