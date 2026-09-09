"""
evaluate.py
Runs the fixed 3000 s, five-600s-segment evaluation scenario (Section 2)
for a given policy (PI or a trained DQN), on a given interface, and
computes tracking RMSE, operating cost, and command smoothness -- the
three general-operation metrics reported throughout the paper.
"""
import numpy as np
from environment import MicrogridEnv, BESS_RATED_KW
from segments import build_segment, SEGMENT_ORDER

IMPORT_PRICE = 0.12   # $/kWh
EXPORT_PRICE = 0.06   # $/kWh
DEGRADATION_PRICE = 0.05  # $/kWh throughput


def run_scenario(policy, interface="conventional", seed=7, grid_event=None,
                  segment_order=None, reset_soc_between=False):
    """policy must have .act(obs) -> p_batt_cmd_kw and (for PI) .reset().
    Returns a dict of full traces plus the three general-operation metrics."""
    if segment_order is None:
        segment_order = SEGMENT_ORDER

    all_cmds, all_pv, all_load, all_soc, all_vdc = [], [], [], [], []
    tripped_any = False
    t_trip = None
    max_dev = 0.0
    cost_total = 0.0
    soc = 0.5

    for seg_idx, seg_name in enumerate(segment_order):
        ge = grid_event if seg_name == "grid_disturbance" else None
        pv_fn, load_fn, ge = build_segment(seg_name, grid_event=ge)
        env = MicrogridEnv(pv_fn, load_fn, seed=seed + seg_idx, interface=interface,
                            grid_event=ge, soc0=soc)
        if hasattr(policy, "reset"):
            policy.reset()
        obs = env.reset()

        for step in range(600):
            a = policy.act(obs)
            pv = obs[0] * 100.0
            load = obs[1] * 120.0
            next_obs, slew_frac = env.step(a)

            all_cmds.append(a)
            all_pv.append(pv)
            all_load.append(load)
            all_soc.append(env.soc)
            all_vdc.append(env.vdc)

            net_import_kwh = (load - pv - a) * (1.0 / 3600.0)
            if net_import_kwh > 0:
                cost_total += net_import_kwh * IMPORT_PRICE
            else:
                cost_total += net_import_kwh * EXPORT_PRICE  # negative = credit
            cost_total += abs(a) * (1.0 / 3600.0) * DEGRADATION_PRICE

            obs = next_obs
            if env.tripped and not tripped_any:
                tripped_any = True
                t_trip = env.t + seg_idx * 600.0

        max_dev = max(max_dev, env.max_vdc_dev_pct)
        soc = env.soc if not reset_soc_between else 0.5

    cmds = np.array(all_cmds)
    ideal = np.array(all_load) - np.array(all_pv)
    ideal = np.clip(ideal, -BESS_RATED_KW, BESS_RATED_KW)
    tracking_rmse = float(np.sqrt(np.mean((cmds - ideal) ** 2)))
    mean_abs_slew = float(np.mean(np.abs(np.diff(cmds))))

    return {
        "tracking_rmse_kw": tracking_rmse,
        "cost_usd": cost_total,
        "mean_abs_slew_kw_s": mean_abs_slew,
        "tripped": tripped_any,
        "t_trip_s": t_trip,
        "max_vdc_dev_pct": max_dev,
        "cmds": cmds,
        "soc_trace": np.array(all_soc),
        "vdc_trace": np.array(all_vdc),
    }
