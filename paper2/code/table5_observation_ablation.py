"""Reproducible 500-trial observation-ablation evaluation for Table 5."""
import json
import numpy as np
import torch
from config import TABLE2_EVENT, TABLE5_N_TRIALS, TABLE5_SEED, mc_draws
from environment import MicrogridEnv
from segments import build_segment
from dqn import QNet, ACTIONS_KW
from metrics import compute_event_metrics


class DQNPolicy:
    def __init__(self, q_net, add_mv_link_obs=False):
        self.q = q_net
        self.add_mv_link_obs = add_mv_link_obs

    def augment(self, obs, env):
        if not self.add_mv_link_obs:
            return obs
        v1 = env._v1_sst if env._v1_sst is not None else 3300.0
        return np.concatenate([obs, [v1 / 3300.0 - 1.0]])

    def act(self, obs):
        with torch.no_grad():
            qvals = self.q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            return float(ACTIONS_KW[int(torch.argmax(qvals).item())])


def run_single(policy, grid_event, seed=7):
    pv_fn, load_fn, ge = build_segment("grid_disturbance", grid_event=grid_event)
    env = MicrogridEnv(pv_fn, load_fn, seed=seed, interface="sst", grid_event=ge, soc0=0.5)
    obs = env.reset()
    cmds, times = [], []
    for _ in range(600):
        times.append(env.t)
        a = policy.act(policy.augment(obs, env))
        cmds.append(a)
        obs, _ = env.step(a)
    m = compute_event_metrics(np.asarray(times), np.asarray(cmds),
                              grid_event["t_start"], grid_event["duration"])
    return {"throughput_kwh": m["throughput_kwh"],
            "mean_slew": m["mean_slew"],
            "time_at_limit": m["time_at_limit"],
            "max_dev_pct": float(env.max_vdc_dev_pct),
            "tripped": bool(env.tripped)}


def main():
    q5 = QNet(n_obs=5)
    q5.load_state_dict(torch.load("../checkpoints/dqn_sst_aware_seed7.pt", map_location="cpu"))
    q6 = QNet(n_obs=6)
    q6.load_state_dict(torch.load("../checkpoints/dqn_mv_link_obs.pt", map_location="cpu"))
    pol5 = DQNPolicy(q5, add_mv_link_obs=False)
    pol6 = DQNPolicy(q6, add_mv_link_obs=True)

    single5 = run_single(pol5, TABLE2_EVENT, seed=TABLE5_SEED)
    single6 = run_single(pol6, TABLE2_EVENT, seed=TABLE5_SEED)
    print("Single scenario:")
    print("  5-input:", single5)
    print("  6-input:", single6)

    draws = mc_draws(TABLE5_N_TRIALS, TABLE5_SEED)
    rows5, rows6 = [], []
    for d in draws:
        ge = {"t_start": d["t_start"], "duration": d["duration"], "depth": d["depth"]}
        rows5.append(run_single(pol5, ge, seed=d["seed"]))
        rows6.append(run_single(pol6, ge, seed=d["seed"]))
        if (d["trial"] + 1) % 50 == 0:
            print(f"{d['trial'] + 1}/{TABLE5_N_TRIALS} trials done")

    def summary(rows):
        return {
            "mean_slew": float(np.mean([r["mean_slew"] for r in rows])),
            "std_slew": float(np.std([r["mean_slew"] for r in rows])),
            "throughput_kwh": float(np.mean([r["throughput_kwh"] for r in rows])),
            "time_at_limit": float(np.mean([r["time_at_limit"] for r in rows])),
            "trip_rate": float(np.mean([r["tripped"] for r in rows])),
            "mean_max_dev_pct": float(np.mean([r["max_dev_pct"] for r in rows])),
        }

    results = {
        "seed": TABLE5_SEED,
        "n_trials": TABLE5_N_TRIALS,
        "single_scenario": {"5_input": single5, "6_input": single6},
        "sweep": {"5_input": summary(rows5), "6_input": summary(rows6)},
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/table5_observation_ablation.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nTable 5 summary")
    print("5-input:", results["sweep"]["5_input"])
    print("6-input:", results["sweep"]["6_input"])
    print("DONE")


if __name__ == "__main__":
    main()
