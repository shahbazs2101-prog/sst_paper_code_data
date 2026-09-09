"""
train_frozen.py
Trains the original DQN checkpoint (Section 2), against the conventional
interface only, no SST-aware physics in the grid_disturbance segments.
This is the checkpoint referred to as "frozen" throughout Section 5.
"""
import torch
import numpy as np
import json
import os
import time
from dqn import train_dqn, QNet
from environment import MicrogridEnv
from evaluate import run_scenario


class DQNPolicy:
    def __init__(self, q_net, add_mv_link_obs=False):
        self.q = q_net
        self.add_mv_link_obs = add_mv_link_obs

    def reset(self):
        pass

    def act(self, obs):
        with torch.no_grad():
            qvals = self.q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
            a_idx = int(torch.argmax(qvals).item())
        from dqn import ACTIONS_KW
        return float(ACTIONS_KW[a_idx])


def main():
    t0 = time.time()
    print("Training frozen DQN checkpoint (seed=7, 260 episodes)...")
    q, reward_hist = train_dqn(seed=7, n_episodes=260, sst_aware=False, verbose=True)
    print(f"Training took {(time.time()-t0)/60:.1f} min")

    os.makedirs("../checkpoints", exist_ok=True)
    torch.save(q.state_dict(), "../checkpoints/dqn_frozen.pt")

    policy = DQNPolicy(q)
    res = run_scenario(policy, interface="conventional", seed=7)
    print(f"\nFrozen DQN, conventional interface, 5-segment scenario:")
    print(f"  tracking RMSE: {res['tracking_rmse_kw']:.2f} kW (paper: 12.10 kW)")
    print(f"  cost: ${res['cost_usd']:.2f} (paper: $1.61)")
    print(f"  mean |slew|: {res['mean_abs_slew_kw_s']:.2f} kW/s (paper: 8.41 kW/s)")

    os.makedirs("../results", exist_ok=True)
    results = {
        "tracking_rmse_kw": res["tracking_rmse_kw"],
        "cost_usd": res["cost_usd"],
        "mean_abs_slew_kw_s": res["mean_abs_slew_kw_s"],
        "reward_first20": float(np.mean(reward_hist[:20])),
        "reward_last20": float(np.mean(reward_hist[-20:])),
        "paper_reported": {"tracking_rmse_kw": 12.10, "cost_usd": 1.61, "mean_abs_slew_kw_s": 8.41},
    }
    with open("../results/frozen_dqn_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
