function selfcheck_pilot
% MATLAB-executed invariants, not predetermined disturbance outcomes.
for a={'SST','LFT_ripple','LFT_matched'}
 c=sst_config(a{1},'nominal',50e-6);x=sst_initial(c);
 for k=0:199
  [~,y]=sst_kernel(k*c.dt,x,c);
  assert(y(18)==0,'Nominal test trips');
  assert(abs(y(22))<1e-6,'Energy ledger mismatch');
  assert(abs(y(13)-800)<1e-6,'Nominal voltage is not an equilibrium');
  x=sst_step(k*c.dt,x,c);
 end
end
c=sst_config('SST','short_interruption');
assert(abs(c.usable/60000-0.45329625)<1e-10,'Capacitor-energy benchmark incorrect');
c=sst_config('SST','cell_mismatch');x=sst_initial(c);
[dx,y]=sst_kernel(0,x,c);
assert(abs(sum(dx(3:12))-y(14)+y(16))<1e-7,'Internal DAB power is not conserved');
assert(all(y(23:31)>=0 & y(23:31)<=0.5),'Phase inversion outside bounds');
fprintf('MATLAB pilot invariant checks passed.\n');
end
