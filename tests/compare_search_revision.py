"""Compare all tabular outputs and wall time against a Git revision.

Run from the repository root after installing test dependencies:
  python tests/compare_search_revision.py --reference 0196fe6
Use --modern for all bundled, pre-corrected modern OIB samples. This checks
inversion/output equivalence, not a new fractionation correction or validation
of the physical model. Both runs use identical inputs and disable plotting.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import types

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from meltinv import inversion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--modern', action='store_true')
    parser.add_argument('--plot-archive', action='store_true',
                        help='Also exercise archive saving in the candidate run')
    args = parser.parse_args()
    revision = subprocess.check_output(
        ['git', 'rev-parse', args.reference], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(
        ['git', 'show', f'{revision}:meltinv/inversion.py'], cwd=ROOT, text=True)
    baseline = types.ModuleType('meltinv._baseline_inversion')
    baseline.__package__ = 'meltinv'
    exec(compile(source, f'{revision}/inversion.py', 'exec'), baseline.__dict__)
    dataset = (ROOT / 'tutorials/data/modern_OIB_precomputed/modern_OIB_corrected.xlsx'
               if args.modern else ROOT / 'tests/reference/examples_corrected.csv')
    frames, times = [], []
    original_cwd = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix='meltinv-compare-') as temp:
            for name, module in [('baseline', baseline), ('candidate', inversion)]:
                work = Path(temp) / name
                work.mkdir()
                os.chdir(work)
                with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink):
                    start = time.perf_counter()
                    result = module.invert_melt_condition(
                        dataset, depleted_location=['Iceland', 'Galapagos'],
                        group_comparison_figure=False,
                        **({'plot_archive': 'run.zip'}
                           if name == 'candidate' and args.plot_archive else {}))
                    times.append(time.perf_counter() - start)
                outputs = {p.name: pd.read_excel(p) for p in sorted(
                    (work / 'inversion_results').glob('*.xlsx'))}
                frames.append((result, outputs))
                print(f'{name}: {times[-1]:.3f} s, {len(result)} samples', flush=True)
            pd.testing.assert_frame_equal(frames[0][0], frames[1][0], check_exact=True)
            assert frames[0][1].keys() == frames[1][1].keys()
            for name in frames[0][1]:
                pd.testing.assert_frame_equal(frames[0][1][name], frames[1][1][name],
                                              check_exact=True)
            print(json.dumps({
                'reference': revision, 'dataset': str(dataset.relative_to(ROOT)),
                'candidate_saved_plot_archive': args.plot_archive,
                'samples': len(frames[0][0]), 'all_table_values_exactly_equal': True,
                'baseline_seconds': times[0], 'candidate_seconds': times[1],
                'speedup': times[0] / times[1], 'python': platform.python_version(),
                'numpy': np.__version__, 'pandas': pd.__version__,
                'platform': platform.platform(),
            }, indent=2))
    finally:
        os.chdir(original_cwd)


if __name__ == '__main__':
    main()
