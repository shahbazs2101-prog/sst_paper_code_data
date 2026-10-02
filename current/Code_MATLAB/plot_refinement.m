function plot_refinement(folder)
for scenario={'rated_interruption','short_interruption','coincident','partial_sag'}
 fig=figure('Visible','off');tiledlayout(3,1);
 for a={'SST','LFT_ripple','LFT_matched'}
  step='25';if strcmp(scenario{1},'rated_interruption'),step='12.5';end
  S=load(fullfile(folder,sprintf('%s_%s_%sus.mat',a{1},scenario{1},step)));
  nexttile(1);hold on;plot(S.t,S.Y(:,13),'DisplayName',a{1});ylabel('LV voltage (V)');
  nexttile(2);hold on;plot(S.t,mean(S.Y(:,4:12),2),'DisplayName',a{1});ylabel('Mean MV voltage (V)');
  nexttile(3);hold on;plot(S.t,S.Y(:,16)/1000,'DisplayName',a{1});ylabel('Delivered (kW)');xlabel('Time (s)');
 end
 nexttile(1);legend('Interpreter','none');title(scenario{1},'Interpreter','none');
 exportgraphics(fig,fullfile(folder,[scenario{1} '.png']),'Resolution',180);close(fig);
end
end
