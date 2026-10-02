function c = sst_config(architecture,scenario,dt)
% Declared pilot assumptions; gains are engineering starting values.
if nargin<3,dt=50e-6;end
c.architecture=char(architecture);c.scenario=char(scenario);c.dt=dt;
c.stop=1.8;c.onset=0.4;c.duration=0.15;c.depth=1;c.load=60000;
c.extra=0;c.extraStart=0.45;c.extraStop=0.75;
c.Vmv=3300;c.Vlv=800;c.Cmv=0.002;c.Cripple=0.002;
c.mvFloor=0.85;c.lvFloor=0.80;c.rating=150000;
c.n=4;c.fs=10000;c.Ldab=0.007207;c.dmax=0.5;
c.Ipk=sqrt(2)*150000/(sqrt(3)*11000);
c.Vgpk=sqrt(2)*11000/sqrt(3);
c.tauCurrent=0.002;c.energyKp=5;c.energyKi=10;
c.lvKp=500;c.lvKi=25000;c.balanceKp=82.9;
c.initialMismatch=zeros(9,1);
c.usable=9*c.Cmv/2*c.Vmv^2*(1-c.mvFloor^2);
c.Cmatch=2*c.usable/(c.Vlv^2*(1-c.lvFloor^2));
switch char(scenario)
 case 'nominal',c.depth=0;
 case 'partial_sag',c.depth=0.30;c.duration=0.30;
 case 'deep_sag',c.depth=0.65;c.duration=0.15;
 case 'short_interruption',c.duration=0.15;
 case 'long_interruption',c.duration=0.65;
 case 'rated_interruption',c.load=150000;c.duration=0.25;
 case 'coincident',c.depth=0.65;c.duration=0.30;c.extra=20000;
 case 'cell_mismatch',c.duration=0.15;c.initialMismatch=[-.01;0;.01;-.01;0;.01;-.01;0;.01];
 otherwise,error('Unknown scenario: %s',scenario);
end
switch c.architecture
 case 'SST',c.Clv=c.Cripple;
 case 'LFT_ripple',c.Clv=c.Cripple;
 case 'LFT_matched',c.Clv=c.Cmatch;
 otherwise,error('Unknown architecture');
end
c.Einit=9*c.Cmv*c.Vmv^2/2+c.Clv*c.Vlv^2/2;
end
