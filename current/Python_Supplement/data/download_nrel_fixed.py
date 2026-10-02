"""
download_nrel_fixed.py
Downloads NREL SRRL BMS irradiance data directly from the verified NREL
domain, without going through pvlib's read_midc_raw_data_from_nrel
(which points at the wrong host in the currently installed pvlib version --
see conversation notes). Uses only the `requests` library.
"""
import requests
import pandas as pd
from pathlib import Path

OUT = Path("data/srrl_bms_20220120.csv")
OUT.parent.mkdir(exist_ok=True, parents=True)

# Confirmed correct endpoint, per NREL's own API documentation at
# https://midcdmz.nrel.gov/apps/data_api_doc.pl?BMS
URL = "https://midcdmz.nrel.gov/apps/data_api.pl"
params = {"site": "BMS", "begin": "20220120", "end": "20220120"}

print(f"Requesting {URL} with {params} ...")
try:
    resp = requests.get(URL, params=params, timeout=30)
    resp.raise_for_status()
except Exception as e:
    print(f"Download failed: {e}")
    raise SystemExit(1)

print("Response received. First 300 characters:")
print(resp.text[:300])

with open(OUT, "w") as f:
    f.write(resp.text)

print(f"\nSaved raw response to {OUT.resolve()}")
print("Open this file and confirm it looks like a real CSV (a header row")
print("followed by comma-separated numeric data) before using it further.")
