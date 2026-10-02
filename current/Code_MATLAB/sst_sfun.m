function sst_sfun(block)
block.NumDialogPrms=1;block.NumInputPorts=0;block.NumOutputPorts=1;
block.SetPreCompPortInfoToDefaults;
block.OutputPort(1).Dimensions=31;
block.OutputPort(1).DatatypeID=0;block.OutputPort(1).Complexity='Real';
c=block.DialogPrm(1).Data;block.SampleTimes=[c.dt 0];
block.SimStateCompliance='DefaultSimState';
block.RegBlockMethod('PostPropagationSetup',@post);
block.RegBlockMethod('InitializeConditions',@init);
block.RegBlockMethod('Outputs',@outputs);
block.RegBlockMethod('Update',@update);
end
function post(b)
b.NumDworks=1;b.Dwork(1).Name='state';b.Dwork(1).Dimensions=26;
b.Dwork(1).DatatypeID=0;b.Dwork(1).Complexity='Real';b.Dwork(1).UsedAsDiscState=true;
end
function init(b)
b.Dwork(1).Data=sst_initial(b.DialogPrm(1).Data);
end
function outputs(b)
[~,y]=sst_kernel(b.CurrentTime,b.Dwork(1).Data,b.DialogPrm(1).Data);
b.OutputPort(1).Data=y;
end
function update(b)
b.Dwork(1).Data=sst_step(b.CurrentTime,b.Dwork(1).Data,b.DialogPrm(1).Data);
end
