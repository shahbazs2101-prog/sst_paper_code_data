function p3_run
root=fileparts(mfilename('fullpath'));cd(root);addpath(root);
stamp=char(datetime('now','Format','yyyyMMdd_HHmmss'));
folder=fullfile(root,'results',stamp);mkdir(folder);
raw=fullfile(root,'raw_results',stamp);mkdir(raw);
diary(fullfile(folder,'execution_log.txt'));cleanup=onCleanup(@()diary('off'));
fprintf('Stage 3 MATLAB %s on %s\n',version,stamp);disp(ver);
% Preserve the actual source used with executed results, not just model outputs.
source=fullfile(folder,'executed_source');mkdir(source);files=dir(fullfile(root,'*.m'));
for k=1:numel(files),copyfile(fullfile(root,files(k).name),source);end
p3_check;
model='SST_Averaged_CHB_PLL_Stage3';
if ~exist([model '.slx'],'file'),p3_build;end
copyfile([model '.slx'],folder);
names=[{'grid_voltage_pu','id_A_peak','iq_A_peak'},arrayfun(@(k)sprintf('MV%d_V',k),1:9,'UniformOutput',false),...
 {'LV_V','grid_power_W','DAB_total_W','delivered_W','unmet_W','trip','grid_saturated','DAB_saturated','stored_energy_J','energy_residual_J'},...
 arrayfun(@(k)sprintf('DAB%d_phase_ratio',k),1:9,'UniformOutput',false),...
 {'PLL_error_deg','modulation_saturated','current_rating_ratio','filter_loss_W','converter_input_W'}];
architectures={'SST','LFT_ripple','LFT_matched'};
scenarios={'nominal','partial_sag','short_interruption','coincident','phase_step','high_load_interruption'};
rows={};
for a=1:3
 for s=1:numel(scenarios)
  for dt=[25e-6 12.5e-6]
   cfg=p3_config(architectures{a},scenarios{s},dt);
   in=Simulink.SimulationInput(model);in=in.setVariable('cfg',cfg,'Workspace',model);
   out=sim(in);ts=out.get('signals');t=ts.Time(:);Y=squeeze(ts.Data);
   if size(Y,1)~=numel(t),Y=Y';end
   assert(size(Y,2)==36 && all(isfinite(Y),'all'),'Invalid outputs');
   tag=sprintf('%s_%s_%gus',cfg.architecture,cfg.scenario,dt*1e6);
   save(fullfile(raw,[tag '.mat']),'cfg','t','Y');
   resid=max(abs(Y(:,22)));assert(resid<.05,'Energy residual exceeds 0.05 J: inspect model and step');
   assert(all(diff(Y(:,18))>=0),'Trip latch failed');
   k=find(Y(:,18)>.5,1);tripTime=NaN;if ~isempty(k),tripTime=t(k);end
   unmet=sum(Y(1:end-1,17).*diff(t));
   rows(end+1,:)={cfg.architecture,cfg.scenario,dt,tripTime,min(Y(:,13)),unmet,resid,max(abs(Y(:,32))),max(Y(:,34)),mean(Y(:,33)),mean(Y(:,20)),Y(end,13),mean(Y(end,4:12))}; %#ok<AGROW>
   keep=unique([1:round(.001/dt):numel(t),numel(t),find(diff(Y(:,18))~=0)',find(diff(Y(:,18))~=0)'+1]);
   t=t(keep);Y=Y(keep,:);
   save(fullfile(folder,[tag '.mat']),'cfg','t','Y');
   writetable(array2table([t,Y],'VariableNames',[{'time_s'},names]),fullfile(folder,[tag '.csv']));
   fprintf('%s: trip=%g, max residual=%g J\n',tag,tripTime,resid);
  end
 end
end
summary=cell2table(rows,'VariableNames',{'architecture','scenario','step_s','trip_time_s','min_LV_V','unmet_J','energy_residual_J','max_PLL_error_deg','max_current_rating_ratio','modulation_saturation_fraction','DAB_saturation_fraction','final_LV_V','final_mean_MV_V'});
writetable(summary,fullfile(folder,'summary.csv'));save(fullfile(folder,'summary.mat'),'summary');
clear cleanup;
zip(fullfile(root,['SST_Stage3_Executed_' stamp '.zip']),folder);
fprintf('Return SST_Stage3_Executed_%s.zip; retain raw_results.\n',stamp);
end
