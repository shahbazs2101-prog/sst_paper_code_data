function [dx,y]=p5_kernel(t,x,c)
% x: abc currents(1:3), nine MV energies(4:12), LV energy(13),
% energyPI(14), LVPI(15), reserved(16:24), trip(25), grid/load/loss
% energy integrals(26:28), PLL angle(29), PLL integral(30),
% current PI integrals(31:32), nine DAB actuator powers(33:41).
assert(all(isfinite(x)) && all(x(4:13)>0),'Invalid physical state');
dx=zeros(44,1);vm=sqrt(2*x(4:12)/c.Cmv);vl=sqrt(2*x(13)/c.Clv);
sag=t>=c.onset && t<c.onset+c.duration;vg=1-c.depth*double(sag);
trueAngle=c.w*t+c.phaseJump*double(t>=c.onset)+c.restorationPhase*double(t>=c.onset+c.duration);
a=x(29)+[0;-2*pi/3;2*pi/3];P=(2/3)*[cos(a)';-sin(a)'];
vgrid=c.Vgpk*vg*cos(trueAngle+[0;-2*pi/3;2*pi/3]);
i=x(1:3);idq=P*i;vdq=P*vgrid;
pllError=vdq(2)/max(c.Vgpk*vg,.1*c.Vgpk);
if vg>=.1
 omega=c.w+c.pllKp*pllError+x(30);dx(30)=c.pllKi*pllError;
else
 omega=c.w; % Declared holdover during unavailable voltage.
end
dx(29)=omega;
iRatio=norm(i)/(sqrt(1.5)*c.Ipk);
cause=double(vl<=c.lvFloor*c.Vlv)+2*double(c.isSST && any(vm<=c.mvFloor*c.Vmv))+4*double(iRatio>=c.currentTripMultiplier);
trip=x(25)>.5 || cause>0;if x(25)>.5,cause=x(44);end
wanted=zeros(2,1);used=zeros(2,1);utilization=0;headroom=0;
d=zeros(9,1);pd=0;pg=0;pc=0;modsat=false;satgrid=false;satdab=false;
demand=c.load+c.extra*double(t>=c.extraStart && t<c.extraStop);
loss=c.Rgrid*sum(i.^2);
if trip
 % Isolated grid and freewheel resistor: inductor energy is dissipated.
 dx(1:3)=-c.Rgrid/c.Lgrid*i;del=0;
else
 if c.isSST,e=sum(c.Cmv*c.Vmv^2/2-x(4:12));else,e=c.Clv*c.Vlv^2/2-x(13);end
 pcommand=demand+c.lossNominal+c.energyKp*e+x(14);
 iqref=-min(1,2*(1-vg))*c.Ipk;
 imax=sqrt(max(0,c.Ipk^2-iqref^2));
 if vdq(1)>.1*c.Vgpk,iraw=pcommand/(1.5*vdq(1));else,iraw=0;end
 idref=min(max(iraw,0),imax);satgrid=iraw>imax || vg<.1;
 wanted=[idref;iqref];used=wanted;
 if c.referenceTau>0
  change=(wanted-x(42:43))/c.referenceTau;
  rateLimit=c.Ipk/c.referenceTau;
  dx(42:43)=change*min(1,rateLimit/max(norm(change),eps));
  used=x(42:43);
 end
 err=used-idq;
 % Rectifier sign: L di/dt = vgrid - vconverter - R i.
 udq=vdq-c.Rgrid*idq+[omega*c.Lgrid*idq(2);-omega*c.Lgrid*idq(1)]-c.currentKp*err-x(31:32);
 raw=cos(a)*udq(1)-sin(a)*udq(2);
 if c.isSST
  lim=[sum(vm(1:3));sum(vm(4:6));sum(vm(7:9))];
  utilization=max(abs(raw)./lim);headroom=min(lim-abs(vgrid));
  u=min(max(raw,-lim),lim);modsat=any(abs(raw)>lim);
 else
  % Two-level VSC with common-mode injection, referred through ideal LFT.
  pole=raw-(max(raw)+min(raw))/2;lim=vl*c.turnRatioLFT/2;
  utilization=max(abs(pole))/lim;headroom=lim-(max(vgrid)-min(vgrid))/2;
  bounded=min(max(pole,-lim),lim);u=bounded-mean(bounded);
  modsat=any(abs(pole)>lim);
 end
 u=u-mean(u);dx(1:3)=(vgrid-u-c.Rgrid*i)/c.Lgrid;
 if ~modsat,dx(31:32)=c.currentKi*err;end
 if ~satgrid && ~modsat || e<0,dx(14)=c.energyKi*e;end
 pg=sum(vgrid.*i);pc=sum(u.*i);del=demand;
 if c.isSST
  K=c.n*vm*vl/(2*c.fs*c.Ldab);cap=K/4;
  ev=c.Vlv-vl;request=demand+c.lvKp*ev+x(15);
  total=min(max(request,0),sum(cap));
  rawP=total/9+c.balanceKp*(vm-mean(vm));
  lo=min(rawP-cap)-1;hi=max(rawP)+1;
  for j=1:40
   lambda=(lo+hi)/2;cmd=min(max(rawP-lambda,0),cap);
   if sum(cmd)>total,lo=lambda;else,hi=lambda;end
  end
  cmd=min(max(rawP-(lo+hi)/2,0),cap);
  powers=min(max(x(33:41),0),cap);pd=sum(powers);
  satdab=request>sum(cap) || request<0 || any(x(33:41)>cap);
  if ~satdab || request>sum(cap) && ev<0 || request<0 && ev>0,dx(15)=c.lvKi*ev;end
  dx(33:41)=(cmd-x(33:41))/c.tauDAB;
  phaseP=u.*i;
  input=[repmat(phaseP(1)/3,3,1);repmat(phaseP(2)/3,3,1);repmat(phaseP(3)/3,3,1)];
  dx(4:12)=input-powers;dx(13)=pd-del;
  d=(1-sqrt(max(0,1-4*powers./K)))/2;
 else
  dx(13)=pc-del;
 end
end
dx(26)=pg;dx(27)=del;dx(28)=loss;
E=sum(x(4:13))+c.Lgrid/2*sum(i.^2);
x0=p5_initial(c);E0=sum(x0(4:13))+c.Lgrid/2*sum(x0(1:3).^2);
res=E-E0-x(26)+x(27)+x(28);
phaseErr=atan2(sin(x(29)-trueAngle),cos(x(29)-trueAngle))*180/pi;
y=[vg;idq;vm;vl;pg;pd;del;demand-del;double(trip);double(satgrid);double(satdab);E;res;d;phaseErr;double(modsat);iRatio;loss;pc;wanted;used;utilization;headroom;cause];
end
