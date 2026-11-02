# Data used by the tutorials

| File | Contents | Source |
|---|---|---|
| `modern_OIB.xlsx` | 1,800 modern ocean-island basalts from 112 locations: major elements, REE and a seismic estimate of lithospheric thickness (`thickness`) | Compiled from the literature; the original publication of each sample is given in the `reference` and `citations` columns. **Please cite the original publications when using these data.** |
| `literature_excess_temperatures.csv` | Published excess temperatures for each plume (`island_name`) | `Tex_Putirka_2008`: Putirka (2008); `Tex_Bao_2022`: Bao et al. (2022) |
| `modern_OIB_Fo90_TP.xlsx` | For each sample of `modern_OIB.xlsx` (`island_name`): the Fo90 primary-magma composition, the olivine added (`ol_added`), and melting pressure (GPa) and temperature (°C) with errors from four thermobarometers: Plank & Forsyth (2016; `_PF16`), Brown Krein et al. (2021; `_BK21`, `_BK21_SPL`) and Lee et al. (2009; `_L09`). Empty where the olivine correction fails | Produced by `make_PF16_pressures.py` with meltPT, using the same olivine correction as `meltinv.invert(..., correction=True)` |
| `PF16_melting_pressures.csv` | The `island_name` and `P_PF16` columns of `modern_OIB_Fo90_TP.xlsx`; the paper compares with PF16 only | Produced by `make_PF16_pressures.py` |
| `modern_OIB_precomputed/` | The full meltinv results for `modern_OIB.xlsx`, so that Tutorial 3 can make the paper figures without the 10-minute calculation | Produced by `tutorials/03_modern_OIB.ipynb` with `RUN_FULL_ANALYSIS = True` |

## How the samples in `modern_OIB.xlsx` were selected

All ocean-island basalts were taken from GEOROC (https://georoc.eu). A sample was excluded if it:

1. lacked SiO2, MgO or total FeO, or reported fewer than 6 of the 14 REE;
2. had MgO < 7.5 wt%;
3. had loss on ignition (LOI) > 5 wt%, or was labelled as altered; or
4. had both Nb/U < 30 and La/Nb ≥ 1.5, suggesting crustal contamination.

Criteria 3 and 4 were applied where the data were reported: LOI is available for 835 samples, and Nb, U and La for 1,450.

References:

- Bao, X., Lithgow-Bertelloni, C. R., Jackson, M. G. & Romanowicz, B. (2022). On the relative temperatures of Earth's volcanic hotspots and mid-ocean ridges. *Science*, 375, 57–61.
- Plank, T. & Forsyth, D. W. (2016). Thermal structure and melting conditions in the mantle beneath the Basin and Range province from seismology and petrology. *Geochemistry, Geophysics, Geosystems*, 17, 1312–1338.
- Putirka, K. (2008). Excess temperatures at ocean islands: implications for mantle layering and convection. *Geology*, 36, 283–286.
