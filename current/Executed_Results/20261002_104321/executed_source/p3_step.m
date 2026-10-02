function xn=p3_step(t,x,c)
% Zero-order event inputs at sample edges: no RK evaluation across event edges.
h=c.dt;
[k1,y1]=p3_kernel(t,x,c);
[k2,y2]=p3_kernel(t+h/2,x+h*k1/2,c);
[k3,y3]=p3_kernel(t+h/2,x+h*k2/2,c);
[k4,y4]=p3_kernel(t+h*(1-1e-9),x+h*k3,c);
xn=x+h*(k1+2*k2+2*k3+k4)/6;
xn(25)=max([x(25),y1(18),y2(18),y3(18),y4(18)]);
assert(all(xn(4:13)>0),'Energy below zero: reduce step and inspect model');
end
