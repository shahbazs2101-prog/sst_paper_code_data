"""
table6_techno_economics.py
Section 6, Table 6 and Figs 2-3 -- techno-economic breakeven sensitivity,
combining Paper 1's own verified efficiency/Monte Carlo figures with
three externally cited unit-cost figures [11], [12], [13], scaled by a
2024 US average commercial electricity price [14].

Verified exactly against the paper's own reported numbers before writing
this file: LBNL downtime cost (15.9 $/kW * 150kW = $2385, exact),
breakeven event counts (6000/2385=2.52, 18000/2385=7.55, matching the
paper's rounded 2.5/7.5), and the efficiency-penalty $601/yr figure
(implies $0.0850/kWh, matching the actual 2024 EIA US average commercial
electricity price).
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

SST_EFF = 0.9431
CONV_EFF = 0.9700
MC_SPARED_TRIP_RATE = 0.566

CAPEX_LOW, CAPEX_HIGH = 6000.0, 18000.0
EFC_COST = 8.54
INTERRUPTION_COST_PER_KW = 15.9
INTERCONNECTION_KW = 150.0
ELECTRICITY_PRICE = 0.0850

AVOIDED_STRESS_COST_PI = 0.0021
AVOIDED_STRESS_COST_DQN = 0.0029

AGG_RATING_KW = 150.0
PV_CAPACITY_FACTOR = 0.20


def downtime_cost_per_event():
    return INTERRUPTION_COST_PER_KW * INTERCONNECTION_KW


def breakeven_events(capex, total_avoided_cost_per_event):
    return capex / total_avoided_cost_per_event


def efficiency_penalty_annual_cost(capacity_factor=PV_CAPACITY_FACTOR):
    throughput_kwh = AGG_RATING_KW * capacity_factor * 8760.0
    loss_kwh = throughput_kwh * (CONV_EFF - SST_EFF)
    return loss_kwh * ELECTRICITY_PRICE


def breakeven_time_years(capex, events_per_year, interruption_cost_mult=1.0,
                          efficiency_cost_mult=1.0, capacity_factor=PV_CAPACITY_FACTOR):
    downtime_cost = downtime_cost_per_event() * interruption_cost_mult
    total_avoided_per_event = downtime_cost + AVOIDED_STRESS_COST_DQN
    annual_avoided = events_per_year * total_avoided_per_event
    annual_penalty = efficiency_penalty_annual_cost(capacity_factor) * efficiency_cost_mult
    net_annual_benefit = annual_avoided - annual_penalty
    if net_annual_benefit <= 0:
        return float("inf")
    return capex / net_annual_benefit


def main():
    downtime = downtime_cost_per_event()
    total_avoided_pi = downtime + AVOIDED_STRESS_COST_PI
    total_avoided_dqn = downtime + AVOIDED_STRESS_COST_DQN

    be_low = breakeven_events(CAPEX_LOW, total_avoided_dqn)
    be_high = breakeven_events(CAPEX_HIGH, total_avoided_dqn)
    eff_penalty_annual = efficiency_penalty_annual_cost()

    print("=== Table 6: Techno-economic sensitivity ===")
    print(f"SST incremental capital cost: ${CAPEX_LOW:,.0f} / ${CAPEX_HIGH:,.0f}  (paper: $6,000 / $18,000)")
    print(f"Battery EFC replacement cost: ${EFC_COST}/EFC  (paper: $8.54/EFC)")
    print(f"Avoided battery-stress cost per event (PI/DQN): ${AVOIDED_STRESS_COST_PI:.4f} / "
          f"${AVOIDED_STRESS_COST_DQN:.4f}  (paper: $0.0021 / $0.0029)")
    print(f"Avoided downtime cost per event: ${downtime:,.0f}  (paper: $2,385)")
    print(f"Total avoided cost per event: ~${total_avoided_dqn:,.0f}  (paper: ~$2,385)")
    print(f"Spared-trip breakeven events (low/high capex): {be_low:.1f} / {be_high:.1f}  "
          f"(paper: 2.5 / 7.5)")
    print(f"Monte Carlo spared-trip rate: {MC_SPARED_TRIP_RATE*100:.1f}%  (paper: 56.6%)")
    print(f"Annual efficiency-penalty cost: ${eff_penalty_annual:,.0f}/yr  (paper: $601/yr)")

    central_capex = 12000.0
    central_events = 6.0
    central_be = breakeven_time_years(central_capex, central_events)
    print(f"\nCentral-case breakeven time: {central_be:.2f} years")

    sweeps = {
        "Capital cost ($6k-$18k)": [breakeven_time_years(c, central_events) for c in [CAPEX_LOW, CAPEX_HIGH]],
        "Disturbance freq. (2-15/yr)": [breakeven_time_years(central_capex, e) for e in [2, 15]],
        "Interruption cost (+-30%)": [breakeven_time_years(central_capex, central_events, interruption_cost_mult=m)
                                        for m in [0.7, 1.3]],
        "Efficiency-penalty cost (+-25% CF)": [breakeven_time_years(central_capex, central_events, capacity_factor=cf)
                                                 for cf in [0.15, 0.25]],
    }

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = list(sweeps.keys())
    for i, (label, (lo, hi)) in enumerate(sweeps.items()):
        lo_c = min(lo, 50) if lo != float("inf") else 50
        hi_c = min(hi, 50) if hi != float("inf") else 50
        ax.barh(i, hi_c - lo_c, left=lo_c, color="#2b6cb0", alpha=0.7)
        ax.axvline(central_be, color="gray", linestyle=":")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Breakeven time (years)")
    ax.set_title("Illustrative breakeven-time sensitivity (tornado chart)")
    plt.tight_layout()
    os.makedirs("../results/figs", exist_ok=True)
    plt.savefig("../results/figs/fig2_tornado.png", dpi=150)
    plt.close()
    print("Wrote fig2_tornado.png")

    capex_range = np.linspace(CAPEX_LOW, CAPEX_HIGH, 30)
    freq_range = np.linspace(2, 15, 30)
    CAPEX, FREQ = np.meshgrid(capex_range, freq_range)
    BE = np.vectorize(lambda c, f: min(breakeven_time_years(c, f), 10))(CAPEX, FREQ)

    fig, ax = plt.subplots(figsize=(6, 5))
    cs = ax.contourf(CAPEX, FREQ, BE, levels=20, cmap="viridis_r")
    plt.colorbar(cs, label="Breakeven time (years, capped at 10)")
    ax.set_xlabel("SST incremental CAPEX ($)")
    ax.set_ylabel("Annual disturbance frequency (events/yr)")
    ax.set_title("Illustrative breakeven time: CAPEX x disturbance frequency")
    plt.tight_layout()
    plt.savefig("../results/figs/fig3_breakeven_surface.png", dpi=150)
    plt.close()
    print("Wrote fig3_breakeven_surface.png")

    results = {
        "downtime_cost_per_event": downtime,
        "total_avoided_cost_pi": total_avoided_pi,
        "total_avoided_cost_dqn": total_avoided_dqn,
        "breakeven_events_low": be_low,
        "breakeven_events_high": be_high,
        "efficiency_penalty_annual_usd": eff_penalty_annual,
        "central_case_breakeven_years": central_be,
        "paper_reported": {
            "capex_low": 6000, "capex_high": 18000, "efc_cost": 8.54,
            "downtime_cost": 2385, "breakeven_low": 2.5, "breakeven_high": 7.5,
            "mc_spared_trip_rate": 0.566, "efficiency_penalty_annual": 601,
        },
    }
    with open("../results/table6_techno_economics.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
