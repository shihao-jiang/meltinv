"""Shared fixtures for the meltinv test suite."""
import os

os.environ.setdefault("MPLBACKEND", "Agg")      # no plotting windows during tests

import numpy as np
import pandas as pd
import pytest

from meltinv.inversion import load_all_grids, source_composition_mix

REE = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
MAJORS = ['SiO2', 'TiO2', 'Al2O3', 'FeO', 'CaO', 'MgO', 'MnO', 'K2O', 'Na2O', 'P2O5']


@pytest.fixture(scope="session")
def grids():
    return load_all_grids()


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    """Run the test inside an empty folder, since meltinv writes its outputs to the working directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def grid_sample(grids):
    """Return a function that makes a synthetic sample whose REE equal one model grid cell exactly."""
    valid = np.argwhere(np.isfinite(grids["simulation"]).all(axis=0) & (grids["simulation"] > 0).all(axis=0))

    def make(k=500, enrichment=0.0, location="synthetic"):
        row, col = valid[k]
        mix = source_composition_mix(enrichment)
        values = {r: grids["simulation"][i, row, col] * mix[r] for i, r in enumerate(REE)}
        return {"location": location, **values}, 67.5 + 5 * col, 16 + 2 * row

    return make


def write_csv(rows, name):
    """Write sample rows to CSV with full precision, so exact grid values survive the round trip."""
    pd.DataFrame(rows).to_csv(name, index=False, float_format="%.17g")
    return name
