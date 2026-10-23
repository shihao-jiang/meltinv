"""Figure rendering, independent of the inversion and model grids."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from .plot_ree import plot_ree, plot_ree_range

def compress_enrichment(e):
    """Same display transform as plot_multiple_slices.py: divide negative
    (depleted) basalt_percentage values by 100, leave enriched (>=0) as is."""
    e = np.asarray(e, dtype=float)
    return np.where(e < 0, e / 100, e)


def misfit_weighted_stats(values, misfit):
    """
    Descriptive mean and population spread, weighted by 1 / (misfit + 1e-6).
    The small offset is the existing rule for handling exact fits; this is not
    an uncertainty model or a standard error of the mean.
    """
    values, misfit = np.asarray(values, dtype=float), np.asarray(misfit, dtype=float)
    w = 1.0 / (misfit + 1e-6)
    mean = np.average(values, weights=w)
    std = np.sqrt(np.average((values - mean) ** 2, weights=w))
    return mean, std


def enrichment_ticks(enrichment_values):
    """Tick positions/labels for the (possibly non-uniformly spaced) enrichment
    axis: nearest grid index to a set of round target values."""
    ev = np.asarray(enrichment_values, dtype=float)
    targets = [-100, -50, 0, 5, 10, 15] if ev.min() < 0 else [0, 3, 6, 9, 12, 15]
    ticks = sorted({int(np.abs(ev - t).argmin()) for t in targets})
    return ticks, [f"{ev[i]:g}" for i in ticks]


def plot_results(df, location, count, result, output_dir="inversion_figures"):
    """Draw the observed/fitted REEs and three slices through the best fit.

    df contains cleaned primary-magma REEs in ppm and a location column.
    result comes from invert_single_group(retain_diagnostics=True), or from a
    saved plotting archive. The labels and slices describe the *uncalibrated*
    best fit; group plots below use calibrated per-sample results. See
    docs/code-guide.md for the dictionary fields and array axes.
    """
    if result["min_idx"] is None:
        return

    p_idx, t_idx = result["min_idx"]
    min_value = result["misfit_value"]
    full_3d_grid = result.get("full_3d_grids")
    if full_3d_grid is not None:
        grid_shape = full_3d_grid.shape
        temperature_slice = full_3d_grid[:, p_idx, :]
        depth_slice = full_3d_grid[:, :, t_idx]
    elif all(key in result for key in ("grid_shape", "temperature_slice", "depth_slice")):
        grid_shape = result["grid_shape"]
        temperature_slice = result["temperature_slice"]
        depth_slice = result["depth_slice"]
    else:
        raise ValueError("Plot diagnostics are missing. Use retain_diagnostics=True "
                         "when fitting, or regenerate_figures() with a saved plot archive.")
    e_i, p_i, t_i = np.unravel_index(result["global_flat_index"], grid_shape)
    basalt_idx = result["basalt_idx"]
    enrichment_values = np.asarray(result["enrichment_values"], dtype=float)

    fig, axs = plt.subplots(2, 2, figsize=(9, 7.35), layout='constrained')
    # Top left: observed REEs and the fitted model envelope.
    ax = axs[0, 0]

    ree_variables = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
                     'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']

    mask = df["location"] == location
    sample_values = df[ree_variables][mask].to_numpy()

    for sample_index, concentrations in enumerate(sample_values):
        label = 'Sample' if sample_index == 0 else None
        plot_ree(ax, concentrations, 'k', 2, label=label)

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

    # Top right: temperature versus thickness at the best-fit enrichment.
    ax = axs[0, 1]
    plot_scale = min_value if min_value > 0 else 1.0
    misfit_label = "misfit / minimum misfit" if min_value > 0 else "absolute log10 misfit (exact best fit)"
    best_misfit_grid = result["misfit_grid"] / plot_scale

    litho_thickness_ref = result["litho_thickness_ref"]

    masked_grid = np.ma.masked_where((best_misfit_grid < 0) | np.isnan(best_misfit_grid), best_misfit_grid)
    # Set colormap with masked color as white
    cmap = plt.colormaps.get_cmap('viridis').copy()
    cmap.set_bad(color='white')
    # Plot masked grid
    im = ax.imshow(masked_grid, cmap=cmap)
    cbar = fig.colorbar(im, ax=ax, label=misfit_label)
    cbar.ax.yaxis.set_major_formatter('{:.1f}'.format)

    # Grid columns are 5 K apart from 65 K; rows are 2 km apart from 16 km.
    ny, nx = result["misfit_grid"].shape
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

    # Retain both legacy markers; the exhaustive search makes them coincide.
    ax.plot(t_i, p_i, marker='o', color='orange', markersize=10)
    ax.plot(t_idx, p_idx, marker='*', color='red', markersize=10)

    # Misfit-ratio contours, not percentiles or confidence intervals.
    # For an exact fit (minimum zero), use absolute misfit to avoid division by zero.
    levels = [1.1, 1.3, 1.5, 2, 2.5, 3, 5]
    cs = ax.contour(best_misfit_grid, levels=levels, colors='white', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.1f')
    if litho_thickness_ref is not None:
        ax.axhline((litho_thickness_ref - 16) / 2, color='black', linestyle='--')

    ratio_of_local_global_misfit = result["ratio_of_local_global_misfit"]

    ax.text(0.02, 0.95, f"Ratio to Global Min Misfit = {ratio_of_local_global_misfit:.1f}", transform=ax.transAxes)

    ax = axs[1, 0]
    best_misfit_grid = temperature_slice / plot_scale
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
    best_misfit_grid = depth_slice / plot_scale
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

    results_dir = Path(output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    output_file = results_dir / f"ree_comparison_{location}_log10_N{count}.png"

    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {output_file.resolve()}")
    plt.close(fig)


def plot_group_comparison(results_df, min_count=3, output_dir="inversion_figures"):
    """
    Plot one figure per location comparing its per-sample temperature,
    thickness and enrichment results. Locations with fewer than min_count samples are skipped.
    Temperature and thickness use calibrated columns. Enrichment is transformed
    only for display; histogram statistics are computed after that transform.
    """
    results_dir = Path(output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    for location, group in results_df.groupby("location"):
        group_number = len(group)
        if group_number < min_count:
            print(f"Skipping group comparison figure for {location}: "
                  f"{group_number} sample(s), at least {min_count} needed.")
            continue

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

