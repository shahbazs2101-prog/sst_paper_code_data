"""
dqn.py
Section 2 -- DQN supervisory EMS: 21 discrete dispatch levels (-100 to
+100 kW, 10 kW apart), 64-64 MLP, target network synced every 250 steps,
replay buffer 20,000, epsilon-greedy 1.0->0.05, gamma=0.97, lr=1e-3,
batch=128, 260 episodes of 600s each, seed=7.

Reward: r = -(w1*Ltrack + w2*LSOC + w3*LVdc + w4*Lcost + w5*Llimit + w6*Lsmooth)
weights (1.0, 5.0, 0.5, 1.5, 2.0, 0.2).
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random

from environment import MicrogridEnv, BESS_RATED_KW, ACTUATOR_SLEW_KW_S, DECISION_DT
from segments import build_segment, SEGMENT_ORDER

ACTIONS_KW = np.arange(-100.0, 100.01, 10.0)  # 21 levels
N_ACTIONS = len(ACTIONS_KW)
N_OBS = 5

W = (1.0, 5.0, 0.5, 1.5, 2.0, 0.2)  # w1..w6
IMPORT_PRICE, EXPORT_PRICE, DEGRADATION_PRICE = 0.12, 0.06, 0.05


class QNet(nn.Module):
    def __init__(self, n_obs=N_OBS, n_actions=N_ACTIONS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_obs, 64), nn.ReLU(),
            nn.Linear(64, 64), nn.ReLU(),
            nn.Linear(64, n_actions),
        )

    def forward(self, x):
        return self.net(x)


class ReplayBuffer:
    def __init__(self, capacity=20000):
        self.buf = deque(maxlen=capacity)

    def push(self, s, a, r, s2, done):
        self.buf.append((s, a, r, s2, done))

    def sample(self, batch_size):
        batch = random.sample(self.buf, batch_size)
        s, a, r, s2, d = zip(*batch)
        return (np.array(s), np.array(a), np.array(r, dtype=np.float32),
                np.array(s2), np.array(d, dtype=np.float32))

    def __len__(self):
        return len(self.buf)


def compute_reward(env, obs, prev_cmd, cmd, pv, load):
    ideal = env.ideal_dispatch(pv, load)
    Ltrack = ((cmd - ideal) / BESS_RATED_KW) ** 2
    LSOC = 1.0 if (env.soc <= 0.20 or env.soc >= 0.90) else 0.0
    vdc_dev = (env.vdc - 800.0) / 800.0
    LVdc = vdc_dev ** 2
    net_import_kwh = (load - pv - cmd) * (DECISION_DT / 3600.0)
    cost = net_import_kwh * IMPORT_PRICE if net_import_kwh > 0 else net_import_kwh * EXPORT_PRICE
    cost += abs(cmd) * (DECISION_DT / 3600.0) * DEGRADATION_PRICE
    Lcost = cost
    max_feasible_step = ACTUATOR_SLEW_KW_S * DECISION_DT
    Llimit = 1.0 if abs(cmd - prev_cmd) > max_feasible_step else 0.0
    Lsmooth = ((cmd - prev_cmd) / BESS_RATED_KW) ** 2

    r = -(W[0] * Ltrack + W[1] * LSOC + W[2] * LVdc + W[3] * Lcost + W[4] * Llimit + W[5] * Lsmooth)
    return r


def train_dqn(seed=7, n_episodes=260, sst_aware=False, add_mv_link_obs=False,
              device="cpu", verbose=True, resume_state=None, episodes_this_call=None):
    """sst_aware: if True, grid_disturbance episodes draw a randomized MV
    sag and step through the SST's own fine-resolution physics (Section
    5.2). add_mv_link_obs: if True, appends a 6th observation (Section
    5.3), only meaningful together with interface='sst' at evaluation.

    resume_state: optional dict from a previous partial run (see
    get_state()/save_state below) to continue training from, so a full
    260-episode run can be split across multiple calls that each fit
    within this environment's per-call time limit.
    episodes_this_call: if set, stop after this many additional episodes
    (from wherever resume_state left off) rather than running all the
    way to n_episodes; returns updated state alongside (q, reward_hist).
    """
    n_obs = N_OBS + (1 if add_mv_link_obs else 0)

    if resume_state is None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
        rng = np.random.default_rng(seed)
        q = QNet(n_obs=n_obs)
        q_target = QNet(n_obs=n_obs)
        q_target.load_state_dict(q.state_dict())
        opt = optim.Adam(q.parameters(), lr=1e-3)
        buf = ReplayBuffer(20000)
        start_ep = 0
        eps = 1.0
        global_step = 0
        reward_hist = []
    else:
        q = QNet(n_obs=n_obs)
        q.load_state_dict(resume_state["q_state"])
        q_target = QNet(n_obs=n_obs)
        q_target.load_state_dict(resume_state["q_target_state"])
        opt = optim.Adam(q.parameters(), lr=1e-3)
        opt.load_state_dict(resume_state["opt_state"])
        buf = resume_state["buf"]
        rng = resume_state["rng"]
        start_ep = resume_state["episode"]
        eps = resume_state["eps"]
        global_step = resume_state["global_step"]
        reward_hist = resume_state["reward_hist"]
        torch.set_rng_state(resume_state["torch_rng_state"])
        random.setstate(resume_state["py_rng_state"])

    eps_end = 0.05
    eps_decay = (1.0 - eps_end) / n_episodes
    gamma = 0.97
    batch_size = 128
    target_sync_every = 250

    end_ep = n_episodes if episodes_this_call is None else min(n_episodes, start_ep + episodes_this_call)

    for ep in range(start_ep, end_ep):
        seg_name = SEGMENT_ORDER[ep % len(SEGMENT_ORDER)]
        grid_event = None
        interface_for_ep = "conventional"
        if seg_name == "grid_disturbance" and sst_aware:
            depth = rng.uniform(0.50, 1.00)
            duration = rng.uniform(0.1, 1.2)
            t_start = rng.uniform(200, 400)
            grid_event = {"t_start": t_start, "duration": duration, "depth": depth}
            interface_for_ep = "sst"

        pv_fn, load_fn, ge = build_segment(seg_name, grid_event=grid_event)
        env = MicrogridEnv(pv_fn, load_fn, seed=seed * 10000 + ep, interface=interface_for_ep,
                            grid_event=ge, soc0=0.5)
        obs = env.reset()
        if add_mv_link_obs:
            v1 = env._v1_sst if env._v1_sst is not None else 3300.0
            obs = np.concatenate([obs, [v1 / 3300.0 - 1.0]])

        prev_cmd = 0.0
        ep_reward = 0.0

        for step in range(600):
            if random.random() < eps:
                a_idx = random.randrange(N_ACTIONS)
            else:
                with torch.no_grad():
                    qvals = q(torch.tensor(obs, dtype=torch.float32).unsqueeze(0))
                    a_idx = int(torch.argmax(qvals).item())
            cmd = float(ACTIONS_KW[a_idx])

            pv = obs[0] * 100.0
            load = obs[1] * 120.0
            next_obs_raw, slew_frac = env.step(cmd)
            r = compute_reward(env, obs, prev_cmd, cmd, pv, load)

            next_obs = next_obs_raw
            if add_mv_link_obs:
                v1 = env._v1_sst if env._v1_sst is not None else 3300.0
                next_obs = np.concatenate([next_obs_raw, [v1 / 3300.0 - 1.0]])

            done = (step == 599)
            buf.push(obs, a_idx, r, next_obs, done)
            obs = next_obs
            prev_cmd = cmd
            ep_reward += r
            global_step += 1

            if len(buf) >= batch_size:
                s, a, rw, s2, d = buf.sample(batch_size)
                s_t = torch.tensor(s, dtype=torch.float32)
                a_t = torch.tensor(a, dtype=torch.long)
                r_t = torch.tensor(rw, dtype=torch.float32)
                s2_t = torch.tensor(s2, dtype=torch.float32)
                d_t = torch.tensor(d, dtype=torch.float32)

                qvals = q(s_t).gather(1, a_t.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    q_next = q_target(s2_t).max(1)[0]
                    target = r_t + gamma * q_next * (1 - d_t)
                loss = nn.functional.mse_loss(qvals, target)
                opt.zero_grad()
                loss.backward()
                opt.step()

            if global_step % target_sync_every == 0:
                q_target.load_state_dict(q.state_dict())

        reward_hist.append(ep_reward)
        eps = max(eps_end, eps - eps_decay)
        if verbose and (ep + 1) % 50 == 0:
            print(f"  episode {ep+1}/{n_episodes}, seg={seg_name}, "
                  f"reward={ep_reward:.2f}, eps={eps:.3f}")

    state = {
        "q_state": q.state_dict(), "q_target_state": q_target.state_dict(),
        "opt_state": opt.state_dict(), "buf": buf, "rng": rng,
        "episode": end_ep, "eps": eps, "global_step": global_step,
        "reward_hist": reward_hist,
        "torch_rng_state": torch.get_rng_state(), "py_rng_state": random.getstate(),
    }
    done_training = end_ep >= n_episodes
    return q, np.array(reward_hist), state, done_training
