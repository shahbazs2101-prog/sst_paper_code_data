"""
sst_chb_model.py
Section 4.1 -- Cascaded H-Bridge (CHB) MV rectifier stage, switching-resolution
verification.

3 cells/phase x 3 phases = 9 cells. Each cell: 3300 V DC link, bipolar
phase-shifted-carrier (PSC) PWM, carrier offset by 1/3 of a carrier period
between the 3 series cells in a phase stack -> 2N+1 = 7-level line-to-neutral
stack voltage.

11 kV MV feeder (line-to-line RMS) -> 6350.85 V phase RMS -> 8981.5 V peak
phase voltage. Per-cell V1=3300V, N=3 -> N*V1=9900V max stack amplitude ->
ma ~ 0.91-0.92 (paper states 0.917; small rounding differences from exactly
matching the paper's own intermediate numbers exactly is not expected).

Rated: 150 kVA aggregate, 7.873 A RMS per-phase current.
A small 2%-pu MV-side series filter inductor couples the CHB stack to the grid.

Produces sst_chb_results.json: delivered power %, current TDD, harmonic
spectrum, and confirms IEEE 519-2022 classical-band compliance margin.
"""
import json
import numpy as np

# ---- System ratings (Section 2, 4.1) ----
S_rated = 150e3          # VA, aggregate
V_LL = 11e3               # V RMS, MV feeder line-to-line
f_grid = 50.0
V_phase_rms = V_LL / np.sqrt(3)
V_phase_peak = V_phase_rms * np.sqrt(2)
I_rated_rms = S_rated / (3 * V_phase_rms)   # 7.873 A

# ---- CHB design (Section 4.1) ----
N_cells = 3
V1 = 3300.0
ma = (V_phase_peak) / (N_cells * V1)   # modulation index from the physical sizing
f_carrier = 1000.0                     # corrected operating point (Section 6.3)
Tcarrier = 1.0 / f_carrier

# ---- Filter (2% pu series MV-side inductor) ----
Zbase = V_phase_rms / I_rated_rms
XL = 0.02 * Zbase
L = XL / (2 * np.pi * f_grid)

# small series ESR on the filter inductor (typical Q~30 for an MV filter
# reactor); this also damps any open-loop DC/drift bias to a true periodic
# steady state, which a purely lossless inductor cannot do on its own.
R_esr = XL / 30.0

print(f"V_phase_peak={V_phase_peak:.1f} V, ma={ma:.4f}, Zbase={Zbase:.2f} ohm, "
      f"XL={XL:.3f} ohm, L={L*1000:.3f} mH, R_esr={R_esr:.4f} ohm, I_rated_rms={I_rated_rms:.4f} A")


def cell_output(t, phase_ref, carrier_offset):
    """
    Bipolar PSC-PWM cell output: +/-V1 depending on whether the phase's
    sinusoidal modulating reference is above or below this cell's own
    (phase-shifted) triangle carrier.
    """
    carrier = 2 * (np.abs(((t - carrier_offset) % Tcarrier) / Tcarrier - 0.5)) * 2 - 1
    return np.where(phase_ref > carrier, V1, -V1)


def simulate_phase(delta_rad, n_cycles=15, n_sub_per_carrier=200, verbose=False):
    """
    Simulate one phase's 3-cell stack, explicit-Euler current through the
    series RL filter against the grid voltage, over n_cycles of the
    50 Hz fundamental (enough for the small ESR to damp out the open-loop
    startup transient). Returns the settled last full fundamental cycle.
    """
    dt = Tcarrier / n_sub_per_carrier
    T_grid = 1.0 / f_grid
    n_steps = int(n_cycles * T_grid / dt)
    t = np.arange(n_steps) * dt

    mod_ref = ma * np.sin(2 * np.pi * f_grid * t + delta_rad)
    v_stack = np.zeros(n_steps)
    for k in range(N_cells):
        offset = k * Tcarrier / N_cells
        v_stack += cell_output(t, mod_ref, offset)

    v_grid = V_phase_peak * np.sin(2 * np.pi * f_grid * t)

    i = np.zeros(n_steps)
    for k in range(n_steps - 1):
        i[k + 1] = i[k] + dt / L * (v_stack[k] - v_grid[k] - R_esr * i[k])

    # keep only the last full fundamental cycle (settled)
    n_last = int(T_grid / dt)
    return t[-n_last:] - t[-n_last], i[-n_last:], v_stack[-n_last:], v_grid[-n_last:], dt


def delivered_power(delta_rad, **kw):
    t, i, v_stack, v_grid, dt = simulate_phase(delta_rad, **kw)
    P = np.mean(v_grid * i)
    return P, (t, i, v_stack, v_grid, dt)


def find_delta_for_target_power(P_target, lo=0.001, hi=0.30, iters=25):
    """Bisection on the power angle delta to hit the target per-phase real power."""
    def f(delta):
        P, _ = delivered_power(delta)
        return P - P_target
    flo, fhi = f(lo), f(hi)
    if flo > 0:
        return lo
    if fhi < 0:
        return hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def compute_tdd(i, dt, I_L=I_rated_rms):
    """Current TDD against the rated load current I_L (IEEE 519 convention),
    using harmonics h=2-50 (classical band). No window needed since the
    input is exactly one settled fundamental period."""
    n = len(i)
    spec = np.fft.rfft(i)
    freqs = np.fft.rfftfreq(n, d=dt)
    fundamental_bin = np.argmin(np.abs(freqs - f_grid))
    amp = np.abs(spec) * 2 / n
    I1 = amp[fundamental_bin]
    h_max = 50
    harmonic_energy = 0.0
    for h in range(2, h_max + 1):
        target_f = h * f_grid
        b = np.argmin(np.abs(freqs - target_f))
        harmonic_energy += amp[b] ** 2
    tdd = np.sqrt(harmonic_energy) / I_L * 100.0
    return tdd, I1, freqs, amp


def main():
    P_target_per_phase = S_rated / 3.0
    delta = find_delta_for_target_power(P_target_per_phase, iters=15)
    P, (t, i, v_stack, v_grid, dt) = delivered_power(delta, n_cycles=15, n_sub_per_carrier=2000)
    S_delivered_pct = (P * 3) / S_rated * 100.0
    tdd, I1, freqs, amp = compute_tdd(i, dt)
    I_rms = np.sqrt(np.mean(i ** 2))

    print(f"delta={np.degrees(delta):.3f} deg, P/phase={P/1000:.3f} kW, "
          f"aggregate delivered={S_delivered_pct:.2f}% of 150 kVA target")
    print(f"I_rms={I_rms:.3f} A (rated {I_rated_rms:.3f} A), TDD={tdd:.3f}%")

    # IEEE 519-2022 classical band check
    Isc_IL = 1667.0
    tdd_limit = 20.0  # % for Isc/IL >= 1000 (highest band)
    compliant = tdd < tdd_limit

    results = {
        "system": {"S_rated_VA": S_rated, "V_LL": V_LL, "V_phase_peak": V_phase_peak,
                   "ma": ma, "N_cells": N_cells, "V1": V1, "f_carrier_Hz": f_carrier,
                   "XL_ohm": XL, "L_H": L, "I_rated_rms": I_rated_rms},
        "operating_point": {"delta_rad": delta, "delta_deg": np.degrees(delta)},
        "results": {
            "delivered_pct_of_target": S_delivered_pct,
            "I_rms_A": I_rms,
            "TDD_pct": tdd,
            "Isc_IL_assumed": Isc_IL,
            "TDD_limit_pct": tdd_limit,
            "IEEE519_compliant": bool(compliant),
        },
        "paper_reported": {"delivered_pct": 99.1, "TDD_pct": 0.56},
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_chb_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # waveform + spectrum for plotting later (Fig. 1)
    np.savez("../results/sst_chb_waveform.npz", t=t, v_stack=v_stack, v_grid=v_grid,
             i=i, freqs=freqs, amp=amp)
    print(f"\nPaper reports: 99.1% delivered, 0.56% TDD. "
          f"This implementation: {S_delivered_pct:.2f}% delivered, {tdd:.3f}% TDD.")


if __name__ == "__main__":
    main()
