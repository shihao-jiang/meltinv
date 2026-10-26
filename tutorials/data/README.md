# Data used by the tutorials

| File | Contents | Source |
|---|---|---|
| `modern_OIB.xlsx` | 1,801 modern ocean-island basalts from 112 locations: major elements, REE and a seismic estimate of lithospheric thickness (`thickness`) | Compiled from the literature; the original publication of each sample is given in the `reference` and `citations` columns. **Please cite the original publications when using these data.** |
| `literature_excess_temperatures.csv` | Published excess temperatures for each plume (`island_name`) | `Tex_Putirka_2008`: Putirka (2008); `Tex_Bao_2022`: Bao et al. (2022) |
| `PF16_melting_pressures.csv` | Melting pressure (GPa) for each sample (`island_name`), from the thermobarometer of Plank & Forsyth (2016) applied to the Fo90 primary-magma compositions | Calculated for the meltinv paper |
| `modern_OIB_precomputed/` | The full meltinv results for `modern_OIB.xlsx`, so that Tutorial 3 can make the paper figures without the 10-minute calculation | Produced by `tutorials/03_modern_OIB.ipynb` with `RUN_FULL_ANALYSIS = True` |

References:

- Bao, X., Lithgow-Bertelloni, C. R., Jackson, M. G. & Romanowicz, B. (2022). On the relative temperatures of Earth's volcanic hotspots and mid-ocean ridges. *Science*, 375, 57–61.
- Plank, T. & Forsyth, D. W. (2016). Thermal structure and melting conditions in the mantle beneath the Basin and Range province from seismology and petrology. *Geochemistry, Geophysics, Geosystems*, 17, 1312–1338.
- Putirka, K. (2008). Excess temperatures at ocean islands: implications for mantle layering and convection. *Geology*, 36, 283–286.
