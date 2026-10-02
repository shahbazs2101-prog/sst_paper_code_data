# Stage 4 bounded current-reference comparison

Place this folder inside the compiled project under Code_MATLAB. Open RUN_STAGE4.m in MATLAB R2025b and Run. Return SST_Stage4_Executed_TIMESTAMP.zip; retain raw_results. No previously executed model is overwritten. Unique p4 function names and a distinct SLX preserve the Stage 3 baseline.

36 runs: SST and total-energy-matched conventional; coincident disturbance, short interruption and phase step; original baseline, 10 ms reference filter and 20 ms reference filter; 25 and 12.5 microsecond steps. Filter settings are exploratory engineering choices, not measured or optimized settings. The candidate is not guaranteed to survive.

For a desired dq reference r and filtered state rf, the candidate obeys drf/dt = (r-rf)/tau, limited in vector norm to Ipk/tau. The original controller uses r directly. Initial rf equals the nominal current reference. The desired reference lies in the same unit current circle as Stage 3. Because filtering is applied to BOTH components throughout the run, it also delays reactive-current response during sag onset. It is not purely a restoration-only modification and must not be presented as meeting the same instantaneous voltage-support response. Both comparator architectures receive the same modification. Actual current is never clipped.

Plant, PLL, filter losses, DAB actuator, capacitor sizes, voltage floors and the 1.25 overcurrent threshold remain unchanged. Stage 4 baseline dynamics should reproduce Stage 3 for the selected scenarios. This identity is an explicit review gate. If the new baseline differs materially, diagnose that before interpreting candidates.

Additional outputs: desired and used dq references; voltage-command utilization before saturation; instantaneous grid-voltage envelope headroom; latched trip cause. Trip cause is a bit mask: 1=LV undervoltage, 2=any SST MV-link undervoltage, 4=overcurrent. Multiple simultaneous causes add their values. The latch retains the first evaluated RK-stage cause rather than inferring it from a decimated waveform.

Voltage headroom is an instantaneous diagnostic, not a complete nonlinear controllability test. Negative headroom means the grid's instantaneous voltage exceeds the available bridge envelope. SST compares each phase against its three-cell stack before neutral adjustment. Conventional compares the grid pole envelope with half the referred LV voltage. The quantity does not itself trigger protection.

Returned waveforms retain EVERY time step from 20 ms before to 60 ms after restoration, with 1 ms samples elsewhere plus trip edges. Full-step MAT data remain in raw_results. No results are preinserted and no assertions should be removed. Stage 3 recovery overcurrent failure remains in the compiled history whether candidates improve, worsen or reproduce it.

This is still an equation-based average converter model, not switching or physically wired Simscape. Do not assert hardware reliability, empirical disturbance probabilities or full novelty solely from a successful candidate run. Follow the Stage 3 method description for unchanged plant assumptions. All test disturbances are synthetic. Source/model snapshots accompany execution outputs.
