"""
sst_thermal_transient.py
Section 6.3 (Fig. 6) -- dynamic electro-thermal transient during an actual
ride-through event. Couples the manufacturer Foster thermal network to each
device's own instantaneous loss, scaled by the time-varying MV-link
voltage/power trajectory already produced by sst_sim.py, rather than the
static converged-average-loss treatment in sst_losses.py.
"""
import json
import numpy as np
from sst_losses import IGBT, SIC, igbt_losses, sic_losses, converge_Tj, T_case
from sst_sim import (simulate_sst, N_cells, C_cell, V1_nom, V1_floor,
                      P_agg_rated, Pcell_rated, grid_availability)


def foster_step(dT_branches, R, tau, P_loss, dt):
    """Advance each Foster RC branch one step under instantaneous loss P_loss.
    dT_branches: array of per-branch temperature rises."""
    for i in range(len(R)):
        dT_inf = P_loss * R[i]
        dT_branches[i] += (dT_inf - dT_branches[i]) * dt / tau[i]
    return dT_branches


def run_transient(P_step_test, duration, depth, t_start=0.5, dt=1e-3, t_total=2.5):
    """Re-run the SST ride-through at the given test-step power, extract the
    per-cell MV link and CHB/DAB current trajectories, and dynamically
    integrate each device's own Foster network against them."""
    n = int(t_total / dt)
    t = np.arange(n) * dt
    V1 = np.full(n, V1_nom)

    # converged nominal (pre-event) operating point, from the static model
    Tj_chb0, Pc_chb0, Ps_chb0 = converge_Tj(
        lambda I, f, T: igbt_losses(I, f, T, hard_switched=True),
        7.873, 1000.0, sum(IGBT["foster_R"]))
    Tj_dab_p0, Pc_dp0, Ps_dp0 = converge_Tj(
        lambda I, f, T: igbt_losses(I, f, T, hard_switched=False),
        8.0, 10e3, sum(IGBT["foster_R"]))
    Tj_dab_s0, Pc_ds0, Ps_ds0 = converge_Tj(sic_losses, 16.0, 10e3, SIC["Rth_jc"])
    P_chb0 = Pc_chb0 + Ps_chb0
    P_dabp0 = Pc_dp0 + Ps_dp0
    P_dabs0 = Pc_ds0 + Ps_ds0

    dT_chb = np.zeros(len(IGBT["foster_R"]))
    dT_dabp = np.zeros(len(IGBT["foster_R"]))
    dT_dabs = 0.0

    dT_chb_trace = np.zeros(n)
    dT_dabp_trace = np.zeros(n)
    dT_dabs_trace = np.zeros(n)

    Pcell_agg_rated = N_cells * Pcell_rated
    k_throttle = 0.0005

    for k in range(1, n):
        g = grid_availability(t[k - 1], t_start, duration, depth)
        P_avail_grid = g * P_agg_rated
        if V1[k - 1] >= V1_floor:
            P_LV = P_step_test
        else:
            throttle = max(0.0, 1 - k_throttle * (V1_floor - V1[k - 1]) / V1_floor)
            P_LV = P_step_test * throttle
        P_grid_drawn = min(P_LV, P_avail_grid)
        E_agg = N_cells * 0.5 * C_cell * V1[k - 1] ** 2
        E_new = max(E_agg + (P_grid_drawn - P_LV) * dt, 1e-6)
        V1[k] = np.sqrt(2 * E_new / (N_cells * C_cell))

        # CHB loss scales with grid-side power actually flowing through it
        # (drops during a sag -- less power in, less CHB loss)
        chb_frac = P_grid_drawn / (Pcell_agg_rated) if Pcell_agg_rated > 0 else 0
        chb_frac = min(1.0, chb_frac / (P_step_test / Pcell_agg_rated) if P_step_test > 0 else 0)
        P_chb_inst = P_chb0 * max(0.0, chb_frac)

        # DAB primary/secondary loss scales with the DAB's own bridge current,
        # which RISES as the MV link droops at roughly constant delivered power
        # (P = V*I -> I ~ 1/V)
        v_ratio = V1_nom / max(V1[k - 1], 1.0)
        P_dabp_inst = P_dabp0 * v_ratio  # conduction dominant, I ~ 1/V -> loss ~ 1/V (approx)
        P_dabs_inst = P_dabs0 * v_ratio ** 2  # I^2R conduction dominant

        dT_chb = foster_step(dT_chb, IGBT["foster_R"], IGBT["foster_tau"], P_chb_inst, dt)
        dT_dabp = foster_step(dT_dabp, IGBT["foster_R"], IGBT["foster_tau"], P_dabp_inst, dt)
        dT_inf_s = P_dabs_inst * SIC["Rth_jc"]
        dT_dabs += (dT_inf_s - dT_dabs) * dt / SIC["tau_th"]

        dT_chb_trace[k] = np.sum(dT_chb) - np.sum([P_chb0 * r for r in IGBT["foster_R"]])
        dT_dabp_trace[k] = np.sum(dT_dabp) - np.sum([P_dabp0 * r for r in IGBT["foster_R"]])
        dT_dabs_trace[k] = dT_dabs - P_dabs0 * SIC["Rth_jc"]

    return t, dT_chb_trace, dT_dabp_trace, dT_dabs_trace, V1


def main():
    print("=== 60 kW test-step scenario, 500ms full interruption ===")
    t, dT_chb, dT_dabp, dT_dabs, V1 = run_transient(60e3, 0.500, 1.00)
    print(f"CHB IGBT: min dTj={dT_chb.min():.3f}C (paper: -0.42C)")
    print(f"DAB primary IGBT: max dTj={dT_dabp.max():.3f}C (paper: +0.03C)")
    print(f"DAB secondary SiC: max |dTj|={np.abs(dT_dabs).max():.4f}C (paper: <0.001C)")

    print("\n=== Rated-power (150kW) step, Thold=181.3ms interruption ===")
    t2, dT_chb2, dT_dabp2, dT_dabs2, V1_2 = run_transient(150e3, 0.1813, 1.00)
    print(f"CHB IGBT: min dTj={dT_chb2.min():.3f}C (paper: -0.91C)")
    print(f"DAB primary IGBT: max dTj={dT_dabp2.max():.3f}C (paper: +0.07C)")
    print(f"DAB secondary SiC: max |dTj|={np.abs(dT_dabs2).max():.4f}C (paper: <0.001C)")

    results = {
        "60kW_500ms": {"CHB_min_dTj": float(dT_chb.min()), "DAB_p_max_dTj": float(dT_dabp.max()),
                        "DAB_s_max_dTj": float(np.abs(dT_dabs).max())},
        "rated_Thold": {"CHB_min_dTj": float(dT_chb2.min()), "DAB_p_max_dTj": float(dT_dabp2.max()),
                          "DAB_s_max_dTj": float(np.abs(dT_dabs2).max())},
        "paper_reported": {"60kW": {"CHB": -0.42, "DAB_p": 0.03, "DAB_s": 0.001},
                            "rated": {"CHB": -0.91, "DAB_p": 0.07, "DAB_s": 0.001}},
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_thermal_transient_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
