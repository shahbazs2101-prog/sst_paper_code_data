"""
environment.py
Shared microgrid environment for Paper 2.

The environment samples PV/load once per decision interval and uses the
same samples for the observation, reward, and physical transition. This
avoids the previous inconsistency in which _obs() and step() drew different
random PV/load samples at the same simulation time.
"""
import numpy as np

PV_RATED_KW = 100.0
BESS_CAP_KWH = 200.0
BESS_RATED_KW = 100.0
SOC_MIN, SOC_MAX = 0.20, 0.90
LOAD_MIN_KW, LOAD_MAX_KW = 60.0, 120.0
V_DC_NOM = 800.0
S_AGG_RATED_KVA = 150.0

DECISION_DT = 1.0
FINE_DT = 0.02
N_SUB = int(round(DECISION_DT / FINE_DT))
ACTUATOR_SLEW_KW_S = 50.0
SEGMENT_LEN_S = 600.0
N_SUB_PER_SEGMENT = int(SEGMENT_LEN_S / DECISION_DT)


class MicrogridEnv:
    """One 600 s microgrid segment with deterministic per-step exogenous state."""

    def __init__(self, pv_fn, load_fn, seed=0, interface="conventional",
                 grid_event=None, soc0=0.5):
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

        # One exogenous sample for the current decision interval. The same
        # values are used by the observation and by the following transition.
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
        pv0 = self.pv_current
        load0 = self.load_current

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

        # Advance the exogenous state exactly once, after the physical
        # transition. The returned observation therefore belongs to the next
        # decision interval.
        self.pv_current = float(self.pv_fn(self.t, self.rng))
        self.load_current = float(self.load_fn(self.t, self.rng))
        return self._obs(), slew_steps_at_limit / N_SUB

    def _update_vdc(self, pv, load, p_batt):
        from interface_physics import update_vdc
        update_vdc(self, pv, load, p_batt, dt=FINE_DT)
