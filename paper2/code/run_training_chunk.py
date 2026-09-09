"""
run_training_chunk.py
Runs one chunk of training (default 120 episodes) for a given run, saving
full resumable state to disk. Call repeatedly with the same --tag until
it reports DONE, to work around this environment's per-call time limit
while still doing exactly the paper-specified full training run (260
episodes, seed 7, no shortcuts).

Usage: python3 run_training_chunk.py --tag frozen [--sst_aware] [--mv_link_obs] [--episodes 260] [--chunk 120]
"""
import argparse
import pickle
import os
import torch
import numpy as np
from dqn import train_dqn, QNet


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--episodes", type=int, default=260)
    p.add_argument("--chunk", type=int, default=120)
    p.add_argument("--sst_aware", action="store_true")
    p.add_argument("--mv_link_obs", action="store_true")
    args = p.parse_args()

    state_path = f"../checkpoints/_train_state_{args.tag}.pkl"
    resume_state = None
    if os.path.exists(state_path):
        with open(state_path, "rb") as f:
            resume_state = pickle.load(f)
        print(f"Resuming from episode {resume_state['episode']}")

    q, reward_hist, state, done = train_dqn(
        seed=args.seed, n_episodes=args.episodes, sst_aware=args.sst_aware,
        add_mv_link_obs=args.mv_link_obs, resume_state=resume_state,
        episodes_this_call=args.chunk, verbose=True)

    os.makedirs("../checkpoints", exist_ok=True)
    with open(state_path, "wb") as f:
        pickle.dump(state, f)

    if done:
        torch.save(q.state_dict(), f"../checkpoints/dqn_{args.tag}.pt")
        # also save the full reward history for this completed run
        np.save(f"../checkpoints/_reward_hist_{args.tag}.npy", state["reward_hist"])
        os.remove(state_path)
        print(f"DONE: episode {state['episode']}/{args.episodes}. "
              f"Checkpoint saved to dqn_{args.tag}.pt")
    else:
        print(f"CONTINUE: episode {state['episode']}/{args.episodes} done so far, "
              f"run this script again with the same --tag to continue.")


if __name__ == "__main__":
    main()
