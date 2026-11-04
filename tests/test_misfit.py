"""The misfit: RMS of log10 residuals normalised by N - 3, and how the best fit is selected."""
import numpy as np
import pandas as pd
import pytest

import meltinv
from meltinv.inversion import compute_total_ree_misfit
from conftest import write_csv

NAMES = ['La', 'Ce', 'Pr', 'Nd', 'Sm']        # 5 elements -> 2 degrees of freedom


def misfit_grid(models, observed, names=NAMES):
    """Misfit on a hand-made grid: models has shape (n_elements, rows, cols); enrichment 0 (factors = 1)."""
    df = pd.DataFrame([observed], columns=names)
    grids = {"ree_variables": names, "simulation": np.asarray(models, dtype=float)}
    return compute_total_ree_misfit(df, [True], 0, grids, min_sample_count=1)


def test_rms_misfit_is_normalised_by_n_minus_3():
    observed = [1.0] * 5
    models = np.ones((5, 1, 2))
    models[:, 0, 1] = 10.0 ** np.array([0.1, -0.2, 0.0, 0.3, 0.1])   # known log10 residuals
    grid, _, best, _ = misfit_grid(models, observed)
    expected = np.sqrt(np.sum(np.array([0.1, -0.2, 0.0, 0.3, 0.1]) ** 2) / (5 - 3))
    assert grid[0, 1] == pytest.approx(expected)
    assert grid[0, 0] == 0
    assert best == (0, 0)


def test_exact_match_with_zero_misfit_is_selected():
    # Regression (PR #1): cells with zero misfit used to be excluded, so a neighbouring cell was chosen.
    observed = [2.0, 3.0, 4.0, 5.0, 6.0]
    models = np.empty((5, 1, 3))
    models[:, 0, 0] = np.array(observed) * 1.2
    models[:, 0, 1] = observed                      # exact match
    models[:, 0, 2] = np.array(observed) * 0.9
    grid, _, best, _ = misfit_grid(models, observed)
    assert best == (0, 1)
    assert grid[best] == 0


def test_flat_misfit_still_returns_a_best_fit():
    grid, _, best, _ = misfit_grid(np.full((5, 1, 2), 2.0), [1.0] * 5)
    assert best is not None
    assert np.allclose(grid, grid[0, 0])


@pytest.mark.parametrize("bad", [0.0, -1.0, np.inf, np.nan])
def test_invalid_model_prediction_excludes_the_cell(bad):
    # Regression (PR #1): a cell that cannot predict a measured element must not be fitted.
    models = np.ones((5, 1, 2))
    models[:, 0, 1] = 1.5
    models[2, 0, 0] = bad                            # cell (0, 0) is otherwise a perfect fit
    grid, _, best, _ = misfit_grid(models, [1.0] * 5)
    assert np.isnan(grid[0, 0])
    assert best == (0, 1)


def test_non_positive_and_infinite_observations_are_ignored():
    observed = [1.0, 1.0, 1.0, 1.0, np.inf]
    grid, _, best, _ = misfit_grid(np.ones((5, 1, 1)), observed)
    assert grid[0, 0] == 0                          # the infinite value is not used
    assert best == (0, 0)


def test_three_or_fewer_residuals_cannot_be_fitted():
    names = ['La', 'Ce', 'Pr']
    out = misfit_grid(np.ones((3, 1, 1)), [1.0, 1.0, 1.0], names)
    assert out == (None, None, None, None)


def test_misfit_scales_with_number_of_elements_as_expected():
    # Same residual on every element: RMS/(N-3) = |r| * sqrt(N / (N - 3)).
    r = 0.05
    for n in [6, 10, 14]:
        names = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu'][:n]
        grid, *_ = misfit_grid(np.full((n, 1, 1), 10 ** r), [1.0] * n, names)
        assert grid[0, 0] == pytest.approx(r * np.sqrt(n / (n - 3)))


@pytest.mark.parametrize("k, enrichment", [(500, 0.0), (1200, 3.0), (1800, 11.7)])
def test_sample_taken_from_the_model_grid_is_recovered_exactly(in_tmp, grid_sample, k, enrichment):
    # End to end through meltinv.invert, on the packaged grids.
    row, T, h = grid_sample(k=k, enrichment=enrichment)
    write_csv([row], "synthetic.csv")
    out = meltinv.invert("synthetic.csv", group_comparison_figure=False)
    assert out.T_mean.iloc[0] == T
    assert out.depth_mean.iloc[0] == h
    assert out.basalt_percentage.iloc[0] == pytest.approx(enrichment)
    assert out.misfit_value.iloc[0] < 1e-12
    assert out.ratio_of_local_global_misfit.iloc[0] == 1
