"""
Joint maize / rice input-subsidy allocation in Cameroon -- lexicographic goal program.

BWO'NYAHRE BAIDI B., KOUAKEP TCHAPTCHIE Y. -- Discover Applied Mathematics.

MODEL
-----
Regions i = 1..10; systems s in {maize (m), rainfed rice (rf), irrigated rice (ir)}.
Decision variables per region and system: x_is (intensified hectares, already cultivated)
and e_is (extension hectares, newly cultivated), plus the production-goal deviation variables
d_m^-, d_m^+, d_r^-, d_r^+ >= 0.

Goals (equalities):  sum_i P_i,m + d_m^- - d_m^+ = T_m ;  sum_i (P_i,rf + P_i,ir) + d_r^- - d_r^+ = T_r
with   P_is = y0*S + tau*phi*(y1-y0)*x + tau*rho*y1*e .

Stage 1 (priority 1): minimise the shortfalls expressed as a *share of each target*
                      (weights 1/T_m and 1/T_r, scaled by 10^6 for numerical conditioning), optionally under a budget ceiling B.
Stage 2 (priority 2): minimise cost subject to the optimal Stage-1 shortfall.
Extension hectares cost (1+kappa) times the intensification package (clearing / set-up).

Everything is solved with scipy.optimize.linprog (HiGHS).  All inputs are in this file with
their source; confidence flags are listed in ../data/parameters_documented.csv.
"""
import json
import numpy as np
from scipy.optimize import linprog

REGIONS = ["Adamawa", "Centre", "East", "Far North", "Littoral",
           "North", "Northwest", "West", "South", "Southwest"]
N = len(REGIONS)

# ----------------------------------------------------------------------------- maize
S_m = {"Adamawa": 67037, "Centre": 129938, "East": 87144, "Far North": 155002,
       "Littoral": 88900, "North": 211286, "Northwest": 56453, "West": 279217,
       "South": 53473, "Southwest": 41492}                     # ha, AGRISTAT 2020
Y0_m = {"Adamawa": 2.29, "Centre": 1.77, "East": 1.11, "Far North": 2.06,
        "Littoral": 2.37, "North": 2.08, "Northwest": 1.50, "West": 1.40,
        "South": 1.89, "Southwest": 1.50}                      # t/ha, AGRISTAT 2020
Y1_m = {"West": 4.5, "Northwest": 4.5, "Centre": 4.0, "East": 4.0, "South": 4.0,
        "Adamawa": 4.0, "Littoral": 3.5, "Southwest": 3.5, "North": 3.5, "Far North": 3.5}
COST_m = 224_250                                               # FCFA/ha

# ----------------------------------------------------------------------------- rice
Y0_r = {"Far North": 3.02, "North": 2.46, "Northwest": 1.31, "Adamawa": 2.24, "Centre": 1.11,
        "East": 1.09, "Littoral": 1.01, "West": 1.35, "South": 1.31, "Southwest": 1.19}
Y1_rf, Y1_ir = 3.75, 6.5                                       # JICA/MINADER 2021 sensitivity cases
COST_rf, COST_ir = 195_143, 135_500                            # FCFA/ha, JICA/MINADER 2021

# Irrigated schemes: areas actually exploited (documented). SEMRY: 12,500 ha cultivated (2023,
# press); UNVDA: 1,530 ha exploited; Lagdo: 600 ha (sector profile citing MINADER, ITPO/UNIDO 2021).
S_ir = {r: 0.0 for r in REGIONS}
S_ir.update({"Far North": 12_500, "North": 600, "Northwest": 1_530})
# Irrigated extension, two documented ceilings (ha):
#   "unexploited": developed but unused perimeters (SEMRY 13,000 developed - 12,500 cultivated;
#                  UNVDA 3,300 - 1,530; Lagdo 0)  -> needs inputs only
#   "potential":   documented extension potential incl. NEW development (SEMRY 8,500, UNVDA 10,700,
#                  Lagdo 9,400) -> would also need public capital (NOT included in the budget)
IR_CAP = {"none": {r: 0.0 for r in REGIONS},
          "unexploited": {**{r: 0.0 for r in REGIONS}, "Far North": 500, "Northwest": 1_770, "North": 0},
          "potential": {**{r: 0.0 for r in REGIONS}, "Far North": 8_500, "Northwest": 10_700, "North": 9_400}}

# Rainfed rice: national 2020 base (reconstructed) minus irrigated production, spread over the
# 7 rainfed regions in proportion to maize area (structural proxy). FLAGGED as reconstructed.
NATIONAL_PROD_2026 = 337_000.0
GROWTH_R = 0.0777
P0_RICE_2020 = NATIONAL_PROD_2026 / (1 + GROWTH_R) ** 6        # 215,101 t
IRRIGATED_REGIONS = {"Far North", "North", "Northwest"}
RAINFED_REGIONS = [r for r in REGIONS if r not in IRRIGATED_REGIONS]


def rice_baseline(y0_irr=4.0):
    """Returns S_rf, y0 irrigated (scalar) and the 2020 national base used."""
    p_irr = sum(S_ir[r] * y0_irr for r in REGIONS)
    p_rf = max(P0_RICE_2020 - p_irr, 0.0)
    tot = sum(S_m[r] for r in RAINFED_REGIONS)
    S_rf = {r: 0.0 for r in REGIONS}
    for r in RAINFED_REGIONS:
        S_rf[r] = p_rf * S_m[r] / tot / Y0_r[r]
    return S_rf


OFFSEASON_REGIONS = ["Far North", "North"]
OFFSEASON_YIELD_RATIO, OFFSEASON_COST = 0.65, 135_500

SND30_m, SND30_r = 8_000_000.0, 750_000.0
BASE_2020_m = sum(Y0_m[r] * S_m[r] for r in REGIONS)
# Production already realised by 2024 relative to the 2020 base (used only in the "updated base"
# scenario; 2024 maize: SND30 report series 2,360,129 t; rice: 215,101 * 1.0777^4)
SHIFT_2024_m = 2_360_129.0 - BASE_2020_m
SHIFT_2024_r = P0_RICE_2020 * (1 + GROWTH_R) ** 4 - P0_RICE_2020


# ----------------------------------------------------------------------------- scenario
DEFAULTS = dict(
    T_m=0.80 * SND30_m, T_r=0.90 * SND30_r,
    beta=0.5,            # float, or dict region -> beta
    land_mode="shared",  # "shared" | "separate"
    kappa=0.30,          # extension cost premium
    tau=1.0,             # adoption rate
    phi_add=1.0,         # additionality of intensification (1 = no crowding-out)
    rho=1.0,             # yield of extension land relative to the ceiling yield
    ceil_factor=1.0,     # multiplier on every ceiling yield
    y0_irr=4.0,          # baseline yield of irrigated schemes (assumption)
    irr_ext="unexploited",
    offseason=False,
    base_shift_m=0.0, base_shift_r=0.0,
    normalize=True,      # weights 1/T (share of target) instead of 1 per tonne
    budget=None,         # FCFA ceiling (None = no ceiling)
)


def _beta(beta, r):
    return beta[r] if isinstance(beta, dict) else beta


def _layout():
    idx, k = {}, 0
    for s in ("m", "rf", "ir"):
        for t in ("x", "e"):
            idx[f"{t}_{s}"] = list(range(k, k + N)); k += N
    for d in ("dm_minus", "dm_plus", "dr_minus", "dr_plus"):
        idx[d] = k; k += 1
    idx["cs"] = list(range(k, k + len(OFFSEASON_REGIONS))); k += len(OFFSEASON_REGIONS)
    idx["n"] = k
    return idx


def _model(p):
    idx = _layout(); n = idx["n"]
    S_rf = rice_baseline(p["y0_irr"])
    S = {"m": S_m, "rf": S_rf, "ir": S_ir}
    Y0 = {"m": Y0_m, "rf": Y0_r, "ir": {r: p["y0_irr"] for r in REGIONS}}
    Y1 = {"m": {r: Y1_m[r] * p["ceil_factor"] for r in REGIONS},
          "rf": {r: Y1_rf * p["ceil_factor"] for r in REGIONS},
          "ir": {r: Y1_ir * p["ceil_factor"] for r in REGIONS}}
    COST = {"m": COST_m, "rf": COST_rf, "ir": COST_ir}
    tau, phi, rho, kap = p["tau"], p["phi_add"], p["rho"], p["kappa"]

    gain_x = {s: {r: tau * phi * max(Y1[s][r] - Y0[s][r], 0.0) for r in REGIONS} for s in S}
    gain_e = {s: {r: tau * rho * Y1[s][r] for r in REGIONS} for s in S}

    A_eq, b_eq = [], []
    rm = np.zeros(n); rr = np.zeros(n)
    for j, r in enumerate(REGIONS):
        rm[idx["x_m"][j]] = gain_x["m"][r]; rm[idx["e_m"][j]] = gain_e["m"][r]
        for s in ("rf", "ir"):
            rr[idx[f"x_{s}"][j]] = gain_x[s][r]; rr[idx[f"e_{s}"][j]] = gain_e[s][r]
    rm[idx["dm_minus"]] = 1; rm[idx["dm_plus"]] = -1
    rr[idx["dr_minus"]] = 1; rr[idx["dr_plus"]] = -1
    if p["offseason"]:
        for k, rn in enumerate(OFFSEASON_REGIONS):
            rr[idx["cs"][k]] = tau * OFFSEASON_YIELD_RATIO * Y1["ir"][rn]
    base_m = sum(Y0["m"][r] * S["m"][r] for r in REGIONS)
    base_r = sum(Y0["rf"][r] * S["rf"][r] + Y0["ir"][r] * S["ir"][r] for r in REGIONS)
    A_eq += [rm, rr]
    b_eq += [p["T_m"] - base_m - p["base_shift_m"], p["T_r"] - base_r - p["base_shift_r"]]

    A_ub, b_ub = [], []
    for j, r in enumerate(REGIONS):                              # land rows: first N (or 2N) rows
        b = _beta(p["beta"], r)
        if p["land_mode"] == "shared":
            row = np.zeros(n)
            for s in ("m", "rf", "ir"): row[idx[f"e_{s}"][j]] = 1
            A_ub.append(row); b_ub.append(b * (S["m"][r] + S["rf"][r] + S["ir"][r]))
        else:
            row = np.zeros(n); row[idx["e_m"][j]] = 1
            A_ub.append(row); b_ub.append(b * S["m"][r])
            row = np.zeros(n); row[idx["e_rf"][j]] = 1; row[idx["e_ir"][j]] = 1
            A_ub.append(row); b_ub.append(b * (S["rf"][r] + S["ir"][r]))
    n_land = len(A_ub)
    for k, rn in enumerate(OFFSEASON_REGIONS):                    # off-season area <= irrigated area
        j = REGIONS.index(rn)
        row = np.zeros(n); row[idx["cs"][k]] = 1; row[idx["e_ir"][j]] = -1
        A_ub.append(row); b_ub.append(S["ir"][rn])

    bounds = [None] * n
    cap = IR_CAP[p["irr_ext"]]
    for j, r in enumerate(REGIONS):
        for s in ("m", "rf", "ir"):
            bounds[idx[f"x_{s}"][j]] = (0, S[s][r])
        bounds[idx["e_m"][j]] = (0, None)
        bounds[idx["e_rf"][j]] = (0, None)
        bounds[idx["e_ir"][j]] = (0, cap[r])
    for d in ("dm_minus", "dm_plus", "dr_minus", "dr_plus"):
        bounds[idx[d]] = (0, None)
    for k in range(len(OFFSEASON_REGIONS)):
        bounds[idx["cs"][k]] = (0, None) if p["offseason"] else (0, 0)

    cost = np.zeros(n)
    for j, r in enumerate(REGIONS):
        for s in ("m", "rf", "ir"):
            cost[idx[f"x_{s}"][j]] = COST[s]
            cost[idx[f"e_{s}"][j]] = COST[s] * (1 + kap)
    for k in range(len(OFFSEASON_REGIONS)):
        cost[idx["cs"][k]] = OFFSEASON_COST

    w = np.zeros(n)
    wm, wr = (1e6 / p["T_m"], 1e6 / p["T_r"]) if p["normalize"] else (1.0, 1.0)  # x1e6: keeps costs above the LP dual tolerance
    w[idx["dm_minus"]] = wm; w[idx["dr_minus"]] = wr
    return dict(idx=idx, n=n, S=S, Y0=Y0, Y1=Y1, A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                A_ub=np.array(A_ub), b_ub=np.array(b_ub), bounds=bounds, cost=cost, w=w,
                n_land=n_land, base_m=base_m, base_r=base_r, gain_x=gain_x, gain_e=gain_e)


def solve(**kw):
    """Two-stage lexicographic goal program. Keyword arguments override DEFAULTS."""
    p = {**DEFAULTS, **kw}
    M = _model(p); idx = M["idx"]
    A_ub, b_ub = M["A_ub"], M["b_ub"]
    if p["budget"] is not None:
        A_ub = np.vstack([A_ub, M["cost"]]); b_ub = np.append(b_ub, p["budget"])
    r1 = linprog(M["w"], A_ub=A_ub, b_ub=b_ub, A_eq=M["A_eq"], b_eq=M["b_eq"],
                 bounds=M["bounds"], method="highs")
    if not r1.success:
        return {"success": False, "message": r1.message}
    A2 = np.vstack([A_ub, M["w"]]); b2 = np.append(b_ub, r1.fun + 1e-6 + 1e-9 * abs(r1.fun))
    r2 = linprog(M["cost"], A_ub=A2, b_ub=b2, A_eq=M["A_eq"], b_eq=M["b_eq"],
                 bounds=M["bounds"], method="highs")
    if not r2.success:
        return {"success": False, "message": r2.message}
    z = r2.x
    g = lambda key: dict(zip(REGIONS, z[idx[key]]))
    out = {"success": True, "params": p, "total_cost_fcfa": r2.fun, "stage1_shortfall": r1.fun,
           "shortfall_m_t": z[idx["dm_minus"]], "shortfall_r_t": z[idx["dr_minus"]],
           "overshoot_m_t": z[idx["dm_plus"]], "overshoot_r_t": z[idx["dr_plus"]]}
    for s in ("m", "rf", "ir"):
        out[f"x_{s}"] = g(f"x_{s}"); out[f"e_{s}"] = g(f"e_{s}")
    out["cs"] = dict(zip(OFFSEASON_REGIONS, z[idx["cs"]]))
    out["production_m_t"] = p["T_m"] - z[idx["dm_minus"]] + z[idx["dm_plus"]]
    out["production_r_t"] = p["T_r"] - z[idx["dr_minus"]] + z[idx["dr_plus"]]
    out["pct_target_m"] = 100 * out["production_m_t"] / p["T_m"]
    out["pct_target_r"] = 100 * out["production_r_t"] / p["T_r"]
    out["pct_official_m"] = 100 * out["production_m_t"] / SND30_m
    out["pct_official_r"] = 100 * out["production_r_t"] / SND30_r
    out["S_rf"] = M["S"]["rf"]; out["base_m"] = M["base_m"]; out["base_r"] = M["base_r"]
    out["gain_m_t"] = float(sum(M["gain_x"]["m"][r] * out["x_m"][r] + M["gain_e"]["m"][r] * out["e_m"][r] for r in REGIONS))
    out["gain_r_t"] = float(sum(M["gain_x"][s][r] * out[f"x_{s}"][r] + M["gain_e"][s][r] * out[f"e_{s}"][r]
                                for s in ("rf", "ir") for r in REGIONS)
                            + sum(p["tau"] * OFFSEASON_YIELD_RATIO * M["Y1"]["ir"][rn] * out["cs"][rn] for rn in OFFSEASON_REGIONS))
    if r2.ineqlin is not None:
        marg = -r2.ineqlin.marginals
        if p["land_mode"] == "shared":
            out["dual_land"] = dict(zip(REGIONS, marg[:N]))
    if r2.eqlin is not None:
        out["dual_goal_m"], out["dual_goal_r"] = -r2.eqlin.marginals[0], -r2.eqlin.marginals[1]
    return out


def min_budget_bn(**kw):
    r = solve(**kw)
    return (r["total_cost_fcfa"] / 1e9, r["shortfall_m_t"], r["shortfall_r_t"]) if r["success"] else (None, None, None)


if __name__ == "__main__":
    r = solve()
    print("Central scenario (80% maize / 90% rice, beta=0.5, kappa=0.30, full adoption)")
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                      if k in ("total_cost_fcfa", "shortfall_m_t", "shortfall_r_t", "production_m_t",
                               "production_r_t", "dual_goal_m", "dual_goal_r")}, indent=1))
