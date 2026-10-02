function x=sst_initial(c)
x=zeros(26,1);
x(1)=c.load/(1.5*c.Vgpk);
x(3:11)=c.Cmv/2*(c.Vmv*(1+c.initialMismatch)).^2;
x(12)=c.Clv*c.Vlv^2/2;
end
