"""Regenerates every result table of the manuscript into ../results/.  Run: python3 run_scenarios.py"""
import os, time
import numpy as np, pandas as pd
from scipy.stats import qmc, spearmanr
import goal_programming_model as g
import data_analysis

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results"); os.makedirs(OUT, exist_ok=True)
bn = lambda v: round(v / 1e9, 2)
T_M, T_R = g.DEFAULTS["T_m"], g.DEFAULTS["T_r"]
tm = lambda f: f * g.SND30_m
tr = lambda f: f * g.SND30_r


def save(df, name):
    df.to_csv(os.path.join(OUT, name), index=False); print("\n==", name); print(df.to_string(index=False))


def clean(x, tol=1.0):
    return 0 if abs(x) < tol else round(x)


central = g.solve()
B_REF = central["total_cost_fcfa"]                       # budget that exactly attains the central targets
print("central budget (Bn FCFA):", bn(B_REF))

# ---- t01 target scenarios --------------------------------------------------------------------
rows = []
for lab, fm, fr in [("80/90 (central)", .8, .9), ("80/100", .8, 1.), ("90/90", .9, .9), ("90/100", .9, 1.), ("100/100 (official)", 1., 1.)]:
    r = g.solve(T_m=tm(fm), T_r=tr(fr))
    rows.append({"targets_maize/rice_pct": lab, "budget_bn": bn(r["total_cost_fcfa"]),
                 "shortfall_maize_t": clean(r["shortfall_m_t"]), "shortfall_rice_t": clean(r["shortfall_r_t"]),
                 "maize_pct_of_official": round(r["pct_official_m"], 1), "rice_pct_of_official": round(r["pct_official_r"], 1)})
save(pd.DataFrame(rows), "t01_target_scenario_matrix.csv")

# ---- t02 budget frontier (budget ceiling, official targets) ------------------------------------
rows = []
for B in list(range(100, 521, 20)) + [round(B_REF / 1e9, 2)]:
    r = g.solve(T_m=tm(1), T_r=tr(1), budget=B * 1e9)
    rows.append({"budget_bn": B, "maize_t": round(r["production_m_t"]), "rice_t": round(r["production_r_t"]),
                 "maize_pct_official": round(r["pct_official_m"], 1), "rice_pct_official": round(r["pct_official_r"], 1),
                 "cost_used_bn": bn(r["total_cost_fcfa"])})
frontier = pd.DataFrame(rows).sort_values("budget_bn")
save(frontier, "t02_budget_frontier.csv")

# ---- t03 adoption at a fixed budget ------------------------------------------------------------
rows = []
for tau in [1.0, 0.8, 0.6, 0.4, 0.2]:
    cap = g.solve(tau=tau, budget=B_REF)
    free = g.solve(tau=tau)
    rows.append({"adoption": tau, "attained_at_budget_B_maize_pct_of_target": round(cap["pct_target_m"], 1),
                 "attained_at_budget_B_rice_pct_of_target": round(cap["pct_target_r"], 1),
                 "budget_to_attain_both_bn": bn(free["total_cost_fcfa"]) if free["shortfall_m_t"] < 1 and free["shortfall_r_t"] < 1 else None,
                 "maize_pct_of_target_with_unlimited_budget": round(free["pct_target_m"], 1),
                 "unavoidable_shortfall_maize_t": clean(free["shortfall_m_t"]),
                 "unavoidable_shortfall_rice_t": clean(free["shortfall_r_t"]),
                 "budget_B_bn": bn(B_REF)})
save(pd.DataFrame(rows), "t03_adoption_fixed_budget.csv")

# ---- t04 land sharing and extension-cost premium ----------------------------------------------
rows = []
for beta in [0.25, 0.5, 0.75, 1.0]:
    row = {"beta": beta}
    for mode in ("shared", "separate"):
        for kap in (0.0, 0.3):
            r = g.solve(beta=beta, land_mode=mode, kappa=kap)
            row[f"{mode}_kappa{kap}_budget_bn"] = bn(r["total_cost_fcfa"])
            row[f"{mode}_kappa{kap}_shortfall_maize_t"] = clean(r["shortfall_m_t"])
    rows.append(row)
save(pd.DataFrame(rows), "t04_land_and_extension_cost.csv")
rows = [{"kappa": k, "budget_bn": bn(g.solve(kappa=k)["total_cost_fcfa"])} for k in (0, .15, .3, .5, .75, 1.0)]
save(pd.DataFrame(rows), "t04b_kappa_sweep.csv")

# ---- t05 partial financing ---------------------------------------------------------------------
rows = [{"government_share": s, "government_bn": bn(B_REF * s), "private_or_partner_bn": bn(B_REF * (1 - s))}
        for s in (0.25, 0.5, 0.75, 1.0)]
save(pd.DataFrame(rows), "t05_partial_financing.csv")

# ---- t06 dual values ---------------------------------------------------------------------------
rows = []
for lab, kw in [("central 80/90, beta 0.5", {}), ("official 100/100, beta 0.5", dict(T_m=tm(1), T_r=tr(1))),
                ("beta 0.75", dict(beta=.75)), ("beta 0.25", dict(beta=.25)), ("kappa 0", dict(kappa=0)),
                ("separate land", dict(land_mode="separate"))]:
    r = g.solve(**kw)
    dm, dr = abs(r["dual_goal_m"]), abs(r["dual_goal_r"])
    att = r["shortfall_m_t"] < 1 and r["shortfall_r_t"] < 1      # duals are meaningful only if targets are attained
    rows.append({"scenario": lab, "targets_attained": att,
                 "marginal_cost_maize_fcfa_per_t": round(dm) if att else None,
                 "marginal_cost_rice_fcfa_per_t": round(dr) if att else None,
                 "ratio_maize_over_rice": round(dm / dr, 2) if att and dr > 1 else None})
save(pd.DataFrame(rows), "t06_dual_values.csv")

# ---- t07 central allocation ----------------------------------------------------------------------
rows = []
for reg in g.REGIONS:
    rows.append({"region": reg, "S_maize_ha": g.S_m[reg], "S_rice_rainfed_ha_RECONSTRUCTED": round(central["S_rf"][reg]),
                 "S_rice_irrigated_ha_documented": g.S_ir[reg],
                 "x_maize": round(central["x_m"][reg]), "e_maize": round(central["e_m"][reg]),
                 "x_rice_rainfed": round(central["x_rf"][reg]), "e_rice_rainfed": round(central["e_rf"][reg]),
                 "x_rice_irrigated": round(central["x_ir"][reg]), "e_rice_irrigated": round(central["e_ir"][reg]),
                 "land_dual_fcfa_per_ha": round(central["dual_land"][reg])})
save(pd.DataFrame(rows), "t07_central_allocation.csv")

# ---- t08 base / gains / target ---------------------------------------------------------------
rows = []
upd = g.solve(base_shift_m=g.SHIFT_2024_m, base_shift_r=g.SHIFT_2024_r)
for lab, r, shm, shr in [("2020 base (central)", central, 0, 0), ("base updated to 2024", upd, g.SHIFT_2024_m, g.SHIFT_2024_r)]:
    rows.append({"calibration": lab, "maize_base_t": round(r["base_m"] + shm), "maize_gain_t": round(r["gain_m_t"]),
                 "maize_target_t": round(T_M), "rice_base_t": round(r["base_r"] + shr), "rice_gain_t": round(r["gain_r_t"]),
                 "rice_target_t": round(T_R), "budget_bn": bn(r["total_cost_fcfa"])})
save(pd.DataFrame(rows), "t08_base_gains_target.csv")

# ---- t09 regional beta -------------------------------------------------------------------------
ob = data_analysis.observed_beta(data_analysis.load_panel())
b_obs = {r: float(np.clip(ob[r2], 0.05, 1.0)) for r, r2 in zip(g.REGIONS, [{"Adamawa": "Adamawa"}.get(x, x) for x in g.REGIONS])}
scen = {"uniform 0.50 (central)": 0.5, "observed 6-year expansion (floor 0.05, cap 1.0)": b_obs,
        "2 x observed (cap 1.0)": {r: min(2 * v, 1.0) for r, v in b_obs.items()},
        "observed, forest regions at least 0.5": {r: (max(v, .5) if r in ("Centre", "East", "South", "Southwest", "Littoral") else v) for r, v in b_obs.items()}}
rows = []
for lab, b in scen.items():
    r = g.solve(beta=b)
    rows.append({"beta_scenario": lab, "budget_bn": bn(r["total_cost_fcfa"]), "shortfall_maize_t": clean(r["shortfall_m_t"]),
                 "shortfall_rice_t": clean(r["shortfall_r_t"]), "maize_pct_of_target": round(r["pct_target_m"], 1)})
save(pd.DataFrame(rows), "t09_regional_beta.csv")
save(pd.DataFrame({"region": g.REGIONS, "beta_observed": [round(b_obs[r], 3) for r in g.REGIONS]}), "t09b_beta_observed_by_region.csv")

# ---- t10 joint sensitivity (Monte-Carlo, scrambled Sobol) -------------------------------------------
N_DRAWS = 512
names = ["beta", "tau", "phi_add", "kappa", "ceil_factor", "rho"]
lo = np.array([.25, .5, .7, 0.0, .85, .8]); hi = np.array([1.0, 1.0, 1.0, .6, 1.0, 1.0])
U = qmc.Sobol(d=len(names), scramble=True, seed=2026).random(N_DRAWS)
D = lo + U * (hi - lo)
recs = []
for row in D:
    kw = dict(zip(names, row))
    free = g.solve(**kw); cap = g.solve(budget=B_REF, **kw)
    recs.append({**{k: round(v, 4) for k, v in kw.items()},
                 "budget_needed_bn": bn(free["total_cost_fcfa"]),
                 "shortfall_maize_t_free": clean(free["shortfall_m_t"]), "shortfall_rice_t_free": clean(free["shortfall_r_t"]),
                 "maize_pct_at_B": round(cap["pct_target_m"], 2), "rice_pct_at_B": round(cap["pct_target_r"], 2)})
draws = pd.DataFrame(recs)
draws.to_csv(os.path.join(OUT, "t10b_joint_sensitivity_draws.csv"), index=False)
ok = (draws.shortfall_maize_t_free == 0) & (draws.shortfall_rice_t_free == 0)
both_at_B = (draws.maize_pct_at_B >= 99.9) & (draws.rice_pct_at_B >= 99.9)
q = lambda s: [round(float(s.quantile(p)), 1) for p in (.05, .25, .5, .75, .95)]
summary = [
    ("share of draws where both central targets are attainable at all (any budget)", round(ok.mean(), 3)),
    ("share of draws where both targets are met at the central budget B", round(both_at_B.mean(), 3)),
    ("budget needed (bn), quantiles 5/25/50/75/95, draws where attainable", q(draws.budget_needed_bn[ok])),
    ("maize % of target attained at B, quantiles 5/25/50/75/95", q(draws.maize_pct_at_B)),
    ("rice % of target attained at B, quantiles 5/25/50/75/95", q(draws.rice_pct_at_B)),
    ("central budget B (bn)", bn(B_REF)), ("draws", N_DRAWS),
]
for p in names:
    summary.append((f"Spearman rank corr. of {p} with maize % attained at B", round(spearmanr(draws[p], draws.maize_pct_at_B)[0], 2)))
save(pd.DataFrame(summary, columns=["statistic", "value"]), "t10_joint_sensitivity_summary.csv")

# ---- t11 crowding-out (additionality of subsidised intensification) -----------------------------
rows = []
for phi in (1.0, 0.9, 0.8, 0.7):
    r = g.solve(phi_add=phi); c = g.solve(phi_add=phi, budget=B_REF)
    rows.append({"additionality_phi": phi, "budget_to_attain_bn": bn(r["total_cost_fcfa"]), "shortfall_maize_t": clean(r["shortfall_m_t"]),
                 "maize_pct_at_B": round(c["pct_target_m"], 1), "rice_pct_at_B": round(c["pct_target_r"], 1)})
save(pd.DataFrame(rows), "t11_crowding_out.csv")

# ---- t12 rice-system sensitivity ------------------------------------------------------------------
doc_shift = -(g.P0_RICE_2020 - (sum(g.S_ir.values()) * 4.0 + 30_000 * 1.5))   # documented-area rice base
rows = []
for lab, kw in [("irrigated extension: none", dict(irr_ext="none")),
                ("irrigated extension: developed-but-unexploited (central)", dict(irr_ext="unexploited")),
                ("irrigated extension: full documented potential (capital NOT included)", dict(irr_ext="potential")),
                ("irrigated baseline yield 3.0 t/ha", dict(y0_irr=3.0)), ("irrigated baseline yield 4.0 t/ha (central)", dict(y0_irr=4.0)),
                ("irrigated baseline yield 5.0 t/ha", dict(y0_irr=5.0)),
                ("rice base from documented areas only (~100 kt)", dict(base_shift_r=doc_shift)),
                ("all ceiling yields -15% (maize and rice)", dict(ceil_factor=.85))]:
    r = g.solve(**kw)
    rows.append({"variant": lab, "budget_bn": bn(r["total_cost_fcfa"]), "shortfall_maize_t": clean(r["shortfall_m_t"]),
                 "shortfall_rice_t": clean(r["shortfall_r_t"]),
                 "irrigated_extension_ha": round(sum(r["e_ir"].values())), "rainfed_extension_ha": round(sum(r["e_rf"].values()))})
save(pd.DataFrame(rows), "t12_rice_system_sensitivity.csv")

# ---- t13 weighting: tonnes vs share-of-target ------------------------------------------------------
rows = []
for lab, kw in [("beta 0.25, 80/90", dict(beta=.25)), ("official 100/100, beta 0.5", dict(T_m=tm(1), T_r=tr(1))),
                ("adoption 0.4", dict(tau=.4)),
                ("severe stress: ceilings -50%, adoption 0.5", dict(ceil_factor=.5, tau=.5))]:
    for norm in (False, True):
        r = g.solve(normalize=norm, **kw)
        rows.append({"scenario": lab, "weights": "share of target (1/T)" if norm else "tonnes (1 per t)",
                     "shortfall_maize_t": clean(r["shortfall_m_t"]), "shortfall_rice_t": clean(r["shortfall_r_t"]),
                     "maize_pct_of_target": round(r["pct_target_m"], 1), "rice_pct_of_target": round(r["pct_target_r"], 1),
                     "budget_bn": bn(r["total_cost_fcfa"])})
save(pd.DataFrame(rows), "t13_weighting_comparison.csv")

# ---- t14 off-season rice (optional extension, never baseline) ----------------------------------------
rows = []
for lab, fm, fr, beta in [("80/90", .8, .9, .5), ("80/100", .8, 1., .5), ("80/100", .8, 1., .35), ("100/100 (official)", 1., 1., .5), ("100/100 (official)", 1., 1., .75), ("100/100 (official)", 1., 1., 1.0)]:
    a = g.solve(T_m=tm(fm), T_r=tr(fr), beta=beta); b = g.solve(T_m=tm(fm), T_r=tr(fr), beta=beta, offseason=True)
    rows.append({"targets": lab, "beta": beta, "baseline_budget_bn": bn(a["total_cost_fcfa"]), "baseline_shortfall_maize_t": clean(a["shortfall_m_t"]),
                 "baseline_shortfall_rice_t": clean(a["shortfall_r_t"]), "offseason_budget_bn": bn(b["total_cost_fcfa"]),
                 "offseason_shortfall_maize_t": clean(b["shortfall_m_t"]), "offseason_shortfall_rice_t": clean(b["shortfall_r_t"]),
                 "offseason_area_ha": round(sum(b["cs"].values()))})
save(pd.DataFrame(rows), "t14_offseason_rice_extension.csv")

# ---- t15 rice cost build-up ----------------------------------------------------------------------------
pd.DataFrame([{"system": "rainfed", "seed": 107143, "npk": 60000, "urea": 28000, "herbicide_nursery": 0, "total_fcfa_per_ha": 195143},
              {"system": "irrigated", "seed": 12500, "npk": 68000, "urea": 36000, "herbicide_nursery": 19000, "total_fcfa_per_ha": 135500}]
             ).to_csv(os.path.join(OUT, "t15_rice_cost_buildup.csv"), index=False)

# ---- t18 uniform vs zone-differentiated maize ceiling ----------------------------------------------------
saved = dict(g.Y1_m)
rows = [{"maize_ceiling": "zone-differentiated 3.5-4.5 t/ha (central)", "budget_bn": bn(central["total_cost_fcfa"])}]
for lab, v in [("uniform 4.0 t/ha", 4.0), ("uniform 3.5 t/ha", 3.5)]:
    g.Y1_m.update({k: v for k in g.Y1_m}); r = g.solve()
    rows.append({"maize_ceiling": lab, "budget_bn": bn(r["total_cost_fcfa"]), "shortfall_maize_t": clean(r["shortfall_m_t"])})
g.Y1_m.update(saved)
save(pd.DataFrame(rows), "t18_maize_ceiling_uniform_vs_zones.csv")

# ---- t16, t17 data exploitation ---------------------------------------------------------------------------
data_analysis.main()
print("\nDone.")
