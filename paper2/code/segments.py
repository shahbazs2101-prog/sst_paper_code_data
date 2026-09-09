"""
segments.py
The five 600 s segments used throughout Section 2/5: normal operation, a
PV cloud-transient disturbance, a load-step disturbance, a segment that
pushes SOC toward both its limits, and the grid-disturbance segment (used
for every ride-through result in Section 5).

The manuscript specifies these at a descriptive level, not with exact
numeric disturbance parameters, so the specific magnitudes/timings below
are documented modeling choices consistent with the paper's own
qualitative description, not values quoted from the text.
"""
import numpy as np
from environment import pv_profile, load_profile, PV_RATED_KW, LOAD_MIN_KW, LOAD_MAX_KW


def make_normal():
    return pv_profile, load_profile


def make_pv_disturbance(dip_start=250.0, dip_depth=0.6, dip_duration=120.0):
    """PV cloud-transient: a temporary fractional dip in PV output."""
    def pv_fn(t, rng):
        base = pv_profile(t, rng)
        if dip_start <= t < dip_start + dip_duration:
            frac = 1.0 - dip_depth * np.sin(np.pi * (t - dip_start) / dip_duration)
            return base * frac
        return base
    return pv_fn, load_profile


def make_load_disturbance(step_start=250.0, step_size_kw=40.0, step_duration=150.0):
    """A step increase in load, held for step_duration then released."""
    def load_fn(t, rng):
        base = load_profile(t, rng)
        if step_start <= t < step_start + step_duration:
            return float(np.clip(base + step_size_kw, LOAD_MIN_KW, LOAD_MAX_KW + step_size_kw))
        return base
    return pv_profile, load_fn


def make_soc_boundary(transition_width=60.0):
    """First half: high PV / low load, pushing SOC toward its 90% ceiling.
    Second half: low PV / high load, pushing SOC toward its 20% floor.
    The transition is ramped over `transition_width` seconds (not an
    instant step) so PV and load never move in opposite directions at
    the same instant, which would otherwise transiently exceed the
    150 kVA aggregate rating regardless of dispatch."""
    def frac_second_half(t):
        return float(np.clip((t - (300.0 - transition_width / 2)) / transition_width, 0.0, 1.0))

    def pv_fn(t, rng):
        f = frac_second_half(t)
        target = PV_RATED_KW * (0.9 * (1 - f) + 0.1 * f)
        return float(np.clip(target + rng.normal(0, 2), 0, PV_RATED_KW))

    def load_fn(t, rng):
        f = frac_second_half(t)
        target = LOAD_MIN_KW * (1 - f) + LOAD_MAX_KW * f
        return float(np.clip(target + rng.normal(0, 2), LOAD_MIN_KW, LOAD_MAX_KW))
    return pv_fn, load_fn


def make_grid_disturbance(grid_event=None, baseline_deficit_kw=29.0):
    """Normal-ish PV/load but with a modest baseline net-import deficit
    (documented modeling choice: the paper's Table 2 reports a ~28.5-29.4
    kW pre-event BESS dispatch range for this segment, implying a
    non-zero baseline deficit rather than the ~0 mean used in 'normal'),
    plus a grid_event dict (t_start, duration, depth) applied via
    interface_physics."""
    def pv_fn(t, rng):
        return pv_profile(t, rng)

    def load_fn(t, rng):
        return float(np.clip(pv_profile(t, rng) + baseline_deficit_kw + rng.normal(0, 2),
                              LOAD_MIN_KW, LOAD_MAX_KW))
    return pv_fn, load_fn, grid_event


SEGMENT_ORDER = ["normal", "pv_disturbance", "load_disturbance", "soc_boundary", "grid_disturbance"]


def build_segment(name, seed_offset=0, grid_event=None):
    """Returns (pv_fn, load_fn, grid_event_or_None) for the named segment."""
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
