function xn=sst_step(t,x,c)
[dx,y]=sst_kernel(t,x,c);
xn=x+c.dt*dx;xn(24)=max(x(24),y(18));
assert(all(xn(3:12)>0),'Step crosses zero energy; reduce time step.');
end
