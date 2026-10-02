function model=p5_build
model='SST_Robustness_Stage5';
if bdIsLoaded(model),close_system(model,0);end
assert(~exist([model '.slx'],'file'),'Preserve existing model: rename before rebuilding');
new_system(model);ws=get_param(model,'ModelWorkspace');assignin(ws,'cfg',p5_config('SST','nominal',25e-6));
add_block('simulink/User-Defined Functions/Level-2 MATLAB S-Function',[model '/Average circuits and controllers'],...
 'FunctionName','p5_sfun','Parameters','cfg','Position',[100 100 350 180]);
add_block('simulink/Sinks/To Workspace',[model '/Signals'],'VariableName','signals','SaveFormat','Timeseries','Position',[450 120 560 165]);
add_line(model,'Average circuits and controllers/1','Signals/1');
set_param(model,'Solver','FixedStepDiscrete','FixedStep','cfg.dt','StopTime','cfg.stop','ReturnWorkspaceOutputs','on');
a=Simulink.Annotation(model,'Three-phase RL plant, SRF PLL, PI current control, average converter voltage limits, nine MV links, DAB power actuators and LV regulation. No switching or physical Simscape wiring.');a.Position=[80 240];
save_system(model);close_system(model,0);
end
