import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import importlib.resources as pkg_resources
import numpy as np
from .frac_correction import fractionation_correction
from .plot_ree import plot_ree, plot_ree_range

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

    required_columns = ['location', 'Al2O3_primary', 'La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
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

def obtain_thickness_major(c_Al2O3):
    """
    The estimated thickness is calculated using a linear empirical relationship
    between Al2O3 and lithospheric thickness. The returned minimum and
    maximum bounds reflect ±1 standard deviation of the calibration.
    """
    k_Al2O3 = -0.07
    b_Al2O3 = 15.29
    std = 1.43
    mean_Al2O3 = np.mean(c_Al2O3)

    x_mean = (mean_Al2O3 - b_Al2O3) / k_Al2O3
    x_min = (mean_Al2O3 - b_Al2O3 + std) / k_Al2O3
    x_max = (mean_Al2O3 - b_Al2O3 - std) / k_Al2O3

    return x_min, x_max

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
    }

def build_group_list(df):
    grouped = df.groupby("location").size().reset_index(name="count")
    return [
        (row["location"], row["count"])
        for _, row in grouped.iterrows()
        if row["count"] >= 2
    ]

def save_results(file_name, inv_result_df):
    results_dir = Path("inversion_results")
    results_dir.mkdir(exist_ok=True)

    base_name = Path(file_name).stem
    output_file = results_dir / f"{base_name}_inversion_summary.xlsx"

    inv_result_df.insert(0, 'location', inv_result_df.pop('location'))

    inv_result_df.to_excel(output_file, index=False)
    print(f"Results saved to: {output_file.resolve()}")


def compute_total_ree_misfit(df, mask, scale_val, grids):
    """
    Compute total normalized misfit grid for one enrichment scale value.
    """
    ree_variables = grids["ree_variables"]
    simulation = grids["simulation"]

    # Apply enrichment scaling
    dict_mix = source_composition_mix(scale_val)
    simulation_scaled = apply_mixing(simulation, ree_variables, dict_mix)

    valid_mask = ~np.isnan(simulation_scaled[0])
    total_misfit_grid = np.zeros_like(simulation_scaled[0], dtype=float)

    num_ree_valid = 0

    for i, ree in enumerate(ree_variables):
        c_sample = df[mask][ree]
        sample_count = np.count_nonzero(~np.isnan(c_sample))

        if sample_count <= 1:
            continue

        misfit_grid = np.zeros_like(total_misfit_grid)

        for c_l in c_sample:
            if c_l > 0:
                misfit_grid[valid_mask] += (
                    simulation_scaled[i][valid_mask] - c_l
                ) ** 2

        std = np.nanstd(c_sample)

        misfit_grid[valid_mask] = (
            np.sqrt(misfit_grid[valid_mask]) / std / sample_count
        )

        misfit_grid = np.where(valid_mask, misfit_grid, np.nan)

        total_misfit_grid += misfit_grid
        num_ree_valid += 1

    if num_ree_valid == 0:
        return None, None, None, None, None, None

    total_misfit_grid /= num_ree_valid

    # Threshold selection
    valid_positive_mask = (total_misfit_grid > 0)
    valid_positive = total_misfit_grid[valid_positive_mask]

    if len(valid_positive) == 0:
        return None, None, None, None, None, None

    # Now consider the Al2O3 constraints

    c_sample_Al2O3 = df[mask]['Al2O3_primary']
    x_Al_min, x_Al_max = obtain_thickness_major(c_sample_Al2O3)
    x_min_Al_idx, x_max_Al_idx = (x_Al_min - 15) / 2, (x_Al_max - 15) / 2

    threshold = np.percentile(valid_positive, 10)
    threshold_mask = (total_misfit_grid < threshold) & valid_positive_mask

    threshold_indices = np.argwhere(threshold_mask)

    # Check if any thresholded index is within x_min_idx and x_max_idx
    bounded_indices = [tuple(idx) for idx in threshold_indices if x_min_Al_idx <= idx[0] <= x_max_Al_idx]

    if bounded_indices:
        # If we have thresholded indices within bounds → use them
        min_val = np.inf
        min_idx = None
        for idx in bounded_indices:
            val = total_misfit_grid[tuple(idx)]
            if val < min_val:
                min_val = val
                min_idx = tuple(idx)
    else:
        return total_misfit_grid, threshold, None, x_min_Al_idx, x_max_Al_idx, dict_mix

    return total_misfit_grid, threshold, min_idx, x_min_Al_idx, x_max_Al_idx, dict_mix

def get_enrichment_values(location, depleted_locations):
    """
    Determine enrichment range based on location name.
    """
    extended_range = list(range(-100, 0, 10)) + list(range(0, 16))
    default_range = list(range(0, 16))

    # Use extended enrichment range if location name contains any depleted keyword
    if depleted_locations is not None:
        if any(keyword in location for keyword in depleted_locations):
            return extended_range
        else:
            return default_range
    else:
        return default_range


def invert_single_group(df, location, count, grids, test_enrichment_values):
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

    for scale_val in test_enrichment_values:

        total_misfit_grid, threshold, min_idx, x_min_Al_idx, x_max_Al_idx, dict_mix = compute_total_ree_misfit(
            df=df,
            mask=mask,
            scale_val=scale_val,
            grids=grids
        )

        if min_idx is not None:
            global_min_value = total_misfit_grid[min_idx]
        else:
            continue

        if global_min_value < best_result["min_misfit_value"]:
            print('Scale:', scale_val, 'Global min misfit:', global_min_value)

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

    for i, ree in enumerate(ree_variables):
        factor = best_result["scaling_factors"][ree]
        mean_ree[i] = factor * mean_ree[i]
        low_ree[i] = factor * low_ree[i]
        high_ree[i] = factor * high_ree[i]

    return {
        "min_idx": best_result["min_idx"],
        "T_mean": 65 + t_idx * 5,
        "depth_mean": 15 + p_idx * 2 + 1,
        "pres_mean": average_pres_grid[p_idx, t_idx],
        "pres_min": average_pres_min_grid[p_idx, t_idx],
        "pres_max": average_pres_max_grid[p_idx, t_idx],
        "basalt_percentage": best_result["scale"],
        "misfit_value": best_result["min_misfit_value"],
        "misfit_grid": best_result["misfit_grid"],
        "threshold": best_result["threshold"],
        "mean_ree": mean_ree,
        "low_ree": low_ree,
        "high_ree": high_ree,
        "litho_thickness_ref": litho_thickness_ref,
        "Al_depth_range": (x_min_Al_idx, x_max_Al_idx)
    }

def remove_keys(d, keys):
    new_d = d.copy()
    if isinstance(keys, str):
        keys = [keys]
    return {k: v for k, v in new_d.items() if k not in keys}

def plot_results(df, location, count, result):
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), layout='constrained')
    # Plot on left panel
    ax = axs[0]

    if result["min_idx"] is None:
        return
    else:
        p_idx, t_idx = result["min_idx"]

    ree_variables = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                     'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']

    mask = df["location"] == location
    sample_values = df[ree_variables][mask].to_numpy()

    for i in sample_values:
        plot_ree(ax, i, 'k', 2, label=None)

    plot_ree(ax, result["mean_ree"], 'red', 2, label=None)

    plot_ree_range(ax, result["mean_ree"], result["low_ree"], result["high_ree"])

    # Plot on left panel
    ax = axs[1]
    best_misfit_grid = result["misfit_grid"]
    best_threshold = result["threshold"]
    litho_thickness_ref = result["litho_thickness_ref"]
    basalt_percentage = result["basalt_percentage"]
    x_min_Al_idx, x_max_Al_idx = result["Al_depth_range"]

    masked_grid = np.ma.masked_where((best_misfit_grid <= 0) | np.isnan(best_misfit_grid), best_misfit_grid)
    # Set colormap with masked color as white
    cmap = plt.colormaps.get_cmap('viridis').copy()
    cmap.set_bad(color='white')
    # Plot masked grid
    im = ax.imshow(masked_grid, cmap=cmap)
    fig.colorbar(im, ax=ax, label='Misfit')

    # Set limits to match data
    nx = 58
    ny = 53
    ax.set_xlim(0, nx)
    ax.set_ylim(ny, 0)

    x_ticks = np.arange(0, nx, 10)
    x_labels = 65 + 5 * x_ticks
    ax.set_xticks(ticks=x_ticks, labels=x_labels)

    y_ticks = np.arange(0, ny, 10)
    y_labels = 15 + 2 * y_ticks
    ax.set_yticks(ticks=y_ticks, labels=y_labels)

    ax.set_xlabel('Excess Temperature (K)')
    ax.set_ylabel('Lithospheric thickness (km)')

    # Find min positive L2 norm value and its location
    ax.plot(t_idx, p_idx, marker='*', color='red', markersize=10)

    # Contour for lowest 3% (excluding 0 and NaN)
    ax.contour(best_misfit_grid, levels=[best_threshold], colors='white', linewidths=1.5)
    if litho_thickness_ref is not None:
        ax.axhline((litho_thickness_ref - 15) / 2, color='black', linestyle='--')

    ax.fill_between([0, 100], 0, x_min_Al_idx, color='white', edgecolor='black', linewidths=1.3, alpha=0.5,
                    linestyle='-')
    ax.fill_between([0, 100], x_max_Al_idx, 100, color='white', edgecolor='black', linewidths=1.3, alpha=0.5,
                    linestyle='-')

    if basalt_percentage >= 0:
        fig.suptitle(f"{location}, Basalt Percentage = {basalt_percentage: .0f} %", fontsize=13.6,
                     fontweight='bold')
    else:
        fig.suptitle(f"{location}, Depleted Percentage = {basalt_percentage: .0f} %", fontsize=13.6,
                     fontweight='bold')

    results_dir = Path("inversion_figures")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"ree_comparison_{location}_N{count}.png"

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {output_file.resolve()}")
    plt.close(fig)


def invert_melt_condition(file_name, depleted_location=None, correction=False,
                          src_Fo=0.9, max_olivine_addition=0.4, make_figures=False):
    if correction == False:
        df = read_melt_composition(file_name)
    else:
        df = fractionation_correction(file_name, src_Fo, max_olivine_addition)

    group_list = build_group_list(df)
    grids = load_all_grids()
    results = []

    for g_i, group in enumerate(group_list):
        location, count = group
        test_enrichment_values = get_enrichment_values(location, depleted_location)
        result = invert_single_group(df, location, count, grids, test_enrichment_values)

        if result is not None:
            result["location"] = location
            result["count"] = count

            keys_to_be_removed = ["misfit_grid", "threshold", "Al_depth_range", "scaling_factors",
                                  "mean_ree", "low_ree", "high_ree", "min_idx"]
            results.append(remove_keys(result, keys_to_be_removed))

            if make_figures == True:
                plot_results(df, location, count, result)

    summary_df = pd.DataFrame(results)
    save_results(file_name, summary_df)

    return summary_df




