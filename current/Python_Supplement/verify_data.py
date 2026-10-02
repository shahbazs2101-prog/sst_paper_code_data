from pathlib import Path
import csv, hashlib, json
import numpy as np
p=Path(__file__).resolve().parent
with (p/'data/20220120.csv').open() as f: raw=list(csv.DictReader(f))
with (p/'data/nrel_srrl_bms_ghi_20220120.csv').open() as f: processed=list(csv.DictReader(f))
assert len(raw)==len(processed)==1440
assert all(int(r['Year'])==2022 and int(r['DOY'])==20 for r in raw)
a=np.array([max(0,float(r['Global CMP22 (vent/cor) [W/m^2]'])) for r in raw])
b=np.array([float(r['GHI_Wm2']) for r in processed])
minutes=np.array([int(r['MST'])//100*60+int(r['MST'])%100 for r in raw])
assert np.array_equal(minutes,np.arange(1440))
assert np.array_equal(a,b)
meta=json.loads((p/'provenance.json').read_text())
assert hashlib.sha256((p/'data/20220120.csv').read_bytes()).hexdigest()==meta['raw_input_sha256']
assert hashlib.sha256((p/'data/nrel_srrl_bms_ghi_20220120.csv').read_bytes()).hexdigest()==meta['input_sha256']
print('PASS: raw dates, minute alignment, 1440 samples, exact clipped CMP22 extraction and input checksums.')
