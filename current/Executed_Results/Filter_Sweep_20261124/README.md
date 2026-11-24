# Filter sweep and MV-cell checks — 24 November 2026

This note records the additional 165 MATLAB simulation tests for SST Paper 1. The tests used 11 fixed cases, five current-reference settings (no filter, 5, 10, 20, and 40 ms), and three system versions: original SST, SST with min–max common-mode control, and the energy-matched conventional LFT–VSC. These are modeled results, not hardware tests.

## Trip counts

| Filter | Original SST | SST min–max | LFT matched |
|---|---:|---:|---:|
| None | 7/11 | 3/11 | 3/11 |
| 5 ms | 7/11 | 3/11 | 3/11 |
| 10 ms | 4/11 | 3/11 | 3/11 |
| 20 ms | 3/11 | 3/11 | 3/11 |
| 40 ms | 3/11 | 3/11 | 3/11 |

The original SST loses four recovery-overcurrent trips with the 20 ms filter. The min–max common-mode change removes these four trips without using a reference filter. Cases 03, 05 and 11 still trip on MV undervoltage in the SST models; the matched LFT model trips on LV undervoltage in those same cases.

## DAB and voltage results

The added MATLAB results record the minimum voltage of each of the nine MV links and the largest phase shift of each of the nine DAB units for every case. The largest DAB phase ratio in the SST sweep is about 0.236, less than the modeled limit of 0.50. DAB saturation is not shown as the cause of the three remaining SST undervoltage trips.

The conventional LFT–VSC has no nine-cell MV link or DAB; MV and DAB values printed for this arm are placeholders, not physical LFT measures.

## Model limits

These additional simulations use the original Stage 6 average-model equations with altered current-reference time constants. The 165 test combinations are separate from the original 132 Stage 6 runs. The original case definitions, code, and published simulation outputs are retained. A same-floor 0.80 pu comparison and experimental checks are not claimed here.

Source used for the 165-case summary: local MATLAB exports `all_case_filter_results.csv`, `filter_comparison_summary.csv`, and `nine_cells_and_DAB.csv`, reviewed with the manuscript. The original per-run raw waveforms are retained locally and are not deposited in this note.
