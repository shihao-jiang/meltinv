"""meltinv web app: upload a spreadsheet, run the inversion, download the results.

Run locally from this folder with:  streamlit run streamlit_app.py
Each run happens in its own temporary folder and in a separate process, because
meltinv writes its outputs to the current folder; simultaneous users therefore
cannot overwrite each other's files. The folder is deleted when the run ends.
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

import meltinv

REE = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
OXIDES = ['SiO2', 'TiO2', 'Al2O3', 'FeO', 'CaO', 'MgO', 'MnO', 'K2O', 'Na2O', 'P2O5']
MIN_REE = 6                      # same acceptance rule as meltinv
MAX_SAMPLES = 3000               # keeps a run within the free server's limits
MAX_INDIVIDUAL_FIGURES = 300     # one 300-dpi figure per sample gets slow and large
TIMEOUT_SECONDS = 60 * 60
EXAMPLE_FILE = Path(__file__).resolve().parents[1] / "examples.xlsx"
REPOSITORY = "https://github.com/shihao-jiang/meltinv"
CITATION = "Jiang, S. et al. (2026). xxx. Journal Name."

SUMMARY_COLUMNS = {
    "location": "Location",
    "count": "Samples",
    "T_mean_cali": "Excess temperature (K)",
    "depth_mean_cali": "Lithospheric thickness (km)",
    "basalt_percentage": "Enrichment (% basalt)",
    "misfit_value": "Misfit",
    "litho_thickness_ref": "Reference thickness (km)",
}


# ---------------------------------------------------------------- input checks

def read_table(name, data):
    """Read an uploaded .xlsx/.xls/.csv file into a DataFrame."""
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(io.BytesIO(data))
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(data))
    raise ValueError("Please upload an .xlsx, .xls or .csv file.")


def check_input(df):
    """Return (errors, notes, usable_ree_per_sample, has_oxides) for an input table."""
    errors, notes = [], []
    missing = [c for c in ["location", *REE] if c not in df.columns]
    if missing:
        errors.append("Missing required column(s): " + ", ".join(f"`{c}`" for c in missing)
                      + ". Column names are case-sensitive.")
        return errors, notes, None, False
    if len(df) == 0:
        errors.append("The file has no rows.")
    if len(df) > MAX_SAMPLES:
        errors.append(f"The file has {len(df)} samples; this website accepts up to {MAX_SAMPLES}. "
                      "Split the file, or install meltinv on your own computer.")
    blank = df["location"].isna() | df["location"].astype(str).str.strip().eq("")
    if blank.any():
        errors.append(f"{blank.sum()} row(s) have no `location`. Every sample needs one.")

    usable = df[REE].apply(pd.to_numeric, errors="coerce").gt(0).sum(axis=1)
    too_few = int((usable < MIN_REE).sum())
    if too_few == len(df) and len(df) > 0:
        errors.append(f"No sample has at least {MIN_REE} usable REE values, so nothing can be inverted.")
    elif too_few:
        notes.append(f"{too_few} sample(s) have fewer than {MIN_REE} usable REE values and will be skipped.")
    has_oxides = all(c in df.columns for c in OXIDES)
    return errors, notes, usable, has_oxides


def template_bytes():
    """An .xlsx template: the required and optional columns, with one example row."""
    columns = ["location", *REE, *OXIDES, "thickness"]
    if EXAMPLE_FILE.exists():
        example = pd.read_excel(EXAMPLE_FILE).reindex(columns=columns).head(1)
    else:
        example = pd.DataFrame(columns=columns)
    buffer = io.BytesIO()
    example.to_excel(buffer, index=False)
    return buffer.getvalue()


# ---------------------------------------------------------------- running meltinv

def safe_stem(name):
    """A file-name stem that is safe on any system; meltinv names its outputs after it."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(name).stem).strip("_") or "samples"
    return stem.replace("corrected", "corr")   # meltinv strips '_corrected' from output names


def build_command(input_name, options):
    command = [sys.executable, "-m", "meltinv.cli", "invert", input_name,
               "--plot_archive", "plot_archive.zip"]
    if options["correction"]:
        command += ["--correction", "--src_Fo", str(options["src_Fo"]),
                    "--max_olivine_addition", str(options["max_olivine_addition"])]
    if options["depleted"]:
        command += ["--depleted", *options["depleted"]]
    if options["individual_figures"]:
        command.append("--individual_sample_figures")
    return command


def run_meltinv(workdir, input_name, options, status):
    """Run the meltinv command line in workdir, reporting progress; return (code, log)."""
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONUNBUFFERED="1")
    process = subprocess.Popen(build_command(input_name, options), cwd=workdir, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    watchdog = threading.Timer(TIMEOUT_SECONDS, process.kill)
    watchdog.start()
    log, figures, start = [], 0, time.time()
    try:
        for line in process.stdout:
            log.append(line.rstrip())
            if line.startswith("Figure saved"):
                figures += 1
            elapsed = f"{time.time() - start:.0f} s"
            if figures:
                status.update(label=f"Drawing figures: {figures} saved ({elapsed})")
            elif "_corrected" in line or "olivine" in line.lower():
                status.update(label=f"Olivine fractionation correction ({elapsed})")
            elif line.startswith("Results saved"):
                status.update(label=f"Inversion finished, saving results ({elapsed})")
        code = process.wait()
    finally:
        watchdog.cancel()
    if time.time() - start >= TIMEOUT_SECONDS:
        log.append(f"Stopped after {TIMEOUT_SECONDS // 60} minutes.")
    return code, log


def readme_text(input_name, options, log):
    skipped = [line for line in log if line.startswith("Skipping")]
    lines = [
        "meltinv results",
        "===============",
        f"Input file: {input_name}",
        f"meltinv version: {meltinv.__version__}",
        f"Date: {time.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "Settings",
        f"  Olivine fractionation correction: {'yes' if options['correction'] else 'no'}",
    ]
    if options["correction"]:
        lines += [f"  Source olivine Fo: {options['src_Fo']}",
                  f"  Maximum olivine addition: {options['max_olivine_addition']}"]
    lines += [
        f"  Possibly depleted locations: {', '.join(options['depleted']) or 'none'}",
        f"  Individual sample figures: {'yes' if options['individual_figures'] else 'no'}",
        "",
        "Contents",
        "  inversion_results/*_sample_inversion_log10.xlsx   one row per sample",
        "  inversion_results/*_sample_inversion_summary_log10.xlsx   one row per location",
        "  inversion_results/*_corrected.xlsx   olivine-corrected compositions (if corrected)",
        "  inversion_figures/   group comparison figures (and individual figures, if requested)",
        "  plot_archive.zip   redraw the figures later with: meltinv plot plot_archive.zip",
        "",
        "Columns ending in _cali are after the pyroxenite T-P correction. Every column is",
        f"explained in the meltinv README: {REPOSITORY}#step-4-reading-the-results",
        "",
        "Skipped samples",
        *([f"  {line}" for line in skipped] or ["  none"]),
        "",
        "If you use these results, please cite:",
        f"  {CITATION}",
    ]
    return "\n".join(lines) + "\n"


def collect_results(workdir, input_name, options, log):
    """Zip every output, and keep the summary table and group figures for display."""
    workdir = Path(workdir)
    buffer = io.BytesIO()
    outputs = [*workdir.glob("inversion_results/*"), *workdir.glob("inversion_figures/*"),
               workdir / "plot_archive.zip"]   # not the input, or the correction's .csv copy of it
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in outputs if p.is_file()):
            archive.write(path, path.relative_to(workdir).as_posix())
        archive.writestr("README.txt", readme_text(input_name, options, log))
        archive.writestr("run_log.txt", "\n".join(log) + "\n")

    summary_files = list(workdir.glob("inversion_results/*_sample_inversion_summary_log10.xlsx"))
    summary = pd.read_excel(summary_files[0]) if summary_files else None
    figures = {}
    for path in sorted(workdir.glob("inversion_figures/group_comparison_*.png")):
        label = re.sub(r"_N\d+$", "", path.stem.removeprefix("group_comparison_"))
        figures[label] = path.read_bytes()
    return {"zip": buffer.getvalue(), "summary": summary, "figures": figures,
            "skipped": [line for line in log if line.startswith("Skipping")], "log": log}


# ---------------------------------------------------------------- page

st.set_page_config(page_title="meltinv", page_icon="🌋", layout="centered")

st.title("meltinv")
st.markdown(
    "Estimate **mantle excess temperature**, **lithospheric thickness** and **source enrichment** "
    "beneath ocean-island and intraplate volcanoes from basalt rare-earth-element (REE) patterns. "
    "Upload a spreadsheet, run the inversion and download the results and figures. "
    "No programming needed."
)
st.caption(
    "Your file is processed in a temporary folder that is deleted as soon as the run finishes, "
    "and is not stored or shared. For unpublished data you would rather not upload, "
    f"[install meltinv]({REPOSITORY}#1-installation) on your own computer."
)

# 1. Prepare -------------------------------------------------------------------
st.header("1. Prepare your file", divider="gray")
st.markdown("One row per sample, in `.xlsx` or `.csv`. Extra columns are allowed and are kept in the results.")
with st.expander("Which columns are needed?"):
    st.markdown(
        f"""
| Column | Needed | Meaning |
|---|---|---|
| `location` | always | Samples with the same location are summarised and plotted together |
| `La` … `Lu` (14 REE) | always | Concentrations in ppm. Blank, zero, negative or text values (such as `bdl`) count as missing; each sample needs at least {MIN_REE} |
| `SiO2`, `TiO2`, `Al2O3`, `FeO`, `CaO`, `MgO`, `MnO`, `K2O`, `Na2O`, `P2O5` | for the olivine correction | Major oxides (wt%) of the measured sample |
| `thickness` | optional | An independent lithospheric thickness (km), e.g. seismic, for comparison only |
"""
    )
left, right = st.columns(2)
left.download_button("Download a template (.xlsx)", template_bytes(), "meltinv_template.xlsx",
                     width="stretch", on_click="ignore")
if EXAMPLE_FILE.exists():
    right.download_button("Download example data (38 samples)", EXAMPLE_FILE.read_bytes(),
                          "meltinv_examples.xlsx", width="stretch", on_click="ignore")

# 2. Upload --------------------------------------------------------------------
st.header("2. Upload", divider="gray")
uploaded = st.file_uploader("Your samples", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
if uploaded is None:
    st.session_state.pop("result", None)
    st.stop()

if st.session_state.get("upload_id") != uploaded.file_id:
    st.session_state.upload_id = uploaded.file_id
    st.session_state.pop("result", None)

try:
    data = read_table(uploaded.name, uploaded.getvalue())
except Exception as exc:          # unreadable or corrupt files
    st.error(f"Could not read the file: {exc}")
    st.stop()

errors, notes, usable, has_oxides = check_input(data)
n_locations = data["location"].nunique() if "location" in data.columns else 0
st.markdown(f"**{len(data)} samples** from **{n_locations} locations**.")
for message in errors:
    st.error(message)
for message in notes:
    st.warning(message)
with st.expander("Preview the first rows"):
    st.dataframe(data.head(20), hide_index=True)
if errors:
    st.stop()

# 3. Options -------------------------------------------------------------------
st.header("3. Options", divider="gray")
correction = st.checkbox(
    "Correct for olivine fractionation first (recommended for measured basalts)",
    value=has_oxides, disabled=not has_oxides,
    help="Adds olivine back until each melt is in equilibrium with mantle olivine, using meltPT. "
         "Leave this off if your file already contains primary-magma compositions.")
if not has_oxides:
    st.caption("The correction needs the 10 major-oxide columns, which this file does not have, "
               "so the REE are used as they are.")
src_Fo, max_olivine_addition = 0.9, 0.5
if correction:
    a, b = st.columns(2)
    src_Fo = a.number_input("Mantle olivine Fo", 0.85, 0.95, 0.90, 0.01, format="%.2f",
                            help="Forsterite content of the mantle olivine the melts equilibrate with.")
    max_olivine_addition = b.number_input("Maximum olivine addition", 0.1, 1.0, 0.5, 0.05,
                                          format="%.2f", help="Maximum mass fraction of olivine added.")

depleted_mode = st.radio(
    "Source enrichment range", ["Enriched only", "Some locations may be depleted", "All locations may be depleted"],
    horizontal=True,
    help="By default the source is primitive mantle plus 0–15% basalt. Locations marked as possibly "
         "depleted also search mixtures of primitive and depleted mantle.")
depleted = []
if depleted_mode == "Some locations may be depleted":
    depleted = st.multiselect("Possibly depleted locations",
                              sorted(data["location"].dropna().astype(str).unique()))
elif depleted_mode == "All locations may be depleted":
    depleted = ["all"]

too_many_for_figures = len(data) > MAX_INDIVIDUAL_FIGURES
individual_figures = st.checkbox(
    "Also make a diagnostic figure for every sample", value=False, disabled=too_many_for_figures,
    help="A 4-panel REE and misfit figure per sample. Group comparison figures are always made.")
if too_many_for_figures:
    st.caption(f"Individual figures are available for files with up to {MAX_INDIVIDUAL_FIGURES} samples.")

options = {"correction": correction, "src_Fo": src_Fo, "max_olivine_addition": max_olivine_addition,
           "depleted": depleted, "individual_figures": individual_figures}

# 4. Run -----------------------------------------------------------------------
st.header("4. Run", divider="gray")
seconds = len(data) * (0.4 if correction else 0.04) + (len(data) * 0.5 if individual_figures else 0) + 15
st.caption(f"Expected time: about {max(1, round(seconds / 60))} minute(s). Keep this page open while it runs.")
if st.button("Run meltinv", type="primary", width="stretch"):
    input_name = safe_stem(uploaded.name) + Path(uploaded.name).suffix.lower()
    with st.status("Starting…", expanded=False) as status, \
            tempfile.TemporaryDirectory(prefix="meltinv_") as workdir:
        (Path(workdir) / input_name).write_bytes(uploaded.getvalue())
        code, log = run_meltinv(workdir, input_name, options, status)
        if code == 0:
            st.session_state.result = collect_results(workdir, input_name, options, log)
            st.session_state.result["name"] = safe_stem(uploaded.name)
            status.update(label="Finished", state="complete")
        else:
            st.session_state.pop("result", None)
            status.update(label="meltinv stopped with an error", state="error", expanded=True)
            st.code("\n".join(log[-30:]) or "No output.", language=None)

# 5. Results -------------------------------------------------------------------
result = st.session_state.get("result")
if result:
    st.header("5. Results", divider="gray")
    n_fitted = int(result["summary"]["count"].sum()) if result["summary"] is not None else 0
    st.success(f"Inverted {n_fitted} samples. Download everything below: the results tables, "
               "figures, settings and a plot archive for redrawing the figures later.")
    st.download_button("Download all results (.zip)", result["zip"], f"{result['name']}_meltinv_results.zip",
                       mime="application/zip", type="primary", width="stretch", on_click="ignore")
    if result["skipped"]:
        with st.expander(f"{len(result['skipped'])} message(s) about skipped samples or figures"):
            st.text("\n".join(result["skipped"]))

    if result["summary"] is not None:
        st.subheader("Location summary")
        st.caption("Misfit-weighted means over the samples at each location, after the T–P correction. "
                   "The downloaded tables also give ±1 standard deviation and every other column.")
        columns = [c for c in SUMMARY_COLUMNS if c in result["summary"].columns]
        st.dataframe(result["summary"][columns].rename(columns=SUMMARY_COLUMNS).round(2), hide_index=True)

    if result["figures"]:
        st.subheader("Group comparison figures")
        location = st.selectbox("Location", list(result["figures"]))
        st.image(result["figures"][location], width="stretch")

    with st.expander("Full log"):
        st.code("\n".join(result["log"][-500:]), language=None)

st.divider()
st.caption(f"meltinv {meltinv.__version__} · [Source code and documentation]({REPOSITORY}) · "
           f"If you use meltinv, please cite {CITATION}")
