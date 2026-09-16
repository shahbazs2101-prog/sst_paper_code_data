"""Reproducible 600 s experiment segments for Paper 2."""
import numpy as np

from config import PV_RATED_KW, LOAD_MIN_KW, LOAD_MAX_KW, SEGMENT_LEN_S
from environment import MicrogridEnv


def pv_profile(t, rng):
    # Bounded synthetic operating profile used by the original repository.
    hour = (t % 600.0) / 600.0 * 24.0
    solar = max(0.0, np.sin(np.pi * (hour - 6.0) / 12.0))
    return float(np.clip(PV_RATED_KW * solar + rng.normal(0.0, 1.5), 0.0, PV_RATED_KW))


def load_profile(t, rng):
    hour = (t % 600.0) / 600.0 * 24.0
    daily = 12.0 * np.sin(2.0 * np.pi * (hour - 7.0) / 24.0)
    return float(np.clip(90.0 + daily + rng.normal(0.0, 2.0), LOAD_MIN_KW, LOAD_MAX_KW))


def make_normal():
    return pv_profile, load_profile


def make_pv_disturbance(dip_start=250.0, dip_depth=0.6, dip_duration=120.0):
    def pv_fn(t, rng):
        base = pv_profile(t, rng)
        if dip_start <= t < dip_start + dip_duration:
            frac = 1.0 - dip_depth * np.sin(np.pi * (t - dip_start) / dip_duration)
            return float(np.clip(base * frac, 0.0, PV_RATED_KW))
        return base
    return pv_fn, load_profile


def make_load_disturbance(step_start=250.0, step_size_kw=40.0, step_duration=150.0):
    def load_fn(t, rng):
        base = load_profile(t, rng)
        if step_start <= t < step_start + step_duration:
            return float(np.clip(base + step_size_kw, LOAD_MIN_KW, LOAD_MAX_KW))
        return base
    return pv_profile, load_fn


def make_soc_boundary(transition_width=60.0):
    def frac_second_half(t):
        return float(np.clip((t - (300.0 - transition_width / 2.0)) / transition_width, 0.0, 1.0))

    def pv_fn(t, rng):
        f = frac_second_half(t)
        target = PV_RATED_KW * (0.9 * (1.0 - f) + 0.1 * f)
        return float(np.clip(target + rng.normal(0.0, 2.0), 0.0, PV_RATED_KW))

    def load_fn(t, rng):
        f = frac_second_half(t)
        target = LOAD_MIN_KW * (1.0 - f) + LOAD_MAX_KW * f
        return float(np.clip(target + rng.normal(0.0, 2.0), LOAD_MIN_KW, LOAD_MAX_KW))
    return pv_fn, load_fn


def make_grid_disturbance(grid_event=None, baseline_deficit_kw=29.0):
    def pv_fn(t, rng):
        return pv_profile(t, rng)

    def load_fn(t, rng):
        # Keep the disturbance segment's baseline net-import deficit explicit.
        pv = pv_profile(t, rng)
        return float(np.clip(pv + baseline_deficit_kw + rng.normal(0.0, 2.0),
                             LOAD_MIN_KW, LOAD_MAX_KW))
    return pv_fn, load_fn, grid_event


SEGMENT_ORDER = ["normal", "pv_disturbance", "load_disturbance", "soc_boundary", "grid_disturbance"]


def build_segment(name, seed_offset=0, grid_event=None):
    if name == "normal":
        pv_fn, load_fn = make_normal()
        return pv_fn, load_fn, None
    if name == "pv_disturbance":
        pv_fn, load_fn = make_pv_disturbance()
        return pv_fn, load_fn, None
    if name == "load_disturbance":
        pv_fn, load_fn = make_load_disturbance()
        return pv_fn, load_fn, None
    if name == "soc_boundary":
        pv_fn, load_fn = make_soc_boundary()
        return pv_fn, load_fn, None
    if name == "grid_disturbance":
        pv_fn, load_fn, ge = make_grid_disturbance(grid_event)
        return pv_fn, load_fn, ge
    raise ValueError(name)
