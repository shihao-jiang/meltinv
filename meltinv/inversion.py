"""Numerical inversion and tabular outputs.

Start at invert_melt_condition for the complete workflow: clean observations,
fit each sample, apply post-fit calibration, then summarise by location.
Plot rendering lives in plotting.py; plot_archive.py saves optional snapshots.
See docs/code-guide.md for array axes, result fields and the distinction between
uncorrected best-fit parameters and calibrated output columns.
"""
import pandas as pd
from pathlib import Path
import importlib.resources as pkg_resources
import numpy as np
from .frac_correction import fractionation_correction
from .plot_archive import PlotArchiveWriter
from ._misfit import ModelLogCache, prepare_observations, evaluate_misfit


def source_composition_mix(basalt_perc):
    """Return REE concentration multipliers relative to primitive mantle.

    Positive percentages mix primitive mantle with the basalt endmember;
    negative percentages use the absolute value as the depleted-mantle fraction.
    For example, -50 denotes equal primitive/depleted-mantle mixing. This is the
    existing source parameterisation, separate from the later calibration.
    """
    PM_1995 = {
        "La": 0.648, "Ce": 1.675, "Pr": 0.254, "Nd": 1.250, "Sm": 0.406, "Eu": 0.154,
        "Gd": 0.544, "Tb": 0.099, "Dy": 0.674, "Ho": 0.149, "Er": 0.438, "Tm": 0.068,
        "Yb": 0.441, "Lu": 0.0675}

    Basalts_1989 = {
        "La": 2.5, "Ce": 7.50, "Pr": 1.32, "Nd": 7.3, "Sm": 2.63, "Eu": 1.02,
        "Gd": 3.68, "Tb": 0.67, "Dy": 4.55, "Ho": 1.01, "Er": 2.97, "Tm": 0.456,
        "Yb": 3.05, "Lu": 0.455}

    DM_SS_2004 = {
        "La": 0.234, "Ce": 0.772, "Pr": 0.131, "Nd": 0.713, "Sm": 0.27, "Eu": 0.107,
        "Gd": 0.395, "Tb": 0.075, "Dy": 0.531, "Ho": 0.122, "Er": 0.371, "Tm": 0.06,
        "Yb": 0.401, "Lu": 0.063}

    if basalt_perc >= 0:
        basalt_perc /= 100
        pm_perc = 1 - basalt_perc
        dict_mix = {}

        for element in PM_1995.keys():
            c = PM_1995[element] * pm_perc + Basalts_1989[element] * basalt_perc
            factor = c / PM_1995[element]
            dict_mix[element] = factor
    elif basalt_perc < 0:
        basalt_perc /= 100
        basalt_perc = abs(basalt_perc)
        pm_perc = 1 - basalt_perc
        dict_mix = {}

        for element in PM_1995.keys():
            c = PM_1995[element] * pm_perc + DM_SS_2004[element] * basalt_perc
            factor = c / PM_1995[element]
            dict_mix[element] = factor

    return dict_mix

def read_melt_composition(file_name):
    '''
    Read melt composition data from an Excel or CSV file.

    The input file must contain the required rare earth element (REE) concentrations in the primary magma
    (i.e., fractionation corrected)along with a sample location column. This function validates the file format
    and checks that all required columns are present before returning the data as a pandas DataFrame.
    '''
    file_path = Path(file_name).expanduser().resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_name}.")
    suffix = file_path.suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        melt_composition = pd.read_excel(file_path)
    elif suffix == ".csv":
        melt_composition = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a .xlsx or .csv file.")

    required_columns = ['location', 'La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                        'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']

    missing = [col for col in required_columns if col not in melt_composition.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            f"The following required columns are missing: {missing_str}"
        )
    else:
        print("Successfully read the melt composition file.")

    return melt_composition

def load_data_file(npy_file_name, allow_pickle=False):
    """
    Load a .npy file stored inside meltinv/data.
    """
    with pkg_resources.files("meltinv.data").joinpath(npy_file_name).open("rb") as f:
        return np.load(f, allow_pickle=allow_pickle)

def apply_mixing(concentrations, ree_variables, dict_mix):
    """
    Apply REE-specific mixing or scaling factors to simulated concentrations.
    This function multiplies each element concentration by a corresponding
    mixing factor defined in ``dict_mix``.
    """
    factors = [float(dict_mix[ree]) for ree in ree_variables]

    scaled = []
    for grid, factor in zip(concentrations, factors):
        grid = np.asarray(grid, dtype=float)
        scaled.append(grid * factor)
    return scaled

def load_all_grids():
    """Load packaged forward-model arrays, without interpolation or refitting.

    REE concentration arrays are ordered (element, thickness, temperature).
    The remaining summary arrays are ordered (thickness, temperature).
    See docs/code-guide.md for units and the legacy pres_* field names.
    """
    ree_variables = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                     'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']

    simulation = []
    lower = []
    upper = []
    # distri = []

    for ree in ree_variables:
        simulation.append(load_data_file(f"ree_average_{ree}.npy"))
        lower.append(load_data_file(f"ree_min_{ree}.npy"))
        upper.append(load_data_file(f"ree_max_{ree}.npy"))
        # distri.append(load_data_file(f"ree_distribution_{ree}.npy", allow_pickle=True))

    return {
        "ree_variables": ree_variables,
        "simulation": np.array(simulation),
        "lower": np.array(lower),
        "upper": np.array(upper),
        # "distribution": distri,
        "pres_mean": load_data_file("melt_average_pres.npy"),
        "pres_min": load_data_file("melt_min_pres.npy"),
        "pres_max": load_data_file("melt_max_pres.npy"),
        "F_mean": load_data_file("ree_average_F.npy"),
        "F_min": load_data_file("ree_min_F.npy"),
        "F_max": load_data_file("ree_max_F.npy"),
        "M_mean": load_data_file("ree_average_M.npy"),
        "M_min": load_data_file("ree_min_M.npy"),
        "M_max": load_data_file("ree_max_M.npy"),
    }

def build_group_list(df, min_count=2):
    grouped = df.groupby("location").size().reset_index(name="count")
    return [
        (row["location"], row["count"])
        for _, row in grouped.iterrows()
        if row["count"] >= min_count
    ]

def save_results(file_name, inv_result_df, suffix="_group_inversion_summary_log10.xlsx"):
    base_name = Path(file_name).stem

    if "corrected" in base_name:
        base_name = base_name.replace("_corrected", "")

    results_dir = Path(f"inversion_results")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"{base_name}{suffix}"

    inv_result_df.insert(0, 'location', inv_result_df.pop('location'))
    if 'sample_number' in inv_result_df.columns:
        inv_result_df.insert(1, 'sample_number', inv_result_df.pop('sample_number'))

    inv_result_df.to_excel(output_file, index=False)
    print(f"Results saved to: {output_file.resolve()}")


def compute_total_ree_misfit(df, mask, scale_val, grids, min_sample_count=2):
    """
    RMS log10 misfit grid for one enrichment value, normalised by N - 3 degrees of freedom
    (N residuals, 3 fitted parameters). Model cells with a missing or non-positive prediction
    for any measured element are excluded (NaN).
    """
    observations = prepare_observations(df, mask, grids["ree_variables"], min_sample_count)
    logs, valid, factors = ModelLogCache(grids, source_composition_mix).get(scale_val)
    misfit, threshold, index = evaluate_misfit(observations, logs, valid)
    return misfit, threshold, index, factors if misfit is not None else None


def get_enrichment_values(location, depleted_locations):
    """
    Determine enrichment range based on location name.
    depleted_locations may be None, a list of location keywords, or 'all'
    (every location uses the extended depleted range).
    """
    extended_range = list(range(-100, 0, 5)) + np.arange(0, 15.1, 0.1).tolist()
    default_range = np.arange(0, 15.1, 0.1).tolist()

    if isinstance(depleted_locations, str):
        depleted_locations = [depleted_locations]

    # 'all' applies the extended enrichment range to every location
    if depleted_locations is not None and any(
            str(keyword).lower() == 'all' for keyword in depleted_locations):
        return extended_range

    # Use extended enrichment range if location name contains any depleted keyword
    if depleted_locations is not None:
        if any(keyword in location for keyword in depleted_locations):
            return extended_range
        else:
            return default_range
    else:
        return default_range


def invert_single_group(df, location, count, grids, test_enrichment_values, min_sample_count=2,
                        *, retain_diagnostics=True, model_cache=None):
    """
    Search the temperature/thickness/enrichment grid for the selected rows.

    The name is retained for compatibility. The public workflow gives each
    sample its own location label, so this function normally fits one sample.
    Return None if no valid fit exists; otherwise return the result dictionary
    documented in docs/code-guide.md. No calibration is applied here.

    retain_diagnostics preserves full misfit surfaces for plotting; turn it off
    for tabular results only. A run-local model_cache reuses log predictions
    across samples. Equal minima retain the first enrichment and row-major cell.
    T_mean is plume excess temperature in K; depth_mean is lithospheric thickness
    in km. The legacy pres_* keys contain melting depths in km, not GPa.
    These are uncorrected best-fit quantities; calibration is applied by the caller.
    """
    ree_variables = grids["ree_variables"]
    simulation_concentrations = grids["simulation"]
    lower_bound_concentrations = grids["lower"]
    upper_bound_concentrations = grids["upper"]

    average_pres_grid = grids["pres_mean"]
    average_pres_min_grid = grids["pres_min"]
    average_pres_max_grid = grids["pres_max"]

    mask = df["location"] == location
    print(location, "Sample number:", count)

    if "thickness" in df.columns:
        litho_thickness_ref = df.loc[mask, "thickness"].mean()
    else:
        litho_thickness_ref = None

    best_result = {
        "min_misfit_value": np.inf,
        "min_idx": None,
        "scale": None,
        "scaling_factors": [1] * 14,
        "threshold": None,
    }

    full_3d_grids = []
    observations = prepare_observations(df, mask, ree_variables, min_sample_count)
    if model_cache is None:
        model_cache = ModelLogCache(grids, source_composition_mix)

    for scale_val in test_enrichment_values:

        logs, valid, dict_mix = model_cache.get(scale_val)
        total_misfit_grid, threshold, min_idx = evaluate_misfit(
            observations, logs, valid, diagnostic_threshold=retain_diagnostics)

        if retain_diagnostics:
            full_3d_grids.append(total_misfit_grid)

        if min_idx is not None:
            global_min_value = total_misfit_grid[min_idx]
        else:
            continue

        if global_min_value < best_result["min_misfit_value"]:
            print(f'Scale: {scale_val:.1f}', 'Global min misfit:', global_min_value)

            best_result.update({
                "min_misfit_value": global_min_value,
                "min_idx": min_idx,
                "misfit_grid": total_misfit_grid,
                "scale": scale_val,
                "scaling_factors": dict_mix,
                "threshold": threshold,
            })

    # Rows represent lithospheric thickness; columns represent excess temperature.
    # The legacy p_idx name denotes a thickness row, not pressure in GPa.
    if best_result["min_idx"] is None:
        return None

    p_idx, t_idx = best_result["min_idx"]
    mean_ree = [arr[p_idx, t_idx] for arr in simulation_concentrations]
    low_ree = [arr[p_idx, t_idx] for arr in lower_bound_concentrations]
    high_ree = [arr[p_idx, t_idx] for arr in upper_bound_concentrations]

    # The running minimum already is the global minimum of the exhaustive search.
    # Strict '<' above preserves the same first-tie selection as np.nanargmin.
    e_gl = test_enrichment_values.index(best_result["scale"])
    global_flat_index = np.ravel_multi_index(
        (e_gl, p_idx, t_idx), (len(test_enrichment_values), *simulation_concentrations.shape[1:]))

    for i, ree in enumerate(ree_variables):
        factor = best_result["scaling_factors"][ree]
        mean_ree[i] = factor * mean_ree[i]
        low_ree[i] = factor * low_ree[i]
        high_ree[i] = factor * high_ree[i]

    return {
        "full_3d_grids": np.array(full_3d_grids) if retain_diagnostics else None,
        "min_idx": best_result["min_idx"],
        "T_mean": 65 + t_idx * 5,
        "depth_mean": 15 + p_idx * 2 + 1,
        "pres_mean": average_pres_grid[p_idx, t_idx],
        "pres_min": average_pres_min_grid[p_idx, t_idx],
        "pres_max": average_pres_max_grid[p_idx, t_idx],
        "F_mean": grids["F_mean"][p_idx, t_idx],
        "F_min": grids["F_min"][p_idx, t_idx],
        "F_max": grids["F_max"][p_idx, t_idx],
        "M_mean": grids["M_mean"][p_idx, t_idx],
        "M_min": grids["M_min"][p_idx, t_idx],
        "M_max": grids["M_max"][p_idx, t_idx],
        "basalt_percentage": best_result["scale"],
        "basalt_idx": test_enrichment_values.index(best_result["scale"]),
        "enrichment_values": test_enrichment_values,
        "misfit_value": best_result["min_misfit_value"],
        "global_min_value": best_result["min_misfit_value"],
        "global_flat_index": global_flat_index,
        "mean_ree_global": mean_ree.copy(),
        "ratio_of_local_global_misfit": 1.0,
        "misfit_grid": best_result["misfit_grid"],
        "threshold": best_result["threshold"],
        "mean_ree": mean_ree,
        "low_ree": low_ree,
        "high_ree": high_ree,
        "litho_thickness_ref": litho_thickness_ref,
    }

def remove_keys(d, keys):
    new_d = d.copy()
    if isinstance(keys, str):
        keys = [keys]
    return {k: v for k, v in new_d.items() if k not in keys}


def calibration(T, P, h, b):
    """Apply the existing post-inversion solidus-offset prescription.

    T: plume excess temperature (K); P: mean melting *depth* (km, divided by
    33 to obtain GPa); h: lithospheric thickness (km); b: enrichment percent.
    Return adjusted (temperature K, thickness km). This does not refit REEs.
    """
    T = np.array(T)
    P = np.array(P) / 33
    b = np.clip(np.array(b, dtype=float), 0, 100)

    def solidus(P):
        return 1101.3 + 141.4 * P - 6.8 * P ** 2

    kG2 = 120
    bG2 = 920
    def solidus_G2(P):
        return bG2 + kG2 * P

    def hybrid_offset(P0, b, gamma=9.0, w=0.5):
        """
        Flux-weighted (Phipps Morgan, 2001; Sobolev et al., 2007) offset
        toward the G2 pyroxenite solidus, fraction x(f)=f*gamma/(f*gamma+1-f),
        gamma anchored to Sobolev et al. (2007) SOM p.S4 Eq.S3 + Table S2a
        (Hawaii-OIB: f=0.16, mean Xpx=0.64 -> gamma~9.3).
        """
        f = b / 100.
        x = f * gamma / (f * gamma + (1 - f))

        T0 = solidus(P0)
        dT_end = solidus_G2(P0) - T0          # full (x=1) isobaric offset: <=0
        P_G2_at_T0 = (T0 - bG2) / kG2
        dP_end = P_G2_at_T0 - P0               # full (x=1) isothermal offset: >=0

        return (1 - w) * x * dP_end, w * x * dT_end

    delta_P, delta_T = hybrid_offset(P, b)

    h_cali = h + delta_P * 33
    T_cali = T + delta_T

    return T_cali, h_cali

def aggregate_per_sample_results(results_df):
    """
    Summarise per-sample results for each location as a 1/misfit-weighted mean
    over all samples. Temperature, thickness and enrichment also get mean -/+ 1 std columns.
    """
    agg_columns = ['T_mean', 'T_mean_cali', 'depth_mean', 'depth_mean_cali',
                   'pres_mean_cali', 'pres_min_cali', 'pres_max_cali',
                   'F_mean', 'F_min', 'F_max', 'M_mean', 'M_min', 'M_max', 'basalt_percentage',
                   'misfit_value', 'global_min_value', 'ratio_of_local_global_misfit',
                   'litho_thickness_ref']
    err_columns = ['T_mean_cali', 'depth_mean_cali', 'basalt_percentage']

    rows = []
    for location, group in results_df.groupby('location'):
        n = len(group)
        weights = 1.0 / (group['misfit_value'].to_numpy() + 1e-6)

        row = {'location': location}
        for col in agg_columns:
            values = pd.to_numeric(group[col], errors='coerce').to_numpy()
            valid = ~np.isnan(values)
            if not valid.any():
                row[col] = np.nan
                continue
            values, col_weights = values[valid], weights[valid]
            mean = np.average(values, weights=col_weights)
            row[col] = mean
            if col in err_columns:
                std = np.sqrt(np.average((values - mean) ** 2, weights=col_weights))
                row[f'{col}_err_minus'] = mean - std
                row[f'{col}_err_plus'] = mean + std
        row['count'] = n
        rows.append(row)

    return pd.DataFrame(rows)


def invert_melt_condition(file_name, depleted_location=None, correction=False,
                          src_Fo=0.9, max_olivine_addition=0.4, individual_sample_figures=False,
                          group_comparison_figure=True, *, plot_archive=None):
    """Fit samples, calibrate parameters, export tables and optionally plot.

    plot_archive=None disables saving. A .zip path saves the data needed for
    regenerate_figures(), even when both plotting flags are False. Tables and
    immediate figures are written relative to the current working directory.
    Return the per-sample DataFrame in input order, excluding unfittable samples.
    """
    from contextlib import nullcontext
    if plot_archive is not None:
        if Path(plot_archive).expanduser().resolve() == Path(file_name).expanduser().resolve():
            raise ValueError("plot_archive must not overwrite the input data file")
        if Path(plot_archive).suffix.lower() != '.zip':
            raise ValueError("plot_archive must have a .zip extension, e.g. 'run.zip'")
    context = (PlotArchiveWriter(plot_archive, {
        "input_file": str(file_name), "depleted_location": depleted_location,
        "correction": correction, "src_Fo": src_Fo,
        "max_olivine_addition": max_olivine_addition,
    }) if plot_archive is not None else nullcontext())
    with context as archive:
        if correction == False:
            df = read_melt_composition(file_name)
        else:
            df = fractionation_correction(file_name, src_Fo, max_olivine_addition)

        # Treat zero, negative, infinite and non-numeric REE values as missing
        ree_variables = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                         'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
        df = df.copy()
        for ree in ree_variables:
            values = pd.to_numeric(df[ree], errors='coerce')
            df[ree] = values.where(np.isfinite(values) & (values > 0))

        if df["location"].isna().any() or df["location"].astype(str).str.strip().eq("").any():
            raise ValueError("Every sample must have a non-empty location")

        # Invert every sample on its own: give each sample a unique location label
        sample_number = df.groupby("location").cumcount() + 1
        original_location = df["location"]
        original_position = range(len(df))
        df["location"] = original_location.astype(str) + "__sample" + sample_number.astype(str)
        location_map = dict(zip(df["location"], zip(original_location, sample_number, original_position)))

        # Skip samples with fewer than min_ree usable REE values
        min_ree = 6
        ree_count = df[ree_variables].notna().sum(axis=1)
        for label, n_ree in zip(df.loc[ree_count < min_ree, "location"], ree_count[ree_count < min_ree]):
            location, number, _ = location_map[label]
            print(f"Skipping {location} sample {number}: {n_ree} usable REE value(s), at least {min_ree} needed.")
        df = df[ree_count >= min_ree]
        if df.empty:
            raise ValueError(f"No sample has at least {min_ree} usable REE values, so nothing can be inverted.")

        group_list = build_group_list(df, min_count=1)
        grids = load_all_grids()
        model_cache = ModelLogCache(grids, source_composition_mix)
        results = []
        for location, count in group_list:
            test_enrichment_values = get_enrichment_values(location, depleted_location)
            result = invert_single_group(df, location, count, grids, test_enrichment_values,
                                         min_sample_count=1, model_cache=model_cache,
                                         retain_diagnostics=individual_sample_figures or plot_archive is not None)

            if result is not None:
                result["location"] = location
                result["count"] = count

                keys_to_be_removed = ["full_3d_grids", "misfit_grid", "threshold", "scaling_factors",
                                      "mean_ree", "mean_ree_global", "low_ree", "high_ree", "min_idx", "global_flat_index",
                                      "basalt_idx", "enrichment_values"]
                results.append(remove_keys(result, keys_to_be_removed))

                if archive is not None:
                    archive.add_sample(df, location, count, result)
                if individual_sample_figures:
                    from .plotting import plot_results
                    plot_results(df, location, count, result)
                # Release this sample's large surface before starting the next search.
                del result

        if not results:
            raise ValueError("No valid model cell could be fitted to the supplied samples")
        results = pd.DataFrame(results)

        results["sample_number"] = results["location"].map(lambda x: location_map[x][1])
        results["_original_position"] = results["location"].map(lambda x: location_map[x][2])
        results["location"] = results["location"].map(lambda x: location_map[x][0])
        results = results.sort_values("_original_position").drop(columns="_original_position").reset_index(drop=True)

        T_mean = results['T_mean']
        P_mean = results['pres_mean']
        depth_mean = results['depth_mean']
        basalt_perc = results['basalt_percentage']

        T_cali, h_cali = calibration(T_mean, P_mean, depth_mean, basalt_perc)

        results.insert(results.columns.get_loc('T_mean') + 1, 'T_mean_cali', T_cali)
        results.insert(results.columns.get_loc('depth_mean') + 1, 'depth_mean_cali', h_cali)

        # Shift melting pressures by the same amount as the calibrated depth
        for col in ['pres_mean', 'pres_min', 'pres_max']:
            results[col] = results[col] + (h_cali - depth_mean)
        results = results.rename(columns={'pres_mean': 'pres_mean_cali', 'pres_min': 'pres_min_cali',
                                          'pres_max': 'pres_max_cali'})
        summary_df = pd.DataFrame(results)

        save_results(file_name, summary_df, suffix="_sample_inversion_log10.xlsx")
        island_summary = aggregate_per_sample_results(summary_df)
        save_results(file_name, island_summary, suffix="_sample_inversion_summary_log10.xlsx")
        if archive is not None:
            archive.add_summary(summary_df)
        if group_comparison_figure:
            from .plotting import plot_group_comparison
            plot_group_comparison(summary_df)

        return summary_df


# Explicit compatibility wrappers keep old notebook imports working without
# importing Matplotlib during a numerical-only run. New code can use plotting.py.
def plot_results(df, location, count, result, output_dir="inversion_figures"):
    """Compatibility wrapper for meltinv.plotting.plot_results."""
    from .plotting import plot_results as render
    return render(df, location, count, result, output_dir)


def plot_group_comparison(results_df, min_count=3, output_dir="inversion_figures"):
    """Compatibility wrapper for meltinv.plotting.plot_group_comparison."""
    from .plotting import plot_group_comparison as render
    return render(results_df, min_count, output_dir)


def compress_enrichment(e):
    """Compatibility wrapper for the plot-only enrichment transformation."""
    from .plotting import compress_enrichment as transform
    return transform(e)


def enrichment_ticks(enrichment_values):
    """Compatibility wrapper for enrichment-axis tick labels."""
    from .plotting import enrichment_ticks as ticks
    return ticks(enrichment_values)


def misfit_weighted_stats(values, misfit):
    """Compatibility wrapper for the plotted weighted mean and spread."""
    from .plotting import misfit_weighted_stats as stats
    return stats(values, misfit)
