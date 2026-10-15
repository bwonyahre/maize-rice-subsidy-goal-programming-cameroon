# -*- coding: utf-8 -*-
"""
Runs the full scenario suite for the major revision and writes CSV result tables to
../results/. Each table maps to a manuscript table (noted in comments).

Run: python3 -I run_scenarios.py
"""
import os
import pandas as pd
from goal_programming_model import (
    solve_goal_program, REGIONS, SND30_TARGET_m, SND30_TARGET_r,
    S_m, S_r, Y0_m, Y0_r, Y1_m, Y1_r, COST_m, COST_r, RICE_COST_LINE_ITEMS,
)

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(OUT, exist_ok=True)


def fmt_bn(fcfa):
    return round(fcfa / 1e9, 2)


# ---------------------------------------------------------------------------------
# TABLE 1 -- target-scenario matrix (80/90 vs official 100/100 vs
# intermediate combinations), beta=0.5, full adoption.
# ---------------------------------------------------------------------------------
rows = []
target_pairs = [
    ("80% maize / 90% rice (central, as in submitted version)", 0.80, 0.90),
    ("80% maize / 100% rice", 0.80, 1.00),
    ("90% maize / 90% rice", 0.90, 0.90),
    ("90% maize / 100% rice", 0.90, 1.00),
    ("100% maize / 100% rice (official SND30 targets)", 1.00, 1.00),
]
for label, fm, fr in target_pairs:
    Tm, Tr = fm * SND30_TARGET_m, fr * SND30_TARGET_r
    res = solve_goal_program(Tm, Tr, beta=0.5)
    rows.append({
        "scenario": label, "target_maize_pct": fm * 100, "target_rice_pct": fr * 100,
        "target_maize_t": Tm, "target_rice_t": Tr,
        "achieved_maize_t": round(res["production_m_t"]),
        "achieved_rice_t": round(res["production_r_t"]),
        "shortfall_maize_t": round(res["shortfall_m_t"]),
        "shortfall_rice_t": round(res["shortfall_r_t"]),
        "min_budget_bn_fcfa": fmt_bn(res["total_cost_fcfa"]),
        "feasible_without_shortfall": res["shortfall_m_t"] < 1 and res["shortfall_r_t"] < 1,
    })
df1 = pd.DataFrame(rows)
df1.to_csv(os.path.join(OUT, "table1_target_scenario_matrix.csv"), index=False)
print(df1.to_string(index=False))
print()

# ---------------------------------------------------------------------------------
# TABLE 2 -- adoption-rate uncertainty, now reported for the GOAL
# PROGRAM (explicit shortfalls instead of bare "infeasible"), beta=0.5, 80/90 targets.
# This becomes part of the MAIN results, not a secondary subsection.
# ---------------------------------------------------------------------------------
rows = []
for tau in [1.00, 0.80, 0.60, 0.40, 0.20]:
    res = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=0.5,
                              adoption_m=tau, adoption_r=tau)
    rows.append({
        "adoption_rate_tau": tau,
        "achieved_maize_pct_of_target": round(res["pct_target_m"], 1),
        "achieved_rice_pct_of_target": round(res["pct_target_r"], 1),
        "shortfall_maize_t": round(res["shortfall_m_t"]),
        "shortfall_rice_t": round(res["shortfall_r_t"]),
        "budget_at_this_adoption_bn_fcfa": fmt_bn(res["total_cost_fcfa"]),
    })
df2 = pd.DataFrame(rows)
df2.to_csv(os.path.join(OUT, "table2_adoption_sensitivity_gp.csv"), index=False)
print(df2.to_string(index=False))
print()

# ---------------------------------------------------------------------------------
# TABLE 3 -- alternative land assumptions.
#   (a) shared land  vs (b) separate land pools per crop
#   (c) extension cost premium over intensification (defection from "same cost" assumption)
# ---------------------------------------------------------------------------------
rows = []
for beta in [0.25, 0.5, 0.75, 1.0]:
    res_shared = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=beta,
                                     land_mode="shared")
    res_sep = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=beta,
                                  land_mode="separate")
    res_sep_extcost = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=beta,
                                          land_mode="separate", ext_cost_multiplier_m=1.3,
                                          ext_cost_multiplier_r=1.3)
    rows.append({
        "beta": beta,
        "shared_land_budget_bn": fmt_bn(res_shared["total_cost_fcfa"]),
        "shared_land_shortfall_m_t": round(res_shared["shortfall_m_t"]),
        "shared_land_shortfall_r_t": round(res_shared["shortfall_r_t"]),
        "separate_land_budget_bn": fmt_bn(res_sep["total_cost_fcfa"]),
        "separate_land_shortfall_m_t": round(res_sep["shortfall_m_t"]),
        "separate_land_shortfall_r_t": round(res_sep["shortfall_r_t"]),
        "separate_land_extcost+30pct_budget_bn": fmt_bn(res_sep_extcost["total_cost_fcfa"]),
        "separate_land_extcost+30pct_shortfall_m_t": round(res_sep_extcost["shortfall_m_t"]),
        "separate_land_extcost+30pct_shortfall_r_t": round(res_sep_extcost["shortfall_r_t"]),
    })
df3 = pd.DataFrame(rows)
df3.to_csv(os.path.join(OUT, "table3_land_assumption_robustness.csv"), index=False)
print(df3.to_string(index=False))
print()

# ---------------------------------------------------------------------------------
# TABLE 4 -- what does the budget figure represent? Partial
# government financing scenarios (government covers only a share of input cost;
# producer/cooperative covers the rest). Central scenario, beta=0.5, full adoption.
# ---------------------------------------------------------------------------------
rows = []
res_full = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=0.5)
full_package_cost = res_full["total_cost_fcfa"]
for gov_share in [1.00, 0.75, 0.50, 0.25]:
    rows.append({
        "government_financed_share_pct": gov_share * 100,
        "full_input_package_value_bn_fcfa": fmt_bn(full_package_cost),
        "government_financed_amount_bn_fcfa": fmt_bn(full_package_cost * gov_share),
        "producer_cooperative_copayment_bn_fcfa": fmt_bn(full_package_cost * (1 - gov_share)),
        "note": "one-time estimate for a single allocation reaching 80pct maize / 90pct rice targets; "
                "NOT an annual recurring figure -- see manuscript Section 5.3 for the annualization discussion.",
    })
df4 = pd.DataFrame(rows)
df4.to_csv(os.path.join(OUT, "table4_budget_definition_partial_financing.csv"), index=False)
print(df4.to_string(index=False))
print()

# ---------------------------------------------------------------------------------
# TABLE 5 -- dual-value (shadow price) robustness check. Report the
# marginal cost ratio maize/rice across several scenarios, not just the single central one.
# ---------------------------------------------------------------------------------
rows = []
for label, fm, fr, beta in [
    ("Central (80/90, beta=0.5)", 0.80, 0.90, 0.5),
    ("Official targets (100/100, beta=0.5)", 1.00, 1.00, 0.5),
    ("Looser land (80/90, beta=0.75)", 0.80, 0.90, 0.75),
    ("Tighter land (80/90, beta=0.25)", 0.80, 0.90, 0.25),
]:
    res = solve_goal_program(fm * SND30_TARGET_m, fr * SND30_TARGET_r, beta=beta)
    dm = res.get("dual_goal_m")
    dr = res.get("dual_goal_r")
    ratio = (dm / dr) if (dm and dr and dr != 0) else None
    rows.append({
        "scenario": label,
        "shortfall_m_t": round(res["shortfall_m_t"]),
        "shortfall_r_t": round(res["shortfall_r_t"]),
        "marginal_cost_maize_fcfa_per_t": round(dm) if dm else None,
        "marginal_cost_rice_fcfa_per_t": round(dr) if dr else None,
        "ratio_maize_over_rice": round(ratio, 2) if ratio else "n/a (binding shortfall, not a clean marginal)",
    })
df5 = pd.DataFrame(rows)
df5.to_csv(os.path.join(OUT, "table5_dual_value_robustness.csv"), index=False)
print(df5.to_string(index=False))
print()

# ---------------------------------------------------------------------------------
# TABLE 6 -- Central allocation detail + regional land dual values (replaces the
# manuscript's Table "allocation_bicrop" and "duales_bicrop", under the
# genuine-GP formulation).
# ---------------------------------------------------------------------------------
res_central = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, beta=0.5)
alloc_rows = []
for r in REGIONS:
    alloc_rows.append({
        "region": r,
        "x_m_ha": round(res_central["x_m"][r]),
        "e_m_ha": round(res_central["e_m"][r]),
        "x_r_ha": round(res_central["x_r"][r]),
        "e_r_ha": round(res_central["e_r"][r]),
        "land_dual_fcfa_per_ha": round(res_central["dual_land"][r]),
        "current_maize_area_S_m_ha": S_m[r],
        "current_rice_area_S_r_ha": round(S_r[r]),
        "rice_area_source": "reconstructed from manuscript optimum" if r in {"Far North", "North", "Northwest"}
                             else "RECONSTRUCTED (see module docstring, not an AGRISTAT figure)",
    })
df6 = pd.DataFrame(alloc_rows)
df6.to_csv(os.path.join(OUT, "table6_central_allocation_and_duals.csv"), index=False)
print(df6.to_string(index=False))
print()
print(f"CENTRAL SCENARIO TOTAL BUDGET: {fmt_bn(res_central['total_cost_fcfa'])} Bn FCFA")

# ---------------------------------------------------------------------------------
# TABLE 7 -- Table 2 reproducibility: full rice cost line-item buildup
# ---------------------------------------------------------------------------------
rows = []
for system, items in RICE_COST_LINE_ITEMS.items():
    total = sum(items.values())
    row = {"system": system, **items, "total_fcfa_per_ha": total}
    rows.append(row)
df7 = pd.DataFrame(rows)
df7.to_csv(os.path.join(OUT, "table7_rice_cost_buildup.csv"), index=False)
print(df7.to_string(index=False))

# ---------------------------------------------------------------------------------
# TABLE 8 -- Off-season (contre-saison) rice as an OPTIONAL extension, never baseline.
# Compared with the baseline at identical targets; low-beta regime where land binds.
# ---------------------------------------------------------------------------------
rows = []
for label, fm, fr, beta in [
    ("80% maize / 90% rice", 0.80, 0.90, 0.50),
    ("80% maize / 100% rice", 0.80, 1.00, 0.50),
    ("80% maize / 100% rice", 0.80, 1.00, 0.40),
    ("80% maize / 100% rice", 0.80, 1.00, 0.35),
    ("80% maize / 100% rice", 0.80, 1.00, 0.30),
    ("100% maize / 100% rice (official)", 1.00, 1.00, 0.50),
    ("100% maize / 100% rice (official)", 1.00, 1.00, 1.00),
]:
    Tm, Tr = fm * SND30_TARGET_m, fr * SND30_TARGET_r
    a = solve_goal_program(Tm, Tr, beta)
    b = solve_goal_program(Tm, Tr, beta, offseason=True)
    rows.append({
        "scenario": label, "beta": beta,
        "baseline_budget_bn": fmt_bn(a["total_cost_fcfa"]),
        "baseline_shortfall_m_t": round(a["shortfall_m_t"]),
        "baseline_shortfall_r_t": round(a["shortfall_r_t"]),
        "offseason_budget_bn": fmt_bn(b["total_cost_fcfa"]),
        "offseason_shortfall_m_t": round(b["shortfall_m_t"]),
        "offseason_shortfall_r_t": round(b["shortfall_r_t"]),
        "offseason_area_far_north_ha": round(b["cs"]["Far North"]),
        "offseason_area_north_ha": round(b["cs"]["North"]),
    })
df8 = pd.DataFrame(rows)
df8.to_csv(os.path.join(OUT, "table8_offseason_rice_extension.csv"), index=False)
print(df8.to_string(index=False))
