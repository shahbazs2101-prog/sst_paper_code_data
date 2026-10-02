"""Voltage-dependent nonlinear DAB headroom and exact zero-sum projection."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent; N=9; C=.002; VR=3300.; D0=.35; DMIN=.1; DMAX=.5
K0=4*VR*800/(2*10000*.007207); P0=K0*D0*(1-D0); KP=82.9; KI=104.2

def project(raw,lo,hi):
    # Euclidean projection onto a box intersected with sum(correction)=0.
    if sum(lo)>0 or sum(hi)<0:raise ValueError('No zero-sum feasible command')
    left=np.min(raw-hi);right=np.max(raw-lo)
    for _ in range(45):
        mid=(left+right)/2;y=np.clip(raw-mid,lo,hi)
        if y.sum()>0:left=mid
        else:right=mid
    return np.clip(raw-(left+right)/2,lo,hi)

def run(seed=19,mismatch_pct=3,dt=.001,save=False):
    rng=np.random.default_rng(seed); mismatch=rng.uniform(-mismatch_pct/100,mismatch_pct/100,N)*P0;mismatch-=mismatch.mean()
    t=np.arange(0,8+dt/2,dt); E=np.full(N,.5*C*VR**2);integ=np.zeros(N);hist=[np.full(N,VR)];res=0.;dlo=1.;dhi=0.;satsteps=0
    for tt in t[1:]:
        v=np.sqrt(2*E/C);e=v-v.mean();raw=KP*e+KI*integ;K=K0*v/VR
        lo=K*DMIN*(1-DMIN)-P0;hi=K*DMAX*(1-DMAX)-P0
        corr=project(raw,lo,hi);d=(1-np.sqrt(np.maximum(0,1-4*(P0+corr)/K)))/2
        power=K*d*(1-d);res=max(res,abs(sum(power-P0)));dlo=min(dlo,min(d));dhi=max(dhi,max(d))
        bounded=(corr<=lo+1e-7)|(corr>=hi-1e-7);satsteps+=int(any(bounded))
        # Freeze integral only if its increment pushes further into a bound.
        freeze=((corr>=hi-1e-7)&(e>0))|((corr<=lo+1e-7)&(e<0));integ[~freeze]+=e[~freeze]*dt
        E+=(mismatch-(power-P0))*dt
        if np.any(E<=0):raise ValueError('Depleted link')
        hist.append(np.sqrt(2*E/C))
    hist=np.array(hist);dev=np.max(abs(hist/VR-1),axis=1)*100;bad=np.flatnonzero(dev>=.05);settle=float(t[bad[-1]+1]) if len(bad) and bad[-1]+1<len(t) else (0. if not len(bad) else None)
    out={'seed':seed,'mismatch_pct_before_centering':mismatch_pct,'centered_mismatch_W':mismatch.tolist(),'dt_s':dt,'peak_deviation_pct':float(max(dev)),'settling_below_0p05_s':settle,'final_max_deviation_pct':float(dev[-1]),'max_zero_sum_residual_W':float(res),'min_d':float(dlo),'max_d':float(dhi),'saturated_time_fraction':satsteps/(len(t)-1)}
    if save:
        np.savez(ROOT/'results/balancing_verified_waveform.npz',t=t,v=hist)
        plt.figure(figsize=(7.2,3.8))
        for i in range(N):plt.plot(t,(hist[:,i]/VR-1)*100,label=f'Cell {i+1}',lw=1)
        plt.axhline(.05,color='k',ls=':');plt.axhline(-.05,color='k',ls=':');plt.xlabel('Time (s)');plt.ylabel('Voltage deviation (%)');plt.legend(ncol=3,fontsize=7);plt.grid(alpha=.2);plt.tight_layout();plt.savefig(ROOT/'figures/balancing_verified.png',dpi=300);plt.close()
    return out

def main():
    base=run(save=True);rows=[base,run(19,3,.0005)]
    for magnitude in [3,10,20]:
        for seed in [7,19,42]:
            if magnitude==3 and seed==19:continue
            rows.append(run(seed,magnitude))
    out={'nominal_power_W':P0,'nominal_limits_W':[K0*DMIN*(1-DMIN)-P0,K0*.25-P0],'base':base,'sensitivity':rows}
    (ROOT/'results/balancing_verified.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
