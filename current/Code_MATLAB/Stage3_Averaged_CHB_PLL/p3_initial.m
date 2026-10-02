function x=p3_initial(c)
x=zeros(41,1);x(1:3)=c.idInitial*cos([0;-2*pi/3;2*pi/3]);
x(4:12)=c.Cmv*c.Vmv^2/2;x(13)=c.Clv*c.Vlv^2/2;
x(33:41)=c.load/9;
end
