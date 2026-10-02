function [dx,y]=sst_kernel(t,x,c)
% State: id iq nine MV energies LV energy gridPI LVPI nine reserved
% differential-integrator states trip latch grid-energy load-energy.
% Power-domain average model. Balanced ideal synchronous alignment.
assert(all(isfinite(x)) && all(x(3:12)>0),'Invalid energy state');
vm=sqrt(2*x(3:11)/c.Cmv);vl=sqrt(2*x(12)/c.Clv);
sag=t>=c.onset && t<c.onset+c.duration;
vg=1-c.depth*double(sag);
demand=c.load+c.extra*double(t>=c.extraStart && t<c.extraStop);
isSST=strcmp(c.architecture,'SST');
trip=x(24)>0.5 || vl<=c.lvFloor*c.Vlv || (isSST && any(vm<=c.mvFloor*c.Vmv));
dx=zeros(26,1);d=zeros(9,1);satdab=false;satgrid=false;
if trip
 pg=0;pd=0;del=0;dx(1:2)=-x(1:2)/c.tauCurrent;
else
 if isSST
  energyError=sum(c.Cmv*c.Vmv^2/2-x(3:11));
 else
  energyError=c.Clv*c.Vlv^2/2-x(12);
 end
 pcommand=demand+c.energyKp*energyError+x(13);
 iqref=-min(1,2*(1-vg))*c.Ipk;
 idmax=sqrt(max(0,c.Ipk^2-iqref^2));
 if vg>1e-9,idraw=pcommand/(1.5*c.Vgpk*vg);else,idraw=0;end
 idref=min(max(idraw,0),idmax);satgrid=idraw>idmax || vg==0;
 dx(1:2)=([idref;iqref]-x(1:2))/c.tauCurrent;
 % Current-circle limit applies to actual current, not only its reference.
 current=x(1:2);current=current*min(1,c.Ipk/max(norm(current),eps));
 pg=max(0,1.5*c.Vgpk*vg*current(1));
 if ~satgrid || energyError<0,dx(13)=c.energyKi*energyError;end
 del=demand;
 if isSST
  K=c.n*vm*vl/(2*c.fs*c.Ldab);
  pmax=K*c.dmax*(1-c.dmax);
  verror=c.Vlv-vl;
  requested=demand+c.lvKp*verror+x(14);
  total=min(max(requested,0),sum(pmax));
  satdab=requested>sum(pmax) || requested<0;
  if ~satdab || (requested>sum(pmax) && verror<0) || (requested<0 && verror>0)
   dx(14)=c.lvKi*verror;
  end
  % Project voltage-balancing request onto feasible per-cell powers
  % while preserving total delivered DAB power.
  raw=total/9+c.balanceKp*(vm-mean(vm));
  lo=min(raw-pmax)-1;hi=max(raw)+1;
  for j=1:55
   lambda=(lo+hi)/2;p=min(max(raw-lambda,0),pmax);
   if sum(p)>total,lo=lambda;else,hi=lambda;end
  end
  p=min(max(raw-(lo+hi)/2,0),pmax);pd=sum(p);
  d=(1-sqrt(max(0,1-4*p./K)))/2;
  dx(3:11)=pg/9-p;
  dx(12)=pd-del;
 else
  pd=0;dx(12)=pg-del;
 end
end
% Latched protection is committed by the discrete stepping function.
dx(25)=pg;dx(26)=del;
Etot=sum(x(3:12));E0=sum(sst_initial_energy(c));
residual=Etot-E0-x(25)+x(26);
y=[vg;x(1:2);vm;vl;pg;pd;del;demand-del;double(trip);double(satgrid);double(satdab);Etot;residual;d];
end
function e=sst_initial_energy(c)
e=[c.Cmv/2*(c.Vmv*(1+c.initialMismatch)).^2;c.Clv*c.Vlv^2/2];
end
