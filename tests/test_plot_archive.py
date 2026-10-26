"""A saved run must reproduce both plot types without touching the inversion."""
import subprocess
import sys
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
from meltinv import invert, regenerate_figures
from meltinv.plot_archive import PlotArchiveWriter
from conftest import write_csv


def test_inversion_import_does_not_import_matplotlib():
    subprocess.run([sys.executable, '-c',
                    "import meltinv; import sys; assert 'matplotlib.pyplot' not in sys.modules"],
                   check=True)


@pytest.mark.parametrize('enrichment', [-35, 0, 7.3])
def test_archive_reproduces_figures_and_preserves_results(in_tmp, grid_sample, monkeypatch, enrichment):
    rows = [grid_sample(k=500+i, enrichment=enrichment, location='A')[0] for i in range(3)]
    if enrichment == 7.3:
        for row in rows:
            row['thickness'] = 75.0  # exercise independent thickness lines

    rows[0]['Lu'] = np.nan  # missing REE must survive saving and plotting
    write_csv(rows, 'input.csv')
    plain = invert('input.csv', depleted_locations='all', group_comparison_figure=False)
    saved = invert('input.csv', depleted_locations='all', individual_sample_figures=True,
                   plot_archive='run.zip')
    pd.testing.assert_frame_equal(plain, saved, check_exact=True)
    original = {p.name: p.read_bytes() for p in (in_tmp/'inversion_figures').glob('*.png')}
    assert len(original) == 4
    with ZipFile('run.zip') as z:
        assert len(z.namelist()) == 5
        import json
        manifest = json.loads(z.read('manifest.json'))
        assert 'matplotlib' in manifest['environment']
    (in_tmp/'input.csv').unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError('Replot must not load model grids or rerun inversion')
    monkeypatch.setattr('meltinv.inversion.load_all_grids', forbidden)
    monkeypatch.setattr('meltinv.inversion.invert_single_group', forbidden)
    regenerate_figures('run.zip', 'replotted')
    regenerated = {p.name: p.read_bytes() for p in (in_tmp/'replotted').glob('*.png')}
    assert original == regenerated  # same rendering environment, exact PNG bytes


def test_failed_archive_does_not_replace_previous_run(tmp_path):
    path = tmp_path/'run.zip'
    path.write_bytes(b'previous run')
    with pytest.raises(RuntimeError):
        with PlotArchiveWriter(path, {}):
            raise RuntimeError('failed inversion')
    assert path.read_bytes() == b'previous run'
    assert list(tmp_path.iterdir()) == [path]


def test_archive_can_be_saved_without_rendering(in_tmp, grid_sample, monkeypatch):
    write_csv([grid_sample()[0]], 'input.csv')
    def forbidden(*args, **kwargs):
        raise AssertionError('Saving an archive must not render figures')
    monkeypatch.setattr('meltinv.plotting.plot_results', forbidden)
    monkeypatch.setattr('meltinv.plotting.plot_group_comparison', forbidden)
    invert('input.csv', group_comparison_figure=False, plot_archive='run.zip')
    assert (in_tmp/'run.zip').exists()
    assert not (in_tmp/'inversion_figures').exists()


def test_cli_plot_dispatch(monkeypatch):
    from meltinv.cli import main
    calls = []
    monkeypatch.setattr('meltinv.plot_archive.regenerate_figures',
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, 'argv', ['meltinv', 'plot', 'run.zip',
                                     '--output_dir', 'figures', '--no_individual'])
    main()
    assert calls == [(('run.zip', 'figures'), {
        'individual_sample_figures': False, 'group_comparison_figure': True})]


@pytest.mark.parametrize('destination', ['input.csv', 'inversion_results/output.xlsx'])
def test_archive_cannot_overwrite_data_file(in_tmp, grid_sample, destination):
    write_csv([grid_sample()[0]], 'input.csv')
    original = (in_tmp/'input.csv').read_bytes()
    with pytest.raises(ValueError, match='plot_archive'):
        invert('input.csv', group_comparison_figure=False, plot_archive=destination)
    assert (in_tmp/'input.csv').read_bytes() == original
    assert not (in_tmp/'inversion_results').exists()


def test_missing_plot_diagnostics_gives_actionable_error(in_tmp):
    import matplotlib.pyplot as plt
    from meltinv.plotting import plot_results
    before = plt.get_fignums()
    with pytest.raises(ValueError, match='retain_diagnostics=True'):
        plot_results(pd.DataFrame(), 'A', 1, {'min_idx': (0, 0), 'misfit_value': 1.0})
    assert plt.get_fignums() == before
    plot_results(pd.DataFrame(), 'A', 1, {'min_idx': None})
    assert plt.get_fignums() == before


def test_unknown_archive_version_is_rejected_before_plotting(in_tmp):
    with ZipFile('future.zip', 'w') as archive:
        archive.writestr('manifest.json', '{"format_version": 999}')
    with pytest.raises(ValueError, match='Unsupported.*version'):
        regenerate_figures('future.zip')
    assert not (in_tmp/'inversion_figures').exists()
