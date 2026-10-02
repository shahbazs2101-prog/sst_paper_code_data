"""Reproducible analyses for the revised SST manuscript.

The ride-through comparison is deliberately energy based.  The SST and the
energy-matched conventional interface use the same usable stored energy and
therefore have identical ideal hold-up capability.  This avoids attributing
stored-energy performance to converter topology.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "nrel_srrl_bms_ghi_20220120.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

P_RATED = 150_000.0
P_BASE = 60_000.0
V_MV = 3300.0
V_MV_MIN = 0.85 * V_MV
N_CELL = 9
C_CELL = 2000e-6
V_LV = 800.0
V_LV_MIN = 0.8 * V_LV
C_UNBUFFERED = 2e-3
E_SST = N_CELL * 0.5 * C_CELL * (V_MV**2 - V_MV_MIN**2)
C_MATCHED = 2 * E_SST / (V_LV**2 - V_LV_MIN**2)
E_UNBUFFERED = 0.5 * C_UNBUFFERED * (V_LV**2 - V_LV_MIN**2)


def read_ghi():
    with DATA.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    minute = np.array([float(r["minute"]) for r in rows])
    ghi = np.array([float(r["GHI_Wm2"]) for r in rows])
    return minute, ghi


def rolling_upper_envelope(x, half_window=45):
    """Local upper envelope used only to normalize measured cloud deficits."""
    out = np.zeros_like(x)
    for i in range(len(x)):
        lo, hi = max(0, i-half_window), min(len(x), i+half_window+1)
        out[i] = np.max(x[lo:hi])
    kernel = np.ones(21) / 21
    return np.convolve(out, kernel, mode="same")


def event_fractions(ghi):
    env = rolling_upper_envelope(ghi)
    deficit = np.zeros_like(ghi)
    np.divide(env-ghi, env, out=deficit, where=env > 50)
    deficit = np.where(env > 50, np.clip(deficit, 0, 1), 0)
    mask = deficit > 0.15
    events, i = [], 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i + 1
        while j < len(mask) and mask[j]:
            j += 1
        if j-i >= 2:
            events.append(float(deficit[i:j].max()))
        i = j
    return events, env, deficit


def deficit_energy(depth, duration, extra_kw=0.0):
    demand = P_BASE + 1000.0 * extra_kw
    vpu = 1.0-depth
    # Disclosed generic voltage-support sensitivity: reactive-current command
    # iq*=2(1-vpu) pu, clipped to the converter current circle.  The remaining
    # d-axis current determines active-power capability.  This is a study
    # assumption, not a claim of compliance with a particular national code.
    iq_pu = min(1.0, 2.0*depth)
    id_pu = np.sqrt(max(0.0, 1.0-iq_pu**2))
    available = vpu * id_pu * P_RATED
    return max(0.0, demand-available) * duration


def scenarios():
    cases = [
        ("30% sag, 150 ms", .30, .150),
        ("65% sag, 150 ms", .65, .150),
        ("Interruption, 150 ms", 1.0, .150),
        ("Interruption, 500 ms", 1.0, .500),
        ("Interruption, 1.2 s", 1.0, 1.200),
    ]
    rows = []
    for name, depth, duration in cases:
        e = deficit_energy(depth, duration)
        rows.append({
            "scenario": name, "deficit_energy_J": e,
            "unbuffered_trip": bool(e > E_UNBUFFERED),
            "sst_trip": bool(e > E_SST),
            "matched_conventional_trip": bool(e > E_SST),
            "sst_min_mv_pu_if_untripped":
                float(np.sqrt(max(V_MV_MIN**2, V_MV**2-2*e/(N_CELL*C_CELL)))/V_MV)
                if e <= E_SST else None,
        })
    return rows


def monte_carlo(events, n=500, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    events = np.asarray(events if events else [.25, .40, .60])
    for i in range(n):
        depth = rng.uniform(.10, 1.0)
        duration = rng.uniform(.05, 1.50)
        pv_kw = float(rng.choice(events)*40) if rng.random() < .70 else 0.0
        load_kw = float(rng.uniform(0, 25)) if rng.random() < .70 else 0.0
        e = deficit_energy(depth, duration, pv_kw+load_kw)
        rows.append({"trial": i, "depth": depth, "duration_s": duration,
                     "pv_deficit_kW": pv_kw, "load_pickup_kW": load_kw,
                     "deficit_energy_J": e,
                     "unbuffered_trip": bool(e > E_UNBUFFERED),
                     "sst_trip": bool(e > E_SST),
                     "matched_conventional_trip": bool(e > E_SST)})
    return rows


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    minute, ghi = read_ghi()
    events, env, deficit = event_fractions(ghi)
    sc = scenarios()
    mc = monte_carlo(events)
    summary = {
        "model": "energy-deficit integration with hard undervoltage trip",
        "grid_support_assumption": "iq_pu=min(1,2*sag_depth); id_pu=sqrt(1-iq_pu^2); Pmax=vpu*id_pu*Prated",
        "usable_sst_energy_J": E_SST,
        "matched_lv_capacitance_F": C_MATCHED,
        "unbuffered_energy_J": E_UNBUFFERED,
        "full_interruption_hold_up_s": E_SST/P_BASE,
        "source_label": {"endpoint": "https://midcdmz.nrel.gov/apps/data_api.pl",
                        "site": "BMS", "begin": "20220120", "end": "20220120",
                        "samples": len(ghi)},
        "supplied_trace_event_count": len(events),
        "event_definition": "at least 2 consecutive minutes >15% below a 91-minute local upper envelope",
        "scenarios": sc,
        "monte_carlo": {
            "seed": 7, "trials": len(mc),
            "unbuffered_trip_rate_pct": 100*sum(r["unbuffered_trip"] for r in mc)/len(mc),
            "sst_trip_rate_pct": 100*sum(r["sst_trip"] for r in mc)/len(mc),
            "matched_conventional_trip_rate_pct": 100*sum(r["matched_conventional_trip"] for r in mc)/len(mc),
        },
    }
    (RESULTS/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (RESULTS/"monte_carlo_trials.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mc[0]); w.writeheader(); w.writerows(mc)

    plt.figure(figsize=(7.2, 3.6))
    plt.plot(minute/60, ghi, lw=1, label="Supplied GHI")
    plt.plot(minute/60, env, lw=1, label="Local upper envelope")
    plt.xlabel("Hour of day"); plt.ylabel("GHI (W m$^{-2}$)")
    plt.xlim(0, 24); plt.grid(alpha=.25); plt.legend(frameon=False, ncol=2)
    plt.tight_layout(); plt.savefig(FIGURES/"nrel_ghi.png", dpi=240); plt.close()

    labels = ["Unbuffered\n2 mF", "SST MV links\n9 x 2 mF", "Matched LV\ncapacitance"]
    hold = [E_UNBUFFERED/P_BASE*1000, E_SST/P_BASE*1000, E_SST/P_BASE*1000]
    plt.figure(figsize=(6.4, 3.6)); bars=plt.bar(labels, hold, color=["#777777", "#1f4e79", "#5b9bd5"])
    plt.ylabel("Ideal 60 kW hold-up (ms)"); plt.grid(axis="y", alpha=.25)
    for b,v in zip(bars,hold): plt.text(b.get_x()+b.get_width()/2,v+8,f"{v:.1f}",ha="center")
    plt.ylim(0, 520); plt.tight_layout(); plt.savefig(FIGURES/"hold_up_comparison.png", dpi=240); plt.close()

    # Corrected 500 ms full-interruption figure: no post-depletion delivery.
    tt=np.linspace(0,0.55,1101); deficit=P_BASE*tt
    plt.figure(figsize=(7.2,4.4))
    ax=plt.subplot(2,1,1); ax.plot(tt*1000,deficit/1000,label='Cumulative deficit',color='#c55a11')
    ax.axhline(E_SST/1000,color='#1f4e79',label='SST and matched budget')
    ax.axhline(E_UNBUFFERED/1000,color='#777',label='2 mF budget')
    ax.axvline(E_SST/P_BASE*1000,color='#1f4e79',ls='--'); ax.set_ylabel('Energy (kJ)'); ax.grid(alpha=.25); ax.legend(frameon=False,ncol=2,fontsize=8)
    ax=plt.subplot(2,1,2); ax.step(tt*1000,(deficit<E_UNBUFFERED).astype(int),where='post',label='2 mF baseline',color='#777')
    ax.step(tt*1000,(deficit<E_SST).astype(int),where='post',label='SST',color='#1f4e79')
    ax.step(tt*1000,(deficit<E_SST).astype(int),where='post',label='Energy-matched',color='#5b9bd5',ls='--')
    ax.set_yticks([0,1],['tripped','regulating']); ax.set_xlabel('Interruption duration (ms)'); ax.grid(alpha=.25); ax.legend(frameon=False,ncol=3,fontsize=8)
    plt.tight_layout(); plt.savefig(FIGURES/'corrected_500ms_interruption.png',dpi=240); plt.close()

    # Trial-level plot consistent with the hard energy boundary.
    depth=np.array([r['depth'] for r in mc]); dur=np.array([r['duration_s'] for r in mc]);
    trip_u=np.array([r['unbuffered_trip'] for r in mc]); trip_s=np.array([r['sst_trip'] for r in mc])
    colors=np.where(trip_s,'#d62728',np.where(trip_u,'#ff8c33','#4daf4a'))
    margins=np.array([(E_SST-r['deficit_energy_J'])/1000 for r in mc])
    plt.figure(figsize=(8.0,3.7)); ax=plt.subplot(1,2,1)
    ax.scatter(dur,depth,c=colors,s=13,alpha=.75); ax.set_xlabel('Sag duration (s)'); ax.set_ylabel('Sag depth'); ax.grid(alpha=.2)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor='#4daf4a',label='neither trips'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#ff8c33',label='2 mF only'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#d62728',label='all energy-matched trip')],frameon=False,fontsize=8)
    ax=plt.subplot(1,2,2); ax.hist(margins,bins=28,color='#5b9bd5'); ax.axvline(0,color='k',ls='--'); ax.set_xlabel('Matched-buffer energy margin (kJ)'); ax.set_ylabel('Trial count'); ax.grid(alpha=.2)
    plt.tight_layout(); plt.savefig(FIGURES/'corrected_monte_carlo.png',dpi=240); plt.close()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
