# Lookup arrays

Each `*.npy` file is a 53 x 58 array (thickness row, temperature column). Cell (row j, column i)
covers lithospheric thickness 15 + 2j to 17 + 2j km and excess temperature 65 + 5i to 70 + 5i K;
values are evaluated at the cell centre (16 + 2j km, 67.5 + 5i K). Cells whose centre lies outside
the convex hull of the simulation snapshots are NaN.

| File | Quantity |
|---|---|
| `ree_average_<REE>.npy` | mean instantaneous-melt concentration over the melt region, weighted by M r (ppm) |
| `ree_average_F.npy`, `ree_average_M.npy` | mean melt fraction (weights M r) and mean melting rate (weights r, Myr^-1) |
| `melt_average_pres.npy`, `melt_average_temp.npy` | mean melting depth (km) and mean potential temperature (K), weights M r |
| `*_min_*.npy`, `*_max_*.npy` | 10th and 90th percentiles over the melt region with the same weights (display only) |

The melt region is S = {M > 0} on a 150 x 150 grid of (depth, r) over 0-300 km, and r is the
true distance from the plume axis.

## How they were built (OT reconstruction v2, 2026-11-05)

- 77 plume-tail snapshots (t >= 3 Myr) from 30 simulation cases, placed at their exact
  (Delta T_plume, h); see the paper's supplementary node table.
- h is the lithospheric thickness of each snapshot: the mean depth of the 1448 K (1175 C)
  isotherm of the model temperature within 150 km of the plume axis, weighted by r (an area
  average over that disc).
- The melting particles of each snapshot that are connected to the plume axis (particles closer
  than 8 km linked in 3-D) are projected to (r = sqrt(x^2 + y^2), depth), mirrored to -r,
  linearly interpolated onto the (depth, r) grid, masked by the melt-region outline,
  Gaussian-smoothed inside it (sigma = 1.3 cells) and floored at 1e-4.
- Every cell centre inside the hull is reconstructed by entropic optimal-transport displacement
  interpolation (GeomLoss 0.2.6, blur 0.5 cell, scaling 0.99): the constant-h line through the
  centre meets the edges of its Delaunay triangle at L and R; the fields at L and R are
  interpolations along those edges at their exact fractions, and the cell field is the
  interpolation from L to R at the cell's fraction of the way.
- Means and percentiles are computed from each reconstructed field. No smoothing is applied
  across the temperature-thickness grid. 1855 cells have values (centres 87.5-342.5 K and
  24-112 km).
