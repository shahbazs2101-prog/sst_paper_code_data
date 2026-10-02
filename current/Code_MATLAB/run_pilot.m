function run_pilot
root=fileparts(mfilename('fullpath'));cd(root);addpath(root);
assert(license('test','Simulink'),'Simulink license required.');
if ~exist('results','dir'),mkdir('results');end
stamp=char(datetime('now','Format','yyyyMMdd_HHmmss'));
folder=fullfile(root,'results',stamp);mkdir(folder);
rawFolder=fullfile(root,'raw_results',stamp);mkdir(rawFolder);
diary(fullfile(folder,'execution_log.txt'));cleanup=onCleanup(@()diary('off'));
fprintf('Executed on %s with MATLAB %s\n',stamp,version);disp(ver);
model='SST_Coupled_Average_Pilot_v01';
if ~exist([model '.slx'],'file'),build_sst_pilot;end
architectures={'SST','LFT_ripple','LFT_matched'};
scenarios={'nominal','partial_sag','deep_sag','short_interruption','long_interruption','rated_interruption','coincident','cell_mismatch'};
rows={};
for a=1:numel(architectures)
 for s=1:numel(scenarios)
  for dt=[50e-6 25e-6]
   cfg=sst_config(architectures{a},scenarios{s},dt);
   in=Simulink.SimulationInput(model);in=in.setVariable('cfg',cfg,'Workspace',model);
   result=sim(in);ts=result.get('pilotSignals');
   t=ts.Time(:);Y=squeeze(ts.Data);
   if size(Y,1)~=numel(t),Y=Y';end
   assert(size(Y,2)==31,'Unexpected signal dimensions');
   label=sprintf('%s_%s_%dus',cfg.architecture,cfg.scenario,round(dt*1e6));
   save(fullfile(rawFolder,[label '.mat']),'cfg','t','Y');
   keep=unique([1:round(0.001/dt):numel(t),numel(t),find(diff(Y(:,18))~=0)',find(diff(Y(:,18))~=0)'+1]);
   fullT=t;fullY=Y;t=t(keep);Y=Y(keep,:);
   save(fullfile(folder,[label '.mat']),'cfg','t','Y');
   T=array2table([t,Y],'VariableNames',[{'time_s'},sst_columns]);
   writetable(T,fullfile(folder,[label '.csv']));
   t=fullT;Y=fullY;
   k=find(Y(:,18)>0.5,1);tripTime=NaN;if ~isempty(k),tripTime=t(k);end
   % Riemann sums use left-edge values, matching the implemented update.
   unmet=sum(Y(1:end-1,17).*diff(t));
   residual=max(abs(Y(:,22)));assert(residual<1e-5*max(cfg.Einit,1),'Energy balance fails');
   assert(all(Y(:,23:31)>=-1e-12,'all') && all(Y(:,23:31)<=0.5+1e-12,'all'),'DAB phase bound fails');
   after=t>=cfg.onset+cfg.duration+0.10;
   recoveryDeviation=max(abs(Y(after,13)/cfg.Vlv-1));
   rows(end+1,:)={cfg.architecture,cfg.scenario,dt,tripTime,min(Y(:,13)),unmet,residual,recoveryDeviation}; %#ok<AGROW>
   fprintf('%s: trip=%g s, min LV=%g V, energy residual=%g J\n',label,tripTime,min(Y(:,13)),residual);
  end
 end
end
summary=cell2table(rows,'VariableNames',{'architecture','scenario','step_s','trip_time_s','min_LV_V','unmet_J','max_energy_residual_J','post_recovery_max_deviation_pu'});
writetable(summary,fullfile(folder,'summary.csv'));
% Convergence flags are exported, not suppressed or treated as guaranteed passes.
convergence=summary(1:2:end,1:2);
convergence.min_LV_change_V=abs(summary.min_LV_V(1:2:end)-summary.min_LV_V(2:2:end));
convergence.unmet_change_J=abs(summary.unmet_J(1:2:end)-summary.unmet_J(2:2:end));
coarse=summary.trip_time_s(1:2:end);fine=summary.trip_time_s(2:2:end);
convergence.trip_status_agrees=isnan(coarse)==isnan(fine);
convergence.trip_time_change_s=abs(coarse-fine);
writetable(convergence,fullfile(folder,'convergence.csv'));
save(fullfile(folder,'summary.mat'),'summary','convergence');
plot_pilot(folder);
clear cleanup; % Close execution diary before archiving.
zip(fullfile(root,['SST_Pilot_Executed_' stamp '.zip']),folder);
fprintf('\nReturn SST_Pilot_Executed_%s.zip for review. No manuscript claims are automatically approved.\n',stamp);
end
