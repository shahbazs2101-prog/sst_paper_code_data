from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
for script in ['verify_data.py','chb_verified.py','sst_dab_model.py','reproduce.py','balancing_verified.py','interface_sensitivity.py','make_figures.py']:
    subprocess.run([sys.executable,str(root/script)],check=True,cwd=root)
