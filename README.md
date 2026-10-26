# meltinv

**meltinv** is a Python package that uses the Rare Earth Element (REE) compositions of primary magmas to jointly invert for:

- **Mantle excess temperature** (mantle potential temperature above ambient, in K)
- **Lithospheric thickness** (km), and the depth range over which melting occurs
- **Relative source enrichment**, meaning how much the mantle source is enriched (or depleted) relative to primitive mantle

It also reports the melt fraction (`F`) and melting rate (`M`) of the best-fitting model.

Every sample is inverted **individually**. The results are then summarised for each location, and a figure compares the samples within each location.

> Looking for the version that fits one solution to a whole group of samples? It lives on the [`group_samples` branch](#group-inversion-the-group_samples-branch).

> Prefer not to use Python? The web app at **https://meltinv.streamlit.app** runs the same analysis from a web page: upload a spreadsheet and download the results and figures. [Tutorial 1](tutorials/01_web_app.md) shows how, and the [app's README](app/README.md) explains how it is hosted.

The package can be used from the **command line** or from **Python**. This README is written as a step-by-step tutorial. Work through it once with the bundled example file, then swap in your own data.

---

## Contents

1. [Installation](#1-installation)
2. [API summary](#2-api-summary)
   - [Arguments](#arguments)
   - [Command line](#command-line)
   - [Output files](#output-files)
3. [Tutorial: your first inversion](#3-tutorial-your-first-inversion)
   - [Step 1: Prepare the input file](#step-1-prepare-the-input-file)
   - [Step 2: (Optional) Fractionation correction](#step-2-optional-fractionation-correction)
   - [Step 3: Run the inversion](#step-3-run-the-inversion)
   - [Step 4: Reading the results](#step-4-reading-the-results)
   - [Step 5: Reading the figures](#step-5-reading-the-figures)
4. [Going further](#4-going-further)
   - [Using the results in Python](#using-the-results-in-python)
   - [Save a run and regenerate figures](#calculate-once-and-regenerate-figures-later)
   - [Group inversion: the group_samples branch](#group-inversion-the-group_samples-branch)
5. [How the inversion works](#5-how-the-inversion-works)
   - [Reading the source code](#reading-the-source-code)
6. [Troubleshooting](#6-troubleshooting)
7. [Running the tests](#7-running-the-tests)
8. [Citation](#8-citation)

---

## 1. Installation

meltinv requires **Python ≥ 3.11**. We recommend installing it in a fresh virtual environment:

```bash
git clone https://github.com/shihao-jiang/meltinv.git
cd meltinv
python3.11 -m venv venv
source venv/bin/activate
pip install .
```

This also installs all dependencies, including a patched version of [meltPT](https://github.com/shihao-jiang/meltPT_fixed) that is used for the fractionation correction. If you want to modify the package, install it in editable mode instead:

```bash
pip install -e .
```

Check that the command-line tool is available:

```bash
meltinv --help
```

---

## 2. API summary

```python
import meltinv

meltinv.invert(
    file_name,                        # .xlsx or .csv input file
    depleted_locations=None,          # locations whose source may be depleted
    correction=False,                 # run the fractionation correction first
    src_Fo=0.9,                       # forsterite content of source olivine
    max_olivine_addition=0.5,         # maximum olivine added during correction
    individual_sample_figures=False,  # 4-panel REE/misfit figure for each sample
    group_comparison_figure=True,     # comparison figure for each location
    plot_archive=None,               # optional .zip snapshot for plotting later
    fe3_fe_total=0.1,                 # Fe3+/total Fe used to split total iron in the correction
    measured_fe3=False,               # True: keep measured FeO/Fe2O3 where both are reported
)

meltinv.correction(file_name, src_Fo=0.9, max_olivine_addition=0.5, fe3_fe_total=0.1, measured_fe3=False)
```

### Arguments

| Argument | Command-line flag | Default | What it does |
|---|---|---|---|
| `file_name` | `FILE` | — | Input `.xlsx` or `.csv` file (see [Step 1](#step-1-prepare-the-input-file)). |
| `depleted_locations` | `--depleted LOC [LOC ...]` or `--depleted all` | `None` | By default, the source enrichment is searched from 0 to 15% basalt mixed into primitive mantle. For the locations given here, mixtures of primitive mantle with 5 to 100% depleted mantle are also searched; these appear as negative `basalt_percentage` values. Give location names or parts of names: matching is by substring and case-sensitive, so `Iceland` matches `Iceland (NNVZ)` but not `iceland`. Use `"all"` for every location. |
| `correction` | `--correction` | `False` | Correct evolved samples back to primary magma before inverting (see [Step 2](#step-2-optional-fractionation-correction)). |
| `src_Fo` | `--src_Fo` | `0.9` | Forsterite content of the mantle-source olivine. Used only by the correction. |
| `max_olivine_addition` | `--max_olivine_addition` | `0.5` | Maximum mass fraction of olivine that may be added. Used only by the correction. |
| `fe3_fe_total` | `--fe3_fe_total` | `0.1` | Fe³⁺/ΣFe used to split each sample's total iron into FeO and Fe2O3. Used only by the correction. |
| `measured_fe3` | `--measured_fe3` | `False` | Keep the measured FeO/Fe2O3 split of samples that report both, and apply `fe3_fe_total` only to the others. Off by default, because reported Fe2O3 is often raised by alteration. Used only by the correction. |
| `individual_sample_figures` | `--individual_sample_figures` | `False` | Save a 4-panel REE and misfit figure for each sample (see [Step 5](#step-5-reading-the-figures)). |
| `group_comparison_figure` | `--no_group_comparison_figure` turns it off | `True` | Save a figure comparing the samples at each location with ≥ 3 samples (see [Step 5](#step-5-reading-the-figures)). |
| `plot_archive` | `--plot_archive PATH.zip` | `None` | Save a plotting snapshot; does not itself draw figures. See [plotting later](#calculate-once-and-regenerate-figures-later). |

`meltinv.invert` returns the per-sample results as a pandas DataFrame, and `meltinv.correction` returns the corrected data. On the command line, the two functions are `meltinv invert FILE [flags]` and `meltinv correction FILE [flags]`.

Older argument names still work: `make_figures` (`--make_figures`) means `individual_sample_figures`, and `per_sample=True` (`--per_sample`) is accepted and ignored. `per_sample=False` raises an error, because group inversion is only on the [`group_samples` branch](#group-inversion-the-group_samples-branch).

### Command line

```text
meltinv correction FILE [--src_Fo 0.9] [--max_olivine_addition 0.5] [--fe3_fe_total 0.1] [--measured_fe3]

meltinv invert FILE [--depleted LOC [LOC ...] | --depleted all]
                    [--correction] [--src_Fo 0.9] [--max_olivine_addition 0.5] [--fe3_fe_total 0.1]
                    [--measured_fe3]
                    [--individual_sample_figures] [--no_group_comparison_figure]
                    [--plot_archive PATH.zip]

meltinv plot PATH.zip [--output_dir DIR] [--no_individual] [--no_groups]
```

For example, to treat the Iceland and Galápagos locations as possibly depleted, correct the samples first and save the individual figures:

```bash
meltinv invert input.xlsx --depleted Iceland Galapagos --correction --individual_sample_figures
```

### Output files

All paths are relative to the current working directory. `{name}` is the input file name without its extension; a trailing `_corrected` is dropped.

| File | Produced by |
|---|---|
| `inversion_results/{name}_corrected.xlsx` | `correction`, or `invert --correction` |
| `inversion_results/{name}_sample_inversion_log10.xlsx` | `invert` (one row per sample) |
| `inversion_results/{name}_sample_inversion_summary_log10.xlsx` | `invert` (one row per location) |
| `inversion_figures/group_comparison_{location}_N{count}.png` | `invert` (unless `--no_group_comparison_figure`) |
| `inversion_figures/ree_comparison_{location}__sample{n}_log10_N1.png` | `invert --individual_sample_figures` |

Existing files with the same name are overwritten. A requested `.zip` plotting
archive is separate from these tables and is replaced only after a successful run.

---

## 3. Tutorial: your first inversion

The repository ships with **`examples.xlsx`**, which contains 38 basalts from five Austral–Cook islands (Mangaia, Raivavae, Rapa, Atiu and Marotiri). We will use it throughout this tutorial.

> All outputs are written to `inversion_results/` and `inversion_figures/` inside your **current working directory**, not next to the input file. Run meltinv from the folder where you want the results to appear.

### Step 1: Prepare the input file

meltinv reads **`.xlsx`** or **`.csv`** files with one row per sample. Extra columns are allowed and are carried through to the outputs.

**Always required:**

| Column | Meaning |
|---|---|
| `location` | Location label. Samples with the same `location` are summarised and plotted together. |
| `La`, `Ce`, `Pr`, `Nd`, `Sm`, `Eu`, `Gd`, `Tb`, `Dy`, `Ho`, `Er`, `Tm`, `Yb`, `Lu` | REE concentrations (ppm) |

For the REE columns:

- Missing values are fine. Blank cells, `0`, negative values and text (such as `bdl`) are all treated as missing.
- Each sample is fitted using whichever of the 14 REE it has values for.
- At least 6 usable REE values are required for one sample to be inverted. Samples with fewer are skipped, with a message naming the location and sample number.

**Required only if you run the fractionation correction (Step 2):**

| Column | Meaning |
|---|---|
| `SiO2`, `TiO2`, `Al2O3`, `FeO`, `CaO`, `MgO`, `MnO`, `K2O`, `Na2O`, `P2O5` | Major-element oxides (wt%) of the measured (evolved) sample |

**Optional:**

| Column | Meaning |
|---|---|
| `thickness` | An independent estimate of lithospheric thickness (km), for example from seismology. It is **not** used in the inversion. It is reported as `litho_thickness_ref` and drawn as a dashed line on the individual figures for comparison. |


### Step 2: (Optional) Fractionation correction

The inversion compares your data with **primary-magma** REE concentrations. If your samples are evolved, first correct them back to a primary composition. meltinv does this with meltPT, which adds olivine incrementally until the melt is in equilibrium with mantle olivine of forsterite content `src_Fo`.

**Command line:**

```bash
meltinv correction examples.xlsx --src_Fo 0.9 --max_olivine_addition 0.5
```

**Python:**

```python
import meltinv

corrected = meltinv.correction("examples.xlsx", src_Fo=0.9, max_olivine_addition=0.5)
```

This writes `inversion_results/examples_corrected.xlsx`. The file contains:

- all your original columns, with the **REE columns replaced** by primary-magma values (diluted by the added olivine, `REE × (1 − ol_added)`);
- `ol_added`, the mass fraction of olivine added to each sample;
- `SiO2_primary`, `TiO2_primary`, …, `P2O5_primary`, the reconstructed primary major-element composition;
- `correction_success`, which is `False` for samples that cannot be corrected. These are already more magnesian than a melt in equilibrium with `src_Fo` olivine, usually because they contain accumulated olivine crystals. Their REE are set to missing, so they are not inverted.

Iron is treated the same way for every sample: total iron is split into FeO and Fe2O3 using `fe3_fe_total` (Fe³⁺/ΣFe = 0.1 by default). Add `measured_fe3=True` (`--measured_fe3`) to keep the measured FeO/Fe2O3 of samples that report both.

> If the input is an Excel file, a `.csv` copy is also written next to it, because meltPT reads CSV.

**Skip this step** if your file already contains primary-magma REE concentrations.

### Step 3: Run the inversion

You can either invert a file that is already corrected, or correct and invert in one go.

**Option A: correct and invert in one command** (recommended for the example):

```bash
meltinv invert examples.xlsx --correction
```

```python
import meltinv

results = meltinv.invert("examples.xlsx", correction=True)
```

**Option B: invert data that is already primary**, such as the output of Step 2:

```bash
meltinv invert inversion_results/examples_corrected.xlsx
```

```python
results = meltinv.invert("inversion_results/examples_corrected.xlsx")
```

While it runs, meltinv prints each sample (labelled `{location}__sample{n}`), followed by every enrichment value that improves the fit. With `--correction`, meltPT first prints a long log of the olivine addition. The example takes about a minute.

```text
Austral-Cook Islands (Atiu)__sample1 Sample number: 1
Scale: 0.0 Global min misfit: ...
Scale: 0.1 Global min misfit: ...
...
Results saved to: .../inversion_results/examples_sample_inversion_log10.xlsx
Results saved to: .../inversion_results/examples_sample_inversion_summary_log10.xlsx
Figure saved to: .../inversion_figures/group_comparison_Austral-Cook Islands (Atiu)_N3.png
...
Figure saved to: .../inversion_figures/group_comparison_Austral-Cook Islands (Marotiri)_N1.png
```

Marotiri has only one sample. It is still inverted, appears in both results files and gets a group comparison figure, but with no standard-deviation band (see Step 5).

### Step 4: Reading the results

The inversion writes two results files.

**1. Location summary:** `inversion_results/examples_sample_inversion_summary_log10.xlsx`

This file has one row per location, made by combining the per-sample results:

1. Every column is averaged over all inverted samples at that location, with weights of `1 / (misfit_value + 1e-6)`, so better-fitting samples count for more.
2. `T_mean_cali`, `depth_mean_cali` and `basalt_percentage` also get `_err_minus` and `_err_plus` columns (weighted mean ± weighted standard deviation), in the same units as the mean. Only the figures compress negative (depleted) enrichment values by dividing them by 100. With a single sample the standard deviation is zero, so both bounds equal the mean.

For the example, the main columns look like this:

| location | count | T_mean_cali (K) | T range (K) | depth_mean_cali (km) | depth range (km) | basalt_percentage | litho_thickness_ref (km) |
|---|---|---|---|---|---|---|---|
| Austral-Cook Islands (Atiu) | 3 | 67.7 | 64.3–71.0 | 60.3 | 56.4–64.1 | 5.1 | 86.7 |
| Austral-Cook Islands (Mangaia) | 12 | 86.4 | 66.8–106.1 | 58.7 | 54.5–62.8 | 3.5 | 83.4 |
| Austral-Cook Islands (Marotiri) | 1 | 106.3 | — | 64.5 | — | 4.0 | 68.3 |
| Austral-Cook Islands (Raivavae) | 13 | 104.4 | 64.5–144.2 | 62.4 | 46.7–78.1 | 3.5 | 73.8 |
| Austral-Cook Islands (Rapa) | 6 | 159.3 | 134.1–184.5 | 91.9 | 81.3–102.5 | 6.2 | 67.9 |

The ranges are the `_err_minus` to `_err_plus` columns. Three of the 38 samples (two from Mangaia, one from Raivavae) are not inverted: their MgO is above 19 wt%, and the olivine correction cannot be applied (see Step 2).

**2. Per-sample results:** `inversion_results/examples_sample_inversion_log10.xlsx`

This file has one row per sample, in the same order as your input file. `sample_number` counts samples (1, 2, …) within each location.

Both files share these columns:

| Column | Meaning |
|---|---|
| `location`, `count` | Location name. In the summary file, `count` is the number of samples at that location; in the per-sample file it is always 1. |
| `T_mean` | Best-fit mantle excess temperature (K) from the peridotite melting grid |
| `T_mean_cali` | `T_mean` after the source-lithology calibration (see [§5](#5-how-the-inversion-works)). **Use this value.** |
| `depth_mean` | Best-fit lithospheric thickness (km) from the grid |
| `depth_mean_cali` | Calibrated lithospheric thickness (km). **Use this value.** |
| `pres_mean_cali`, `pres_min_cali`, `pres_max_cali` | Mean, minimum and maximum melting depth (km, about 33 km/GPa), shifted by the same calibration as the thickness |
| `F_mean`, `F_min`, `F_max` | Mean, minimum and maximum melt fraction of the best-fit model |
| `M_mean`, `M_min`, `M_max` | Mean, minimum and maximum melting rate of the best-fit model |
| `basalt_percentage` | Best-fit **relative source enrichment**. Positive values (0 to 15) are the % of basalt mixed into primitive mantle. Negative values (−100 to −5, only with `--depleted`) are the % of depleted mantle mixed into primitive mantle. |
| `misfit_value` | RMS log10 misfit of the best-fit model (lower is better; see [§5](#5-how-the-inversion-works)) |
| `global_min_value` | Lowest misfit anywhere in the full temperature–thickness–enrichment search |
| `ratio_of_local_global_misfit` | `misfit_value / global_min_value`. A value of 1 means the reported solution is the global minimum. |
| `litho_thickness_ref` | Your optional `thickness` value (empty if not supplied) |

### Step 5: Reading the figures

meltinv can make two kinds of figure. Both are saved in `inversion_figures/`.

#### Group comparison figures (on by default)

One figure per location is saved as `inversion_figures/group_comparison_{location}_N{count}.png`. It compares the per-sample results within that location:

| Panel | What it shows |
|---|---|
| **(a)** | Excess temperature vs lithospheric thickness, one point per sample |
| **(b)** | Relative enrichment vs lithospheric thickness |
| **(c)** | Excess temperature vs relative enrichment |
| **(d-1) to (d-3)** | Histograms of temperature, thickness and enrichment. The dashed line is the misfit-weighted mean and the grey band is ± 1 weighted standard deviation, computed using the same weighting rule as the location summary in Step 4. Enrichment histograms apply the display transformation before computing their statistics, so these need not equal a transformation of the exported mean and bounds. |

In panels (a) to (c), points are coloured by misfit; darker blue is a better fit. Depleted enrichment values (negative) are divided by 100 so they fit on the same axis. Panel (d) marks the weighted mean of each histogram and, for locations with at least 3 samples, a ±1 standard-deviation band; locations with one or two samples get the mean only.

The axes are fixed (temperature 50 to 300 K, thickness 15 to 130 km, enrichment −1.2 to 16) so that figures for different locations can be compared directly. Samples outside these ranges are not shown.

To turn these figures off, use `--no_group_comparison_figure` (Python: `group_comparison_figure=False`).

#### Individual figures (`--individual_sample_figures`)

With `--individual_sample_figures`, one figure per sample is saved as `inversion_figures/ree_comparison_{location}__sample{n}_log10_N1.png`. These are off by default because large datasets would produce many files.

```bash
meltinv invert examples.xlsx --correction --individual_sample_figures
```

Each individual figure has four panels:

| Panel | What it shows |
|---|---|
| **Top left** | Chondrite-normalised REE pattern: the sample (black), the best-fit model (red) with its forward-model min/max envelope (shading), and the global best fit (orange). The inverted temperature, thickness and enrichment are printed in the corner. |
| **Top right** | Misfit across excess temperature and lithospheric thickness, at the best-fit enrichment. Colours and contours show misfit divided by the minimum misfit, so 1.1 means 10% worse than the best fit. The red star marks the best fit, the orange circle the global minimum, and the dashed line `litho_thickness_ref`. |
| **Bottom left** | Misfit across excess temperature and enrichment, at the best-fit thickness |
| **Bottom right** | Misfit across thickness and enrichment, at the best-fit temperature |

The contours describe how misfit changes around the best fit; they are not statistical confidence regions. Individual figures show the uncalibrated fit, while group figures use the calibrated parameters. If the best misfit is exactly zero, the colour scale and contours show absolute misfit instead of a ratio. A long, narrow low-misfit valley, as in the temperature–thickness panel, shows a trade-off between the two parameters.

---

## 4. Going further

### Using the results in Python

`meltinv.invert` returns the per-sample results as a pandas DataFrame, so you can analyse them directly:

```python
import meltinv

df = meltinv.invert("examples.xlsx", correction=True)

print(df[["location", "sample_number", "T_mean_cali", "depth_mean_cali", "basalt_percentage"]])

# Spread of inverted temperatures at each location
print(df.groupby("location")["T_mean_cali"].describe())
```

The location summary is written to file only. Read it back with pandas if you need it:

```python
import pandas as pd

summary = pd.read_excel("inversion_results/examples_sample_inversion_summary_log10.xlsx")
```

### Calculate once and regenerate figures later

To restyle or redraw figures without rerunning the inversion, save a plot
archive during the run. It holds everything the individual and group
comparison figures need:

```python
from meltinv import invert, regenerate_figures

results = invert(
    "samples.csv",
    individual_sample_figures=False,
    group_comparison_figure=False,
    plot_archive="run.zip",
)
# Later, even in a new Python session without samples.csv or the model grids:
regenerate_figures("run.zip", output_dir="replotted_figures")
```

The equivalent CLI commands are:

```sh
meltinv invert samples.csv --no_group_comparison_figure --plot_archive run.zip
meltinv plot run.zip --output_dir replotted_figures
```

`regenerate_figures` accepts `individual_sample_figures=False` or
`group_comparison_figure=False` to render only one type; the CLI equivalents
are `--no_individual` and `--no_groups`.

The archive is a **plotting snapshot**: the REE observations actually used
(after any correction), the fitted patterns, the three misfit slices shown in
each individual figure and the calibrated values used by the group figures.
It does not hold the full search surface, so a different slice needs a new
inversion; the Excel tables remain the full results. Saving makes a run slower
(about 26 s → 43 s for the full modern-OIB dataset in one timing test), so it is off
by default. A failed run leaves any earlier archive at that path untouched.

### Group inversion: the group_samples branch

This version (`main`) always inverts each sample individually. The **`group_samples`** branch keeps the older group inversion, which fits one solution to all samples at a location together (at least 2 samples per location). To use it, install that branch instead:

```bash
git clone -b group_samples https://github.com/shihao-jiang/meltinv.git meltinv-group
cd meltinv-group
pip install .
```

On that branch, group inversion is the default and `--per_sample` switches to the per-sample inversion described here. See the README on that branch for details.

---

## 5. How the inversion works

1. **Forward-model grid.** The package ships with precomputed melting models (`meltinv/data/*.npy`). They give the REE concentrations of accumulated melts, with min/max envelopes, melting depths, melt fractions (`F`) and melting rates (`M`). The grid spans mantle excess temperature (65 to 350 K in 5 K steps) and lithospheric thickness (16 to 120 km in 2 km steps).
2. **Source enrichment.** For each trial enrichment value, the model REE concentrations are rescaled for a source made by mixing:
   - primitive mantle (McDonough & Sun, 1995) with 0 to 15% basalt (Sun & McDonough, 1989), in steps of 0.1%; or
   - with `--depleted`, primitive mantle with 5 to 100% depleted mantle (Salters & Stracke, 2004).
3. **Misfit.** For each sample, the misfit is the root-mean-square (RMS) of the log10 residuals over the N usable REE, corrected for the 3 fitted parameters (temperature, thickness and enrichment): misfit = √( Σ (log10 c_model − log10 c_sample)² / (N − 3) ). This is the current residual statistic, not a reduced chi-squared: no measurement uncertainties or REE error covariance are used. The ordinary RMS log residual is this statistic multiplied by √((N − 3)/N), so its numerical value should not be interpreted directly as a typical percentage error.
4. **Best fit.** For each sample, the temperature, thickness and enrichment combination with the lowest misfit is reported.
5. **Calibration.** The grid assumes a peridotite source. The best-fit temperature and thickness are then corrected for the effect of a pyroxenite (G2) component on the solidus. This uses flux-weighted mixing (Phipps Morgan, 2001; Sobolev et al., 2007), with the pyroxenite fraction taken from the inverted enrichment. The results are the `_cali` columns.
6. **Location summary.** The per-sample results are combined for each location with a misfit-weighted average, as described in [Step 4](#step-4-reading-the-results).

The individual diagnostic figures show the **uncalibrated** fit from step 4 (`T_mean`, `depth_mean`). The results tables' `_cali` columns and the group comparison figures use the **calibrated** values from step 5, so a sample's temperature can differ between the two kinds of figure.

### Reading the source code

| Question | Start here |
|---|---|
| What arguments can I pass? | `core.py`: `invert` is the Python entry point; `cli.py` maps command-line options onto the same call. |
| Which observations are used? | `inversion.py`: `invert_melt_condition` reads and optionally corrects the data, cleans the REEs and applies the six-usable-REE rule. |
| What exactly is searched? | `inversion.py`: `get_enrichment_values`, `source_composition_mix`, then `invert_single_group`. Despite its name, the workflow calls it for **one sample** at a time. Its docstring lists every field of the result. |
| Where is the misfit calculated? | `_misfit.py`: `prepare_observations` and `evaluate_misfit`. Model log-concentrations are cached once per enrichment value and reused across samples. |
| What does calibration change? | `inversion.py`: `calibration` adjusts the fitted temperature and thickness **after** the REE fit; it does not refit. |
| How are locations summarised? | `inversion.py`: `aggregate_per_sample_results`. |
| How do I change a figure? | `plotting.py`: `plot_results` (individual figures) and `plot_group_comparison` (group figures). |
| How do I redraw figures from an old run? | `plot_archive.py`: `regenerate_figures`. Its module docstring describes the archive layout. |

Some names are historical and can mislead:

- `p_idx` is a lithospheric-thickness row (`16 + 2 × p_idx` km), not a pressure; `t_idx` is a temperature column (`65 + 5 × t_idx` K).
- `pres_mean`, `pres_min` and `pres_max` (and their `_cali` versions) are melting **depths in km**. Calibration divides the mean depth by 33 to get GPa.
- `basalt_percentage` is the source-enrichment parameter: positive values mix primitive mantle with basalt, negative values with depleted mantle.
- `global_min_value` always equals `misfit_value`, and `ratio_of_local_global_misfit` is always 1. Both are kept so the output columns do not change.

---

## 6. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `The following required columns are missing: ...` | Column names are case-sensitive. Check `location` and the 14 REE names. |
| `Unsupported file format` | Only `.xlsx`, `.xls` and `.csv` are accepted. |
| A sample is missing from the results | It has fewer than 6 usable REE values. Look for a `Skipping ... sample n` message in the output. |
| A sample is missing from a group comparison figure | Its result lies outside the fixed axis ranges. Check the per-sample results file. |
| `KeyError` on `SiO2` (or another oxide) during correction | The correction needs all 10 major-oxide columns listed in [Step 1](#step-1-prepare-the-input-file). |
| `per_sample=False` raises an error | Group inversion is only on the [`group_samples` branch](#group-inversion-the-group_samples-branch). |
| Results appear in an unexpected folder | Outputs go to the **current working directory**. `cd` to where you want them before running. |

---

## 7. Running the tests

meltinv has an automated test suite in `tests/`. It checks the misfit, the input cleaning, the olivine-correction handling, the location summaries and the command line, and compares a full inversion of the example data with stored reference results.

Install the test dependencies once, from the repository folder:

```bash
pip install -e ".[test]"
```

Then run the tests:

```bash
pytest
```

This takes about 30 seconds. To also run the slower test that redoes the meltPT olivine correction:

```bash
pytest -m "slow or not slow"
```

The same tests run automatically on GitHub for every push and pull request (see the **Actions** tab).

To check that a change leaves every result unchanged, compare it with an earlier Git revision. The script runs both versions on the same input and requires every value in the returned table and both exported spreadsheets to be identical:

```bash
python tests/compare_search_revision.py --reference 0196fe6
python tests/compare_search_revision.py --reference 0196fe6 --modern
```

The second command uses all bundled pre-corrected modern-OIB samples; add `--plot-archive` to include archive saving. The reported times include file input/output but not the olivine correction or figures. This checks that two implementations agree, not that the model is physically right.

**When you change the code:**

- If every test passes, the change has not affected anything the tests check.
- If `test_reference.py` fails after a change that was meant to alter the results (for example a new misfit or calibration), regenerate the reference with `python tests/update_reference.py` (add `--correct` if the olivine correction changed), and say why in the commit message.
- If a test fails after a change that was *not* meant to alter the results, the failure points to a bug.
- When you fix a bug, add a test that would have caught it.

---

## 8. Citation

If you use **meltinv** in your research, please cite:

Jiang et al. (2026), xxx, *Journal Name*.

## License

MIT. See [LICENSE](LICENSE).
