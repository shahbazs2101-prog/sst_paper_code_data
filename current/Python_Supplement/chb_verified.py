"""Ideal unipolar PSC CHB waveform check; no closed-loop rectifier claim."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import brentq
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
VLL=11000.; S=150000.; F=50.; FC=1000.; VDC=3300.; N=3
IR=S/(np.sqrt(3)*VLL); VP=VLL*np.sqrt(2/3); MA=VP/(N*VDC)
X=.02*VLL**2/S; L=X/(2*np.pi*F); R=X/30

def simulate(delta,sub=2000):
    dt=1/FC/sub; count=round(1/F/dt); t=np.arange(count)*dt
    w=2*np.pi*F; period=1/F; edges=[0.,period]
    def carrier(tt,k):return 4*abs(((tt*FC-k/(2*N))%1)-.5)-1
    for k in range(N):
        vertices=np.array([k/(2*N)/FC+j/(2*FC) for j in range(-3,45)])
        vertices=np.unique(np.r_[0,vertices[(vertices>0)&(vertices<period)],period])
        for sign in [1,-1]:
            def f(tt):return sign*MA*np.sin(w*tt+delta)-carrier(tt,k)
            for left,right in zip(vertices[:-1],vertices[1:]):
                if f(left)*f(right)<0:edges.append(brentq(f,left,right,xtol=1e-15))
    edges=np.unique(edges); mids=(edges[:-1]+edges[1:])/2; levels=np.zeros(len(mids))
    for k in range(N):
        c=np.array([carrier(tt,k) for tt in mids]);ref=MA*np.sin(w*mids+delta)
        levels+=VDC*((ref>c).astype(float)-(-ref>c).astype(float))
    def particular(tt,v):return v/R-VP*(R*np.sin(w*tt)-w*L*np.cos(w*tt))/(R**2+(w*L)**2)
    def march(initial):
        starts=[initial]
        for j,v in enumerate(levels):
            val=particular(edges[j+1],v)+(starts[-1]-particular(edges[j],v))*np.exp(-R*(edges[j+1]-edges[j])/L)
            starts.append(val)
        return np.array(starts)
    zero=march(0.);i0=zero[-1]/(1-np.exp(-R*period/L));starts=march(i0)
    inds=np.minimum(np.searchsorted(edges,t,side='right')-1,len(levels)-1);vs=levels[inds]
    current=particular(t,vs)+(starts[inds]-particular(edges[inds],vs))*np.exp(-R*(t-edges[inds])/L)
    vg=VP*np.sin(w*t)
    spec=np.abs(np.fft.rfft(current))*2/count/np.sqrt(2)
    tdd=np.sqrt(np.sum(spec[2:51]**2))/IR*100
    p=np.mean(vg*current)*3
    return dict(t=t,i=current,v_stack=vs,v_grid=vg,amp_rms=spec),dict(power_W=float(p),power_pct=float(p/S*100),current_rms_A=float(np.sqrt(np.mean(current**2))),TDD_pct=float(tdd),THD_all_sampled_pct=float(np.sqrt(np.sum(spec[2:]**2))/spec[1]*100),delta_rad=float(delta),sub=sub,dt_s=dt)

def main():
    lo,hi=0,.08
    for _ in range(25):
        mid=(lo+hi)/2; _,r=simulate(mid)
        if r['power_W']<S: lo=mid
        else: hi=mid
    delta=(lo+hi)/2; waves,base=simulate(delta)
    convergence=[simulate(delta,s)[1] for s in [1000,2000,4000]]
    out={'parameters':{'L_H':L,'R_ohm':R,'ma':MA,'rated_current_A':IR,'carrier_displacement_deg':60,'f_carrier_Hz':FC},'base':base,'fixed_angle_convergence':convergence,'voltage_levels':np.unique(waves['v_stack']).tolist(),'harmonic_definition':'RMS harmonics 2-50 divided by rated RMS demand current; no IEEE compliance claim'}
    (ROOT/'results').mkdir(exist_ok=True);(ROOT/'figures').mkdir(exist_ok=True)
    (ROOT/'results/chb_verified.json').write_text(json.dumps(out,indent=2));np.savez(ROOT/'results/chb_verified_waveform.npz',**waves)
    fig,ax=plt.subplots(2,1,figsize=(7.2,4.6))
    ax[0].plot(waves['t']*1000,waves['v_stack']/1000,lw=.6,label='Unipolar CHB stack');ax[0].plot(waves['t']*1000,waves['v_grid']/1000,lw=1,label='Grid');ax[0].set_ylabel('Voltage (kV)');ax[0].set_xlabel('Time (ms)');ax[0].legend(fontsize=8)
    ax[1].stem(np.arange(2,51),waves['amp_rms'][2:51]/IR*100,basefmt=' ');ax[1].set_xlabel('Harmonic order');ax[1].set_ylabel('Rated current (%)')
    for a in ax:a.grid(alpha=.2)
    fig.tight_layout();fig.savefig(ROOT/'figures/chb_verified.png',dpi=300);plt.close(fig);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
