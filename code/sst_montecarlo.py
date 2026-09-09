"""
sst_montecarlo.py
Section 6.5 -- 500-trial randomized Monte Carlo disturbance sweep.

Each trial draws: sag depth ~ U(0.10, 1.00), sag duration ~ U(0.05, 1.50)s,
and (70% chance each, independently) a coincident PV cloud-transient
(magnitude bootstrap-resampled from sst_real_profiles.py's event catalog,
scaled to a 40kW ceiling, ramping over U(0.05,0.30)s) and a coincident load
pickup (U(0,25)kW, arriving 0-200ms after the sag starts). Both interfaces
are run against the identical drawn disturbance (paired trial).
"""
import json
import numpy as np
from sst_sim import (V_LV_nom, trip_band, P_agg_rated, P_step, C_conv,
                      N_cells, C_cell, V1_nom, V1_floor, grid_availability)

RNG_SEED = 7


def run_trial(depth, duration, pv_frac, pv_ramp, pv_offset, load_kw, load_offset,
              dt, t_start=0.2, t_margin=0.3):
    t_total = t_start + duration + t_margin
    n = int(t_total / dt)
    t = np.arange(n) * dt

    def demand(tt):
        d = P_step
        if pv_frac is not None:
            pv_start = t_start + pv_offset
            if tt >= pv_start:
                ramp = min(1.0, (tt - pv_start) / pv_ramp)
                d += pv_frac * 40e3 * ramp
        if load_kw is not None:
            load_start = t_start + load_offset
            if tt >= load_start:
                d += load_kw * 1e3
        return d

    # ---- conventional (unbuffered) ----
    V = V_LV_nom
    tripped_c = False
    t_trip_c = None
    dev_c_max = 0.0
    for k in range(1, n):
        if tripped_c:
            break
        tt = t[k - 1]
        g = grid_availability(tt, t_start, duration, depth)
        P_avail = g * P_agg_rated
        P_dem = demand(tt)
        shortfall = max(0.0, P_dem - P_avail)
        dVdt = -shortfall / (C_conv * V) if shortfall > 0 else 0.0
        V = V + dVdt * dt
        dev = abs(V - V_LV_nom) / V_LV_nom
        dev_c_max = max(dev_c_max, dev)
        if dev > trip_band:
            tripped_c = True
            t_trip_c = t[k]

    # ---- SST ----
    V1 = V1_nom
    V_LV_s = V_LV_nom
    tripped_s = False
    t_trip_s = None
    dev_s_max = 0.0
    k_throttle = 0.0005
    for k in range(1, n):
        if tripped_s:
            break
        tt = t[k - 1]
        g = grid_availability(tt, t_start, duration, depth)
        P_avail_grid = g * P_agg_rated
        P_dem = demand(tt)
        if V1 >= V1_floor:
            P_LV = P_dem
        else:
            throttle = max(0.0, 1 - k_throttle * (V1_floor - V1) / V1_floor)
            P_LV = P_dem * throttle
        P_grid_drawn = min(P_LV, P_avail_grid)
        E = N_cells * 0.5 * C_cell * V1 ** 2
        E_new = max(E + (P_grid_drawn - P_LV) * dt, 1e-6)
        V1 = np.sqrt(2 * E_new / (N_cells * C_cell))
        shortfall = P_dem - P_LV
        dVdt = -shortfall / (C_conv * V_LV_s) if shortfall > 0 else 0.0
        V_LV_s = V_LV_s + dVdt * dt
        dev = abs(V_LV_s - V_LV_nom) / V_LV_nom
        dev_s_max = max(dev_s_max, dev)
        if dev > trip_band:
            tripped_s = True
            t_trip_s = t[k]

    return {
        "conv_tripped": tripped_c, "conv_max_dev_pct": dev_c_max * 100.0,
        "sst_tripped": tripped_s, "sst_max_dev_pct": dev_s_max * 100.0,
    }


def main():
    rng = np.random.default_rng(RNG_SEED)
    n_trials = 500

    # pull the (synthetic-stand-in) event catalog from sst_real_profiles.py
    import sst_real_profiles as srp
    events = srp.main()  # regenerates + returns event fraction list
    if len(events) == 0:
        events = [0.3, 0.4, 0.5]

    rows = []
    for i in range(n_trials):
        depth = rng.uniform(0.10, 1.00)
        duration = rng.uniform(0.05, 1.50)
        has_pv = rng.random() < 0.70
        has_load = rng.random() < 0.70
        pv_frac = float(rng.choice(events)) if has_pv else None
        pv_ramp = rng.uniform(0.05, 0.30) if has_pv else None
        pv_offset = rng.uniform(0, min(0.2, duration)) if has_pv else None
        load_kw = rng.uniform(0, 25) if has_load else None
        load_offset = rng.uniform(0, 0.2) if has_load else None

        # coarser dt for the shorter trials, resolving ms-scale trips
        dt = 5e-5 if duration < 0.3 else 1.5e-4

        r = run_trial(depth, duration, pv_frac, pv_ramp, pv_offset, load_kw,
                      load_offset, dt)
        r.update({"depth": depth, "duration": duration})
        rows.append(r)
        if (i + 1) % 50 == 0:
            print(f"{i+1}/{n_trials} trials done")

    conv_trip = sum(r["conv_tripped"] for r in rows)
    sst_trip = sum(r["sst_tripped"] for r in rows)
    both_trip = sum(r["conv_tripped"] and r["sst_tripped"] for r in rows)
    conv_only = sum(r["conv_tripped"] and not r["sst_tripped"] for r in rows)
    sst_only = sum(r["sst_tripped"] and not r["conv_tripped"] for r in rows)

    sst_untripped_devs = [r["sst_max_dev_pct"] for r in rows if not r["sst_tripped"]]
    sst_untripped_devs.sort()

    def pct(p):
        if not sst_untripped_devs:
            return float("nan")
        idx = min(len(sst_untripped_devs) - 1, int(p / 100.0 * len(sst_untripped_devs)))
        return sst_untripped_devs[idx]

    print(f"\nConventional trip rate: {conv_trip}/{n_trials} = {conv_trip/n_trials*100:.1f}% "
          f"(paper: 57.8%)")
    print(f"SST trip rate: {sst_trip}/{n_trials} = {sst_trip/n_trials*100:.1f}% (paper: 1.2%)")
    print(f"Conventional-trips-only (discordant): {conv_only} (paper: 283, 56.6%)")
    print(f"SST-trips-only (discordant, wrong direction): {sst_only} (paper: 0)")
    print(f"Both trip: {both_trip} (paper: 6, 1.2%)")
    print(f"SST untripped-trial deviation: median={pct(50):.3f}% "
          f"90th={pct(90):.3f}% 99th={pct(99):.3f}% max={max(sst_untripped_devs):.3f}% "
          f"(paper: 0.45% / 1.25% / 1.44% / 1.53%)")

    results = {
        "n_trials": n_trials,
        "conv_trip_rate_pct": conv_trip / n_trials * 100,
        "sst_trip_rate_pct": sst_trip / n_trials * 100,
        "conv_only_discordant": conv_only,
        "sst_only_discordant": sst_only,
        "both_trip": both_trip,
        "sst_untripped_median_pct": pct(50),
        "sst_untripped_90pct_pct": pct(90),
        "sst_untripped_99pct_pct": pct(99),
        "sst_untripped_max_pct": max(sst_untripped_devs) if sst_untripped_devs else None,
        "paper_reported": {
            "conv_trip_rate_pct": 57.8, "sst_trip_rate_pct": 1.2,
            "conv_only_discordant": 283, "both_trip": 6,
            "median_pct": 0.45, "p90_pct": 1.25, "p99_pct": 1.44, "max_pct": 1.53,
        },
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_montecarlo_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
