"""
interface_physics.py
DC-bus voltage dynamics for the two grid interfaces, reusing the same
physics and parameters verified in the companion hardware paper [1]'s
own code (sst_sim.py): conventional LFT+VSC trip behavior, and the SST's
MV-link energy-balance ride-through model. Ported here to run at this
paper's FINE_DT substep resolution, driven by whatever net grid import
the microgrid's own dispatch actually needs at each instant, rather than
[1]'s fixed 60 kW test step.
"""
import numpy as np

V_DC_NOM = 800.0
TRIP_BAND = 0.20
C_CONV = 2e-3           # F, conventional LV bus capacitance
P_AGG_RATED_KW = 150.0  # kW, aggregate grid-interface rating

N_CELLS = 9
C_CELL = 2000e-6        # F, per-cell MV DC-link capacitance
V1_NOM = 3300.0
V1_FLOOR = 0.85 * V1_NOM
K_THROTTLE = 0.0005     # same documented approximation as [1]'s code


def grid_availability(env, t):
    ev = env.grid_event
    if ev is None:
        return 1.0
    if ev["t_start"] <= t < ev["t_start"] + ev["duration"]:
        return 1.0 - ev["depth"]
    return 1.0


def update_vdc(env, pv, load, p_batt, dt=0.02):
    """Advance env.vdc (and, for the SST interface, env._v1_sst) by one
    FINE_DT substep. net_import_kw > 0 means the microgrid needs to draw
    that much from the grid; < 0 means it would export."""
    net_import_kw = load - pv - p_batt
    g = grid_availability(env, env.t)
    p_avail_kw = g * P_AGG_RATED_KW

    if env.interface == "conventional":
        if net_import_kw > 0:
            shortfall_kw = max(0.0, net_import_kw - p_avail_kw)
        else:
            shortfall_kw = 0.0  # exporting is never grid-capacity-limited here
        if shortfall_kw > 0 and not env.tripped:
            dVdt = -shortfall_kw * 1000.0 / (C_CONV * env.vdc)
            env.vdc += dVdt * dt
        dev = abs(env.vdc - V_DC_NOM) / V_DC_NOM
        env.max_vdc_dev_pct = max(env.max_vdc_dev_pct, dev * 100.0)
        if not env.tripped and dev > TRIP_BAND:
            env.tripped = True
            env.t_trip = env.t

    else:  # SST
        if env._v1_sst is None:
            env._v1_sst = V1_NOM
        V1 = env._v1_sst
        demand_kw = max(net_import_kw, 0.0)
        if V1 >= V1_FLOOR:
            p_lv_kw = demand_kw
        else:
            throttle = max(0.0, 1 - K_THROTTLE * (V1_FLOOR - V1) / V1_FLOOR)
            p_lv_kw = demand_kw * throttle
        p_grid_drawn_kw = min(p_lv_kw, p_avail_kw)
        E = N_CELLS * 0.5 * C_CELL * V1 ** 2
        dE = (p_grid_drawn_kw - p_lv_kw) * 1000.0 * dt
        E_new = max(E + dE, 1e-6)
        env._v1_sst = np.sqrt(2 * E_new / (N_CELLS * C_CELL))

        shortfall_kw = demand_kw - p_lv_kw
        if shortfall_kw > 0 and not env.tripped:
            dVdt = -shortfall_kw * 1000.0 / (C_CONV * env.vdc)
            env.vdc += dVdt * dt
        dev = abs(env.vdc - V_DC_NOM) / V_DC_NOM
        env.max_vdc_dev_pct = max(env.max_vdc_dev_pct, dev * 100.0)
        if not env.tripped and dev > TRIP_BAND:
            env.tripped = True
            env.t_trip = env.t
