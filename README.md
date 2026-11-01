# Joint maize / rice input-subsidy allocation in Cameroon: lexicographic goal program

Reproducibility package for *Joint Optimization of Regional Allocation of Seed and Agricultural Input
Subsidies for Maize and Rice in Cameroon: A Goal-Programming Approach in Support of the SND30*
(Bwo'nyahre Baidi B., Kouakep Tchaptchie Y.).

## Contents
```
code/goal_programming_model.py   model: three systems (maize, rainfed rice, irrigated rice), shared land,
                                 extension premium, adoption, additionality, budget ceiling, off-season rice
code/data_analysis.py            exploitation of the project data workbook (observed yields and area expansion)
code/run_scenarios.py            regenerates every result table (results/t01 ... t18)
code/make_figures.py             regenerates Figures 4-7 (figures/)
data/projet_mais_cameroun_donnees.xlsx   project data workbook (regional maize panel 2007-2024, sources per row)
data/parameters_documented.csv   every parameter with source and confidence flag
data/table2_rice_cost_buildup.md rice input-cost line items and the seed-cost explanation
results/                         output tables;  figures/  output figures
```
## Reproduce
```
pip install numpy scipy pandas openpyxl matplotlib --break-system-packages
cd code && python3 run_scenarios.py && python3 make_figures.py
```
Deterministic (HiGHS; the Monte-Carlo draws use a fixed-seed scrambled Sobol sequence).

## Model in one paragraph
Stage 1 minimises the shortfall against the maize and rice targets, each measured as a share of its target;
Stage 2 minimises cost among Stage-1-optimal solutions. Newly cultivated hectares cost (1+kappa) times the
input package (central kappa = 0.30). With `budget=B` the same program maximises attainment under a ceiling B.

## Data honesty note
* Maize areas, yields: AGRISTAT 2022 (verbatim). Ceiling yields and kappa: estimates, tested in sensitivity.
* **Irrigated rice areas** (14,630 ha) are documented from public sources (SEMRY 2023; UNIDO ITPO 2021 profile).
  The irrigated baseline yield (4.0 t/ha) is an assumption.
* **Rainfed rice areas (about 125,200 ha) and the national 2020 rice base (215,101 t) are reconstructed**, not
  measured: the regional AGRISTAT rice-area table was not available. Replace them if it is found.
* The SND30 national maize series (1,985,330 t in 2020) differs from the AGRISTAT regional total (2,087,957 t).
