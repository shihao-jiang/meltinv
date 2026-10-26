"""
Paper figure for the modern ocean-island basalt comparison (used by 03_modern_OIB.ipynb).

The figure compares meltinv's location summaries with independent estimates, grouped by
volcanic province and ordered by mean seismic lithospheric thickness:
  (a) lithospheric thickness vs seismic estimates
  (b) average melting pressure vs the Plank & Forsyth (2016) thermobarometer
  (c) excess temperature vs Putirka (2008) and Bao et al. (2022)
  (d) source enrichment
"""
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

KM_TO_GPA = 0.03          # 1 km of depth ~ 0.03 GPa


def province(location):
    """Volcanic province = location name without the bracketed island, e.g. 'Azores (Pico)' -> 'Azores'."""
    return re.sub(r"\s*\(.*?\)", "", str(location)).strip()


def thickness_error_fraction(thickness_km):
    """
    (min, max) fractional uncertainty of the seismic lithospheric thickness, from a polynomial fit to the
    plate-cooling-model uncertainty; valid for 6.7-106.8 km (the edge value is used outside that range).
    """
    min_coef = [1.1841056973765778e-07, -1.4158154301026311e-05, 0.0001800133247248022,
                0.009235571225822506, -6.244578625328507]
    max_coef = [-8.10108163130438e-07, 0.0001951352391256604, -0.01689213563454741,
                0.6341780697761912, -2.4741450082049954]
    h = np.clip(thickness_km, 6.66, 106.77)
    return np.polyval(min_coef, h) / 100 * 2, np.polyval(max_coef, h) / 100 * 2


def select(summary, misfit_cutoff):
    """Locations with a good fit, with their province, ordered by the province's mean seismic thickness."""
    df = summary[summary["misfit_value"] < misfit_cutoff].copy()
    df["province"] = df["location"].apply(province)
    order = df.groupby("province")["litho_thickness_ref"].mean().sort_values().index.tolist()
    return df, order


def _temperature_band(x, y, ax):
    """Smooth envelope (±20 K) around the literature temperatures."""
    x, y = np.asarray(x), np.asarray(y)
    xu, inv = np.unique(x, return_inverse=True)
    lo = np.array([y[inv == i].min() - 20 for i in range(len(xu))])
    hi = np.array([y[inv == i].max() + 20 for i in range(len(xu))])
    xd = np.linspace(xu.min(), xu.max(), 400)
    ax.fill_between(xd, PchipInterpolator(xu, lo)(xd), PchipInterpolator(xu, hi)(xd),
                    color="tab:orange", alpha=0.1, label="Literature range")


def comparison_figure(summary, lit_T, pf16, misfit_cutoff=0.06, corrected=True, title=None):
    """
    Four-panel comparison figure.

    summary : meltinv location summary (..._sample_inversion_summary_log10.xlsx)
    lit_T   : table with columns island_name, Tex_Putirka_2008, Tex_Bao_2022
    pf16    : table with columns island_name, P_PF16 (one row per sample)
    corrected : plot the T-P corrected values (True) or the uncorrected ones (False)
    """
    df, order = select(summary, misfit_cutoff)
    if corrected:
        T, h, P, Pmin, Pmax = df.T_mean_cali, df.depth_mean_cali, df.pres_mean_cali, df.pres_min_cali, df.pres_max_cali
    else:  # meltinv shifts the melting pressures by the same amount as the thickness correction
        shift = df.depth_mean_cali - df.depth_mean
        T, h = df.T_mean, df.depth_mean
        P, Pmin, Pmax = df.pres_mean_cali - shift, df.pres_min_cali - shift, df.pres_max_cali - shift
    df = df.assign(T_plot=T, h_plot=h, P_plot=P, Pmin_plot=Pmin, Pmax_plot=Pmax)
    lit_T = lit_T.set_index("island_name")

    fig, axs = plt.subplots(4, 1, figsize=(10, 13), layout="constrained", sharex=True)

    # (a) lithospheric thickness
    ax = axs[0]
    for i, name in enumerate(order):
        g = df[df.province == name]
        ax.axvline(i, color="grey", alpha=0.2, linestyle="--")
        lo, hi = g.litho_thickness_ref.min(), g.litho_thickness_ref.max()
        ax.vlines(i, lo - 2, hi + 2, colors="lightgray", lw=10)
        ax.vlines(i, lo * (1 + thickness_error_fraction(lo)[0]), hi * (1 + thickness_error_fraction(hi)[1]),
                  colors="lightgray", alpha=0.5, lw=10)
        ax.scatter([i] * len(g), g.litho_thickness_ref, color="gray", s=25, marker="s", zorder=3,
                   label="Seismic thickness" if i == 0 else None)
        ax.scatter([i] * len(g), g.h_plot, edgecolors="black", color="lightblue", s=72, zorder=5,
                   label="This study" if i == 0 else None)
    err = np.mean(np.abs(df.litho_thickness_ref - df.h_plot))
    ax.invert_yaxis()
    ax.set(ylim=(120, 10), ylabel="Lithospheric Thickness (km)", xticks=range(len(order)))
    ax.text(0.005, 0.95, f"(a) Average error = {err:.1f} km", transform=ax.transAxes)
    ax.legend()

    # (b) average melting pressure
    ax = axs[1]
    for i, name in enumerate(order):
        g = df[df.province == name]
        ax.axvline(i, color="grey", alpha=0.2, linestyle="--")
        ax.scatter([i] * len(g), g.P_plot * KM_TO_GPA, edgecolors="black", color="#8ad1aa", s=72, zorder=5,
                   label="This study" if i == 0 else None)
        ax.vlines(i, g.Pmin_plot.min() * KM_TO_GPA, g.Pmax_plot.max() * KM_TO_GPA, colors="green", alpha=0.3, lw=10)
        p = pf16.loc[pf16.island_name.astype(str).str.contains(name, case=False, regex=False), "P_PF16"].to_numpy()
        p = p[np.isfinite(p)]
        if len(p):
            ax.scatter(i, p.mean(), color="orange", s=25, marker="s",
                       label="Plank & Forsyth (2016)" if i == 0 else None)
            ax.fill_between([i - 0.15, i + 0.15], p.mean() - p.std(), p.mean() + p.std(), color="orange", alpha=0.5)
    ax.set(ylim=(6, 1.55), yticks=[6 - k * 0.8 for k in range(6)], ylabel="Average Melting Pressure (GPa)")
    ax.text(0.005, 0.95, "(b)", transform=ax.transAxes)
    ax.legend(loc=1)

    # (c) excess temperature
    ax = axs[2]
    colors = {"Tex_Putirka_2008": "#dd8452", "Tex_Bao_2022": "#4c72b0"}
    labels = {"Tex_Putirka_2008": "Putirka (2008)", "Tex_Bao_2022": "Bao et al. (2022)"}
    xs, ys = [], []
    for i, name in enumerate(order):
        ax.axvline(i, color="grey", alpha=0.15, linestyle="--")
        if name not in lit_T.index:
            continue
        for ref in ["Tex_Putirka_2008", "Tex_Bao_2022"]:
            v = lit_T.loc[name, ref]
            if np.isfinite(v) and v > 0:
                xs.append(i)
                ys.append(v)
                ax.scatter(i, v, color=colors[ref], s=60, alpha=0.5, marker="s", label=labels[ref] if i == 0 else None)
    if xs:
        _temperature_band(xs, ys, ax)
    for i, name in enumerate(order):
        g = df[df.province == name]
        ax.scatter([i] * len(g), g.T_plot, color="#FF3333", s=72, edgecolors="black", alpha=0.9,
                   label="This study" if i == 0 else None)
        ax.vlines(i, g.T_plot.min() - 10, g.T_plot.max() + 10, colors="#FF3333", alpha=0.3, lw=10)
    ax.set(ylim=(50, 350), ylabel="Plume Excess Temperature (K)")
    ax.text(0.005, 0.95, "(c)", transform=ax.transAxes)
    ax.legend(ncol=2)

    # (d) source enrichment
    ax = axs[3]
    for i, name in enumerate(order):
        g = df[df.province == name]
        ax.axvline(i, color="grey", alpha=0.2, linestyle="--")
        ax.scatter([i] * len(g), g.basalt_percentage, color="#984EA3", s=72, edgecolors="black", alpha=0.8,
                   label="This study" if i == 0 else None)
        ax.vlines(i, g.basalt_percentage.min() - 0.5, g.basalt_percentage.max() + 0.5, colors="#984EA3",
                  alpha=0.3, lw=10)
    ax.set(ylim=(0, 15), ylabel="Basalt Percentage (%)")
    ax.text(0.005, 0.95, "(d)", transform=ax.transAxes)
    ax.legend()
    ax.set_xticks(range(len(order)), order, rotation=45, ha="right")

    if title:
        axs[0].set_title(title)
    return fig


def agreement(summary, lit_T, pf16, misfit_cutoff=0.06):
    """Mean differences from the independent estimates, before and after the T-P correction."""
    df, _ = select(summary, misfit_cutoff)
    shift = df.depth_mean_cali - df.depth_mean
    lit = lit_T.set_index("island_name")
    rows = []
    for label, T, h, P in [("before T–P correction", df.T_mean, df.depth_mean, df.pres_mean_cali - shift),
                           ("after T–P correction", df.T_mean_cali, df.depth_mean_cali, df.pres_mean_cali)]:
        d = df.assign(T=T, h=h, P=P * KM_TO_GPA)
        row = {"": label, "locations": len(d),
               "thickness − seismic, mean |Δ| (km)": np.mean(np.abs(d.h - d.litho_thickness_ref)),
               "thickness − seismic, mean Δ (km)": np.mean(d.h - d.litho_thickness_ref)}
        Tp = d.groupby("province").T.mean()
        for ref, name in [("Tex_Putirka_2008", "Putirka (2008)"), ("Tex_Bao_2022", "Bao et al. (2022)")]:
            both = pd.concat([Tp, lit[ref]], axis=1, join="inner").dropna()
            both = both[both[ref] > 0]
            row[f"T − {name}, mean |Δ| (K)"] = np.mean(np.abs(both["T"] - both[ref]))
        Pp = d.groupby("province").P.mean()
        dp = [Pp[n] - pf16.loc[pf16.island_name.astype(str).str.contains(n, case=False, regex=False), "P_PF16"].mean()
              for n in Pp.index]
        row["P − Plank & Forsyth (2016), mean |Δ| (GPa)"] = np.nanmean(np.abs(dp))
        rows.append(row)
    return pd.DataFrame(rows).set_index("")
