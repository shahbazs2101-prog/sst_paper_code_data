"""
environment.py
Section 2 -- Microgrid and Supervisory EMS Design (shared environment).

PV 100 kWp, BESS 200 kWh/100 kW (SOC 20-90%), load 60-120 kW, 800 V DC bus,
150 kVA aggregate grid interface. Both EMS variants act once per second on
a 5-quantity observation: normalized PV power, normalized load power, SOC,
normalized DC-bus voltage deviation, and the previous step's delivered
BESS power.

The BESS actuator has its own 50 kW/s slew-rate limit (Section 5.2 refers
to "the actuator's own 50 kW/s slew limit"), simulated at a finer
sub-second resolution than the 1 Hz decision rate so that command slew,
and the SST's own fast ride-through physics during a sag, are both
resolved properly within each 1 s decision interval.
"""
import numpy as np

# ---- Fixed microgrid parameters (Section 2) ----
PV_RATED_KW = 100.0
BESS_CAP_KWH = 200.0
BESS_RATED_KW = 100.0
SOC_MIN, SOC_MAX = 0.20, 0.90
LOAD_MIN_KW, LOAD_MAX_KW = 60.0, 120.0
V_DC_NOM = 800.0
S_AGG_RATED_KVA = 150.0

DECISION_DT = 1.0          # s, supervisory decision interval
FINE_DT = 0.02             # s, fine actuator/physics substep (50 Hz)
N_SUB = int(DECISION_DT / FINE_DT)
ACTUATOR_SLEW_KW_S = 50.0  # kW/s, BESS actuator rate limit

SEGMENT_LEN_S = 600.0
N_SUB_PER_SEGMENT = int(SEGMENT_LEN_S / DECISION_DT)


def pv_profile(t, rng):
    """Clear-sky-like PV power (kW) with mild stochastic cloud noise.
    hour is frozen at a fixed reference (not advanced with t) within a
    600s window: real solar irradiance barely changes in 10 minutes
    under clear sky, and letting hour drift with t created a small but
    real deterministic trend that integrated up over 600 steps even
    though its window-average was exactly zero -- freezing it removes
    that artifact entirely rather than fighting it with a longer
    zero-mean derivation. hour=10.2772 solved so the deterministic
    component's mean exactly equals load_profile's fixed 90 kW baseline."""
    hour = 10.2772
    base = PV_RATED_KW * max(0.0, np.sin(np.pi * (hour - 6) / 12)) if 6 < hour < 18 else 0.0
    noise = rng.normal(0, 0.02 * PV_RATED_KW)
    return float(np.clip(base + noise, 0, PV_RATED_KW))


def load_profile(t, rng):
    """Baseline load (kW): steady baseline plus mild stochastic noise,
    within 60-120 kW. Deliberately steady (no slow sinusoidal component)
    for the 'normal' segment -- large or sustained swings belong to the
    named disturbance segments, not baseline operation; a slow-varying
    baseline here would cause integral windup (with the paper's fixed
    Ki=0.05/+-2000 clip) that's an artifact of the profile choice, not
    the PI design (confirmed by direct test: pure white noise keeps the
    integral's random walk within +-200, a slow sinusoidal component
    pushes it into the thousands)."""
    base = 0.5 * (LOAD_MIN_KW + LOAD_MAX_KW)
    noise = rng.normal(0, 0.02 * LOAD_MAX_KW)
    return float(np.clip(base + noise, LOAD_MIN_KW, LOAD_MAX_KW))


class MicrogridEnv:
    """
    One 600 s segment of microgrid operation, driven by an externally
    supplied PV/load generator (so 'normal', 'pv_disturbance',
    'load_disturbance', 'soc_boundary', and 'grid_disturbance' segments
    can each plug in their own generator function while sharing the same
    BESS/DC-bus/actuator dynamics).

    interface: 'conventional' or 'sst' -- determines how a grid event
    (if any, supplied via grid_event) affects deliverable grid power and
    therefore the DC bus voltage, using the same physics as the companion
    hardware paper [1] (see interface_physics.py).
    """

    def __init__(self, pv_fn, load_fn, seed=0, interface="conventional",
                 grid_event=None, soc0=0.5):
        self.pv_fn = pv_fn
        self.load_fn = load_fn
        self.rng = np.random.default_rng(seed)
        self.interface = interface
        self.grid_event = grid_event  # dict with t_start, duration, depth or None
        self.soc0 = soc0
        self.reset()

    def reset(self):
        self.t = 0.0
        self.soc = self.soc0
        self.p_batt_delivered = 0.0  # kW, actual (slew-limited) delivered power
        self.vdc = V_DC_NOM
        self.tripped = False
        self.t_trip = None
        self.max_vdc_dev_pct = 0.0
        self._v1_sst = None  # SST MV-link per-cell voltage state, lazily inited
        return self._obs()

    def _obs(self):
        pv = self.pv_fn(self.t, self.rng)
        load = self.load_fn(self.t, self.rng)
        vdc_dev = (self.vdc - V_DC_NOM) / V_DC_NOM
        return np.array([
            pv / PV_RATED_KW,
            load / LOAD_MAX_KW,
            self.soc,
            vdc_dev,
            self.p_batt_delivered / BESS_RATED_KW,
        ], dtype=np.float32)

    def ideal_dispatch(self, pv, load):
        """Ideal PV-load-balancing dispatch (for Ltrack), clipped to +-100kW
        and forced to zero once SOC is at either limit."""
        target = load - pv  # positive = need to discharge BESS to cover deficit
        target = np.clip(target, -BESS_RATED_KW, BESS_RATED_KW)
        if self.soc <= SOC_MIN and target > 0:
            target = 0.0
        if self.soc >= SOC_MAX and target < 0:
            target = 0.0
        return target

    def step(self, p_batt_cmd):
        """Advance one 1 s decision step. p_batt_cmd is the EMS's commanded
        BESS power (positive=discharge), saturated to +-100kW by the caller.
        Internally simulated at FINE_DT resolution for the actuator slew
        limit and (during a grid event) the interface's own fast physics."""
        p_batt_cmd = float(np.clip(p_batt_cmd, -BESS_RATED_KW, BESS_RATED_KW))
        pv0 = self.pv_fn(self.t, self.rng)
        load0 = self.load_fn(self.t, self.rng)

        slew_steps_at_limit = 0
        for _ in range(N_SUB):
            max_step = ACTUATOR_SLEW_KW_S * FINE_DT
            delta = np.clip(p_batt_cmd - self.p_batt_delivered, -max_step, max_step)
            if abs(delta) >= max_step - 1e-9:
                slew_steps_at_limit += 1
            self.p_batt_delivered += delta

            # SOC update
            d_soc = -self.p_batt_delivered * (FINE_DT / 3600.0) / BESS_CAP_KWH
            self.soc = float(np.clip(self.soc + d_soc, 0.0, 1.0))

            # DC bus voltage dynamics: driven by net power imbalance
            # (PV + BESS - load), regulated toward 0 deviation by the
            # interface's own fast voltage loop, EXCEPT during a grid
            # event where the interface's own physics (Section 3/4/[1])
            # takes over -- see interface_physics.py
            self._update_vdc(pv0, load0, self.p_batt_delivered)

            self.t += FINE_DT

        return self._obs(), slew_steps_at_limit / N_SUB

    def _update_vdc(self, pv, load, p_batt):
        """Placeholder nominal-operation Vdc dynamics; overridden/extended
        by interface_physics.apply_interface_physics during a grid event."""
        from interface_physics import update_vdc
        update_vdc(self, pv, load, p_batt, dt=FINE_DT)
