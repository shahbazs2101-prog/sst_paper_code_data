function c=p3_config(architecture,scenario,dt)
c.architecture=char(architecture);c.scenario=char(scenario);c.dt=dt;
c.stop=3;c.onset=0.4;c.duration=0.15;c.depth=1;c.load=60000;
c.extra=0;c.extraStart=.45;c.extraStop=.75;c.phaseJump=0;
c.Vmv=3300;c.Vlv=800;c.Cmv=.002;c.Clv=.002;
c.mvFloor=.85;c.lvFloor=.8;c.rating=150000;
c.n=4;c.fs=10000;c.Ldab=.007207;c.Lgrid=.051354;c.Rgrid=.53778;
c.w=2*pi*50;c.Vgpk=sqrt(2)*11000/sqrt(3);
c.Ipk=sqrt(2)*150000/(sqrt(3)*11000);c.currentTripMultiplier=1.25;
c.currentKp=c.Lgrid*2*pi*100;c.currentKi=c.Rgrid*2*pi*100;
c.pllKp=2*.707*2*pi*20;c.pllKi=(2*pi*20)^2;
c.energyKp=5;c.energyKi=10;c.lvKp=500;c.lvKi=25000;
c.balanceKp=82.9;c.tauDAB=.0002;c.turnRatioLFT=11000/415;
c.isSST=strcmp(c.architecture,'SST');
switch c.scenario
 case 'nominal',c.depth=0;
 case 'partial_sag',c.depth=.3;c.duration=.3;
 case 'short_interruption'
 case 'coincident',c.depth=.65;c.duration=.3;c.extra=20000;
 case 'phase_step',c.depth=0;c.phaseJump=15*pi/180;
 case 'high_load_interruption',c.load=140000;c.duration=.25;
 otherwise,error('Unknown scenario');
end
% Match TOTAL usable capacitor energy, including the SST LV ripple capacitor.
Euse=9*c.Cmv/2*c.Vmv^2*(1-c.mvFloor^2)+.002/2*c.Vlv^2*(1-c.lvFloor^2);
if strcmp(c.architecture,'LFT_matched'),c.Clv=2*Euse/(c.Vlv^2*(1-c.lvFloor^2));end
assert(any(strcmp(c.architecture,{'SST','LFT_ripple','LFT_matched'})));
c.idInitial=(c.Vgpk-sqrt(c.Vgpk^2-4*c.Rgrid*c.load/1.5))/(2*c.Rgrid);
assert(c.idInitial<=c.Ipk,'Initial demand cannot be supported at the current rating including filter losses');
c.lossNominal=1.5*c.Rgrid*c.idInitial^2;
end
