"""
sst_dab_model.py
Section 4.2 -- DAB isolation stage switching-resolution verification.

Single-phase-shift (SPS) DAB cell:
  n = 4 (3300V -> 800V nominal, referred mismatch handled by phase-shift margin)
  Lk = 7.207 mH sized so rated power (16.667 kW) occurs at d = 0.35
  fs = 10 kHz

Produces sst_dab_results.json:
  - analytic vs switched-model power transfer across d = 0.10-0.50
  - max relative error (paper reports 0.08%)
  - ZVS confirmation across d >= 0.02
"""
import json
import numpy as np

# ---- Design parameters (Section 4.2) ----
n = 4.0
V1 = 3300.0        # V, per-cell MV DC link
V2 = 800.0         # V, LV terminal
fs = 10e3          # Hz
Lk = 7.207e-3       # H
Pcell_rated = 16667.0  # W (16.667 kW)

Ts = 1.0 / fs


def analytic_power(d):
    """SPS analytic power-transfer formula."""
    return n * V1 * V2 * d * (1 - d) / (2 * fs * Lk)


def steady_state_iL0(d, V2p):
    """
    Closed-form periodic steady-state inductor current at t=0 (start of the
    primary bridge's positive half-cycle), derived from half-wave symmetry
    iL(t+Ts/2) = -iL(t) applied to the piecewise-constant v_L(t) = v1(t)-v2'(t).

    Convention (matches the paper's P = n*V1*V2*d(1-d)/(2*fs*Lk) formula,
    verified against exact segment-wise integration): d in [0, 0.5] is the
    secondary bridge's phase shift as a fraction of a HALF switching period,
    i.e. shift = d*(Ts/2), not a fraction of the full period.
        iL(0) = -(Ts/(2*Lk)) * [0.5*(V1-V2p) + 2*V2p*(d/2)]
    """
    dfrac = d / 2.0  # fraction of full period Ts
    return -(Ts / (2 * Lk)) * (0.5 * (V1 - V2p) + 2 * V2p * dfrac)


def switched_model_power(d, n_sub=4000):
    """
    Exact piecewise-linear time-domain simulation of one periodic steady-state
    cycle of the leakage-inductor current under the actual SPS square-wave
    bridge voltages, starting from the closed-form steady-state initial
    condition (no transient settling needed since the IC is exact).

    Returns (avg_power, zvs_ok).
    """
    V2p = n * V2  # secondary bridge voltage referred to primary
    shift = d * Ts / 2.0  # secondary phase shift = d * half-period
    iL0 = steady_state_iL0(d, V2p)

    t = np.linspace(0, Ts, n_sub, endpoint=False)
    dt = t[1] - t[0]

    def v1_wave(tt):
        phase = (tt % Ts) / Ts
        return np.where(phase < 0.5, V1, -V1)

    def v2_wave(tt):
        shifted = (tt - shift) % Ts
        phase = shifted / Ts
        return np.where(phase < 0.5, V2p, -V2p)

    v1 = v1_wave(t)
    v2r = v2_wave(t)
    v_L = v1 - v2r

    iL = iL0 + np.cumsum(v_L) * dt / Lk
    # shift so iL[0] == iL0 exactly (cumsum starts the integral at index 0
    # already applied for dt, so correct by subtracting the first increment)
    iL = iL0 + np.concatenate(([0.0], np.cumsum(v_L)[:-1])) * dt / Lk

    p_inst = v1 * iL
    avg_power = np.trapezoid(np.append(p_inst, p_inst[0]), dx=dt) / Ts

    # ZVS check: at each bridge's own switching instant, that bridge's current
    # must already be flowing in the direction the *next* voltage level will
    # drive it (so the antiparallel diode conducts first -> zero-voltage turn-on).
    # Primary switches at t=0 (going -V1->+V1: need iL(0-)<0, i.e. iL just
    # before wrap = iL(Ts-) < 0) and at t=Ts/2 (+V1->-V1: need iL(Ts/2-)>0).
    idx_half = np.searchsorted(t, Ts / 2)
    zvs_primary = (iL[-1] < 0) and (iL[idx_half - 1] > 0)

    idx_d = np.searchsorted(t, shift % Ts)
    idx_d_half = np.searchsorted(t, (shift + Ts / 2) % Ts)
    # secondary bridge current is opposite-referenced to primary: ZVS at the
    # -V2'->+V2' transition requires iL(shift-) > 0 (secondary's own
    # antiparallel diode conducts first), and iL < 0 at the +V2'->-V2' one.
    zvs_secondary = (iL[max(idx_d - 1, 0)] > 0) and (iL[max(idx_d_half - 1, 0)] < 0)

    return avg_power, bool(zvs_primary and zvs_secondary)


def main():
    d_values = np.linspace(0.10, 0.50, 17)
    rows = []
    max_rel_err = 0.0
    zvs_all_ok = True
    for d in d_values:
        p_an = analytic_power(d)
        p_sw, zvs_ok = switched_model_power(d)
        rel_err = abs(p_sw - p_an) / p_an * 100.0
        max_rel_err = max(max_rel_err, rel_err)
        zvs_all_ok = zvs_all_ok and zvs_ok
        rows.append({
            "d": float(d),
            "analytic_kW": p_an / 1000.0,
            "switched_kW": p_sw / 1000.0,
            "rel_err_pct": rel_err,
            "zvs_ok": zvs_ok,
        })
        print(f"d={d:.2f}  analytic={p_an/1000:.3f} kW  switched={p_sw/1000:.3f} kW  "
              f"err={rel_err:.3f}%  ZVS={zvs_ok}")

    # ZVS range sweep d >= 0.02
    zvs_range = []
    for d in np.arange(0.02, 0.51, 0.02):
        _, ok = switched_model_power(d)
        zvs_range.append(bool(ok))
    zvs_full_range_ok = all(zvs_range)

    results = {
        "design_params": {"n": n, "V1": V1, "V2": V2, "fs_Hz": fs, "Lk_H": Lk,
                           "Pcell_rated_W": Pcell_rated, "d_rated": 0.35},
        "sweep": rows,
        "max_rel_err_pct": max_rel_err,
        "zvs_full_range_ge_0.02_ok": zvs_full_range_ok,
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_dab_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nMax relative error across sweep: {max_rel_err:.3f}%  (paper reports 0.08%)")
    print(f"ZVS holds across d>=0.02: {zvs_full_range_ok}")


if __name__ == "__main__":
    main()
