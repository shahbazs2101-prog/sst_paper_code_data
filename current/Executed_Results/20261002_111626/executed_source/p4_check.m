function p4_check
for a={'SST','LFT_ripple','LFT_matched'}
 c=p4_config(a{1},'nominal',25e-6);x=p4_initial(c);
 [dx,y]=p4_kernel(0,x,c);
 assert(numel(x)==44 && numel(y)==43);
 assert(abs(sum(dx(4:12)))<1e-5 && abs(dx(13))<1e-5,'Initial total DC power is not balanced');
 assert(abs(sum(dx(4:13))+c.Lgrid*sum(x(1:3).*dx(1:3))-y(14)+y(16)+y(35))<1e-7,'Instantaneous energy conservation fails');
 for k=0:399
  [~,y]=p4_kernel(k*c.dt,x,c);assert(y(18)==0,'Nominal protection trip');
  assert(abs(y(13)-800)<.01,'Nominal LV drift');
  assert(abs(y(22))<.01,'Energy ledger drift');x=p4_step(k*c.dt,x,c);
 end
end
fprintf('Stage 4 MATLAB initial equilibrium and energy checks passed.\n');
end
