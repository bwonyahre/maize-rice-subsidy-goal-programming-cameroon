# -*- coding: utf-8 -*-
"""
Genuine goal-programming model for joint maize/rice subsidy allocation - Cameroon / SND30
============================================================================================

Reproducibility code for the major revision of:
"Joint Optimization of Regional Allocation of Seed and Agricultural Input Subsidies
for Maize and Rice in Cameroon: A Goal-Programming Approach in Support of the SND30"
BWO'NYAHRE BAIDI B., KOUAKEP TCHAPTCHIE Y. -- submitted to Discover Applied Mathematics.

WHAT CHANGED RELATIVE TO THE ORIGINAL SUBMISSION (reviewer point 1)
---------------------------------------------------------------------
The original submission solved a minimum-cost LP under hard "target >= T" constraints
and *labeled* it a goal program. This script implements a GENUINE goal program:
production targets and the budget ceiling are formulated as GOALS fitted with explicit
non-negative deviation variables (shortfall d-, overshoot d+), and the program is solved
as a two-stage LEXICOGRAPHIC goal program:

    Stage 1 (Priority 1 -- social objective): minimize the weighted shortfall on the two
             production targets,  w_m * d_m^- + w_r * d_r^-
    Stage 2 (Priority 2 -- fiscal objective): among all solutions that attain the Stage-1
             optimal (minimal) shortfall, minimize total subsidy cost (equivalently,
             minimize budget overshoot d_B^+ against an aspiration budget).

This has a concrete advantage over the hard-constraint LP used in the original
submission: when land is too tight to reach both targets (e.g. beta <= 0.25), the
hard-constraint LP simply reports "infeasible" with no further information. The genuine
GP instead reports *exactly how far short* each crop falls -- directly useful for
reviewer points 3, 4 and 5 (scenario analysis, conditional framing, land assumptions).

DATA PROVENANCE
----------------
All parameters are listed in data/parameters_documented.csv with an explicit SOURCE
and CONFIDENCE field. Two blocks of parameters have different evidentiary status:
  - Maize yields/costs/areas and rice yields/costs for the 3 irrigated regions: taken
    verbatim from the submitted manuscript's own tables (Tables 1, 2, 4, 5), which in
    turn cite AGRISTAT 2022, INS regional yearbooks and the JICA/MINADER (2021)
    rice competitiveness study.
  - Current rice area (S_i,r) for the 7 RAINFED regions: RECONSTRUCTED (not an
    AGRISTAT figure). The original project's consolidated rice workbook was not
    preserved. These 7 values are obtained by (a) back-calculating a 2020 national
    baseline rice production figure from the manuscript's own August-2026 estimate
    (~337,000 t) and its documented 2020-2024 growth rate (+7.77%/yr), (b) subtracting
    the production already accounted for by the three irrigated regions (reconstructed
    from the manuscript's own optimal solution, see below), and (c) allocating the
    rainfed remainder across the 7 rainfed regions in proportion to each region's
    current MAIZE area (S_i,m) as a structural proxy for general cropping intensity.
    This is a coarse, explicitly flagged estimate, NOT a disaggregated AGRISTAT figure;
    it is used only to populate scenarios that were not already pinned down by the
    original submission's own published numbers. See Section 4.4 and Limitation L1 in
    the revised manuscript.

Dependencies: numpy, scipy, pandas (pip install numpy scipy pandas --break-system-packages)
"""

import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

# ---------------------------------------------------------------------------------
# 1. REGIONS AND PARAMETERS
# ---------------------------------------------------------------------------------

REGIONS = ["Adamawa", "Centre", "East", "Far North", "Littoral",
           "North", "Northwest", "West", "South", "Southwest"]

IRRIGATED = {"Far North", "North", "Northwest"}
RAINFED = [r for r in REGIONS if r not in IRRIGATED]

# --- Maize parameters (verbatim from submitted manuscript Tables 1-2; AGRISTAT 2022) ---
S_m = {  # current maize area, ha (AGRISTAT 2020)
    "Adamawa": 67037, "Centre": 129938, "East": 87144, "Far North": 155002,
    "Littoral": 88900, "North": 211286, "Northwest": 56453, "West": 279217,
    "South": 53473, "Southwest": 41492,
}
Y0_m = {  # baseline yield, t/ha (AGRISTAT 2020)
    "Adamawa": 2.29, "Centre": 1.77, "East": 1.11, "Far North": 2.06,
    "Littoral": 2.37, "North": 2.08, "Northwest": 1.50, "West": 1.40,
    "South": 1.89, "Southwest": 1.50,
}
Y1_m = {  # ceiling yield, t/ha, differentiated by IRAD agroecological zone
    "West": 4.5, "Northwest": 4.5,
    "Centre": 4.0, "East": 4.0, "South": 4.0, "Adamawa": 4.0,
    "Littoral": 3.5, "Southwest": 3.5, "North": 3.5, "Far North": 3.5,
}
COST_m = 224_250  # FCFA/ha, subsidized package (composite seed + NPK/urea)

# --- Rice parameters (verbatim: JICA/MINADER 2021 Rice Task Force competitiveness study) ---
Y0_r = {  # baseline yield, t/ha (AGRISTAT)
    "Far North": 3.02, "North": 2.46, "Northwest": 1.31,
    "Adamawa": 2.24, "Centre": 1.11, "East": 1.09, "Littoral": 1.01,
    "West": 1.35, "South": 1.31, "Southwest": 1.19,
}
Y1_r = {r: (6.5 if r in IRRIGATED else 3.75) for r in REGIONS}
COST_r = {r: (135_500 if r in IRRIGATED else 195_143) for r in REGIONS}

# Rice input cost line items (Table 2 of manuscript), reproduced here for full
# traceability (reviewer point 6) -- see data/table2_rice_cost_buildup.csv
RICE_COST_LINE_ITEMS = {
    "rainfed":  {"seed": 107_143, "npk": 60_000, "urea": 28_000, "herbicide_nursery": 0},
    "irrigated": {"seed": 12_500, "npk": 68_000, "urea": 36_000, "herbicide_nursery": 19_000},
}

# --- Current rice area S_i,r ---------------------------------------------------
# Irrigated regions: RECOVERED from the submitted manuscript's own optimal solution
# (Table "allocation_bicrop"), where x_i,r is reported to equal "all or nearly all"
# of S_i,r. Treated as an exact reconstruction, not an estimate.
S_r_irrigated = {"Far North": 1_619, "North": 40_321, "Northwest": 41_639}

# Rainfed regions: RECONSTRUCTED (see module docstring + data/README). National 2020
# baseline rice production backed out from the manuscript's August-2026 estimate
# (~337,000 t) deflated at +7.77%/yr over 6 years, minus the production implied by the
# irrigated-region areas above; the remainder is allocated across the 7 rainfed regions
# in proportion to each region's current maize area S_i,m (structural proxy).
_NATIONAL_PROD_2026 = 337_000.0
_GROWTH_RATE = 0.0777
_NATIONAL_PROD_2020 = _NATIONAL_PROD_2026 / (1 + _GROWTH_RATE) ** 6
_PROD_IRRIGATED_2020 = sum(S_r_irrigated[r] * Y0_r[r] for r in IRRIGATED)
_PROD_RAINFED_2020 = max(_NATIONAL_PROD_2020 - _PROD_IRRIGATED_2020, 0.0)
_MAIZE_AREA_RAINFED_TOTAL = sum(S_m[r] for r in RAINFED)

S_r_rainfed = {}
for r in RAINFED:
    share = S_m[r] / _MAIZE_AREA_RAINFED_TOTAL
    prod_r = _PROD_RAINFED_2020 * share
    S_r_rainfed[r] = prod_r / Y0_r[r]

S_r = {**S_r_irrigated, **S_r_rainfed}

# --- Targets ---------------------------------------------------------------------
SND30_TARGET_m = 8_000_000.0   # t, official SND30 2030 target
SND30_TARGET_r = 750_000.0     # t, official SND30 2030 target


# ---------------------------------------------------------------------------------
# 2. PRODUCTION FUNCTION
# ---------------------------------------------------------------------------------

def production(region, crop, x, e, adoption=1.0, y1_override=None):
    """P_i,k(x,e) = y0*S + adoption*(y1-y0)*x + adoption*y1*e."""
    if crop == "m":
        y0, y1, S = Y0_m[region], Y1_m[region], S_m[region]
    else:
        y0, y1, S = Y0_r[region], Y1_r[region], S_r[region]
    if y1_override is not None:
        y1 = y1_override
    return y0 * S + adoption * (y1 - y0) * x + adoption * y1 * e


# ---------------------------------------------------------------------------------
# 3. GENUINE LEXICOGRAPHIC GOAL PROGRAM
# ---------------------------------------------------------------------------------
#
# Decision vector (len = 4n + 4):
#   x_m[0..n-1], e_m[0..n-1], x_r[0..n-1], e_r[0..n-1],
#   d_m_minus, d_m_plus, d_r_minus, d_r_plus
#
# Goal constraints (equalities):
#   sum_i P_i,m(x,e) + d_m^- - d_m^+ = T_m
#   sum_i P_i,r(x,e) + d_r^- - d_r^+ = T_r
#
# Hard constraints:
#   shared land:         e_i,m + e_i,r <= beta * (S_i,m + S_i,r)          [land_mode="shared"]
#   OR separate land:    e_i,m <= beta_m * S_i,m  and  e_i,r <= beta_r * S_i,r   [land_mode="separate"]
#   bounds:               0 <= x_i,k <= S_i,k ;  e_i,k >= 0
#   all deviation vars >= 0

def _var_index(n):
    idx = {}
    idx["x_m"] = list(range(0, n))
    idx["e_m"] = list(range(n, 2 * n))
    idx["x_r"] = list(range(2 * n, 3 * n))
    idx["e_r"] = list(range(3 * n, 4 * n))
    idx["d_m_minus"] = 4 * n
    idx["d_m_plus"] = 4 * n + 1
    idx["d_r_minus"] = 4 * n + 2
    idx["d_r_plus"] = 4 * n + 3
    idx["n_vars"] = 4 * n + 4
    return idx


def _build_constraints(T_m, T_r, beta, land_mode="shared", beta_r=None,
                        adoption_m=1.0, adoption_r=1.0, ext_cost_multiplier_m=1.0,
                        ext_cost_multiplier_r=1.0):
    """Builds A_eq, b_eq, A_ub, b_ub, bounds for the goal-program constraint set
    (everything except the objective, which differs by stage)."""
    n = len(REGIONS)
    idx = _var_index(n)
    nvar = idx["n_vars"]

    # --- goal (equality) constraints ---
    A_eq, b_eq = [], []

    row_m = np.zeros(nvar)
    for j, r in enumerate(REGIONS):
        row_m[idx["x_m"][j]] = adoption_m * (Y1_m[r] - Y0_m[r])
        row_m[idx["e_m"][j]] = adoption_m * Y1_m[r]
    row_m[idx["d_m_minus"]] = 1.0
    row_m[idx["d_m_plus"]] = -1.0
    base_m = sum(Y0_m[r] * S_m[r] for r in REGIONS)
    A_eq.append(row_m); b_eq.append(T_m - base_m)

    row_r = np.zeros(nvar)
    for j, r in enumerate(REGIONS):
        row_r[idx["x_r"][j]] = adoption_r * (Y1_r[r] - Y0_r[r])
        row_r[idx["e_r"][j]] = adoption_r * Y1_r[r]
    row_r[idx["d_r_minus"]] = 1.0
    row_r[idx["d_r_plus"]] = -1.0
    base_r = sum(Y0_r[r] * S_r[r] for r in REGIONS)
    A_eq.append(row_r); b_eq.append(T_r - base_r)

    # --- land inequality constraints ---
    A_ub, b_ub = [], []
    if land_mode == "shared":
        for j, r in enumerate(REGIONS):
            row = np.zeros(nvar)
            row[idx["e_m"][j]] = 1.0
            row[idx["e_r"][j]] = 1.0
            A_ub.append(row); b_ub.append(beta * (S_m[r] + S_r[r]))
    elif land_mode == "separate":
        br = beta_r if beta_r is not None else beta
        for j, r in enumerate(REGIONS):
            row_e_m = np.zeros(nvar); row_e_m[idx["e_m"][j]] = 1.0
            A_ub.append(row_e_m); b_ub.append(beta * S_m[r])
            row_e_r = np.zeros(nvar); row_e_r[idx["e_r"][j]] = 1.0
            A_ub.append(row_e_r); b_ub.append(br * S_r[r])
    else:
        raise ValueError("land_mode must be 'shared' or 'separate'")

    # --- bounds ---
    bounds = [None] * nvar
    for j, r in enumerate(REGIONS):
        bounds[idx["x_m"][j]] = (0, S_m[r])
        bounds[idx["e_m"][j]] = (0, None)
        bounds[idx["x_r"][j]] = (0, S_r[r])
        bounds[idx["e_r"][j]] = (0, None)
    bounds[idx["d_m_minus"]] = (0, None)
    bounds[idx["d_m_plus"]] = (0, None)
    bounds[idx["d_r_minus"]] = (0, None)
    bounds[idx["d_r_plus"]] = (0, None)

    cost_vec = np.zeros(nvar)
    for j, r in enumerate(REGIONS):
        cost_vec[idx["x_m"][j]] = COST_m
        cost_vec[idx["e_m"][j]] = COST_m * ext_cost_multiplier_m
        cost_vec[idx["x_r"][j]] = COST_r[r]
        cost_vec[idx["e_r"][j]] = COST_r[r] * ext_cost_multiplier_r

    return idx, np.array(A_eq), np.array(b_eq), np.array(A_ub), np.array(b_ub), bounds, cost_vec


def solve_goal_program(T_m, T_r, beta, w_m=1.0, w_r=1.0, land_mode="shared", beta_r=None,
                        adoption_m=1.0, adoption_r=1.0, ext_cost_multiplier_m=1.0,
                        ext_cost_multiplier_r=1.0):
    """Two-stage lexicographic goal program. Returns a result dict with both stages,
    the achieved production, shortfalls, minimum cost and dual values."""
    n = len(REGIONS)
    idx, A_eq, b_eq, A_ub, b_ub, bounds, cost_vec = _build_constraints(
        T_m, T_r, beta, land_mode, beta_r, adoption_m, adoption_r,
        ext_cost_multiplier_m, ext_cost_multiplier_r)
    nvar = idx["n_vars"]

    # --- Stage 1: minimize weighted shortfall (priority 1) ---
    c1 = np.zeros(nvar)
    c1[idx["d_m_minus"]] = w_m
    c1[idx["d_r_minus"]] = w_r
    res1 = linprog(c1, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res1.success:
        return {"success": False, "message": res1.message, "stage": 1}

    shortfall_opt = res1.fun  # weighted shortfall achieved at stage 1

    # --- Stage 2: among stage-1-optimal solutions, minimize total cost ---
    A_ub2 = list(A_ub)
    b_ub2 = list(b_ub)
    # lock in the stage-1 optimal weighted shortfall (with small numerical tolerance)
    lock_row = c1.copy()
    A_ub2.append(lock_row); b_ub2.append(shortfall_opt + 1e-6)
    res2 = linprog(cost_vec, A_ub=np.array(A_ub2), b_ub=np.array(b_ub2),
                    A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res2.success:
        return {"success": False, "message": res2.message, "stage": 2}

    x = res2.x
    n_ = len(REGIONS)
    x_m = dict(zip(REGIONS, x[idx["x_m"]]))
    e_m = dict(zip(REGIONS, x[idx["e_m"]]))
    x_r = dict(zip(REGIONS, x[idx["x_r"]]))
    e_r = dict(zip(REGIONS, x[idx["e_r"]]))
    d_m_minus, d_m_plus = x[idx["d_m_minus"]], x[idx["d_m_plus"]]
    d_r_minus, d_r_plus = x[idx["d_r_minus"]], x[idx["d_r_plus"]]

    prod_m = sum(production(r, "m", x_m[r], e_m[r], adoption_m, Y1_m[r]) for r in REGIONS)
    prod_r = sum(production(r, "r", x_r[r], e_r[r], adoption_r, Y1_r[r]) for r in REGIONS)
    total_cost = res2.fun

    out = {
        "success": True,
        "stage1_weighted_shortfall": shortfall_opt,
        "stage1_status": res1.message,
        "stage2_status": res2.message,
        "n_iterations_stage1": res1.nit,
        "n_iterations_stage2": res2.nit,
        "total_cost_fcfa": total_cost,
        "production_m_t": prod_m,
        "production_r_t": prod_r,
        "target_m_t": T_m,
        "target_r_t": T_r,
        "shortfall_m_t": d_m_minus,
        "shortfall_r_t": d_r_minus,
        "overshoot_m_t": d_m_plus,
        "overshoot_r_t": d_r_plus,
        "pct_target_m": 100 * prod_m / T_m if T_m else None,
        "pct_target_r": 100 * prod_r / T_r if T_r else None,
        "x_m": x_m, "e_m": e_m, "x_r": x_r, "e_r": e_r,
        "beta": beta, "land_mode": land_mode,
        "adoption_m": adoption_m, "adoption_r": adoption_r,
        "raw_stage2": res2,
    }
    # dual values (shadow prices) from stage-2 solve: land constraints + goal constraints
    if hasattr(res2, "ineqlin") and res2.ineqlin is not None:
        marg = res2.ineqlin.marginals
        if land_mode == "shared":
            out["dual_land"] = dict(zip(REGIONS, -marg[:n_]))
        else:
            out["dual_land_m"] = {REGIONS[j]: -marg[2 * j] for j in range(n_)}
            out["dual_land_r"] = {REGIONS[j]: -marg[2 * j + 1] for j in range(n_)}
    if hasattr(res2, "eqlin") and res2.eqlin is not None:
        marg = res2.eqlin.marginals
        out["dual_goal_m"] = -marg[0]
        out["dual_goal_r"] = -marg[1]
    return out


if __name__ == "__main__":
    print("Central scenario (80% maize / 90% rice, beta=0.5, full adoption):")
    r = solve_goal_program(0.80 * SND30_TARGET_m, 0.90 * SND30_TARGET_r, 0.5)
    print(json.dumps({k: v for k, v in r.items() if k not in ("x_m", "e_m", "x_r", "e_r", "raw_stage2")},
                      indent=2, default=str))
