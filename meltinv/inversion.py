import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import importlib.resources as pkg_resources
import numpy as np
from .frac_correction import fractionation_correction
from .plot_ree import plot_ree, plot_ree_range

def compress_enrichment(e):
    """Same display transform as plot_multiple_slices.py: divide negative
    (depleted) basalt_percentage values by 100, leave enriched (>=0) as is."""
    e = np.asarray(e, dtype=float)
    return np.where(e < 0, e / 100, e)


def misfit_weighted_stats(values, misfit):
    """
    Mean and std over all samples, weighted by 1/misfit.
    """
    values, misfit = np.asarray(values, dtype=float), np.asarray(misfit, dtype=float)
    w = 1.0 / (misfit + 1e-6)
    mean = np.average(values, weights=w)
    std = np.sqrt(np.average((values - mean) ** 2, weights=w))
    return mean, std

def source_composition_mix(basalt_perc):
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
    ree_variables = grids["ree_variables"]
    simulation = grids["simulation"]

    # Apply enrichment scaling
    dict_mix = source_composition_mix(scale_val)
    simulation_scaled = apply_mixing(simulation, ree_variables, dict_mix)

    valid_mask = np.ones_like(simulation_scaled[0], dtype=bool)

    # Root-mean-square log10 residual over all usable REE values, corrected for the
    # 3 fitted parameters (T, h, enrichment): sqrt( sum of squared residuals / (N - 3) )
    total_sq_grid = np.zeros_like(simulation_scaled[0], dtype=float)
    num_residuals = 0
    num_ree_valid = 0

    for i, ree in enumerate(ree_variables):
        c_sample = pd.to_numeric(df.loc[mask, ree], errors="coerce").to_numpy(dtype=float)
        c_sample = c_sample[np.isfinite(c_sample) & (c_sample > 0)]

        if len(c_sample) < min_sample_count:
            continue

        # Only model cells with a finite, positive prediction for this element can be fitted
        model = simulation_scaled[i]
        usable = np.isfinite(model) & (model > 0)
        valid_mask &= usable

        for c_l in c_sample:
            total_sq_grid[usable] += (np.log10(model[usable]) - np.log10(c_l)) ** 2
            num_residuals += 1

        num_ree_valid += 1

    degrees_of_freedom = num_residuals - 3
    if num_ree_valid == 0 or degrees_of_freedom <= 0:
        return None, None, None, None

    total_misfit_grid = np.where(valid_mask, np.sqrt(total_sq_grid / degrees_of_freedom), np.nan)

    if not valid_mask.any():
        return total_misfit_grid, None, None, dict_mix

    # The best fit is the global minimum (an exact match with zero misfit included);
    # the 10th-percentile threshold is kept for reference only
    threshold = np.percentile(total_misfit_grid[valid_mask], 10)
    min_idx = np.unravel_index(np.nanargmin(total_misfit_grid), total_misfit_grid.shape)

    return total_misfit_grid, threshold, min_idx, dict_mix

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


def invert_single_group(df, location, count, grids, test_enrichment_values, min_sample_count=2):
    """
    Perform inversion for a single volcanic location group.
    Return the best inversion result for this group.
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

    for scale_val in test_enrichment_values:

        total_misfit_grid, threshold, min_idx, dict_mix = compute_total_ree_misfit(
            df=df,
            mask=mask,
            scale_val=scale_val,
            grids=grids,
            min_sample_count=min_sample_count
        )

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

    # Convert best index to physical values
    if best_result["min_idx"] is None:
        return None

    p_idx, t_idx = best_result["min_idx"]
    mean_ree = [arr[p_idx, t_idx] for arr in simulation_concentrations]
    low_ree = [arr[p_idx, t_idx] for arr in lower_bound_concentrations]
    high_ree = [arr[p_idx, t_idx] for arr in upper_bound_concentrations]

    global_flat_index = np.nanargmin(full_3d_grids)
    e_gl, p_gl, t_gl = np.unravel_index(global_flat_index, np.array(full_3d_grids).shape)
    mean_ree_global = [arr[p_gl, t_gl] for arr in simulation_concentrations]
    dict_mix_global = source_composition_mix(test_enrichment_values[e_gl])

    for i, ree in enumerate(ree_variables):
        factor = best_result["scaling_factors"][ree]
        mean_ree[i] = factor * mean_ree[i]
        low_ree[i] = factor * low_ree[i]
        high_ree[i] = factor * high_ree[i]

    for i, ree in enumerate(ree_variables):
        factor = dict_mix_global[ree]
        mean_ree_global[i] = factor * mean_ree_global[i]

    return {
        "full_3d_grids": np.array(full_3d_grids),
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
        "global_min_value": np.nanmin(full_3d_grids),
        "global_flat_index": global_flat_index,
        "mean_ree_global": mean_ree_global,
        "ratio_of_local_global_misfit": (1.0 if np.nanmin(full_3d_grids) == 0 else
                                         best_result["min_misfit_value"] / np.nanmin(full_3d_grids)),
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

def enrichment_ticks(enrichment_values):
    """Tick positions/labels for the (possibly non-uniformly spaced) enrichment
    axis: nearest grid index to a set of round target values."""
    ev = np.asarray(enrichment_values, dtype=float)
    targets = [-100, -50, 0, 5, 10, 15] if ev.min() < 0 else [0, 3, 6, 9, 12, 15]
    ticks = sorted({int(np.abs(ev - t).argmin()) for t in targets})
    return ticks, [f"{ev[i]:g}" for i in ticks]

def plot_results(df, location, count, result):
    fig, axs = plt.subplots(2, 2, figsize=(9, 7.35), layout='constrained')

    # Plot on left panel
    ax = axs[0, 0]

    if result["min_idx"] is None:
        return
    else:
        p_idx, t_idx = result["min_idx"]
        min_value = result["misfit_value"]
        full_3d_grid = result["full_3d_grids"]
        global_min_value = result["global_min_value"]
        global_flat_index = result["global_flat_index"]
        e_i, p_i, t_i = np.unravel_index(global_flat_index, full_3d_grid.shape)
        basalt_idx = result["basalt_idx"]
        enrichment_values = np.asarray(result["enrichment_values"], dtype=float)

    ree_variables = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                     'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']

    mask = df["location"] == location
    sample_values = df[ree_variables][mask].to_numpy()

    flag = 0
    for i in sample_values:
        if flag == 0:
            plot_ree(ax, i, 'k', 2, label='Sample')
            flag = 1
        else:
            plot_ree(ax, i, 'k', 2, label=None)

    plot_ree(ax, result["mean_ree_global"], 'orange', 2, label='Global Best Fit')
    plot_ree(ax, result["mean_ree"], 'red', 2, label='Best Fit')
    plot_ree_range(ax, result["mean_ree"], result["low_ree"], result["high_ree"])

    ax.legend(loc='lower left')

    inv_temp = int(result["T_mean"])
    inv_thickness = int(result["depth_mean"])
    inv_basalt = result["basalt_percentage"]
    ax.text(0.99, 0.987, f"{location}", ha='right', va='top', fontweight='bold', transform=ax.transAxes)
    ax.text(0.99, 0.93, f'Temperature = {inv_temp} K\nThickness = {inv_thickness} km'
                        f'\nEnrichment Factor = {inv_basalt:.1f}', transform=ax.transAxes, ha='right', va='top', multialignment='right')

    # Plot on left panel
    ax = axs[0, 1]
    plot_scale = min_value if min_value > 0 else 1.0
    misfit_label = "misfit / minimum misfit" if min_value > 0 else "absolute log10 misfit (exact best fit)"
    best_misfit_grid = result["misfit_grid"] / plot_scale

    litho_thickness_ref = result["litho_thickness_ref"]
    basalt_percentage = result["basalt_percentage"]

    masked_grid = np.ma.masked_where((best_misfit_grid < 0) | np.isnan(best_misfit_grid), best_misfit_grid)
    # Set colormap with masked color as white
    cmap = plt.colormaps.get_cmap('viridis').copy()
    cmap.set_bad(color='white')
    # Plot masked grid
    im = ax.imshow(masked_grid, cmap=cmap)
    cbar = fig.colorbar(im, ax=ax, label=misfit_label)
    cbar.ax.yaxis.set_major_formatter('{:.1f}'.format)

    # Set limits to match data
    nx = 58
    ny = 53
    ax.set_xlim(0, nx)
    ax.set_ylim(ny, 0)

    x_ticks = np.arange(0, nx, 10)
    x_labels = 65 + 5 * x_ticks
    ax.set_xticks(ticks=x_ticks, labels=x_labels)

    y_ticks = np.arange(0, ny, 10)
    y_labels = 16 + 2 * y_ticks
    ax.set_yticks(ticks=y_ticks, labels=y_labels)

    ax.set_xlabel('Excess Temperature (K)')
    ax.set_ylabel('Lithospheric thickness (km)')

    # Find min positive L2 norm value and its location
    ax.plot(t_i, p_i, marker='o', color='orange', markersize=10)
    ax.plot(t_idx, p_idx, marker='*', color='red', markersize=10)

    # Contour for lowest 3% (excluding 0 and NaN)
    levels = [1.1, 1.3, 1.5, 2, 2.5, 3, 5]
    cs = ax.contour(best_misfit_grid, levels=levels, colors='white', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.1f')
    if litho_thickness_ref is not None:
        ax.axhline((litho_thickness_ref - 16) / 2, color='black', linestyle='--')

    ratio_of_local_global_misfit = result["ratio_of_local_global_misfit"]

    ax.text(0.02, 0.95, f"Ratio to Global Min Misfit = {ratio_of_local_global_misfit:.1f}", transform=ax.transAxes)

    ax = axs[1, 0]
    best_misfit_grid = full_3d_grid[:, p_idx, :] / plot_scale
    masked_grid = np.ma.masked_where((best_misfit_grid < 0) | np.isnan(best_misfit_grid), best_misfit_grid)

    im = ax.imshow(masked_grid, cmap=cmap, aspect='auto')
    ax.set_xlim(0, nx)
    x_ticks = np.arange(0, nx, 10)
    x_labels = 65 + 5 * x_ticks
    ax.set_xticks(ticks=x_ticks, labels=x_labels)
    ax.set_xlabel('Excess Temperature (K)')

    y_ticks, y_labels = enrichment_ticks(enrichment_values)
    ax.set_yticks(ticks=y_ticks, labels=y_labels)
    ax.plot(t_i, e_i, marker='o', color='orange', markersize=10)
    ax.plot(t_idx, basalt_idx, marker='*', color='red', markersize=10)

    ax.set_ylabel('Relative Enrichment')

    cs = ax.contour(best_misfit_grid, levels=levels, colors='white', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.1f')

    ax = axs[1, 1]
    best_misfit_grid = full_3d_grid[:, :, t_idx] / plot_scale
    masked_grid = np.ma.masked_where((best_misfit_grid < 0) | np.isnan(best_misfit_grid), best_misfit_grid)
    im = ax.imshow(masked_grid, cmap=cmap, aspect='auto')
    ax.set_xlim(0, ny)

    x_ticks = np.arange(0, ny, 10)
    x_labels = 16 + 2 * x_ticks
    ax.set_xticks(ticks=x_ticks, labels=x_labels)
    ax.set_xlabel('Lithospheric thickness (km)')

    y_ticks, y_labels = enrichment_ticks(enrichment_values)
    ax.set_yticks(ticks=y_ticks, labels=y_labels)
    ax.plot(p_i, e_i, marker='o', color='orange', markersize=10)
    ax.plot(p_idx, basalt_idx, marker='*', color='red', markersize=10)

    if litho_thickness_ref is not None:
        ax.axvline((litho_thickness_ref - 16) / 2, color='black', linestyle='--')

    ax.set_ylabel('Relative Enrichment')

    cs = ax.contour(best_misfit_grid, levels=levels, colors='white', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.1f')

    results_dir = Path("inversion_figures")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"ree_comparison_{location}_log10_N{count}.png"

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {output_file.resolve()}")
    plt.close(fig)

def calibration(T, P, h, b):
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


def plot_group_comparison(results_df, min_count_for_std=3):
    """
    Plot one figure per location comparing its per-sample temperature,
    thickness and enrichment results. The histograms show the 1/misfit-weighted mean,
    and the ±1 std band only for locations with at least min_count_for_std samples.
    """
    results_dir = Path("inversion_figures")
    results_dir.mkdir(exist_ok=True)

    for location, group in results_df.groupby("location"):
        group_number = len(group)
        show_std = group_number >= min_count_for_std

        thickness = group["depth_mean_cali"].to_numpy(dtype=float)
        temperature = group["T_mean_cali"].to_numpy(dtype=float)
        enrichment = compress_enrichment(group["basalt_percentage"])
        misfit = group["misfit_value"].to_numpy(dtype=float)
        misfit_kwargs = dict(c=misfit * 100, cmap="Blues_r", vmin=0.0, vmax=3, edgecolors="k")
        label_size = 8

        fig, axs = plt.subplots(2, 2, figsize=(9, 7))

        ax = axs[0, 0]
        ax.scatter(temperature, thickness, **misfit_kwargs)
        ax.set_ylabel("Lithospheric Thickness (km)")
        ax.set_xlabel("Excess Temperature (K)")
        ax.set_ylim(15, 130)
        ax.set_xlim(50, 300)
        ax.text(0.02, 0.97, "(a)", transform=ax.transAxes, va="top", ha="left")

        ax = axs[0, 1]
        sc = ax.scatter(enrichment, thickness, **misfit_kwargs)
        ax.set_ylabel("Thickness (km)")
        ax.set_xlabel("Relative Enrichment")
        ax.set_ylim(15, 130)
        ax.set_xlim(-1.2, 16)
        cbar = fig.colorbar(sc, ax=ax)
        cbar.ax.tick_params(labelsize=label_size)
        cbar.set_ticks(np.linspace(0, 3, 7))
        cbar.set_label(r"Misfit (×10$^{-2}$)", fontsize=label_size)
        ax.text(0.02, 0.97, "(b)", transform=ax.transAxes, va="top", ha="left")

        ax = axs[1, 0]
        ax.scatter(temperature, enrichment, **misfit_kwargs)
        ax.set_ylabel("Relative Enrichment")
        ax.set_xlabel("Excess Temperature (K)")
        ax.set_ylim(-1.2, 16)
        ax.set_xlim(50, 300)
        ax.text(0.02, 0.97, "(c)", transform=ax.transAxes, va="top", ha="left")

        subspec = axs[1, 1].get_subplotspec()
        axs[1, 1].remove()
        gs_sub = subspec.subgridspec(3, 1, hspace=0.7)

        histograms = [
            (temperature, np.linspace(50, 300, 26), "orange", (50, 300), "(d-1) Excess Temperature (K)"),
            (thickness, np.linspace(15, 130, 26), "steelblue", (15, 130), "(d-2) Lithospheric Thickness (km)"),
            (enrichment, np.linspace(-1., 16, 18), "seagreen", (-1.2, 16), "(d-3) Relative Enrichment"),
        ]
        for i, (values, bins, color, xlim, title) in enumerate(histograms):
            mean, std = misfit_weighted_stats(values, misfit)
            ax = fig.add_subplot(gs_sub[i])
            ax.tick_params(axis="both", labelsize=label_size)
            ax.hist(values, bins=bins, color=color, edgecolor="black")
            if show_std:
                ax.axvspan(mean - std, mean + std, color="black", alpha=0.15)
            ax.axvline(mean, color="black", linestyle="--", linewidth=1.5)
            ax.set_xlim(*xlim)
            ax.text(0.0, 1.02, title, transform=ax.transAxes,
                    va="bottom", ha="left", fontsize=label_size + 1)

        fig.suptitle(f"{location} (N={group_number})")
        fig.tight_layout(pad=0.5, w_pad=0.3, h_pad=0.3)

        output_file = results_dir / f"group_comparison_{location}_N{group_number}.png"
        plt.savefig(output_file, dpi=350)
        print(f"Figure saved to: {output_file.resolve()}")
        plt.close(fig)


def invert_melt_condition(file_name, depleted_location=None, correction=False,
                          src_Fo=0.9, max_olivine_addition=0.4, individual_sample_figures=False,
                          group_comparison_figure=True):
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
    results = []
    for g_i, group in enumerate(group_list):
        location, count = group
        test_enrichment_values = get_enrichment_values(location, depleted_location)
        result = invert_single_group(df, location, count, grids, test_enrichment_values,
                                     min_sample_count=1)

        if result is not None:
            result["location"] = location
            result["count"] = count

            keys_to_be_removed = ["full_3d_grids", "misfit_grid", "threshold", "scaling_factors",
                                  "mean_ree", "mean_ree_global", "low_ree", "high_ree", "min_idx", "global_flat_index",
                                  "basalt_idx", "enrichment_values"]
            results.append(remove_keys(result, keys_to_be_removed))

            if individual_sample_figures:
                plot_results(df, location, count, result)

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
    if group_comparison_figure:
        plot_group_comparison(summary_df)

    return summary_df




