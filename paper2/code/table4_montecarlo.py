"""Reproducible 500-trial Monte-Carlo evaluation for Table 4."""
import json
import numpy as np
import torch
from scipy.stats import binomtest
from config import MC_N_TRIALS, MC_SEED, mc_draws
from environment import MicrogridEnv
from segments import build_segment
from dqn import QNet, ACTIONS_KW
from metrics import compute_event_metrics


class DQNPolicy:
    def __init__(self, q_net):
        self.q = q_net

    def act(self, obs):
        with torch.no_grad():
            qvals = self.q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            return float(ACTIONS_KW[int(torch.argmax(qvals).item())])


def run_trial(policy, interface, seed, depth, duration, t_start):
    grid_event = {"t_start": t_start, "duration": duration, "depth": depth}
    pv_fn, load_fn, ge = build_segment("grid_disturbance", grid_event=grid_event)
    env = MicrogridEnv(pv_fn, load_fn, seed=seed, interface=interface, grid_event=ge, soc0=0.5)
    obs = env.reset()
    cmds, times = [], []
    for _ in range(600):
        times.append(env.t)
        a = policy.act(obs)
        cmds.append(a)
        obs, _ = env.step(a)
    m = compute_event_metrics(np.asarray(times), np.asarray(cmds), t_start, duration)
    return {
        "tripped": bool(env.tripped),
        "max_dev_pct": float(env.max_vdc_dev_pct),
        **m,
    }


def summarize(rows):
    trips = int(sum(r["tripped"] for r in rows))
    return trips, {
        "trip_rate": trips / len(rows),
        "mean_slew": float(np.mean([r["mean_slew"] for r in rows])),
        "throughput": float(np.mean([r["throughput_kwh"] for r in rows])),
        "time_at_limit": float(np.mean([r["time_at_limit"] for r in rows])),
        "mean_max_dev_pct": float(np.mean([r["max_dev_pct"] for r in rows])),
    }


def main():
    q_frozen = QNet()
    q_frozen.load_state_dict(torch.load("../checkpoints/dqn_frozen.pt", map_location="cpu"))
    q_sst = QNet()
    q_sst.load_state_dict(torch.load("../checkpoints/dqn_sst_aware_seed7.pt", map_location="cpu"))
    pol_frozen, pol_sst = DQNPolicy(q_frozen), DQNPolicy(q_sst)

    rows = {"conventional": {"frozen": [], "sst_aware": []},
            "sst": {"frozen": [], "sst_aware": []}}
    draws = mc_draws(MC_N_TRIALS, MC_SEED)

    for d in draws:
        for iface in ("conventional", "sst"):
            rows[iface]["frozen"].append(run_trial(pol_frozen, iface, d["seed"], d["depth"], d["duration"], d["t_start"]))
            rows[iface]["sst_aware"].append(run_trial(pol_sst, iface, d["seed"], d["depth"], d["duration"], d["t_start"]))
        if (d["trial"] + 1) % 50 == 0:
            print(f"{d['trial'] + 1}/{MC_N_TRIALS} trials done")

    results = {"n_trials": MC_N_TRIALS, "seed": MC_SEED, "interfaces": {}}
    for iface in ("conventional", "sst"):
        f, fs = summarize(rows[iface]["frozen"])
        s, ss = summarize(rows[iface]["sst_aware"])
        f_only = sum(rf["tripped"] and not rs["tripped"] for rf, rs in zip(rows[iface]["frozen"], rows[iface]["sst_aware"]))
        s_only = sum(rs["tripped"] and not rf["tripped"] for rf, rs in zip(rows[iface]["frozen"], rows[iface]["sst_aware"]))
        n_disagree = f_only + s_only
        pval = binomtest(s_only, n_disagree, 0.5).pvalue if n_disagree else None
        results["interfaces"][iface] = {
            "frozen": fs, "sst_aware": ss,
            "frozen_trips": f, "sst_aware_trips": s,
            "frozen_trips_only": f_only, "sst_aware_trips_only": s_only,
            "n_disagree": n_disagree, "paired_test_p": pval,
        }
        print(f"\n{iface}: frozen {f}/{MC_N_TRIALS} ({100*fs['trip_rate']:.1f}%), "
              f"SST-aware {s}/{MC_N_TRIALS} ({100*ss['trip_rate']:.1f}%), p={pval}")
        print(f"  event mean|slew|: {fs['mean_slew']:.3f} vs {ss['mean_slew']:.3f} kW/s")
        print(f"  event throughput: {fs['throughput']:.5f} vs {ss['throughput']:.5f} kWh")
        print(f"  event time-at-limit: {fs['time_at_limit']:.3f} vs {ss['time_at_limit']:.3f}")

    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/table4_montecarlo.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("DONE")


if __name__ == "__main__":
    main()
