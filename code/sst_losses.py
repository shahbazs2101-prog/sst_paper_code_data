"""
sst_losses.py
Section 6.3 -- Switching-loss and electro-thermal simulation.

Devices (Section 6.3, manuscript text):
  CHB cell bridge + DAB primary bridge: Infineon FF400R33KF2C 3.3kV/400A Si IGBT
    - Vce,sat: 4.25 V typ @25C, 4.30 V @125C (full datasheet typ, not the
      commonly-misquoted 3.4V minimum-at-25C figure)
    - Eon: 470 mJ @25C -> 730 mJ @125C
    - Eoff: 430 mJ @25C -> 510 mJ @125C
    - test condition: VCE=1800V, IC=400A
  DAB secondary bridge: Wolfspeed WAS350M12BM3 1.2kV/350A SiC MOSFET module
    - Rds(on): 4.0 mOhm typ @25C (datasheet), estimated ~1.7x rise by 150C
      (typical SiC temperature coefficient) -> ~6.8 mOhm @150C

Runs the CHB carrier-frequency sweep (10kHz -> 1kHz) that motivates the
Section 4.1 design correction, and produces the final Table 3 / Table 4
efficiency figures.

IMPLEMENTATION NOTE: this uses fixed representative RMS operating currents
(I_rms parameters below) at each device position, not a direct integration
of the actual switching-current waveforms produced by sst_chb_model.py /
sst_dab_model.py. The manuscript text describes integrating loss directly
over the verified switching waveforms; wiring that up here would be a
natural follow-on improvement, but isn't what this script currently does.
"""
import json
import numpy as np

# ---- Device parameters ----
# IGBT (CHB cell bridge, DAB primary bridge)
IGBT = {
    "Vce_sat_25C": 4.25, "Vce_sat_125C": 4.30,   # V
    "Eon_25C": 0.470, "Eon_125C": 0.730,          # J
    "Eoff_25C": 0.430, "Eoff_125C": 0.510,        # J
    "VCE_test": 1800.0, "IC_test": 400.0,
    # 4-branch Foster network (Rth in K/W, tau in s) -- representative of a
    # 3.3kV/400A dual module datasheet table; dominant branch ~1s per paper text
    "foster_R": [0.008, 0.015, 0.020, 0.030],
    "foster_tau": [0.001, 0.01, 0.1, 1.0],
}
# SiC MOSFET (DAB secondary bridge)
SIC = {
    "Rds_25C": 4.0e-3, "Rds_150C": 6.8e-3,  # ohm
    "Rth_jc": 0.12,  # K/W, single steady-state value (Wolfspeed publishes one value)
    "tau_th": 0.05,  # s, single-pole approximation of the module's thermal mass
}

T_case = 60.0  # deg C, disclosed assumption


def interp_temp(v25, v_other, T_other, Tj):
    """Piecewise-linear interpolation between the datasheet's two breakpoints.
    Clamped to [25C, T_other] -- no extrapolation beyond the datasheet's own
    stated range, since linear extrapolation of switching/conduction
    parameters past the manufacturer's characterized range isn't physically
    defensible."""
    frac = (Tj - 25.0) / (T_other - 25.0)
    frac = np.clip(frac, 0.0, 1.0)
    return v25 + frac * (v_other - v25)


def igbt_losses(I_rms, f_sw, Tj, hard_switched=True):
    """Conduction + switching loss for one IGBT position at given RMS current,
    switching frequency, and junction temperature."""
    Vce = interp_temp(IGBT["Vce_sat_25C"], IGBT["Vce_sat_125C"], 125.0, Tj)
    P_cond = Vce * I_rms  # constant-drop model referenced to RMS (paper's own simplification)

    if hard_switched:
        Eon = interp_temp(IGBT["Eon_25C"], IGBT["Eon_125C"], 125.0, Tj)
        Eoff = interp_temp(IGBT["Eoff_25C"], IGBT["Eoff_125C"], 125.0, Tj)
    else:
        Eon = 0.0  # ZVS removes turn-on loss
        Eoff = interp_temp(IGBT["Eoff_25C"], IGBT["Eoff_125C"], 125.0, Tj)

    # scale switching energy by actual V/I ratio vs datasheet test point
    scale = (1800.0 / IGBT["VCE_test"]) * (I_rms / IGBT["IC_test"])
    # (kept general in case future calls use a different blocking voltage)
    P_sw = (Eon + Eoff) * f_sw * scale
    return P_cond, P_sw


def sic_losses(I_rms, f_sw, Tj):
    """SiC MOSFET: ZVS on both transitions -> conduction loss only (~negligible
    switching loss from residual capacitive/dead-time effects, small nonzero term)."""
    Rds = interp_temp(SIC["Rds_25C"], SIC["Rds_150C"], 150.0, Tj)
    P_cond = I_rms ** 2 * Rds
    # small residual switching loss even under ZVS (dead-time / Coss discharge)
    P_sw = 0.15 * I_rms * f_sw * 1e-6  # small empirical residual, watts
    return P_cond, P_sw


def converge_Tj(loss_fn, I_rms, f_sw, Rth_jc, T_case=T_case, tol=1e-4, max_iter=100):
    """Fixed-point iteration: loss -> Tj -> temp-dependent params -> loss."""
    Tj = T_case
    for _ in range(max_iter):
        P_cond, P_sw = loss_fn(I_rms, f_sw, Tj)
        P_tot = P_cond + P_sw
        Tj_new = T_case + P_tot * Rth_jc
        if abs(Tj_new - Tj) < tol:
            Tj = Tj_new
            break
        Tj = Tj_new
    return Tj, P_cond, P_sw


def chb_cell_efficiency(f_carrier, I_rms=7.873, Pcell=16667.0):
    """CHB cell (one IGBT position's worth of loss per phase-leg pair, scaled
    to the per-cell 16.667kW rating). Hard-switched, no ZVS in the CHB stage."""
    Rth_igbt = sum(IGBT["foster_R"])
    Tj, P_cond, P_sw = converge_Tj(
        lambda I, f, T: igbt_losses(I, f, T, hard_switched=True),
        I_rms, f_carrier, Rth_igbt)
    P_loss = P_cond + P_sw
    eff = (Pcell - P_loss) / Pcell * 100.0
    return eff, Tj, P_cond, P_sw


def dab_cell_efficiency(I_rms_primary=8.0, I_rms_secondary=16.0, f_sw=10e3,
                         Pcell=16667.0):
    """DAB cell: ZVS on both bridges -> Eon=0. Primary IGBT + secondary SiC."""
    Rth_igbt = sum(IGBT["foster_R"])
    Tj_p, Pc_p, Ps_p = converge_Tj(
        lambda I, f, T: igbt_losses(I, f, T, hard_switched=False),
        I_rms_primary, f_sw, Rth_igbt)
    Tj_s, Pc_s, Ps_s = converge_Tj(
        sic_losses, I_rms_secondary, f_sw, SIC["Rth_jc"])
    P_loss = (Pc_p + Ps_p) + (Pc_s + Ps_s)
    eff = (Pcell - P_loss) / Pcell * 100.0
    return eff, (Tj_p, Tj_s), (Pc_p, Ps_p, Pc_s, Ps_s)


def carrier_frequency_sweep():
    freqs = [10e3, 5e3, 2e3, 1e3, 0.5e3]
    rows = []
    for f in freqs:
        eff, Tj, Pc, Ps = chb_cell_efficiency(f)
        rows.append({"f_carrier_Hz": f, "CHB_cell_eff_pct": eff, "Tj_C": Tj})
        print(f"f_carrier={f/1000:.1f} kHz: CHB cell efficiency={eff:.2f}%  Tj={Tj:.1f}C")
    return rows


def main():
    print("=== CHB carrier-frequency sweep (motivates 10kHz -> 1kHz correction) ===")
    sweep = carrier_frequency_sweep()

    print("\n=== Final operating point (1 kHz CHB carrier) ===")
    chb_eff, chb_Tj, chb_Pc, chb_Ps = chb_cell_efficiency(1000.0)
    print(f"CHB cell: eff={chb_eff:.2f}%  Tj={chb_Tj:.1f}C  Pcond={chb_Pc:.1f}W  Psw={chb_Ps:.1f}W")

    dab_eff, (dab_Tj_p, dab_Tj_s), (dab_Pc_p, dab_Ps_p, dab_Pc_s, dab_Ps_s) = dab_cell_efficiency()
    print(f"DAB cell: eff={dab_eff:.2f}%  Tj_primary={dab_Tj_p:.1f}C  Tj_secondary={dab_Tj_s:.1f}C")
    print(f"  primary IGBT: Pcond={dab_Pc_p:.1f}W Psw={dab_Ps_p:.1f}W (ZVS, Eon=0)")
    print(f"  secondary SiC: Pcond={dab_Pc_s:.1f}W Psw={dab_Ps_s:.1f}W")

    combined_new_stages = chb_eff / 100.0 * dab_eff / 100.0 * 100.0
    lv_inverter_eff = 98.0  # literature figure, reused stage
    full_sst_eff = combined_new_stages / 100.0 * lv_inverter_eff / 100.0 * 100.0
    conventional_eff = 99.0 * 98.0 / 100.0  # LFT x VSC, literature

    print(f"\nCombined CHB+DAB: {combined_new_stages:.2f}%")
    print(f"Full SST (with 98% LV inverter): {full_sst_eff:.2f}%")
    print(f"Conventional interface (99% LFT x 98% VSC): {conventional_eff:.2f}%")
    print(f"\nPaper reports: CHB 98.85%, DAB 97.35%, Full SST 94.31%, Conventional 97.00%")

    results = {
        "carrier_sweep": sweep,
        "final_operating_point": {
            "CHB_cell_eff_pct": chb_eff, "CHB_Tj_C": chb_Tj,
            "DAB_cell_eff_pct": dab_eff,
            "DAB_Tj_primary_C": dab_Tj_p, "DAB_Tj_secondary_C": dab_Tj_s,
            "combined_new_stages_pct": combined_new_stages,
            "full_SST_eff_pct": full_sst_eff,
            "conventional_eff_pct": conventional_eff,
        },
        "paper_reported": {
            "CHB_eff_pct": 98.85, "DAB_eff_pct": 97.35,
            "full_SST_eff_pct": 94.31, "conventional_eff_pct": 97.00,
            "CHB_10kHz_eff_pct": 92.6, "CHB_1kHz_eff_pct": 98.9,
        },
    }
    import os
    os.makedirs("../results", exist_ok=True)
    with open("../results/sst_losses_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
