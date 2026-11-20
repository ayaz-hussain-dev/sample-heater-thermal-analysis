# Model and assumptions

## CAD

The footprint is 60 × 40 mm. Six blind wells have diameter 8 mm and depth 12 mm. The lengthwise centre coordinates are 15, 30 and 45 mm; the widthwise coordinates are 12 and 28 mm. A is 20 mm high and B is 15 mm high, leaving 8 mm and 3 mm of metal beneath the wells respectively. Both models use a pad, a pocket and a rectangular pattern in CATIA V5.

## Material and loads

| Quantity | Value |
|---|---:|
| Density | 2770 kg/m³ |
| Specific heat | 875 J/(kg·K) |
| Conductivity at -100, 0, 100, 200 °C | 114, 144, 165, 175 W/(m·K) |
| Initial / ambient temperature | 22 / 22 °C |
| Base input | 10 W, constant from 0 to 600 s |
| Heater area | 2400 mm² |
| Nominal base-normal input flux | 0.004166667 W/mm² = 4166.667 W/m² |
| Convection coefficient | 10 W/(m²·K) = 0.00001 W/(mm²·K) |
| Convection scope | All faces except the heater base; includes blind-well walls and floors |

The material is the built-in generic Aluminum Alloy. A particular commercial alloy grade or surface finish is not established. Its properties are not being claimed for a manufactured prototype.

## Solver and postprocessing

ANSYS Mechanical 2026 R1 Teaching was used for the transient thermal solves. Time integration is on, automatic time stepping is off and the duration is 600 s. Results are stored at all solved time points. Nominal element size and node/element counts are recorded in data/cases.json and results/case_summary.csv. The mesher uses program-controlled element order. Exact element IDs, minimum quality measures and an element-quality histogram were not exported, so they are not inferred here.

The main A/B comparison uses 1 mm meshes and 1.25 s time steps. Refinement studies change either mesh size or time step within each pair. Because the study is staged, the eight rows are not one common-time-step three-grid sequence; no Richardson order or GCI is claimed.

Temperature_WellWalls is scoped to 12 cylindrical face patches representing the six well walls. It excludes the six flat floors. All-body temperature and heat-flux results retain their original scope. Contour heat flux uses the displayed averaged treatment; the table's Average column is retained as an ANSYS-reported statistic, not assumed to be a volume-, mass- or area-weighted mean.

## Interpretation

- Warm-up time is the first interpolated crossing of a selected benchmark by the minimum exported well-wall temperature.
- The benchmarks 40, 50, 60 and 65 °C are chosen for numerical comparison. They are not medical assay requirements or acceptance criteria.
- Wall spread is maximum minus minimum over all selected cylindrical walls at the same instant. It combines within-well and across-well spatial variation.
- Power × warm-up time is input energy, not sample energy or efficiency.
- Total Heat Flux is a conductive flux magnitude. Multiplying its unsigned spatial mean by arbitrary surface area does not produce a verified net heat rate.
- The pointwise peak heat flux is not mesh converged in these tests. Local edge behaviour and result recovery may contribute, but their separate contributions have not been isolated.

## Limits and follow-up

The model omits tubes, liquid samples, thermal contact resistance, sample heat capacity, fixtures, radiation and a temperature controller. A uniform convection coefficient is prescribed on external and cavity surfaces; air flow and natural convection inside the wells are not solved. Only one initial condition and one heater power are solved in FEA. The smaller wall spread in A is a numerical observation under this setup, not a measured device tolerance.

The temperature sensitivity checks use whole-body extrema. Wall-scoped refinement exports, an independently integrated FEA energy balance, physical heater/contact measurements and controlled-temperature tests would be needed for stronger device-level conclusions. No physical prototype testing was performed.
