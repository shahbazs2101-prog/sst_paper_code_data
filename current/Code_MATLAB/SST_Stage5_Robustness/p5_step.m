function xn=p5_step(t,x,c)
% Zero-order event inputs at sample edges: no RK evaluation across event edges.
h=c.dt;
[k1,y1]=p5_kernel(t,x,c);
[k2,y2]=p5_kernel(t+h/2,x+h*k1/2,c);
[k3,y3]=p5_kernel(t+h/2,x+h*k2/2,c);
[k4,y4]=p5_kernel(t+h*(1-1e-9),x+h*k3,c);
xn=x+h*(k1+2*k2+2*k3+k4)/6;
xn(25)=max([x(25),y1(18),y2(18),y3(18),y4(18)]);
if x(25)>.5,xn(44)=x(44);else
 for ys={y1,y2,y3,y4}
  if ys{1}(18)>.5,xn(44)=ys{1}(43);break;end
 end
end
assert(all(xn(4:13)>0),'Energy below zero: reduce step and inspect model');
end
