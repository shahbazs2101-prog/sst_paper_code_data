"""
table5_observation_ablation.py
Section 5.3, Table 5 -- compares the 5-input SST-aware checkpoint against
a 6-input variant (MV-link voltage added to observation), on the SST
interface only, using the same single-scenario and 500-trial checks as
table2/table4.
"""
import json
import numpy as np
import torch
from environment import MicrogridEnv
from segments import build_segment
from dqn import QNet, ACTIONS_KW

GRID_EVENT = {"t_start": 300.0, "duration": 2.0, "depth": 1.0}
N_TRIALS = 200  # reduced from 500 for this ablation given per-call time limits;
                 # documented deviation from the paper's own 500-trial count


class DQNPolicy:
    def __init__(self, q_net, add_mv_link_obs=False):
        self.q = q_net
        self.add_mv_link_obs = add_mv_link_obs

    def act(self, obs):
        with torch.no_grad():
            qvals = self.q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            return float(ACTIONS_KW[int(torch.argmax(qvals).item())])


def run_single(policy, grid_event, seed=7):
    pv_fn, load_fn, ge = build_segment("grid_disturbance", grid_event=grid_event)
    env = MicrogridEnv(pv_fn, load_fn, seed=seed, interface="sst", grid_event=ge, soc0=0.5)
    obs = env.reset()
    if policy.add_mv_link_obs:
        v1 = env._v1_sst if env._v1_sst is not None else 3300.0
        obs = np.concatenate([obs, [v1 / 3300.0 - 1.0]])
    cmds = []
    for step in range(600):
        a = policy.act(obs)
        cmds.append(a)
        obs, _ = env.step(a)
        if policy.add_mv_link_obs:
            v1 = env._v1_sst if env._v1_sst is not None else 3300.0
            obs = np.concatenate([obs, [v1 / 3300.0 - 1.0]])
    cmds = np.array(cmds)
    throughput = float(np.sum(np.abs(cmds)) * (1.0 / 3600.0))
    mean_slew = float(np.mean(np.abs(np.diff(cmds))))
    return {"throughput_kwh": throughput, "mean_slew": mean_slew,
            "max_dev_pct": env.max_vdc_dev_pct, "tripped": env.tripped}


def main():
    q5 = QNet(n_obs=5)
    q5.load_state_dict(torch.load("../checkpoints/dqn_sst_aware_seed7.pt"))
    q6 = QNet(n_obs=6)
    q6.load_state_dict(torch.load("../checkpoints/dqn_mv_link_obs.pt"))
    pol5 = DQNPolicy(q5, add_mv_link_obs=False)
    pol6 = DQNPolicy(q6, add_mv_link_obs=True)

    r5 = run_single(pol5, GRID_EVENT)
    r6 = run_single(pol6, GRID_EVENT)
    print("Single scenario (2s full MV interruption, SST interface):")
    print(f"  5-input: throughput={r5['throughput_kwh']:.4f}kWh slew={r5['mean_slew']:.2f}kW/s "
          f"dev={r5['max_dev_pct']:.3f}%")
    print(f"  6-input: throughput={r6['throughput_kwh']:.4f}kWh slew={r6['mean_slew']:.2f}kW/s "
          f"dev={r6['max_dev_pct']:.3f}%")
    print("  paper: 5-input 0.0730kWh/5.60kW/s -> 6-input 0.0678kWh/4.20kW/s")

    rng = np.random.default_rng(11)
    slews5, slews6, thr5, thr6 = [], [], [], []
    for i in range(N_TRIALS):
        depth = rng.uniform(0.10, 1.00)
        duration = rng.uniform(0.05, 1.5)
        t_start = rng.uniform(200, 350)
        ge = {"t_start": t_start, "duration": duration, "depth": depth}
        seed = 2000 + i
        r5s = run_single(pol5, ge, seed=seed)
        r6s = run_single(pol6, ge, seed=seed)
        slews5.append(r5s["mean_slew"]); slews6.append(r6s["mean_slew"])
        thr5.append(r5s["throughput_kwh"]); thr6.append(r6s["throughput_kwh"])
        if (i + 1) % 50 == 0:
            print(f"{i+1}/{N_TRIALS} trials done")

    print(f"\n{N_TRIALS}-trial sweep, SST interface:")
    print(f"  5-input: mean|slew|={np.mean(slews5):.2f}+-{np.std(slews5):.2f} kW/s, "
          f"throughput={np.mean(thr5):.4f}kWh")
    print(f"  6-input: mean|slew|={np.mean(slews6):.2f}+-{np.std(slews6):.2f} kW/s, "
          f"throughput={np.mean(thr6):.4f}kWh")
    print("  paper (500 trials): 5-input 8.15+-2.83kW/s / 0.0608kWh -> "
          "6-input 3.74+-2.41kW/s / 0.0588kWh")

    results = {
        "single_scenario": {"5_input": r5, "6_input": r6},
        "n_trial_sweep": N_TRIALS,
        "sweep": {
            "mean_slew_5input": float(np.mean(slews5)), "std_slew_5input": float(np.std(slews5)),
            "mean_slew_6input": float(np.mean(slews6)), "std_slew_6input": float(np.std(slews6)),
            "throughput_5input": float(np.mean(thr5)), "throughput_6input": float(np.mean(thr6)),
        },
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/table5_observation_ablation.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
