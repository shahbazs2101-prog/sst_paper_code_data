function plot_pilot(folder)
for scenario={'short_interruption','long_interruption','rated_interruption'}
 fig=figure('Visible','off');tiledlayout(3,1);
 for a={'SST','LFT_ripple','LFT_matched'}
  f=fullfile(folder,sprintf('%s_%s_25us.mat',a{1},scenario{1}));S=load(f);
  nexttile(1);hold on;plot(S.t,S.Y(:,13),'DisplayName',a{1});ylabel('LV voltage (V)');
  nexttile(2);hold on;plot(S.t,S.Y(:,16)/1000,'DisplayName',a{1});ylabel('Delivered (kW)');
  nexttile(3);hold on;plot(S.t,S.Y(:,18),'DisplayName',a{1});ylabel('Trip');xlabel('Time (s)');
 end
 nexttile(1);legend('Interpreter','none','Location','best');title(scenario{1},'Interpreter','none');
 exportgraphics(fig,fullfile(folder,[scenario{1} '.png']),'Resolution',180);close(fig);
end
end
