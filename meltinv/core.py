from . import inversion
from .inversion import invert_melt_condition
from .frac_correction import fractionation_correction

def invert(file_name, depleted_locations=None, correction=False, src_Fo=0.9,
           max_olivine_addition=0.5, individual_sample_figures=False,
           group_comparison_figure=True, make_figures=None, per_sample=True, *, plot_archive=None,
           fe3_fe_total=0.1, measured_fe3=False):
    """
    High-level API for melt inversion. Every sample is inverted individually.

    plot_archive optionally saves a self-contained snapshot for regenerate_figures().
    It can be saved with both plotting flags disabled.

    fe3_fe_total is the Fe3+/sum Fe the olivine correction uses to split total iron,
    for every sample by default; with measured_fe3=True, samples reporting both FeO
    and Fe2O3 keep their measured split.

    make_figures is kept for backward compatibility; it sets individual_sample_figures.
    per_sample is kept for backward compatibility; only True is supported here.
    """
    if not per_sample:
        raise ValueError(
            "Group inversion (per_sample=False) is not available on this version. "
            "Install the 'group_samples' branch of meltinv to invert groups of samples.")

    if make_figures is not None:
        individual_sample_figures = make_figures

    summary_df = invert_melt_condition(file_name, depleted_locations, correction,
                          src_Fo, max_olivine_addition, individual_sample_figures,
                          group_comparison_figure, plot_archive=plot_archive,
                          fe3_fe_total=fe3_fe_total, measured_fe3=measured_fe3)

    return summary_df

def correction(file_name, src_Fo=0.9, max_olivine_addition=0.5, fe3_fe_total=0.1, measured_fe3=False):
    return fractionation_correction(file_name, src_Fo, max_olivine_addition, fe3_fe_total, measured_fe3)



