from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import sst_dab_model as d
ROOT=Path(__file__).resolve().parent; FIG=ROOT/'figures'
def diagram(labels,name,note):
    fig,ax=plt.subplots(figsize=(8,2.3));ax.set_xlim(0,1.04);ax.set_ylim(0,1);ax.axis('off')
    width=.175
    for j,label in enumerate(labels):
        x=.02+j*.20
        ax.add_patch(FancyBboxPatch((x,.38),width,.38,boxstyle='round,pad=.008',facecolor='#edf2f5',edgecolor='#334455'))
        ax.text(x+width/2,.57,label,ha='center',va='center',fontsize=9)
        if j<len(labels)-1:ax.annotate('',(x+.20,.57),(x+width,.57),arrowprops={'arrowstyle':'->'})
    ax.text(.5,.18,note,ha='center',va='center',fontsize=9)
    fig.tight_layout();fig.savefig(FIG/name,dpi=300);plt.close(fig)
diagram(['Voltage / power\nreference','Outer regulation\nconcept','Phase shift\nd = 2 delay / T','Ideal bridge\nswitching','Leakage current\npower check'],'dab_control_verified.png','Only the ideal bridge power check is executed; no closed-loop LV regulator is validated.')
diagram(['Cell voltages\ne = V - mean(V)','PI differential\npower request','Zero-sum box\nprojection','Nonlinear inverse\nP to phase shift','Cell energy\nupdate'],'balancing_controller_verified.png','Positive correction increases outgoing DAB power; bounds are updated from each cell voltage.')
Ts=1/d.fs;t=np.arange(4000)*Ts/4000;shift=.35*Ts/2
v1=np.where(t<Ts/2,d.V1,-d.V1);v2=np.where(((t-shift)%Ts)<Ts/2,d.n*d.V2,-d.n*d.V2)
i0=d.steady_state_iL0(.35,d.n*d.V2);i=i0+np.r_[0,np.cumsum(v1-v2)[:-1]]*(Ts/4000)/d.Lk
fig,ax=plt.subplots(2,1,figsize=(7.2,4));ax[0].plot(t*1e6,v1/1000,label='Primary');ax[0].plot(t*1e6,v2/1000,label='Secondary referred');ax[0].set_ylabel('Voltage (kV)');ax[0].legend(fontsize=8);ax[1].plot(t*1e6,i);ax[1].set_ylabel('Primary current (A)');ax[1].set_xlabel('Time (microseconds)')
for a in ax:a.grid(alpha=.2)
fig.tight_layout();fig.savefig(FIG/'dab_wave_verified.png',dpi=300);plt.close(fig)
ds=np.linspace(.1,.5,17);fig,ax=plt.subplots(figsize=(6.7,3.5));ax.plot(ds,[d.analytic_power(x)/1000 for x in ds],label='Analytical');ax.plot(ds,[d.switched_model_power(x)[0]/1000 for x in ds],'o',ms=4,label='Numerical switching');ax.set_xlabel('Half-period-normalized phase shift d');ax.set_ylabel('Power (kW)');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(FIG/'dab_power_verified.png',dpi=300);plt.close(fig)

fig,ax=plt.subplots(figsize=(8.5,2.6));ax.set_xlim(0,1.08);ax.set_ylim(0,1);ax.axis('off')
labels=['MV link\n3300 V','Primary bridge\nideal switches','Primary-referred\nLk = 7.207 mH','Transformer\nn = 4','Secondary bridge\nideal switches','LV bus\n800 V']
for j,label in enumerate(labels):
    x=.015+j*.175;ax.add_patch(FancyBboxPatch((x,.4),.15,.34,boxstyle='round,pad=.005',facecolor='#edf2f5',edgecolor='#334455'));ax.text(x+.075,.57,label,ha='center',va='center',fontsize=8.5)
    if j<5:ax.annotate('',(x+.175,.57),(x+.15,.57),arrowprops={'arrowstyle':'->'})
ax.text(.54,.18,'SPS secondary delay = dTs/2; 0.10 <= d <= 0.50. Device commutation is outside this ideal model.',ha='center',fontsize=9)
fig.tight_layout();fig.savefig(FIG/'dab_circuit_verified.png',dpi=300);plt.close(fig)
