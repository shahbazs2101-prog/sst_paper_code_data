"""Conditional headroom-limited interruption and paired sensitivity analysis."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib.pyplot as plt
import reproduce as r
ROOT=Path(__file__).resolve().parent
PMAX0=9*4*3300*800/(2*10000*.007207)*.25

def headroom():
    rows=[]
    for kw in [60,90,120,140,150]:
        floor=max(.85,kw*1000/PMAX0);energy=r.E_SST if floor==.85 else 9*.5*.002*3300**2*(1-floor**2)
        rows.append({'deficit_kW':kw,'sst_effective_floor_pu':floor,'energy_only_hold_ms':r.E_SST/(kw*1000)*1000,'sst_headroom_hold_ms':energy/(kw*1000)*1000,'matched_ideal_hold_ms':r.E_SST/(kw*1000)*1000})
    return rows

def main():
    _,ghi=r.read_ghi();events,_,_=r.event_fractions(ghi);rows=[]
    for seed in [7,19,42]:
        trials=r.monte_carlo(events,500,seed)
        rows.append({'seed':seed,'unbuffered_trips':sum(x['unbuffered_trip'] for x in trials),'sst_trips':sum(x['sst_trip'] for x in trials),'matched_trips':sum(x['matched_conventional_trip'] for x in trials),'paired_outcome_disagreements':sum(x['sst_trip']!=x['matched_conventional_trip'] for x in trials)})
    # Reuse seed-7 inputs, varying usable energy rather than resampling disturbances.
    trials=r.monte_carlo(events);energy_sweep=[]
    for factor in [.5,.75,1,1.25,1.5]:
        trips=sum(x['deficit_energy_J']>factor*r.E_SST for x in trials)
        energy_sweep.append({'energy_factor':factor,'trips_of_500':trips})
    h=headroom();out={'nominal_aggregate_DAB_max_W':PMAX0,'headroom_interruption':h,'paired_seed_sensitivity':rows,'energy_sweep':energy_sweep}
    (ROOT/'results/interface_sensitivity.json').write_text(json.dumps(out,indent=2,default=lambda x:x.item()))
    fig,ax=plt.subplots(1,2,figsize=(8,3.7));ax[0].plot([x['deficit_kW'] for x in h],[x['energy_only_hold_ms'] for x in h],'o-',label='Energy-only matched');ax[0].plot([x['deficit_kW'] for x in h],[x['sst_headroom_hold_ms'] for x in h],'s--',label='SST with DAB headroom');ax[0].set_xlabel('Constant deficit (kW)');ax[0].set_ylabel('Hold-up (ms)');ax[0].legend(fontsize=8)
    ax[1].plot([x['energy_factor'] for x in energy_sweep],[x['trips_of_500']/5 for x in energy_sweep],'o-');ax[1].set_xlabel('Usable energy / nominal energy');ax[1].set_ylabel('Conditional trips (%)')
    for a in ax:a.grid(alpha=.2)
    fig.tight_layout();fig.savefig(ROOT/'figures/interface_sensitivity.png',dpi=300);plt.close(fig);print(json.dumps(out,indent=2,default=lambda x:x.item()))
if __name__=='__main__':main()
