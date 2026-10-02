function p3_sfun(b)
b.NumDialogPrms=1;b.NumInputPorts=0;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;
b.OutputPort(1).Dimensions=36;b.OutputPort(1).DatatypeID=0;b.OutputPort(1).Complexity='Real';
c=b.DialogPrm(1).Data;b.SampleTimes=[c.dt 0];b.SimStateCompliance='DefaultSimState';
b.RegBlockMethod('PostPropagationSetup',@post);b.RegBlockMethod('InitializeConditions',@init);
b.RegBlockMethod('Outputs',@outputs);b.RegBlockMethod('Update',@update);
end
function post(b)
b.NumDworks=1;b.Dwork(1).Name='state';b.Dwork(1).Dimensions=41;
b.Dwork(1).DatatypeID=0;b.Dwork(1).Complexity='Real';b.Dwork(1).UsedAsDiscState=true;
end
function init(b)
b.Dwork(1).Data=p3_initial(b.DialogPrm(1).Data);
end
function outputs(b)
[~,y]=p3_kernel(b.CurrentTime,b.Dwork(1).Data,b.DialogPrm(1).Data);b.OutputPort(1).Data=y;
end
function update(b)
b.Dwork(1).Data=p3_step(b.CurrentTime,b.Dwork(1).Data,b.DialogPrm(1).Data);
end
