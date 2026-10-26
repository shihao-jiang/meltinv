"""Olivine fractionation correction (the part that does not need meltPT itself)."""
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from meltinv.frac_correction import save_fraction
from conftest import REE, MAJORS


def primary_output(ol_added, complete):
    """Mimic meltPT's Suite.primary: olivine added and primary major elements per sample."""
    return pd.DataFrame({"ol_added": ol_added,
                         **{f"{m}_primary_wt": [1.0 if ok else np.nan for ok in complete] for m in MAJORS}})


def test_successful_correction_dilutes_ree_by_added_olivine(in_tmp):
    sample = pd.DataFrame({c: [10.0, 10.0] for c in ["location", *REE, *MAJORS]})
    sample["location"] = "A"
    out = save_fraction("s.csv", sample, primary_output([0.2, 0.0], [True, True]))
    assert out.La.tolist() == pytest.approx([8.0, 10.0])
    assert out.correction_success.tolist() == [True, True]
    assert "SiO2_primary" in out.columns
    assert (in_tmp / "inversion_results/s_corrected.xlsx").exists()


def test_failed_correction_gives_missing_ree_not_zero_olivine(in_tmp):
    # Regression (PR #1): failed corrections used to be treated as 0 % olivine added,
    # so uncorrected REE entered the inversion without any warning.
    sample = pd.DataFrame({c: [10.0, 10.0, 10.0] for c in ["location", *REE, *MAJORS]})
    sample["location"] = "A"
    primary = primary_output([0.2, np.nan, 0.3], [True, False, False])
    with pytest.warns(RuntimeWarning, match="failed for 2 sample"):
        out = save_fraction("s.csv", sample, primary)
    assert out.La.iloc[0] == pytest.approx(8.0)
    assert out.loc[1:, REE].isna().all().all()
    assert out.correction_success.tolist() == [True, False, False]
    assert sample.La.eq(10.0).all()                 # the input table is not modified


def test_olivine_addition_outside_0_to_1_counts_as_failed(in_tmp):
    sample = pd.DataFrame({c: [10.0, 10.0] for c in ["location", *REE, *MAJORS]})
    sample["location"] = "A"
    with pytest.warns(RuntimeWarning):
        out = save_fraction("s.csv", sample, primary_output([1.0, -0.1], [True, True]))
    assert out.correction_success.tolist() == [False, False]


def test_fe3_setting_reaches_meltpt(in_tmp, monkeypatch):
    import meltPT
    from meltinv.frac_correction import fractionation_correction
    seen = {}

    class StopAfterSetup(Exception):
        pass

    def fake_suite(path, **kwargs):
        seen.update(kwargs, data=pd.read_csv(path))
        raise StopAfterSetup

    monkeypatch.setattr(meltPT, "Suite", fake_suite)
    sample = pd.DataFrame({c: [10.0] for c in ["location", *REE, *MAJORS]})
    sample["location"] = "A"
    sample["Fe2O3"] = 2.0
    sample.to_csv("s.csv", index=False)
    with pytest.raises(StopAfterSetup):
        fractionation_correction("s.csv", fe3_fe_total=0.15)
    assert seen["src_FeIII_totFe"] == 0.15
    # By default all iron reaches meltPT as total FeO, so one Fe3+/sum Fe applies to every sample
    assert seen["data"].FeO.iloc[0] == pytest.approx(10.0 + 2.0 * 0.8998)
    assert seen["data"].Fe2O3.iloc[0] == 0.0
    with pytest.raises(StopAfterSetup):
        fractionation_correction("s.csv", fe3_fe_total=0.15, measured_fe3=True)
    assert seen["data"].Fe2O3.iloc[0] == 2.0
    assert pd.read_csv("s.csv").Fe2O3.iloc[0] == 2.0          # the input file is not modified


def test_measured_iron_split_is_kept_and_total_iron_is_split_by_fe3(in_tmp):
    # meltPT behaviour behind measured_fe3=True: a sample reporting both FeO and Fe2O3
    # keeps them; a sample with total iron only is split using Fe3+/sum Fe.
    from meltPT.parse import parse_csv
    rows = pd.DataFrame({"Sample": ["measured", "total only"], "SiO2": 48.0, "TiO2": 2.0, "Al2O3": 13.0,
                         "FeO": [8.0, 0.0], "Fe2O3": [3.0, 0.0], "FeO_tot": [0.0, 11.0], "MnO": 0.2,
                         "MgO": 10.0, "CaO": 10.0, "Na2O": 2.5, "K2O": 0.5, "P2O5": 0.3})
    rows.to_csv("fe.csv", index=False)
    df = parse_csv("fe.csv", src_FeIII_totFe=0.1)       # meltPT renormalises oxides to 100 %
    fe3_ratio = df.Fe2O3 * 0.8998 / (df.FeO + df.Fe2O3 * 0.8998)
    assert fe3_ratio.tolist() == pytest.approx([3.0 * 0.8998 / (8.0 + 3.0 * 0.8998), 0.1], rel=1e-3)


def test_importing_meltinv_does_not_load_meltpt():
    # meltPT is only needed when a correction is requested.
    code = "import sys, meltinv; print('meltPT' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
