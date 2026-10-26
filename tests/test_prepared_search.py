"""Numerical equivalence of cached searches, diagnostic retention and tie handling."""
import numpy as np
import pandas as pd
import pytest

from meltinv._misfit import ModelLogCache, prepare_observations, evaluate_misfit
from meltinv.inversion import source_composition_mix, invert_single_group


@pytest.mark.parametrize('enrichment', [-100, -35, 0, 7.3, 15])
@pytest.mark.parametrize('min_count', [1, 3])
def test_prepared_scores_match_direct_formula_bit_for_bit(enrichment, min_count):
    rng = np.random.default_rng(23102026)
    names = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu']
    model = rng.uniform(0.1, 20, (6, 3, 4))
    model[1, 0, 0] = np.nan
    model[2, 0, 1] = 0
    model[3, 0, 2] = np.inf
    df = pd.DataFrame(rng.uniform(0.1, 20, (3, 6)), columns=names)
    df.loc[0, 'La'] = np.nan
    df.loc[1, 'Ce'] = -1
    df.loc[2, 'Eu'] = np.inf
    grids = {'ree_variables': names, 'simulation': model}
    cache = ModelLogCache(grids, source_composition_mix)
    logs, valid, factors = cache.get(enrichment)
    assert cache.get(enrichment)[0] is logs
    observations = prepare_observations(df, [True] * 3, names, min_count)
    got, threshold, index = evaluate_misfit(observations, logs, valid)

    # Independent direct evaluation of the original element-then-sample formula.
    total = np.zeros((3, 4))
    admissible = np.ones((3, 4), dtype=bool)
    n = 0
    for i, name in enumerate(names):
        measurements = df[name][np.isfinite(df[name]) & (df[name] > 0)]
        if len(measurements) < min_count:
            continue
        prediction = model[i] * factors[name]
        usable = np.isfinite(prediction) & (prediction > 0)
        admissible &= usable
        for observed in measurements:
            total[usable] += (np.log10(prediction[usable]) - np.log10(observed)) ** 2
            n += 1
    expected = np.where(admissible, np.sqrt(total / (n - 3)), np.nan)
    np.testing.assert_array_equal(got, expected)
    assert index == np.unravel_index(np.nanargmin(expected), expected.shape)
    assert threshold == np.percentile(expected[admissible], 10)


def test_streamed_and_diagnostic_search_keep_first_tie(monkeypatch):
    names = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu']
    predictions = np.ones((6, 2, 3))
    grids = {'ree_variables': names, 'simulation': predictions,
             'lower': predictions, 'upper': predictions}
    for key in ['pres', 'F', 'M']:
        for statistic in ['mean', 'min', 'max']:
            grids[f'{key}_{statistic}'] = np.ones((2, 3))
    df = pd.DataFrame([{'location': 'A', **dict.fromkeys(names, 1.0)}])
    monkeypatch.setattr('meltinv.inversion.source_composition_mix',
                        lambda _: dict.fromkeys(names, 1.0))
    dense = invert_single_group(df, 'A', 1, grids, [-5, 0, 5], min_sample_count=1)
    streamed = invert_single_group(df, 'A', 1, grids, [-5, 0, 5], min_sample_count=1,
                                   retain_diagnostics=False)
    assert dense['full_3d_grids'].shape == (3, 2, 3)
    assert streamed['full_3d_grids'] is None
    assert streamed['threshold'] is None
    assert streamed['basalt_percentage'] == -5
    assert streamed['min_idx'] == (0, 0)
    assert streamed['global_flat_index'] == 0
    assert streamed['misfit_value'] == 0
    for key in dense.keys() - {'full_3d_grids', 'threshold'}:
        np.testing.assert_equal(streamed[key], dense[key], err_msg=key)


def test_individual_figures_still_have_diagnostic_surfaces(in_tmp, grid_sample):
    from meltinv import invert
    from conftest import write_csv
    write_csv([grid_sample(location='A')[0]], 'sample.csv')
    result = invert('sample.csv', individual_sample_figures=True,
                    group_comparison_figure=False)
    assert result.misfit_value.iloc[0] < 1e-12
    assert (in_tmp / 'inversion_figures/ree_comparison_A__sample1_log10_N1.png').exists()
