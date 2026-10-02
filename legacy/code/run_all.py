"""
run_all.py
Runs every script in this repository in the correct dependency order, so
nothing crashes on a missing results/ file from a script that hasn't run
yet. Safe to run from a completely clean checkout.

Order:
  1. sst_dab_model.py, sst_chb_model.py, sst_losses.py  (independent)
  2. sst_sim.py                                          (independent)
  3. sst_real_profiles.py                                (independent;
     prints a loud warning if the real NREL CSV isn't present in data/)
  4. sst_montecarlo.py       (depends on sst_real_profiles.py's event catalog)
  5. sst_balancing.py, sst_thermal_transient.py           (thermal_transient
     depends on sst_losses.py and sst_sim.py)
  6. sst_plots.py, sst_graphical_abstract.py              (depend on all
     results/ files above existing)

Usage: python3 run_all.py
"""
import subprocess
import sys
import time

SCRIPTS_IN_ORDER = [
    "sst_dab_model.py",
    "sst_chb_model.py",
    "sst_losses.py",
    "sst_sim.py",
    "sst_real_profiles.py",
    "sst_montecarlo.py",
    "sst_balancing.py",
    "sst_thermal_transient.py",
    "sst_plots.py",
    "sst_graphical_abstract.py",
]


def main():
    for script in SCRIPTS_IN_ORDER:
        print(f"\n{'='*70}\nRunning {script}\n{'='*70}")
        t0 = time.time()
        result = subprocess.run([sys.executable, script])
        elapsed = time.time() - t0
        if result.returncode != 0:
            print(f"\n!!! {script} FAILED (exit code {result.returncode}) "
                  f"after {elapsed:.1f}s -- stopping.")
            sys.exit(result.returncode)
        print(f"--- {script} done in {elapsed:.1f}s ---")

    print(f"\n{'='*70}\nAll scripts completed successfully.\n{'='*70}")


if __name__ == "__main__":
    main()
