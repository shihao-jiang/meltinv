from . import inversion
from .inversion import invert_melt_condition
from .frac_correction import fractionation_correction

def invert(file_name, depleted_locations=None, correction=False, src_Fo=0.9,
           max_olivine_addition=0.5, make_figures=False):
    """
    High-level API for melt inversion.
    """
    summary_df = invert_melt_condition(file_name, depleted_locations, correction,
                          src_Fo, max_olivine_addition, make_figures)

    return summary_df

def correction(file_name, src_Fo=0.9, max_olivine_addition=0.5):
    return fractionation_correction(file_name, src_Fo, max_olivine_addition)



