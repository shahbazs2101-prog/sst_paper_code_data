"""Single source of truth for Paper 2 experiment settings."""
import numpy as np

PV_RATED_KW = 100.0
BESS_CAP_KWH = 200.0
BESS_RATED_KW = 100.0
SOC_MIN = 0.20
SOC_MAX = 0.90
LOAD_MIN_KW = 60.0
LOAD_MAX_KW = 120.0
V_DC_NOM = 800.0
S_AGG_RATED_KVA = 150.0

DECISION_DT = 1.0
FINE_DT = 0.02
ACTUATOR_SLEW_KW_S = 50.0
SEGMENT_LEN_S = 600.0
N_DECISION_STEPS = int(round(SEGMENT_LEN_S / DECISION_DT))
N_SUB = int(round(DECISION_DT / FINE_DT))

TABLE2_SEED = 7
TABLE2_EVENT = {"t_start": 300.0, "duration": 2.0, "depth": 1.0}

MC_SEED = 7
MC_N_TRIALS = 500
MC_DEPTH_RANGE = (0.10, 1.00)
MC_DURATION_RANGE = (0.05, 1.50)
MC_TSTART_RANGE = (200.0, 350.0)

# Table 5 is paired to Table 4: same 500 event draws and environment seeds.
TABLE5_SEED = MC_SEED
TABLE5_N_TRIALS = MC_N_TRIALS

TRAIN_SEED = 7
TRAIN_EPISODES = 260


def mc_draws(n_trials=MC_N_TRIALS, seed=MC_SEED):
    """Return the exact randomized event sequence used by Tables 4 and 5."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_trials):
        depth = float(rng.uniform(*MC_DEPTH_RANGE))
        duration = float(rng.uniform(*MC_DURATION_RANGE))
        t_start = float(rng.uniform(*MC_TSTART_RANGE))
        out.append({
            "trial": i,
            "depth": depth,
            "duration": duration,
            "t_start": t_start,
            "seed": 1000 + i,
        })
    return out
