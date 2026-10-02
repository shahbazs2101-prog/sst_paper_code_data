function run_refinement
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
scenarios={'rated_interruption','short_interruption','coincident','partial_sag'};
rows={};
for a=1:numel(architectures)
 for s=1:numel(scenarios)
  if strcmp(scenarios{s},'rated_interruption'),steps=12.5e-6;else,steps=25e-6;end
  for dt=steps
   cfg=sst_config(architectures{a},scenarios{s},dt);
   if ~strcmp(cfg.scenario,'rated_interruption'),cfg.stop=6;end
   in=Simulink.SimulationInput(model);in=in.setVariable('cfg',cfg,'Workspace',model);
   result=sim(in);ts=result.get('pilotSignals');
   t=ts.Time(:);Y=squeeze(ts.Data);
   if size(Y,1)~=numel(t),Y=Y';end
   assert(size(Y,2)==31,'Unexpected signal dimensions');
   label=sprintf('%s_%s_%gus',cfg.architecture,cfg.scenario,dt*1e6);
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
   finalLV=Y(end,13);finalMVmean=mean(Y(end,4:12));
   recovered=NaN;
   if isempty(k)
    ok=abs(Y(:,13)/cfg.Vlv-1)<=0.01;
    if strcmp(cfg.architecture,'SST'),ok=ok & all(abs(Y(:,4:12)/cfg.Vmv-1)<=0.01,2);end
    lastBad=find(~ok & t>=cfg.onset+cfg.duration,1,'last');
    if isempty(lastBad),recovered=0;elseif lastBad<numel(t),recovered=t(lastBad+1)-(cfg.onset+cfg.duration);end
   end
   rows(end+1,:)={cfg.architecture,cfg.scenario,dt,tripTime,min(Y(:,13)),unmet,residual,recoveryDeviation,finalLV,finalMVmean,recovered}; %#ok<AGROW>
   fprintf('%s: trip=%g s, min LV=%g V, energy residual=%g J\n',label,tripTime,min(Y(:,13)),residual);
  end
 end
end
summary=cell2table(rows,'VariableNames',{'architecture','scenario','step_s','trip_time_s','min_LV_V','unmet_J','max_energy_residual_J','post_recovery_max_deviation_pu','final_LV_V','final_MV_mean_V','recovery_within_1pct_s'});
writetable(summary,fullfile(folder,'summary.csv'));
save(fullfile(folder,'summary.mat'),'summary');
plot_refinement(folder);
clear cleanup; % Close execution diary before archiving.
zip(fullfile(root,['SST_Refinement_Executed_' stamp '.zip']),folder);
fprintf('\nReturn SST_Refinement_Executed_%s.zip for review. No manuscript claims are automatically approved.\n',stamp);
end
