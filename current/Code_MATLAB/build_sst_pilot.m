function model=build_sst_pilot
model='SST_Coupled_Average_Pilot_v01';
if bdIsLoaded(model),close_system(model,0);end
if exist([model '.slx'],'file'),error('Model exists; rename it before rebuilding to preserve edits.');end
new_system(model);
% Block parameters are evaluated during add_block. Seed the model workspace first.
modelWorkspace=get_param(model,'ModelWorkspace');
assignin(modelWorkspace,'cfg',sst_config('SST','nominal',50e-6));
add_block('simulink/User-Defined Functions/Level-2 MATLAB S-Function',[model '/Coupled plant and controllers'],...
 'FunctionName','sst_sfun','Parameters','cfg','Position',[100 90 340 180]);
add_block('simulink/Sinks/To Workspace',[model '/Recorded signals'],'VariableName','pilotSignals',...
 'SaveFormat','Timeseries','Position',[430 110 565 155]);
add_line(model,'Coupled plant and controllers/1','Recorded signals/1');
set_param(model,'Solver','FixedStepDiscrete','FixedStep','cfg.dt','StopTime','cfg.stop',...
 'ReturnWorkspaceOutputs','on');
annotation=Simulink.Annotation(model,['Average power-domain coupled pilot. Nine MV energy states, LV capacitor, ' ...
 'finite-bandwidth dq current actuator, PI energy and LV regulation, DAB SPS limits, balancing and latched protection. ' ...
 'Ideal grid angle; no switching, PLL, network unbalance, losses or physical CHB modulation.']);
annotation.Position=[80 230];
save_system(model);close_system(model,0);
end
