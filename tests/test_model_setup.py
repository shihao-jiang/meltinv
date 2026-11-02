"""Packaged model grids, source compositions, enrichment ranges and the T-P correction."""
import numpy as np
import pytest

import meltinv
from meltinv.inversion import calibration, get_enrichment_values, lree_depleted, source_composition_mix
from conftest import REE, write_csv


def test_packaged_grids_have_the_expected_shape(grids):
    assert grids["ree_variables"] == REE
    assert grids["simulation"].shape == (14, 53, 58)        # REE x thickness x temperature
    for key in ["lower", "upper"]:
        assert grids[key].shape == grids["simulation"].shape
    for key in ["pres_mean", "F_mean", "M_mean"]:
        assert grids[key].shape == (53, 58)


def test_enrichment_search_ranges():
    default = get_enrichment_values(False)
    assert len(default) == 151 and default[0] == 0 and default[-1] == pytest.approx(15.0)
    extended = get_enrichment_values(True)                       # adds -100 to -5
    assert len(extended) == 171 and extended[0] == -100 and extended[19] == -5


def test_only_lree_depleted_samples_search_depleted_sources():
    # (La/Sm)_N = (La/0.648)/(Sm/0.406), primitive mantle of McDonough & Sun (1995)
    assert lree_depleted(0.5 * 0.648, 0.406)                    # (La/Sm)_N = 0.5
    assert not lree_depleted(0.648, 0.406)                      # exactly primitive mantle
    assert not lree_depleted(2 * 0.648, 0.406)
    for la, sm in [(np.nan, 1.0), (1.0, np.nan), (0.0, 1.0), (1.0, 0.0)]:
        assert not lree_depleted(la, sm)                        # missing or zero: enriched search only


def test_depleted_search_follows_each_sample_la_sm(in_tmp, grid_sample):
    # cell 426 is among the most LREE-depleted model cells: (La/Sm)_N = 0.75 with 60% depleted mantle
    rows = [grid_sample(k=426, enrichment=-60, location="A")[0],
            grid_sample(k=426, enrichment=-60, location="A")[0]]
    rows[1]["La"] = 3 * rows[1]["Sm"] * 0.648 / 0.406            # same sample made LREE-enriched
    assert lree_depleted(rows[0]["La"], rows[0]["Sm"]) and not lree_depleted(rows[1]["La"], rows[1]["Sm"])
    write_csv(rows, "input.csv")
    out = meltinv.invert("input.csv", group_comparison_figure=False)
    assert out.basalt_percentage.iloc[0] < 0 and out.basalt_percentage.iloc[1] >= 0


def test_source_mixing_end_members():
    # Primitive mantle (McDonough & Sun 1995), basalt (Sun & McDonough 1989), depleted mantle (Salters & Stracke 2004)
    assert all(v == pytest.approx(1.0) for v in source_composition_mix(0).values())
    assert source_composition_mix(-100)["La"] == pytest.approx(0.234 / 0.648)
    assert source_composition_mix(15)["Lu"] == pytest.approx((0.15 * 0.455 + 0.85 * 0.0675) / 0.0675)


def test_t_p_correction_is_zero_without_enrichment_and_grows_with_it():
    T, P, h = np.array([150.0] * 3), np.array([100.0] * 3), np.array([60.0] * 3)
    T_cali, h_cali = calibration(T, P, h, np.array([0.0, 5.0, 10.0]))
    assert T_cali[0] == pytest.approx(150.0) and h_cali[0] == pytest.approx(60.0)
    assert T_cali[2] < T_cali[1] < 150.0          # cooler with more pyroxenite
    assert h_cali[2] > h_cali[1] > 60.0           # thicker with more pyroxenite


def test_depleted_sources_get_no_t_p_correction():
    T_cali, h_cali = calibration(np.array([150.0]), np.array([100.0]), np.array([60.0]), np.array([-50.0]))
    assert T_cali[0] == pytest.approx(150.0) and h_cali[0] == pytest.approx(60.0)
