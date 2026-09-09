"""
table2_joint_eval.py
Section 5, Table 2 -- runs the PI baseline and frozen DQN against both
interfaces during a shared 2 s full MV interruption embedded in the
grid_disturbance segment, and reports Vdc max deviation, trip outcome,
and BESS dispatch range for all four combinations.

KNOWN LIMITATION (documented, not silently glossed over): the exact trip
TIMING reported here does not match the paper's Table 2 closely, and
attempts to tune it closer (baseline deficit magnitude, profile noise
amplitude) showed the result is highly sensitive to inputs the manuscript
text doesn't specify -- small changes flip which policy trips faster, or
whether a policy trips at all within the tested window. This differs
from Paper 1's CHB/loss discrepancies, where real device parameters were
available even without the exact datasheet tables; here, no such anchor
exists for this specific segment's baseline profile. What DOES reproduce
reliably: the qualitative pattern the paper's finding rests on -- the
conventional interface is at genuine trip risk during an MV interruption
regardless of supervisory policy, while the SST interface always rides
through with small deviation, regardless of policy. Treat any specific
trip-time number from this script as illustrative, not a validated match.
"""
import json
import numpy as np
import torch
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


GRID_EVENT = {"t_start": 300.0, "duration": 2.0, "depth": 1.0}  # 2s full interruption at t=300s


def run_joint(policy, interface, seed=7):
    pv_fn, load_fn, ge = build_segment("grid_disturbance", grid_event=GRID_EVENT)
    env = MicrogridEnv(pv_fn, load_fn, seed=seed, interface=interface, grid_event=ge, soc0=0.5)
    if hasattr(policy, "reset"):
        policy.reset()
    obs = env.reset()
    cmds = []
    for step in range(600):
        a = policy.act(obs)
        cmds.append(a)
        obs, _ = env.step(a)
    cmds = np.array(cmds)
    return {
        "max_vdc_dev_pct": env.max_vdc_dev_pct,
        "tripped": env.tripped,
        "t_trip_s": env.t_trip,
        "dispatch_min_kw": float(cmds.min()),
        "dispatch_max_kw": float(cmds.max()),
    }


def main():
    q = QNet()
    q.load_state_dict(torch.load("../checkpoints/dqn_frozen.pt"))
    dqn_policy = DQNPolicy(q)
    pi_policy = PIController()

    combos = [
        ("PI baseline", "conventional", pi_policy),
        ("DQN", "conventional", dqn_policy),
        ("PI baseline", "sst", pi_policy),
        ("DQN", "sst", dqn_policy),
    ]
    paper = {
        ("PI baseline", "conventional"): {"dev": 20.0, "trip": "1.04s", "range": "28.5-100.0"},
        ("DQN", "conventional"): {"dev": 20.0, "trip": "0.07s", "range": "29.4-90.0"},
        ("PI baseline", "sst"): {"dev": 0.55, "trip": "rode through", "range": "28.5-40.8"},
        ("DQN", "sst"): {"dev": 0.54, "trip": "rode through", "range": "29.4-40.0"},
    }

    results = {}
    print(f"{'Policy x interface':<25}{'Vdc dev%':<12}{'Outcome':<20}{'Dispatch range':<20}")
    for name, iface, policy in combos:
        r = run_joint(policy, iface)
        outcome = f"tripped @ {r['t_trip_s']:.2f}s" if r["tripped"] else "rode through"
        rng_str = f"{r['dispatch_min_kw']:.1f}-{r['dispatch_max_kw']:.1f}"
        print(f"{name+' / '+iface:<25}{r['max_vdc_dev_pct']:<12.3f}{outcome:<20}{rng_str:<20}")
        p = paper[(name, iface)]
        print(f"  paper: dev={p['dev']}%  trip={p['trip']}  range={p['range']} kW")
        results[f"{name}_{iface}"] = r

    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/table2_joint_eval.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
