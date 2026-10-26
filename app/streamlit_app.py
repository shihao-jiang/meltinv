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

# Other spellings of the required column names, to suggest a rename
ALIASES = {
    "location": ["island", "volcano", "locality", "site", "sample location", "group"],
    "FeO": ["feot", "feo*", "feo(t)", "feotot", "feo total", "feo_t", "feot (wt%)"],
}


def read_table(name, data):
    """Read an uploaded .xlsx/.xls/.csv file into a DataFrame (first sheet only)."""
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(io.BytesIO(data))
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(data))
    raise ValueError("Please upload an .xlsx, .xls or .csv file.")


def _simplify(name):
    """Lower case, without units, spaces or punctuation: 'La (ppm)' -> 'la'."""
    name = re.sub(r"[\(\[].*?[\)\]]|\b(ppm|wt%|wt\.%|wt)\b", "", str(name).lower())
    return re.sub(r"[^a-z0-9*]", "", name)


def suggest_renames(df, wanted):
    """Map each wanted column that is missing to a similar existing column, where one exists."""
    by_simple = {_simplify(c): c for c in df.columns}
    renames = {}
    for column in wanted:
        if column in df.columns:
            continue
        for candidate in [column, *ALIASES.get(column, [])]:
            if _simplify(candidate) in by_simple:
                renames[column] = by_simple[_simplify(candidate)]
                break
    return renames


def header_row_hint(data):
    """If 'location' appears in a later row, the column names probably do not start in row 1."""
    for i, row in data.head(10).iterrows():
        if any(str(v).strip().lower() == "location" for v in row.values):
            return i + 2   # spreadsheet row number: header is row 1, data start at row 2
    return None


def check_input(df):
    """Check an input table. Return (problems, notes, has_oxides, oxide_problem).

    problems and notes are lists of (title, explanation and suggested fix);
    problems stop the run, notes do not.
    """
    problems, notes = [], []
    missing = [c for c in ["location", *REE] if c not in df.columns]
    if missing:
        renames = suggest_renames(df, missing)
        fix = ["Column names must match exactly, including capital letters."]
        if renames:
            fix.append("Rename these columns in your file: " + "; ".join(
                f"`{found}` → `{column}`" for column, found in renames.items()) + ".")
        row = header_row_hint(df)
        if row:
            fix.append(f"The column names seem to be in row {row} of your sheet. Delete the rows "
                       "above them so the names are in the first row.")
        if not renames and not row:
            fix.append("Download the template above and copy your data into it.")
        problems.append(("Missing columns: " + ", ".join(missing), " ".join(fix)))
        return problems, notes, False, None

    if len(df) == 0:
        problems.append(("The file has no samples",
                         "Put the column names in the first row and one sample per row below them."))
    if len(df) > MAX_SAMPLES:
        problems.append((f"Too many samples ({len(df)})",
                         f"This website accepts up to {MAX_SAMPLES} samples per file. Split the file "
                         f"into smaller files, or [install meltinv]({REPOSITORY}#1-installation) "
                         "on your own computer, which has no limit."))
    blank = df["location"].isna() | df["location"].astype(str).str.strip().eq("")
    if blank.any():
        rows = ", ".join(str(i + 2) for i in df.index[blank][:10])
        problems.append((f"{blank.sum()} sample(s) have no location",
                         f"Fill in the `location` column in spreadsheet row(s) {rows}"
                         f"{' and others' if blank.sum() > 10 else ''}. Samples with the same "
                         "location are summarised together; give a sample its own name to treat it alone."))

    values = df[REE].apply(pd.to_numeric, errors="coerce")
    text = df[REE].apply(lambda col: col.map(lambda v: isinstance(v, str) and v.strip() != ""))
    commas = df[REE].apply(lambda col: col.map(
        lambda v: isinstance(v, str) and re.fullmatch(r"\s*\d+,\d+\s*", v) is not None))
    if commas.any().any():
        problems.append(("Some REE values use a decimal comma",
                         f"{int(commas.sum().sum())} value(s), such as `{df[REE][commas].stack().iloc[0]}`, "
                         "use a comma as the decimal point. Change them to a full stop (1,25 → 1.25), "
                         "or save the file from Excel as .xlsx rather than .csv."))
    elif text.any().any():
        example = df[REE][text].stack().iloc[0]
        notes.append(("Some REE cells contain text",
                      f"{int(text.sum().sum())} cell(s), such as `{example}`, are text and are treated as "
                      "missing values. That is right for entries like `bdl` or `n.d.`; if any are real "
                      "values, remove the text and keep only the number."))

    usable = values.gt(0).sum(axis=1)
    too_few = usable < MIN_REE
    if too_few.all() and len(df) > 0:
        problems.append((f"No sample has at least {MIN_REE} REE values",
                         "Check that the REE columns hold numbers in ppm, not text or blanks."))
    elif too_few.any():
        rows = ", ".join(str(i + 2) for i in df.index[too_few][:10])
        notes.append((f"{too_few.sum()} sample(s) will be skipped",
                      f"They have fewer than {MIN_REE} usable REE values (spreadsheet row(s) {rows}"
                      f"{' and others' if too_few.sum() > 10 else ''}). The other samples are inverted normally."))

    missing_oxides = [c for c in OXIDES if c not in df.columns]
    oxide_problem = None
    if missing_oxides:
        renames = suggest_renames(df, missing_oxides)
        oxide_problem = ("The olivine correction needs the major oxides " + ", ".join(
            f"`{c}`" for c in OXIDES) + f"; this file is missing {', '.join(missing_oxides)}.")
        if renames:
            oxide_problem += " Rename: " + "; ".join(f"`{found}` → `{c}`" for c, found in renames.items()) + "."
        if "FeO" in missing_oxides and any(_simplify(c).startswith("fe2o3") for c in df.columns):
            oxide_problem += (" If you only have Fe2O3 (total iron), add a `FeO` column equal to "
                              "0.8998 × Fe2O3.")
        oxide_problem += " Without them, the REE are used as they are."
    return problems, notes, not missing_oxides, oxide_problem


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
uploaded = st.file_uploader("Your samples", type=["xlsx", "xls", "csv"], label_visibility="collapsed",
                            help="One file at a time. For Excel files, only the first sheet is read.")
st.caption("One file at a time; to analyse several datasets together, put them in one file. "
           "For Excel files only the first sheet is read.")
if uploaded is None:
    st.session_state.pop("result", None)
    st.stop()

if st.session_state.get("upload_id") != uploaded.file_id:
    st.session_state.upload_id = uploaded.file_id
    st.session_state.pop("result", None)

try:
    data = read_table(uploaded.name, uploaded.getvalue())
except Exception as exc:          # unreadable or corrupt files
    st.error(f"The file could not be opened ({exc}). Open it in Excel, check that the data are on the "
             "first sheet with the column names in the first row, and save it again as .xlsx.",
             title="Could not read the file")
    st.stop()

problems, notes, has_oxides, oxide_problem = check_input(data)
n_locations = data["location"].nunique() if "location" in data.columns else 0
st.markdown(f"**{len(data)} samples** from **{n_locations} locations**.")
for title, fix in problems:
    st.error(fix, title=title)
for title, fix in notes:
    st.warning(fix, title=title)
with st.expander("Preview the first rows"):
    st.dataframe(data.head(20), hide_index=True, alt="First rows of the uploaded file")
if problems:
    st.info("Fix the problems above in your file, then upload it again.")
    st.stop()

# 3. Options -------------------------------------------------------------------
st.header("3. Options", divider="gray")
correction = st.checkbox(
    "Correct for olivine fractionation first (recommended for measured basalts)",
    value=has_oxides, disabled=not has_oxides,
    help="Adds olivine back until each melt is in equilibrium with mantle olivine, using meltPT. "
         "Leave this off if your file already contains primary-magma compositions.")
if oxide_problem:
    st.caption(oxide_problem)
src_Fo, max_olivine_addition = 0.9, 0.5
if correction:
    a, b = st.columns(2)
    src_Fo = a.number_input("Mantle olivine Fo", 0.85, 0.95, 0.90, 0.01, format="%.2f",
                            help="Forsterite content of the mantle olivine the melts equilibrate with.")
    max_olivine_addition = b.number_input("Maximum olivine addition", 0.1, 1.0, 0.5, 0.05,
                                          format="%.2f", help="Maximum mass fraction of olivine added.")

depleted_mode = st.segmented_control(
    "Source enrichment range", ["Enriched only", "Some locations may be depleted", "All locations may be depleted"],
    default="Enriched only", required=True,
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
                       mime="application/zip", type="primary", width="stretch", on_click="ignore",
                       icon=":material/download:")
    if result["skipped"]:
        with st.expander(f"{len(result['skipped'])} message(s) about skipped samples or figures"):
            st.text("\n".join(result["skipped"]))

    if result["summary"] is not None:
        st.subheader("Location summary")
        st.caption("Misfit-weighted means over the samples at each location, after the T–P correction. "
                   "The downloaded tables also give ±1 standard deviation and every other column.")
        columns = [c for c in SUMMARY_COLUMNS if c in result["summary"].columns]
        st.dataframe(result["summary"][columns].rename(columns=SUMMARY_COLUMNS).round(2), hide_index=True,
                     alt="Inverted temperature, thickness, enrichment and misfit for each location")

    if result["figures"]:
        st.subheader("Group comparison figures")
        location = st.selectbox("Location", list(result["figures"]))
        st.image(result["figures"][location], width="stretch",
                 alt=f"Group comparison figure for {location}: temperature, thickness and enrichment of each sample")

    with st.expander("Full log"):
        st.code("\n".join(result["log"][-500:]), language=None)

st.divider()
st.caption(f"meltinv {meltinv.__version__} · [Source code and documentation]({REPOSITORY}) · "
           f"If you use meltinv, please cite {CITATION}")
