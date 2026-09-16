"""Shared microgrid environment for Paper 2.

PV/load are sampled once per 1 s decision interval. The same realization is
used for the observation and for the physical transition/reward inputs.
"""
import numpy as np
from config import (PV_RATED_KW, BESS_CAP_KWH, BESS_RATED_KW, SOC_MIN, SOC_MAX,
                    LOAD_MIN_KW, LOAD_MAX_KW, V_DC_NOM, S_AGG_RATED_KVA,
                    DECISION_DT, FINE_DT, ACTUATOR_SLEW_KW_S, SEGMENT_LEN_S,
                    N_SUB)


def pv_profile(t, rng):
    hour = 10.2772
    base = PV_RATED_KW * max(0.0, np.sin(np.pi * (hour - 6) / 12)) if 6 < hour < 18 else 0.0
    noise = rng.normal(0, 0.02 * PV_RATED_KW)
    return float(np.clip(base + noise, 0, PV_RATED_KW))


def load_profile(t, rng):
    base = 0.5 * (LOAD_MIN_KW + LOAD_MAX_KW)
    noise = rng.normal(0, 0.02 * LOAD_MAX_KW)
    return float(np.clip(base + noise, LOAD_MIN_KW, LOAD_MAX_KW))


class MicrogridEnv:
    """One 600 s segment with deterministic exogenous state per decision step."""

    def __init__(self, pv_fn, load_fn, seed=0, interface="conventional", grid_event=None, soc0=0.5):
        self.pv_fn = pv_fn
        self.load_fn = load_fn
        self.rng = np.random.default_rng(seed)
        self.interface = interface
        self.grid_event = grid_event
        self.soc0 = soc0
        self.reset()

    def reset(self):
        self.t = 0.0
        self.soc = self.soc0
        self.p_batt_delivered = 0.0
        self.vdc = V_DC_NOM
        self.tripped = False
        self.t_trip = None
        self.max_vdc_dev_pct = 0.0
        self._v1_sst = None
        # Draw exactly one realization for interval [0, 1 s).
        self.pv_current = float(self.pv_fn(self.t, self.rng))
        self.load_current = float(self.load_fn(self.t, self.rng))
        return self._obs()

    def _obs(self):
        vdc_dev = (self.vdc - V_DC_NOM) / V_DC_NOM
        return np.array([
            self.pv_current / PV_RATED_KW,
            self.load_current / LOAD_MAX_KW,
            self.soc,
            vdc_dev,
            self.p_batt_delivered / BESS_RATED_KW,
        ], dtype=np.float32)

    def ideal_dispatch(self, pv, load):
        target = np.clip(load - pv, -BESS_RATED_KW, BESS_RATED_KW)
        if self.soc <= SOC_MIN and target > 0:
            target = 0.0
        if self.soc >= SOC_MAX and target < 0:
            target = 0.0
        return target

    def step(self, p_batt_cmd):
        p_batt_cmd = float(np.clip(p_batt_cmd, -BESS_RATED_KW, BESS_RATED_KW))
        pv0, load0 = self.pv_current, self.load_current
        slew_steps_at_limit = 0
        for _ in range(N_SUB):
            max_step = ACTUATOR_SLEW_KW_S * FINE_DT
            delta_requested = p_batt_cmd - self.p_batt_delivered
            delta = np.clip(delta_requested, -max_step, max_step)
            if abs(delta_requested) > max_step + 1e-12:
                slew_steps_at_limit += 1
            self.p_batt_delivered += delta
            d_soc = -self.p_batt_delivered * (FINE_DT / 3600.0) / BESS_CAP_KWH
            self.soc = float(np.clip(self.soc + d_soc, 0.0, 1.0))
            self._update_vdc(pv0, load0, self.p_batt_delivered)
            self.t += FINE_DT

        # Draw exactly one new realization for the next decision interval.
        self.pv_current = float(self.pv_fn(self.t, self.rng))
        self.load_current = float(self.load_fn(self.t, self.rng))
        return self._obs(), slew_steps_at_limit / N_SUB

    def _update_vdc(self, pv, load, p_batt):
        from interface_physics import update_vdc
        update_vdc(self, pv, load, p_batt, dt=FINE_DT)
