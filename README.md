


> # meltinv

**meltinv** is a Python package for joint inversion of:

- Melt temperature
- Lithospheric thickness (and the corresponding melt pressure range)
- Mantle relative source enrichment

using Rare Earth Element (REE) compositions and Al<sub>2</sub>O<sub>3</sub> concentrations in the primary magma.

---

## Features

- Read CSV or Excel files containing sample major and trace element compositions.

- Perform fractionation-correction calculations from the command line or within Python using **meltPT**, and automatically calculate the major and trace element concentrations of the primary magma.

- Use the primary magma REE compositions to invert melting conditions for groups of samples (at least two samples per group), and output the inversion results as Excel files.

- For each group, generate figures comparing REE compositions of the observations and the model predictions, and showing the misfit distribution in lithospheric thickness–temperature space.

## Installation

Clone the repository:

```
git clone https://github.com/?/meltinv.git
cd meltinv
pip install .
```
If you would like to develop this package, please replace the last line with the following command:

```
pip install -e .
```


## Core Functions

The **meltinv** package provides two main functions:

- **`correction`**  
  Estimates the primary magma composition by first reconstructing the original melt from major element data, and then using olivine addition to calculate the Rare Earth Element (REE) concentrations of the primary magma.

- **`invert`**  
  Simultaneously inverts for melting temperature, lithospheric thickness, and relative mantle source enrichment for groups of samples.

### Function 1: Fractionation Correction  
  
```python  
import meltinv  
meltinv.correction("input_file.xlsx", src_Fo=0.9, max_olivine_addition=0.5)
```
**Parameters:**

-   `input_file`: Path to the input **CSV** or **Excel** file.
    
-   `src_Fo`: Forsterite content of the mantle source olivine. The default value is 0.9.
    
-   `max_olivine_addition`: Maximum proportion of olivine added during correction. The default value is 0.5.

### Function 2: Inversion

The inversion can be performed directly using primary magma REE compositions. You do not need to run the `correction` step beforehand if your input file already contains primary melt REE data.

```python
import meltinv
meltinv.invert("input_file.xlsx", correction=False)
```
Alternatively, fractionation correction can be applied within the inversion step by enabling `correction=True`:
```python
meltinv.invert(
    "input_file.xlsx",
    correction=True,
    src_Fo=0.9,
    max_olivine_addition=0.5,
    make_figures=True
)
```
**Parameters:**

-   `file_name`: Input **CSV** or **Excel** file containing sample data. The input file must contain the following columns:  `  
['location',  
'La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',  
'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']`.

	Note: (i) Not all elements above are required to have values for every sample; missing values (`None`) are permitted. Any value of `0` is treated as missing (`None`).
	
	(ii) However, for each sample to be included in the inversion, it must contain at least **6 valid (non-missing) REE values**. Samples with fewer than 6 available REE measurements will be excluded from the inversion. 
	
	(iii) Samples from the same location are treated as a group.
    
- `depleted_locations`: Optional **list** of locations that may represent depleted mantle sources. For these locations, the inversion considers an expanded range of source compositions. In addition to mixing basalts with primitive mantle, it also allows contributions from a depleted mantle endmember when estimating the source composition.
    
-   `correction`: Whether to perform fractionation correction before inversion
    
-   `src_Fo`: Forsterite content of source olivine (used only when `correction=True`)
    
-   `max_olivine_addition`: Maximum olivine addition during correction (used only when `correction=True`)
    
-   `make_figures`: If `True`, generates REE comparison and misfit plots (saved as **PNG files**) for each group of samples.

## Command Line Usage

The **meltinv** package provides a command-line interface for performing fractionation correction and inversion directly from the terminal.

### Function 1: Fractionation Correction  

The `correction` function performs fractionation correction to estimate primary magma compositions from major and trace element data.  
  
```bash  
meltinv correction <file_name> [options]
```

**Arguments:**

-   `file_name` (required)
    
-   `--src_Fo` (optional, default = 0.9)
    
-   `--max_olivine_addition` (optional, default = 0.5)

Run correction with custom parameters:
```bash  
meltinv correction input.xlsx --src_Fo  0.89 --max_olivine_addition  0.45
```
    
### Function 2: Inversion

The `invert` function can be executed from the command line with the following arguments:

```bash
meltinv invert <file_name> [options]
```

**Arguments:**

-   `file_name` (required)
    
-   `--depleted` (optional):  
    One or more location names treated as depleted mantle sources. For these locations, the inversion considers an expanded range of source compositions, including a depleted mantle endmember.
    
-   `--correction` (optional):  
    If specified, performs fractionation correction before inversion.
    
-   `--src_Fo` (optional, default = 0.9)
    
-   `--max_olivine_addition` (optional, default = 0.5)
    
-   `--make_figures` (optional)

### Examples

Run inversion without correction:
```bash
meltinv invert input.xlsx
```
Run inversion with depleted mantle locations:
```bash
meltinv invert input.csv --depleted Iceland Galapagos
```
Run inversion with fractionation correction:
```bash
meltinv invert input.csv --correction
```
Run inversion with all options enabled:
```bash
meltinv invert input.xlsx \  
  --depleted Iceland Galapagos \  
  --correction \  
  --src_Fo  0.89 \  
  --max_olivine_addition 0.39 \  
  --make_figures
```
## Output

-  The fractionation-corrected file is saved to  `"your_path/inversion_results/{file_name}_corrected.xlsx"`, 
where `{file_name}` is the base name of the input file.

-  The inversion results are saved in `"your_path/inversion_results/{file_name}_inversion_summary.xlsx"`, 
where `{file_name}` is the base name of the input file.

-  The generated figures are saved in:  `"your_path/inversion_figures/ree_comparison_{location}_N{count}.png"`, where `{location}` is the sample location  and `{count}` is the number of samples in the group



## Citation

If you are using **meltinv**  in your research, please cite:

Jiang et al. (2026), xxx, Journal Name
