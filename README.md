# Reproducibility package

**Joint Optimization of Regional Allocation of Seed and Agricultural Input Subsidies
for Maize and Rice in Cameroon: A Goal-Programming Approach in Support of the SND30**
B. BWO'NYAHRE BAIDI, Y. KOUAKEP TCHAPTCHIE — *Discover Applied Mathematics* (major revision)

This package replaces the "available upon request" Data Availability Statement of the
submitted version with a complete, runnable, self-contained set of code, data and
results (reviewer point 10).

## Contents

```
code/
  goal_programming_model.py   core genuine goal-programming model (reviewer point 1)
  run_scenarios.py            generates every result table used in the revised manuscript
data/
  parameters_documented.csv   every model parameter, by region/crop, WITH its source and
                               a confidence flag (reviewer point 6)
  table2_rice_cost_buildup.md line-item reconstruction of the rice input cost table,
                               with the JICA source value for each line (reviewer point 6)
results/
  table1_target_scenario_matrix.csv          reviewer point 3 (scenario matrix incl. 100/100)
  table2_adoption_sensitivity_gp.csv         reviewer point 4 (adoption uncertainty, explicit
                                              shortfalls instead of bare "infeasible")
  table3_land_assumption_robustness.csv      reviewer point 5 (shared vs separate land,
                                              extension cost premium)
  table4_budget_definition_partial_financing.csv   reviewer point 7
  table5_dual_value_robustness.csv           reviewer point 8
  table6_central_allocation_and_duals.csv    central scenario detail, with data-source flag
                                              per region
  table7_rice_cost_buildup.csv               reviewer point 6
```

## How to reproduce

```
pip install numpy scipy pandas --break-system-packages
cd code
python3 goal_programming_model.py   # central scenario, sanity check
python3 run_scenarios.py            # regenerates every CSV in ../results/
```
Requires Python >= 3.9, scipy >= 1.10 (HiGHS solver). No external data download is
required: all inputs are hard-coded in `goal_programming_model.py` with inline source
citations, so the computation is fully self-contained and deterministic.

## What changed from the submitted version (methodology)

The submitted manuscript solved a minimum-cost LP under hard "achieved production >=
target" constraints and described it as "equivalent to a single-priority goal program."
Reviewer 1 correctly noted this is a relabeled LP, not a genuine goal program. This
package implements an authentic **two-stage lexicographic goal program**:

- **Stage 1 (Priority 1):** minimize the weighted shortfall against the two production
  targets, using explicit non-negative deviation variables `d_m^-, d_m^+, d_r^-, d_r^+`.
- **Stage 2 (Priority 2):** among all solutions attaining the Stage-1-optimal shortfall,
  minimize total subsidy cost.

Unlike the hard-constraint LP, this formulation never simply returns "infeasible": when
land or budget is too tight, it reports the exact shortfall in tonnes for each crop,
which is used directly in the scenario tables above (reviewer points 3, 4, 5).

## Data honesty note (important — read before citing table6)

Current rice area (`S_i,r`) for the **three irrigated regions** (Far North, North,
Northwest) is recovered from the submitted manuscript's own published optimal solution,
where the text states the optimal rice intensification area equals "all or nearly all"
of the current area — so these three values are an exact reconstruction, not a guess.

Current rice area for the **seven rainfed regions** could not be recovered: the original
project's disaggregated AGRISTAT rice-by-region table was lost between work sessions and
is not reproduced from an official source here. These seven values are a **documented,
transparent estimate** (see the docstring of `goal_programming_model.py`, function
derivation for `S_r_rainfed`), built from (a) the manuscript's own national rice
production trajectory, (b) subtraction of the (exact) irrigated-region production, and
(c) a proportional allocation to the 7 rainfed regions using their current maize area as
a structural proxy. **This is flagged explicitly in the revised manuscript as a
limitation and is not presented as an AGRISTAT figure.** Because rice extension is zero
in all seven rainfed regions at every tested optimum (the land and cost structure makes
rainfed-rice extension unattractive relative to maize or irrigated rice), this
reconstruction does not affect the central published result, but it does enter the new
land-sensitivity and alternative-scenario tables and should be refined with the original
disaggregated source before any policy use beyond this article.

## Citation of primary sources

- DESA/MINADER. Annuaire statistique du MINADER (AGRISTAT), édition 2022.
- Institut National de la Statistique du Cameroun (INS). Annuaires statistiques régionaux, 2019–2024.
- Task-force Riz, MINADER/JICA. Analyse de la compétitivité de la filière riz au Cameroun. 2021.
- République du Cameroun. Rapport d'évaluation à mi-parcours de la SND30. 2025.
