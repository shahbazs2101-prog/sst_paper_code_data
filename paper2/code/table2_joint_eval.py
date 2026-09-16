"""Reproducible Table 2 evaluation."""
import json
import numpy as np
import torch
from config import TABLE2_EVENT, TABLE2_SEED, N_DECISION_STEPS
from environment import MicrogridEnv
from segments import build_segment
from pi_controller import PIController
from dqn import QNet, ACTIONS_KW


class DQNPolicy:
    def __init__(self, q_net):
        self.q = q_net

    def reset(self):
        pass

    def act(self, obs):
        with torch.no_grad():
            qvals = self.q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            return float(ACTIONS_KW[int(torch.argmax(qvals).item())])


def run_joint(policy, interface, seed=TABLE2_SEED):
    pv_fn, load_fn, ge = build_segment("grid_disturbance", grid_event=TABLE2_EVENT)
    env = MicrogridEnv(pv_fn, load_fn, seed=seed, interface=interface, grid_event=ge, soc0=0.5)
    policy.reset() if hasattr(policy, "reset") else None
    obs = env.reset()
    cmds, times = [], []
    for _ in range(N_DECISION_STEPS):
        times.append(env.t)
        a = policy.act(obs)
        cmds.append(a)
        obs, _ = env.step(a)
    cmds = np.asarray(cmds)
    return {
        "max_vdc_dev_pct": float(env.max_vdc_dev_pct),
        "tripped": bool(env.tripped),
        "t_trip_s": env.t_trip,
        "dispatch_min_kw": float(cmds.min()),
        "dispatch_max_kw": float(cmds.max()),
    }


def main():
    q = QNet()
    q.load_state_dict(torch.load("../checkpoints/dqn_frozen.pt", map_location="cpu"))
    dqn_policy = DQNPolicy(q)
    pi_policy = PIController()

    combos = [
        ("PI baseline", "conventional", pi_policy),
        ("DQN", "conventional", dqn_policy),
        ("PI baseline", "sst", pi_policy),
        ("DQN", "sst", dqn_policy),
    ]
    results = {}
    for name, iface, policy in combos:
        r = run_joint(policy, iface)
        results[f"{name}_{iface}"] = r
        outcome = f"tripped @ {r['t_trip_s']:.2f}s" if r["tripped"] else "rode through"
        print(f"{name} / {iface}: dev={r['max_vdc_dev_pct']:.3f}% | {outcome} | "
              f"dispatch={r['dispatch_min_kw']:.1f}-{r['dispatch_max_kw']:.1f} kW")

    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/table2_joint_eval.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
