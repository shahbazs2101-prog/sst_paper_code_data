"""
pi_controller.py
Section 2 -- PI baseline supervisory EMS.

Continuous controller: computes the instantaneous PV-load deficit,
applies PI gains (Kp=0.9, Ki=0.05) with a conditionally-clamped integral
(clipped to +-2000, updated only when doing so would not push an
already-saturated output further into saturation), adds an SOC-centering
trim (Ksoc=0.6) and a bus-voltage trim (Kv=0.4), saturates to +-100kW.
"""
import numpy as np
from environment import BESS_RATED_KW

KP = 0.9
KI = 0.05
K_SOC = 0.6
K_VDC = 0.4
INTEGRAL_CLIP = 2000.0
SOC_TARGET = 0.5


class PIController:
    def __init__(self):
        self.integral = 0.0

    def reset(self):
        self.integral = 0.0

    def act(self, obs):
        pv_pu, load_pu, soc, vdc_dev, prev_delivered_pu = obs
        pv = pv_pu * 100.0  # PV_RATED_KW
        load = load_pu * 120.0  # LOAD_MAX_KW (normalization base used in obs)
        prev_delivered = prev_delivered_pu * BESS_RATED_KW
        target = np.clip(load - pv, -BESS_RATED_KW, BESS_RATED_KW)
        # closed-loop tracking error (target vs what was actually delivered
        # last step, from the observation's own 5th quantity) -- NOT the
        # raw exogenous deficit itself, which never changes regardless of
        # tracking quality and would make the integral diverge unboundedly
        # for any sustained nonzero deficit (verified directly: using raw
        # deficit as the integrated signal saturates the integral at its
        # +-2000 clip within ~70 steps of a 29kW sustained deficit, well
        # before genuine tracking has a chance to matter).
        error = target - prev_delivered

        unsat = KP * error + KI * self.integral
        soc_trim = K_SOC * (soc - SOC_TARGET) * 100.0
        vdc_trim = -K_VDC * vdc_dev * 100.0
        p_cmd_unsat = unsat + soc_trim + vdc_trim
        p_cmd = float(np.clip(p_cmd_unsat, -BESS_RATED_KW, BESS_RATED_KW))

        saturating = p_cmd != p_cmd_unsat
        would_worsen = (saturating and (
            (p_cmd_unsat > BESS_RATED_KW and error > 0) or
            (p_cmd_unsat < -BESS_RATED_KW and error < 0)))
        if not would_worsen:
            self.integral = float(np.clip(self.integral + error, -INTEGRAL_CLIP, INTEGRAL_CLIP))

        return p_cmd
