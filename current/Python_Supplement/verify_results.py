"""Independent numerical checks of physical constraints and manuscript values."""
from pathlib import Path
import json
import numpy as np
import chb_verified as c
import balancing_verified as b
import reproduce as r
import sst_dab_model as d
root=Path(__file__).resolve().parent
assert abs(r.E_SST-27197.775)<1e-7
assert abs(r.C_MATCHED*.5*(800**2-640**2)-r.E_SST)<1e-8
assert abs(d.analytic_power(.35)-16667.12918)<.01
assert abs(d.switched_model_power(.35)[0]/d.analytic_power(.35)-1)<.002
for n in [9]:
    rng=np.random.default_rng(3)
    for _ in range(25):
        raw=rng.uniform(-30000,30000,n);lo=rng.uniform(-12000,-1000,n);hi=rng.uniform(100,2000,n)
        x=b.project(raw,lo,hi)
        assert max(abs(x.sum()),0)<1e-6
        assert np.all(x>=lo-1e-7) and np.all(x<=hi+1e-7)
        K=b.K0*np.ones(n);P=b.P0+x
        # Test inverse separately with valid nominal power limits.
        x=b.project(raw,np.full(n,b.K0*.1*.9-b.P0),np.full(n,b.K0*.25-b.P0));P=b.P0+x
        ds=(1-np.sqrt(1-4*P/K))/2
        assert np.all(ds>=.1-1e-9) and np.all(ds<=.5+1e-9)
        assert np.max(abs(K*ds*(1-ds)-P))<1e-8
waves,res=c.simulate(.02003024697303772)
assert np.array_equal(np.unique(waves['v_stack']),np.arange(-3,4)*3300)
assert abs(res['power_W']-150000)<.05
assert 7.70<res['THD_all_sampled_pct']<7.71
bal=np.load(root/'results/balancing_verified_waveform.npz');E=.5*.002*(bal['v']**2).sum(axis=1)
assert np.max(abs(E-E[0]))<1e-5
summary=json.loads((root/'results/interface_sensitivity.json').read_text())
assert all(x['paired_outcome_disagreements']==0 for x in summary['paired_seed_sensitivity'])
assert 112.34<summary['headroom_interruption'][-1]['sst_headroom_hold_ms']<112.36
print('PASS: energy matching, seven switching levels, power relation, phase inversion, box projection, aggregate energy and paired outcomes.')
