"""
sst_sim.py
Sections 5-6.2 -- MV-side disturbance-rejection methodology and the five-
scenario ride-through comparison (Table 2), average-value (switching-cycle-
averaged) model as described in the paper.

Both interfaces held at a fixed 60 kW net LV-bus power deficit; an MV-side
grid voltage sag/interruption is applied partway through at controlled
depth and duration. +/-20% LV-bus trip band on both interfaces.
"""
import json
import numpy as np

# ---- System parameters (Section 2, 5) ----
V_LV_nom = 800.0
trip_band = 0.20  # +/-20%
P_agg_rated = 150e3   # W, aggregate SST/conventional rating
P_step = 60e3          # W, fixed test-step deficit

# Conventional (unbuffered)
C_conv = 2e-3  # F, 2 mF LV bus cap (ripple-filtering size only)

# SST MV link
N_cells = 9
C_cell = 2000e-6      # F, per-cell MV DC-link capacitance
V1_nom = 3300.0
V1_floor = 0.85 * V1_nom  # 2805 V
Pcell_rated = 16667.0     # W

# Energy-buffer-matched conventional baseline (Section 6.2.1, exact value given)
C_matched = 236092e-6  # F


def grid_availability(t, t_start, duration, depth):
    """Fraction of nominal grid capacity available: 1.0 normally, dropping to
    (1-depth) for [t_start, t_start+duration)."""
    if t_start <= t < t_start + duration:
        return 1.0 - depth
    return 1.0


def simulate_conventional(t_start, duration, depth, C_bus, dt=2e-5, t_total=2.0):
    """Unbuffered (or LV-buffered with C_bus) conventional interface:
    deliverable power scales with sagged grid voltage magnitude; shortfall
    integrates onto the LV bus capacitance. Returns (t, V, tripped, t_trip)."""
    n = int(t_total / dt)
    t = np.arange(n) * dt
    V = np.full(n, V_LV_nom)
    tripped = False
    t_trip = None
    for k in range(1, n):
        if tripped:
            V[k] = V[k - 1]
            continue
        g = grid_availability(t[k - 1], t_start, duration, depth)
        P_avail = g * P_agg_rated
        shortfall = max(0.0, P_step - P_avail)
        if shortfall > 0:
            dVdt = -shortfall / (C_bus * V[k - 1])
        else:
            dVdt = 0.0
        V[k] = V[k - 1] + dVdt * dt
        dev = abs(V[k] - V_LV_nom) / V_LV_nom
        if not tripped and dev > trip_band:
            tripped = True
            t_trip = t[k]
            V[k] = V_LV_nom * (1 - trip_band) if V[k] < V_LV_nom else V_LV_nom * (1 + trip_band)
    max_dev = np.max(np.abs(V - V_LV_nom)) / V_LV_nom * 100.0
    return t, V, tripped, t_trip, max_dev


def simulate_sst(t_start, duration, depth, dt=2e-5, t_total=2.0):
    """SST: CHB draws grid power up to availability; DAB delivers exactly
    the LV-side demand while V1 >= floor (LV bus perfectly regulated,
    average-value fixed point); once V1 < floor, DAB output throttles
    proportionally to V1/V1_floor, and any shortfall integrates onto the
    (same-sized) LV bus capacitance."""
    n = int(t_total / dt)
    t = np.arange(n) * dt
    V1 = np.full(n, V1_nom)
    V_LV = np.full(n, V_LV_nom)
    for k in range(1, n):
        g = grid_availability(t[k - 1], t_start, duration, depth)
        P_avail_grid = g * P_agg_rated

        if V1[k - 1] >= V1_floor:
            P_LV_delivered = P_step  # unthrottled, exact regulation
        else:
            # Gentle proportional throttle (paper describes "throttled
            # proportionally" qualitatively without giving the droop gain;
            # this small gain keeps both post-budget scenarios trip-free
            # with small, growing deviation, matching the paper's reported
            # shape -- exact percentages are approximate without the
            # original controller's gain).
            k_throttle = 0.0005
            throttle = max(0.0, 1 - k_throttle * (V1_floor - V1[k - 1]) / V1_floor)
            P_LV_delivered = P_step * throttle

        # MV link energy balance: CHB draws only what the DAB demands,
        # capped by whatever the (possibly sagged) grid can still provide
        P_grid_drawn = min(P_LV_delivered, P_avail_grid)
        E_agg = N_cells * 0.5 * C_cell * V1[k - 1] ** 2
        dE = (P_grid_drawn - P_LV_delivered) * dt
        E_new = max(E_agg + dE, 1e-6)
        V1[k] = np.sqrt(2 * E_new / (N_cells * C_cell))

        shortfall = P_step - P_LV_delivered
        if shortfall > 0:
            dVdt = -shortfall / (C_conv * V_LV[k - 1])
        else:
            dVdt = 0.0
        V_LV[k] = V_LV[k - 1] + dVdt * dt

    max_dev = np.max(np.abs(V_LV - V_LV_nom)) / V_LV_nom * 100.0
    min_V1_pu = np.min(V1) / V1_nom
    tripped = max_dev / 100.0 > trip_band
    return t, V_LV, V1, tripped, max_dev, min_V1_pu


def simulate_coincident(t_start, duration, depth, pv_deficit_kw=25.0, pv_ramp=0.150,
                         load_kw=15.0, dt=2e-5, t_total=2.0):
    """Section 6.4 -- coincident PV cloud-transient + load pickup riding on
    top of the same 60kW baseline, overlapping the sag window (not
    synchronized to its exact start)."""
    n = int(t_total / dt)
    t = np.arange(n) * dt
    V1 = np.full(n, V1_nom)
    V_LV = np.full(n, V_LV_nom)
    pv_start = t_start + 0.05 * duration  # small offset, not exactly synced
    load_start = t_start + 0.08 * duration

    def demand(tt):
        d = P_step
        if tt >= pv_start:
            d += pv_deficit_kw * 1e3 * min(1.0, (tt - pv_start) / pv_ramp)
        if tt >= load_start:
            d += load_kw * 1e3
        return d

    for k in range(1, n):
        g = grid_availability(t[k - 1], t_start, duration, depth)
        P_avail_grid = g * P_agg_rated
        P_dem = demand(t[k - 1])

        if V1[k - 1] >= V1_floor:
            P_LV_delivered = P_dem
        else:
            k_throttle = 0.0005
            throttle = max(0.0, 1 - k_throttle * (V1_floor - V1[k - 1]) / V1_floor)
            P_LV_delivered = P_dem * throttle

        P_grid_drawn = min(P_LV_delivered, P_avail_grid)
        E_agg = N_cells * 0.5 * C_cell * V1[k - 1] ** 2
        E_new = max(E_agg + (P_grid_drawn - P_LV_delivered) * dt, 1e-6)
        V1[k] = np.sqrt(2 * E_new / (N_cells * C_cell))

        shortfall = P_dem - P_LV_delivered
        dVdt = -shortfall / (C_conv * V_LV[k - 1]) if shortfall > 0 else 0.0
        V_LV[k] = V_LV[k - 1] + dVdt * dt

    max_dev = np.max(np.abs(V_LV - V_LV_nom)) / V_LV_nom * 100.0
    min_V1_pu = np.min(V1) / V1_nom
    return max_dev, min_V1_pu


def run_coincident_table():
    t_start = 0.5
    scenarios = [
        {"name": "Moderate sag (65%, 150ms) + PV/load", "depth": 0.65, "duration": 0.150},
        {"name": "Full interruption (500ms) + PV/load", "depth": 1.00, "duration": 0.500},
    ]
    print("\n=== Section 6.4: Coincident PV/load disturbance (Table 5) ===")
    rows = []
    for sc in scenarios:
        _, _, trip_u, ttrip_u, _ = simulate_conventional(
            t_start, sc["duration"], sc["depth"], C_conv,
            t_total=t_start + sc["duration"] + 1.0)
        dev_s, minv = simulate_coincident(t_start, sc["duration"], sc["depth"],
                                            t_total=t_start + sc["duration"] + 1.0)
        conv_str = f"tripped @ {(ttrip_u - t_start)*1000:.1f} ms" if trip_u else "no trip"
        print(f"{sc['name']}: conventional={conv_str}  SST: {dev_s:.3f}% / {minv:.3f} pu")
        rows.append({"scenario": sc["name"], "conventional": conv_str,
                     "sst_max_dev_pct": dev_s, "sst_min_V1_pu": minv})
    print("Paper: Moderate+PV/load: tripped@24.2ms | 0.930%/0.977pu")
    print("       Full 500ms+PV/load: tripped@3.8ms | 0.930%/0.719pu")
    return rows


def main():
    scenarios = [
        {"name": "Shallow, non-binding (30% sag, 150 ms)", "depth": 0.30, "duration": 0.150},
        {"name": "Moderate (65% sag, 150 ms)", "depth": 0.65, "duration": 0.150},
        {"name": "Full interruption, 150 ms (< budget)", "depth": 1.00, "duration": 0.150},
        {"name": "Full interruption, 500 ms (> budget)", "depth": 1.00, "duration": 0.500},
        {"name": "Full interruption, 1.2 s (well beyond)", "depth": 1.00, "duration": 1.200},
    ]
    t_start = 0.5
    results = []
    print(f"{'Scenario':<42} {'Conv(unbuf)':<22} {'Conv(matched)':<22} {'SST':<22}")
    for sc in scenarios:
        _, _, trip_u, ttrip_u, dev_u = simulate_conventional(
            t_start, sc["duration"], sc["depth"], C_conv, t_total=t_start + sc["duration"] + 1.5)
        _, _, trip_m, ttrip_m, dev_m = simulate_conventional(
            t_start, sc["duration"], sc["depth"], C_matched, t_total=t_start + sc["duration"] + 1.5)
        _, _, V1arr, trip_s, dev_s, minV1pu = simulate_sst(
            t_start, sc["duration"], sc["depth"], t_total=t_start + sc["duration"] + 1.5)

        row_u = f"{dev_u:.3f}% / trip@{(ttrip_u - t_start)*1000:.1f}ms" if trip_u else f"{dev_u:.3f}% / no trip"
        row_m = f"{dev_m:.3f}% / trip@{(ttrip_m - t_start)*1000:.1f}ms" if trip_m else f"{dev_m:.3f}% / no trip"
        row_s = f"{dev_s:.3f}% / MV {minV1pu:.3f}pu"
        print(f"{sc['name']:<42} {row_u:<22} {row_m:<22} {row_s:<22}")

        results.append({
            "scenario": sc["name"], "depth": sc["depth"], "duration_ms": sc["duration"] * 1000,
            "conventional_unbuffered": {"max_dev_pct": dev_u, "tripped": bool(trip_u),
                                          "t_trip_ms": (ttrip_u - t_start) * 1000 if trip_u else None},
            "conventional_matched": {"max_dev_pct": dev_m, "tripped": bool(trip_m),
                                       "t_trip_ms": (ttrip_m - t_start) * 1000 if trip_m else None},
            "sst": {"max_dev_pct": dev_s, "min_V1_pu": minV1pu, "tripped": bool(trip_s)},
        })

    print("\nPaper's Table 2 (for comparison):")
    print("  Shallow: 0.000%/no trip | 0.006%/no trip | 0.000%/1.000pu")
    print("  Moderate: 20.0%/trip@30.6ms | 1.56%/no trip | 0.000%/0.994pu")
    print("  150ms full: 20.0%/trip@3.8ms | 8.55%/no trip | 0.000%/0.953pu")
    print("  500ms full: 20.0%/trip@3.8ms | 20.0%/trip@453.2ms | 0.017%/0.833pu")
    print("  1.2s full: 20.0%/trip@3.8ms | 20.0%/trip@453.2ms | 0.069%/0.515pu")

    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_sag_results.json", "w") as f:
        json.dump(results, f, indent=2)

    coincident_rows = run_coincident_table()
    with open("../results/sst_coincident_results.json", "w") as f:
        json.dump(coincident_rows, f, indent=2)


if __name__ == "__main__":
    main()
