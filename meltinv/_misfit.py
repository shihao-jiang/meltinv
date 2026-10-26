"""Prepared log-concentrations for the exhaustive search (no scientific settings).

Model arrays have axes (REE, thickness row, temperature column). The cache is
local to one inversion run, so it cannot reuse predictions from another grid.
"""
import numpy as np
import pandas as pd


class ModelLogCache:
    """Cache each enrichment's log predictions and positive/finite mask.

    Keep log10(concentration * factor), rather than adding separate logarithms:
    this preserves the original floating-point operations, including exact fits.
    At 171 enrichments, 14 REEs and 53 x 58 cells the arrays occupy about 63 MiB.
    Treat the source grids as immutable for the lifetime of this cache.
    """

    def __init__(self, grids, mixing_function):
        self.grids = grids
        self.mixing_function = mixing_function
        self._entries = {}

    def get(self, enrichment):
        if enrichment not in self._entries:
            factors = self.mixing_function(enrichment)
            scaled = np.asarray([
                np.asarray(grid, dtype=float) * float(factors[ree])
                for grid, ree in zip(self.grids['simulation'], self.grids['ree_variables'])
            ])
            valid = np.isfinite(scaled) & (scaled > 0)
            logs = np.full_like(scaled, np.nan)
            logs[valid] = np.log10(scaled[valid])
            self._entries[enrichment] = logs, valid, factors
        return self._entries[enrichment]


def prepare_observations(df, mask, ree_variables, min_sample_count):
    """Prepare measured concentrations for repeated comparison with model grids.

    Return (element_index, log10_values) pairs in REE order. Each values array
    contains the positive, finite measurements for that element in sample order.
    min_sample_count is a count per element, not the six-REE sample filter used
    by invert_melt_condition. The public per-sample workflow passes 1 here.
    Concentrations must use the same units as the model (ppm).
    """
    observations = []
    for i, ree in enumerate(ree_variables):
        values = pd.to_numeric(df.loc[mask, ree], errors='coerce').to_numpy(dtype=float)
        values = values[np.isfinite(values) & (values > 0)]
        if len(values) >= min_sample_count:
            observations.append((i, np.log10(values)))
    return observations


def evaluate_misfit(observations, model_logs, model_valid, *, diagnostic_threshold=True):
    """Evaluate sqrt(sum(log10 residual squared) / (N - 3)) at every cell.

    N counts measured residuals; model_logs/model_valid have axes
    (REE, lithospheric-thickness row, excess-temperature column). Return
    (misfit_grid, tenth_percentile, best_index), where best_index is (row, col).
    With insufficient observations all three are None. If no model cell is
    valid, the grid contains NaNs and the last two values are None. The optional
    percentile is a legacy diagnostic, not a confidence threshold or filter.
    This residual measure is not an uncertainty-normalised reduced chi-squared.

    Any invalid prediction for a measured element excludes that model cell.
    Summation order matches the original element-then-sample loop. Ties select
    the first cell in row-major order; zero residuals remain valid minima.
    """
    residual_count = sum(len(values) for _, values in observations)
    if not observations or residual_count <= 3:
        return None, None, None
    valid = np.ones(model_logs.shape[1:], dtype=bool)
    squared = np.zeros(model_logs.shape[1:], dtype=float)
    for i, values in observations:
        usable = model_valid[i]
        valid &= usable
        for value in values:
            squared[usable] += (model_logs[i][usable] - value) ** 2
    misfit = np.where(valid, np.sqrt(squared / (residual_count - 3)), np.nan)
    if not valid.any():
        return misfit, None, None
    threshold = np.percentile(misfit[valid], 10) if diagnostic_threshold else None
    index = np.unravel_index(np.nanargmin(misfit), misfit.shape)
    return misfit, threshold, index
