"""
table4_montecarlo.py
Section 5.2, Table 4 -- 500-trial randomized sweep comparing the frozen
and SST-aware DQN checkpoints, paired (same disturbance draw for both
checkpoints), on both interfaces. Reports trip rate, Vdc max deviation,
BESS throughput, mean |slew|, and time-at-slew-limit, plus a paired exact
test on the trip-rate disagreements (matching the paper's own p=0.0039
methodology).
"""
import json
import numpy as np
import torch
from scipy.stats import binomtest
from environment import MicrogridEnv
from segments import build_segment
from dqn import QNet, ACTIONS_KW

N_TRIALS = 500


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
    cmds = []
    for step in range(600):
        a = policy.act(obs)
        cmds.append(a)
        obs, _ = env.step(a)
    cmds = np.array(cmds)
    throughput_kwh = float(np.sum(np.abs(cmds)) * (1.0 / 3600.0))
    mean_slew = float(np.mean(np.abs(np.diff(cmds))))
    time_at_limit = float(np.mean(np.abs(np.diff(cmds)) >= 49.0))  # near the 50kW/s cap
    return {
        "tripped": env.tripped, "max_dev_pct": env.max_vdc_dev_pct,
        "throughput_kwh": throughput_kwh, "mean_slew": mean_slew,
        "time_at_limit": time_at_limit,
    }


def main(start=0, n_trials=N_TRIALS, state_path="../results/_mc_state.pkl"):
    import os
    import pickle
    q_frozen = QNet()
    q_frozen.load_state_dict(torch.load("../checkpoints/dqn_frozen.pt"))
    q_sst = QNet()
    q_sst.load_state_dict(torch.load("../checkpoints/dqn_sst_aware_seed7.pt"))
    pol_frozen = DQNPolicy(q_frozen)
    pol_sst = DQNPolicy(q_sst)

    rng = np.random.default_rng(7)
    rows = {"conventional": {"frozen": [], "sst_aware": []},
            "sst": {"frozen": [], "sst_aware": []}}
    draws = []
    start_i = 0

    if os.path.exists(state_path):
        with open(state_path, "rb") as f:
            state = pickle.load(f)
        rows = state["rows"]
        draws = state["draws"]
        start_i = state["next_i"]
        # replay the rng to the correct position
        for _ in range(start_i):
            rng.uniform(0.10, 1.00); rng.uniform(0.05, 1.5); rng.uniform(200, 350)
        print(f"Resuming Monte Carlo sweep from trial {start_i}")

    end_i = min(N_TRIALS, start_i + n_trials)
    for i in range(start_i, end_i):
        depth = rng.uniform(0.10, 1.00)
        duration = rng.uniform(0.05, 1.5)
        t_start = rng.uniform(200, 350)
        seed = 1000 + i
        for iface in ["conventional", "sst"]:
            r_f = run_trial(pol_frozen, iface, seed, depth, duration, t_start)
            r_s = run_trial(pol_sst, iface, seed, depth, duration, t_start)
            rows[iface]["frozen"].append(r_f)
            rows[iface]["sst_aware"].append(r_s)

    if end_i < N_TRIALS:
        with open(state_path, "wb") as f:
            pickle.dump({"rows": rows, "draws": draws, "next_i": end_i}, f)
        print(f"CONTINUE: {end_i}/{N_TRIALS} trials done so far, run again to continue.")
        return

    # done -- compute and print/save final summary
    os.makedirs("../results", exist_ok=True)
    results = {}
    for iface in ["conventional", "sst"]:
        f = rows[iface]["frozen"]
        s = rows[iface]["sst_aware"]
        trip_f = sum(r["tripped"] for r in f)
        trip_s = sum(r["tripped"] for r in s)
        both_f_trip_s_not = sum(rf["tripped"] and not rs["tripped"] for rf, rs in zip(f, s))
        both_s_trip_f_not = sum(rs["tripped"] and not rf["tripped"] for rf, rs in zip(f, s))
        n_disagree = both_f_trip_s_not + both_s_trip_f_not
        pval = binomtest(both_s_trip_f_not, n_disagree, 0.5).pvalue if n_disagree > 0 else None

        mean_slew_f = np.mean([r["mean_slew"] for r in f])
        mean_slew_s = np.mean([r["mean_slew"] for r in s])
        thr_f = np.mean([r["throughput_kwh"] for r in f])
        thr_s = np.mean([r["throughput_kwh"] for r in s])

        print(f"\n=== {iface} interface ===")
        print(f"  Trip rate: frozen {trip_f}/{N_TRIALS} ({trip_f/N_TRIALS*100:.1f}%) vs "
              f"SST-aware {trip_s}/{N_TRIALS} ({trip_s/N_TRIALS*100:.1f}%)")
        print(f"  Disagreements: {n_disagree} (frozen-trips-only={both_f_trip_s_not}, "
              f"sst-aware-trips-only={both_s_trip_f_not}), paired test p={pval}")
        print(f"  Mean |slew|: frozen {mean_slew_f:.2f} vs SST-aware {mean_slew_s:.2f} kW/s")
        print(f"  Throughput: frozen {thr_f:.4f} vs SST-aware {thr_s:.4f} kWh")

        results[iface] = {
            "trip_rate_frozen": trip_f / N_TRIALS, "trip_rate_sst_aware": trip_s / N_TRIALS,
            "n_disagree": n_disagree, "sst_aware_trips_only": both_s_trip_f_not,
            "frozen_trips_only": both_f_trip_s_not, "paired_test_p": pval,
            "mean_slew_frozen": float(mean_slew_f), "mean_slew_sst_aware": float(mean_slew_s),
            "throughput_frozen": float(thr_f), "throughput_sst_aware": float(thr_s),
        }

    print("\nPaper's Table 4 (for comparison):")
    print("  Conventional trip rate: 4.0% (frozen) -> 5.8% (SST-aware), p=0.0039")
    print("  Conventional mean|slew|: 6.66 (frozen) -> 8.28 (SST-aware) kW/s")
    print("  SST trip rate: 0.0% both; SST mean|slew|: 6.50 -> 8.15 kW/s")

    with open("../results/table4_montecarlo.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    if os.path.exists(state_path):
        os.remove(state_path)
    print("DONE")


if __name__ == "__main__":
    import sys
    chunk = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    main(n_trials=chunk)
