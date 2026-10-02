function AUDIT_STAGE6_RAW
% Read-only audit of Stage 6 full-step MAT records; does not simulate.
here=fileparts(mfilename('fullpath'));
raw=uigetdir(pwd,'Select raw_results or its timestamp subfolder');
if isequal(raw,0),return;end
expected=readtable(fullfile(here,'expected_stage6_summary.csv'),'TextType','string');
files=dir(fullfile(raw,'**','*.mat'));
folder=fullfile(here,['Raw_Audit_' char(datetime('now','Format','yyyyMMdd_HHmmss'))]);mkdir(folder);
rows=cell(numel(files),10);keys=strings(numel(files),1);allOK=true;
for j=1:numel(files)
 name=files(j).name;path=fullfile(files(j).folder,name);
 ok=false;message="";sha="";n=0;trip=NaN;cause=NaN;delta=NaN;
 try
  fid=fopen(path,'rb');assert(fid>=0,'Cannot open file');b=fread(fid,Inf,'*uint8');fclose(fid);
  md=java.security.MessageDigest.getInstance('SHA-256');md.update(b);sha=string(lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[])));clear b
  D=load(path,'cfg','t','Y');c=D.cfg;t=D.t(:);Y=D.Y;n=numel(t);
  assert(size(Y,1)==n && size(Y,2)==43,'Invalid array dimensions');
  assert(all(isfinite(t)) && all(isfinite(Y),'all'),'Nonfinite data');
  assert(n==round(c.stop/c.dt)+1,'Not a complete full-step record');
  assert(abs(t(1))<1e-10 && abs(t(end)-c.stop)<1e-9,'Wrong time endpoints');
  assert(all(diff(t)>0) && max(abs(diff(t)-c.dt))<1e-10,'Nonuniform or incorrect time step');
  assert(all(ismember(Y(:,18),[0 1])) && all(diff(Y(:,18))>=0),'Invalid trip latch');
  k=find(Y(:,18)>.5,1);cause=0;if ~isempty(k),trip=t(k);cause=Y(k,43);end
  if ~isempty(k),assert(all(abs(Y(k:end,16))<1e-8),'Delivered load after trip');end
  keys(j)=string(sprintf('%s_%s_%s_%gus',c.architecture,c.caseId,c.variant,c.dt*1e6));
  e=expected(expected.architecture==string(c.architecture) & expected.scenario==string(c.caseId) & expected.variant==string(c.variant) & abs(expected.step_s-c.dt)<1e-12,:);
  assert(height(e)==1,'Missing or duplicate expected summary row');
  assert((isnan(trip)&&isnan(e.trip_time_s)) || abs(trip-e.trip_time_s)<1e-10,'Trip time mismatch');
  assert(cause==e.trip_cause_mask,'Trip cause mismatch');
  sag=t>=c.onset & t<c.onset+c.duration;
  actual=[min(Y(:,13)),sum(Y(1:end-1,17).*diff(t)),max(abs(Y(:,22))),max(abs(Y(:,32))),max(Y(:,34)),mean(Y(:,33)),mean(Y(:,20)),Y(end,13),mean(Y(end,4:12)),sum(abs(Y(sag,3)-Y(sag,38)))*c.dt];
  wanted=[e.min_LV_V,e.unmet_J,e.energy_residual_J,e.max_PLL_error_deg,e.max_current_rating_ratio,e.modulation_saturation_fraction,e.DAB_saturation_fraction,e.final_LV_V,e.final_mean_MV_V,e.sag_reactive_tracking_error_As];
  delta=max(abs(actual-wanted)./max(1,abs(wanted)));
  assert(delta<1e-9,'Full-step summary metrics differ');
  assert(actual(3)<.05,'Energy residual exceeds execution threshold');
  ok=true;message="PASS";
 catch err
  message=string(err.message);
 end
 allOK=allOK&&ok;rows(j,:)={string(name),keys(j),files(j).bytes,sha,n,trip,cause,delta,ok,message};
 fprintf('%d/%d %s: %s\n',j,numel(files),name,message);
end
report=cell2table(rows,'VariableNames',{'filename','run_key','bytes','sha256','sample_count','trip_time_s','trip_cause_mask','max_relative_metric_error','passed','message'});
writetable(report,fullfile(folder,'raw_audit.csv'));
expectedKeys=strings(height(expected),1);
for j=1:height(expected),expectedKeys(j)=string(sprintf('%s_%s_%s_%gus',expected.architecture(j),expected.scenario(j),expected.variant(j),expected.step_s(j)*1e6));end
complete=numel(files)==132 && numel(unique(keys))==132 && isequal(sort(keys),sort(expectedKeys));
fid=fopen(fullfile(folder,'audit_summary.txt'),'w');
fprintf(fid,'MATLAB %s\nFiles: %d\nAll per-file checks passed: %d\nExact 132-run coverage: %d\n',version,numel(files),allOK,complete);fclose(fid);
zip([folder '.zip'],{'raw_audit.csv','audit_summary.txt'},folder);
fprintf('\nAudit complete. Overall PASS: %d\nUpload %s.zip\n',allOK&&complete,folder);
end
