# meltinv tutorials

Step-by-step tutorials that take you through a meltinv analysis. **Tutorial 1** uses the meltinv website and needs no programming. **Tutorials 2 and 3** are Jupyter notebooks that use meltinv from Python. You can read the notebooks online, run them in your browser without installing anything, or run them on your own computer.

[![Launch on Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/shihao-jiang/meltinv/main?labpath=tutorials%2F02_python_quick_start.ipynb)

| Tutorial | What you will do | Data | Run time |
|---|---|---|---|
| [01 – The meltinv website](01_web_app.md) | Upload the example file to the website, choose the options, and read the downloaded results and figures. No programming | `examples.xlsx` (38 samples) | ~1 min |
| [02 – Quick start in Python](02_python_quick_start.ipynb) | The same analysis from Python: input checks, olivine correction, results tables, figures, redrawing figures from a saved run, and a comparison with seismic thickness | `examples.xlsx` (38 samples) | ~1 min |
| [03 – Modern ocean-island basalts](03_modern_OIB.ipynb) | The paper's comparison: a hands-on run on five locations, then the full dataset (1,801 samples, 112 locations), quality checks, a comparison with seismic, thermobarometric and published estimates, and the paper figure with and without the T–P correction | `data/modern_OIB.xlsx` and the stored full results | ~2 min (about 10 min with `RUN_FULL_ANALYSIS = True`) |

## Reading the tutorials online

The notebooks are saved with all their outputs and figures, so you can read them without running anything:

- on GitHub, by clicking a notebook in the table above;
- on [nbviewer](https://nbviewer.org/github/shihao-jiang/meltinv/blob/main/tutorials/02_python_quick_start.ipynb), which renders notebooks a little more faithfully.

## Running the tutorials in your browser (Binder)

Click the **launch binder** button above. [Binder](https://mybinder.org) builds a temporary JupyterLab with meltinv installed and opens Tutorial 2. The first launch can take a few minutes. Binder sessions are temporary, so download anything you want to keep before closing the tab.

## Running the tutorials on your own computer

Install meltinv with the notebook tools, from the repository folder:

```bash
pip install -e ".[tutorials]"
```

Then start JupyterLab from the `tutorials` folder, using the same Python that meltinv is installed in:

```bash
cd tutorials
python -m jupyterlab
```

Open a notebook and run the cells from top to bottom (**Run → Run All Cells**).

If the first cell fails with `ModuleNotFoundError: No module named 'meltinv'`, the notebook is running in a different Python from the one meltinv is installed in. Close JupyterLab and start it again with `python -m jupyterlab` from the environment where you installed meltinv. On macOS, plain `jupyter lab` can pick the wrong Python.

The data used by the tutorials, and their sources, are described in [data/README.md](data/README.md).

Each tutorial writes its outputs to its own folder, `tutorials/output/<tutorial name>/`, so nothing is written into the rest of the repository. Delete that folder at any time to start again.
