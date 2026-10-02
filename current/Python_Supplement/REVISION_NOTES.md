# Technical changes and validation

- Corrected the DAB displacement convention to d = 2*delay/T and d*T/2 gate timing.
- Replaced bipolar CHB code with true unipolar seven-level switching. Corrected RMS harmonic normalization; full-spectrum THD is also reported to avoid presenting a low-order metric as total ripple.
- Removed the unsubstantiated fundamental-reference-delivery claim; nominal CHB power is explicitly set by a power-angle search.
- Replaced linearized phase-shift commands and fixed headroom with nonlinear inversion and voltage-dependent bounds. Positive correction increases outgoing power.
- Added a physically meaningful rated-demand DAB power boundary and disclosure of the ideal conventional power envelope.
- Added three-seed ride-through sensitivity, energy-budget sensitivity, balancing mismatch tests and time-step checks; reported saturation failures.
- Completed missing metadata for insulation, soft-switching and EV integration references, and corrected the microgrid review author order.
- Removed revision-history prose and unsupported loss/thermal predictions. Condensed hardware validation discussion.
- Added numbered display equations, a parameter table, regenerated numerical figures and table-pagination corrections.

Readiness limits: coauthors still need to approve scientific scope, affiliation/contribution details and source provenance. The paper remains a simulation/analytical study; journal novelty and acceptance are not guaranteed. No hardware, HIL, MATLAB execution or device-level ZVS was added or implied.

## Measurement provenance update
Raw BMS archive and download script supplied on 1 October 2026. Exact CMP22 extraction and MST minute alignment are verified. The corrected package already used this processed file; the old uploaded NPZ/JSON run used a different synthetic trace. Device-level SST ZVS remains unverified; the separate 800 V iEnergy commutation-cell package is not transferred as SST evidence.
