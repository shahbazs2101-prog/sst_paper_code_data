"""Verify saved filter-sweep exports without rerunning simulations."""
from pathlib import Path
from collections import Counter
import csv
import math

root = Path(__file__).resolve().parent
def read(name):
    with (root / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))
def key(r):
    return r["system"], r["case_id"], r["filter"]

runs = read("all_case_filter_results.csv")
cells = read("nine_cells_and_DAB.csv")
summary = read("filter_comparison_summary.csv")
defs = {r["case_id"]: r for r in read("eleven_case_definitions.csv")}
matrix = {(r["system"],r["case_id"]): r for r in read("trip_matrix_by_case.csv")}
assert len(runs) == len(cells) == 165
assert len({key(r) for r in runs}) == len({key(r) for r in cells}) == 165
assert len(summary) == 15 and len(defs) == 11 and len(matrix) == 33
cd = {key(r): r for r in cells}
for r in runs:
    d = defs[r["case_id"]]
    assert all(float(d[k]) == float(r[k]) for k in ("base_kW","sag_s","phase_deg"))
    assert int(float(r["trip"])) == int(matrix[(r["system"],r["case_id"])][r["filter"]])
    if r["system"] != "LFT_matched":
        q = cd[key(r)]
        assert math.isclose(float(r["min_MV_cell_V"]), min(float(q[f"min_MV{i}_V"]) for i in range(1,10)), rel_tol=1e-8, abs_tol=1e-8)
        assert math.isclose(float(r["max_DAB_d"]), max(float(q[f"max_DAB{i}_d"]) for i in range(1,10)), rel_tol=1e-8, abs_tol=1e-8)
    else:
        assert key(r) in cd
for s in summary:
    rr = [r for r in runs if r["system"] == s["system"] and r["filter"] == s["filter"]]
    assert len(rr) == 11
    assert sum(int(float(r["trip"])) for r in rr) == int(s["trips_of_11"])
    for bit, col in [(4,"overcurrent_trips"),(2,"MV_voltage_trips"),(1,"LV_voltage_trips")]:
        assert sum(bool(int(float(r["first_cause_mask"])) & bit) for r in rr) == int(s[col])
    print(s["system"], s["filter"], s["trips_of_11"])
print("PASS: 165 saved rows, cell extrema, case parameters, matrix and grouped trip counts.")
