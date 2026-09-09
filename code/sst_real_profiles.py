"""
sst_real_profiles.py
Section 6.5 -- loads (or, here, synthesizes a documented stand-in for) one
day of 1-minute GHI data and extracts cloud-transient event magnitudes for
sst_montecarlo.py to bootstrap-resample from.

IMPORTANT PROVENANCE NOTE: the paper cites real NREL SRRL BMS data
(20 Jan 2022, station "BMS", Golden CO). The real file lives at
https://midcdmz.nrel.gov/apps/data_api.pl?site=BMS&begin=20220120&end=20220120
but that host disallows automated fetching (robots.txt) and is outside this
environment's network allowlist, so it could not be downloaded here.

What follows is a SYNTHETIC clear-sky-plus-cloud-transients GHI trace built
to match the paper's own stated statistical description of that day (1-minute
resolution, a winter clear-sky envelope, ~14 identifiable fractional-deficit
cloud-transient events) -- NOT a copy of the real measurement file. If you
can retrieve the real CSV, drop it in ../data/nrel_srrl_bms_ghi_20220120.csv
with columns [minute, GHI_Wm2] and this script will use it in place of the
synthetic trace automatically.
"""
import os
import json
import numpy as np


REAL_DATA_PATH = "../data/nrel_srrl_bms_ghi_20220120.csv"


def clear_sky_ghi(minute_of_day, day_of_year=20, lat=39.74):
    """Simple clear-sky GHI envelope (cosine-of-zenith-ish model), scaled to
    a plausible winter Golden-CO peak (~450 W/m^2 in January)."""
    hour = minute_of_day / 60.0
    # solar noon ~12:00, daylight roughly 07:15-17:00 in January at this latitude
    sunrise, sunset = 7.25, 17.0
    if hour < sunrise or hour > sunset:
        return 0.0
    frac = (hour - sunrise) / (sunset - sunrise)
    shape = np.sin(np.pi * frac) ** 1.3
    return max(0.0, 460.0 * shape)


def synthesize_day(seed=20220120):
    """1440 minutes, clear-sky envelope with ~14 randomized cloud-transient
    dips (fractional deficits), matching the paper's disclosed event count."""
    rng = np.random.default_rng(seed)
    minutes = np.arange(1440)
    clear = np.array([clear_sky_ghi(m) for m in minutes])
    ghi = clear.copy()

    n_events = 14
    daylight_idx = np.where(clear > 20)[0]
    event_centers = rng.choice(daylight_idx, size=n_events, replace=False)
    event_centers.sort()
    event_fracs = []
    for c in event_centers:
        depth = rng.uniform(0.15, 0.75)  # fractional deficit at event peak
        width = rng.integers(3, 15)      # minutes
        for m in range(max(0, c - width), min(1440, c + width)):
            dist = abs(m - c) / width
            dip = depth * max(0.0, 1 - dist) * clear[m]
            ghi[m] = max(0.0, ghi[m] - dip)
        event_fracs.append(depth)
    return minutes, clear, ghi, np.array(event_fracs)


def load_or_synthesize():
    if os.path.exists(REAL_DATA_PATH):
        data = np.genfromtxt(REAL_DATA_PATH, delimiter=",", names=True)
        minutes = data["minute"]
        ghi = data["GHI_Wm2"]
        clear = np.array([clear_sky_ghi(m) for m in minutes])
        source = "real (loaded from data/)"
    else:
        minutes, clear, ghi, _ = synthesize_day()
        source = "SYNTHETIC STAND-IN (see module docstring)"
    return minutes, clear, ghi, source


def extract_event_fractions(minutes, clear, ghi, threshold=0.08):
    """Identify fractional-deficit cloud-transient events: contiguous runs
    where (clear-ghi)/clear exceeds `threshold` during daylight, return each
    event's peak fractional deficit."""
    deficit = np.where(clear > 20, (clear - ghi) / np.maximum(clear, 1e-6), 0.0)
    in_event = deficit > threshold
    events = []
    i = 0
    while i < len(in_event):
        if in_event[i]:
            j = i
            while j < len(in_event) and in_event[j]:
                j += 1
            events.append(float(np.max(deficit[i:j])))
            i = j
        else:
            i += 1
    return events


def main():
    minutes, clear, ghi, source = load_or_synthesize()
    events = extract_event_fractions(minutes, clear, ghi)
    print(f"Data source: {source}")
    if "SYNTHETIC" in source:
        print("*** WARNING: USING SYNTHETIC STAND-IN DATA, NOT THE REAL NREL "
              "MEASUREMENT FILE. Results from this run (and any Monte Carlo "
              "sweep built on it) do NOT reflect the real 20 Jan 2022 event "
              "population the manuscript describes. See this module's "
              "docstring for how to supply the real CSV. ***")
    print(f"Identified {len(events)} cloud-transient events (paper reports 14)")
    print(f"Event fractional-deficit magnitudes: {[f'{e:.2f}' for e in events]}")

    results = {
        "data_source": source,
        "n_events": len(events),
        "event_fractions": events,
        "paper_reported_n_events": 14,
    }
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_real_profiles_results.json", "w") as f:
        json.dump(results, f, indent=2)
    # save the trace itself for reuse by sst_montecarlo.py
    np.savez("../results/ghi_trace.npz", minutes=minutes, clear=clear, ghi=ghi,
             events=np.array(events))
    return events


if __name__ == "__main__":
    main()
