"""Common event-window metrics used by Tables 4 and 5."""
import numpy as np


def event_mask(times, t_start, duration):
    times = np.asarray(times, dtype=float)
    return (times >= t_start) & (times < t_start + duration)


def compute_event_metrics(times, cmds, t_start, duration, actuator_limit_kw_s=50.0):
    """Compute command metrics only over the defined disturbance interval.

    Throughput uses command samples whose decision interval starts inside the
    event. Slew is computed from command transitions whose end point lies
    inside the event. This definition is shared by Tables 4 and 5.
    """
    times = np.asarray(times, dtype=float)
    cmds = np.asarray(cmds, dtype=float)
    if len(cmds) < 2:
        return {"throughput_kwh": 0.0, "mean_slew": 0.0,
                "time_at_limit": 0.0}

    m_cmd = event_mask(times, t_start, duration)
    throughput_kwh = float(np.sum(np.abs(cmds[m_cmd])) / 3600.0)

    transition_times = times[1:]
    m_slew = event_mask(transition_times, t_start, duration)
    slew = np.abs(np.diff(cmds))[m_slew]
    mean_slew = float(np.mean(slew)) if len(slew) else 0.0
    time_at_limit = float(np.mean(slew >= actuator_limit_kw_s)) if len(slew) else 0.0

    return {
        "throughput_kwh": throughput_kwh,
        "mean_slew": mean_slew,
        "time_at_limit": time_at_limit,
    }
