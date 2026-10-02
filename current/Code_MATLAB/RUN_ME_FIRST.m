% Extract the zip into a new folder, open this script in MATLAB R2025b,
% and click Run. MATLAB and Simulink are required; Simscape is not required.
root=fileparts(mfilename('fullpath'));cd(root);addpath(root);
selfcheck_pilot;
run_pilot;
