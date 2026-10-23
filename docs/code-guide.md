# Reading and changing meltinv

Start with the README's example inversion. You do not need to understand the
archive format or cache to use the package. This guide is for a researcher who
wants to follow the calculation, check an assumption, or change a figure.

## Where to start in the code

| Question | Start here |
|---|---|
| What arguments can I pass? | `meltinv/core.py`: `invert` is the public Python entry point; `cli.py` translates command-line options into the same calls. |
| Which observations are used? | `inversion.py`: `invert_melt_condition` reads/corrects the data, cleans REEs and applies the six-usable-REE rule. |
| What exactly is searched? | `inversion.py`: `get_enrichment_values`, `source_composition_mix`, then `invert_single_group`. Despite its legacy name, the public workflow calls this last function for **one sample** at a time. |
| Where is the residual statistic? | `_misfit.py`: `prepare_observations` selects measurements, `evaluate_misfit` computes the grid of residual scores. |
| What does calibration change? | `inversion.py`: `calibration` adjusts fitted temperature and thickness **after** the REE fit. It does not run a new fit. |
| How are locations summarised? | `inversion.py`: `aggregate_per_sample_results` calculates weighted means and spreads from per-sample results. |
| How do I change colours, axes or labels? | `plotting.py`: `plot_results` draws individual diagnostics; `plot_group_comparison` draws location comparisons. |
| How do I redraw figures from an old run? | `plot_archive.py`: `regenerate_figures` reads a saved snapshot and calls those plotting functions. No model grids or input file are read. |

The full workflow is:

```text
input measurements → optional olivine correction → clean/filter REEs
    → search each sample → uncalibrated best-fit results
        → individual diagnostic plots and/or saved slices (optional)
        → post-fit calibration → per-sample table → location summary
                                   → group comparison plots (optional)
```

The archive stores both uncalibrated diagnostic data and the calibrated values
needed by group plots. This distinction explains why the temperature annotation
in an individual diagnostic can differ from the temperature in a group plot.

## Array axes and names that can be misleading

The packaged model concentrations have shape `(REE, thickness, temperature)`.
A misfit grid for one enrichment has shape `(thickness, temperature)`.
The complete search surface has shape `(enrichment, thickness, temperature)`.
For the bundled grids these last two dimensions are 53 and 58.

- A temperature column `t_idx` corresponds to `65 + 5*t_idx` K of excess temperature.
- A thickness row `p_idx` corresponds to `16 + 2*p_idx` km. The legacy `p_idx`
  name does **not** mean pressure in GPa.
- `pres_mean`, `pres_min`, `pres_max` also contain **melting depths in km**.
  Calibration divides the mean depth by 33 to obtain its pressure in GPa.
- `basalt_percentage` is the source-enrichment parameter. Positive values mix
  primitive mantle with basalt; negative values mix it with depleted mantle.
  Its use in the post-fit calibration is an existing scientific prescription.
- `min_sample_count` inside the low-level residual code is the minimum number
  of observations **per element**. The public sample-by-sample workflow passes
  1. It is separate from the six-usable-REE acceptance rule.

## The result dictionary before calibration

`invert_single_group` returns `None` for a failed fit, or a dictionary:

| Fields | Meaning |
|---|---|
| `min_idx`, `basalt_idx` | Best thickness/temperature index pair and enrichment index. |
| `T_mean`, `depth_mean`, `basalt_percentage` | Uncalibrated fitted excess temperature (K), thickness (km), and source enrichment. |
| `pres_*`, `F_*`, `M_*` | Melting-depth, melt-fraction and melting-rate summaries at the best cell, from the packaged forward grids. |
| `misfit_value`, `global_min_value` | Same exhaustive-search minimum. Both names are retained for compatibility. |
| `global_flat_index` | Best cell's flattened index in `(enrichment, thickness, temperature)` order. |
| `ratio_of_local_global_misfit` | Compatibility field, set to 1 even for an exact fit; no division by zero is performed. |
| `mean_ree`, `low_ree`, `high_ree` | Source-scaled model REE predictions and the forward-model envelope, in ppm. These are not statistically calibrated confidence limits. |
| `mean_ree_global` | Same prediction as `mean_ree`, retained for the existing plot interface. |
| `misfit_grid` | Entire thickness/temperature slice at the best-fit enrichment. |
| `full_3d_grids` | Complete surface when diagnostics are retained, otherwise `None`. |
| `enrichment_values` | Ordered enrichment search values, including the irregular spacing on the depleted side. |
| `threshold` | Legacy tenth-percentile diagnostic, or `None`. It is not an acceptance filter or confidence bound. |
| `litho_thickness_ref` | Optional independent thickness for comparison, never used to choose the fit. |

The public `invert` function returns the **calibrated per-sample DataFrame**,
not this internal dictionary. It also writes the full tables to Excel.

## Why the faster search gives the same answer

For each sample the observations are converted to log10 once. For each source
enrichment, `ModelLogCache` stores the scaled model logarithms and a mask of valid
predictions so other samples can reuse them. A fresh cache is made for every run;
the source grids must not be modified during that run.

The implementation deliberately keeps `log10(concentration * factor)` and the
original element-then-sample addition order. Algebraically equivalent changes can
alter floating-point rounding. Equal minima keep the first enrichment searched,
then the first cell in row-major order. These details matter for exact-fit tests.
The cache consumes roughly 63 MiB for the full bundled enrichment range.

The score is `sqrt(sum(log10 residual**2)/(N-3))`. It has no measurement-error
weights or covariance model, so it is not reduced chi-squared. The distribution of
this score under missing REEs and observational noise still needs scientific
validation. Reproducing the old results does not establish that validation.

## What a plotting archive contains

`run.zip` contains:

- `manifest.json`: format version, package and library versions, run options,
  and the location/count/file mapping for each fitted sample.
- `samples/000000.npz`, etc.: observations in the fixed REE order below, fitted
  patterns and annotations, `misfit_grid`, and two additional slices.
  `temperature_slice` has axes `(enrichment, temperature)` at the best thickness;
  `depth_slice` has axes `(enrichment, thickness)` at the best temperature.
  `grid_shape` records the original three-dimensional shape for index conversion.
- `summary.npz`: location labels and the four numerical columns used by group
  plots: calibrated thickness, calibrated temperature, enrichment and misfit.

REE order is La, Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu.
NumPy arrays keep their floating-point precision. No pickle objects are stored.
The format version identifies the schema; added descriptive manifest fields do
not change the arrays required by version 1. The reader rejects unknown versions.

An archive is a plotting snapshot, not the original data plus a complete scientific
provenance record. It does not retain every search cell or every input column.
It supports the existing figures, not arbitrary new slices. Exact pixels also
require the same plotting code, fonts and rendering environment; library versions
are recorded to help diagnose differences. A successful run replaces an existing
archive at the requested `.zip` path; a failed run leaves it intact.

## Checking a change

Run `pytest -m "slow or not slow"` for the regression suite, including the
olivine-correction example. `test_plot_archive.py` checks exact numerical and PNG
round trips, independent replotting, and failure handling.

For a full comparison of all returned and exported table values against main:

```sh
MPLBACKEND=Agg python tests/compare_search_revision.py --reference 0196fe6 --modern --plot-archive
```

This uses pre-corrected modern-OIB data. It does not repeat the full olivine
correction or validate the physical assumptions. Preserve the reference outputs
when making a change intended to leave scientific results unchanged.
