"""
Recompute modern_OIB_Fo90_TP.xlsx and PF16_melting_pressures.csv for the samples in modern_OIB.xlsx.

modern_OIB_Fo90_TP.xlsx holds, for every sample, the primary composition from meltPT, the olivine
added, and pressure and temperature (with errors) from four thermobarometers: Plank & Forsyth
(2016, PF16), Brown Krein et al. (2021; BK21 and BK21_SPL) and Lee et al. (2009, L09). The paper
uses PF16 only, which is also written to PF16_melting_pressures.csv for the comparison figure.

The primary compositions are made exactly as by meltinv's olivine correction for the paper
(meltinv.invert(..., correction=True)): total iron split with Fe3+/sum Fe = 0.1, olivine added
until in equilibrium with Fo90, at most 50 wt% olivine (meltPT; see pyproject.toml for the commit).
Samples whose correction fails get no pressure or temperature.

Run from this folder:  ../../venv/bin/python make_PF16_pressures.py
"""
import tempfile
from pathlib import Path

import pandas as pd
from meltPT import BacktrackOlivineFractionation, Suite

from meltinv.frac_correction import as_total_iron

SRC_FO, FE3_FE_TOTAL, MAX_OLIVINE = 0.9, 0.1, 0.5
METHODS = ["PF16", "BK21_SPL", "BK21", "L09"]

samples = pd.read_excel("modern_OIB.xlsx")
with tempfile.TemporaryDirectory() as tmp:
    csv = Path(tmp) / "total_iron.csv"
    as_total_iron(samples).to_csv(csv, index=False)
    suite = Suite(str(csv), src_Fo=SRC_FO, src_FeIII_totFe=FE3_FE_TOTAL)
suite.backtrack_compositions(backtracker=BacktrackOlivineFractionation(max_olivine_addition=MAX_OLIVINE))

tables = [samples[["location"]].rename(columns={"location": "island_name"}),
          suite.primary.reset_index(drop=True)]
for method in METHODS:
    suite.compute_pressure_temperature(method=method)
    tables.append(suite.PT.reset_index(drop=True).rename(columns=lambda c: f"{c}_{method}"))
tp = pd.concat(tables, axis=1)
tp.to_excel(f"modern_OIB_Fo{round(SRC_FO * 100)}_TP.xlsx", index=False)

tp[["island_name", "P_PF16"]].to_csv("PF16_melting_pressures.csv", index=False)
print(f"{tp.P_PF16.notna().sum()} of {len(tp)} samples have a PF16 pressure; columns: {list(tp.columns)}")
