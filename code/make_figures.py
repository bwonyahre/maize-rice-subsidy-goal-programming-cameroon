"""Figures 4, 5, 6 and 7 of the manuscript, drawn from ../results/*.csv.  Run after run_scenarios.py."""
import os
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures"); os.makedirs(FIG, exist_ok=True)
BLUE, GREEN, ORANGE, RED, GREY, LBLUE, LGREEN = "#1f4e79", "#2e8b57", "#ff8c00", "#8b0000", "#6b6b6b", "#8faadc", "#a9d3b8"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

# Fig 4 -- base, gains, targets (model base 2020 and 2024 level shown separately)
t8 = pd.read_csv(os.path.join(R, "t08_base_gains_target.csv"))
c, u = t8.iloc[0], t8.iloc[1]
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.8))
for a, crop, unit, f, cb, cl in [(ax[0], "maize", "Mt", 1e6, BLUE, LBLUE), (ax[1], "rice", "thousand t", 1e3, GREEN, LGREEN)]:
    vals = [c[f"{crop}_base_t"], u[f"{crop}_base_t"], c[f"{crop}_target_t"], 8e6 if crop == "maize" else 7.5e5]
    labs = ["Base 2020\n(model)", "Level 2024\n(report / trend)", "Target\n80% / 90%", "Official\ntarget"]
    bars = a.bar(labs, [v / f for v in vals], color=[cl, cl, ORANGE, RED], width=.6, hatch=None)
    bars[1].set_hatch("//"); bars[1].set_edgecolor("white")
    for b_, v in zip(bars, vals): a.text(b_.get_x() + b_.get_width() / 2, v / f, f"{v / f:,.2f}" if crop == "maize" else f"{v / f:,.0f}", ha="center", va="bottom", fontweight="bold", fontsize=10)
    a.set_title(crop.capitalize(), fontweight="bold"); a.set_ylabel(f"Production ({unit})"); a.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart9_bicrop_targets.png"), dpi=170); plt.close(fig)

# Fig 5 -- minimum budget vs beta, with and without extension premium; unattainable points flagged
t4 = pd.read_csv(os.path.join(R, "t04_land_and_extension_cost.csv"))
fig, ax = plt.subplots(figsize=(8.2, 5))
for col, lab, colr, mk in [("shared_kappa0.3_budget_bn", "shared land, extension +30% (central)", BLUE, "o"),
                           ("shared_kappa0.0_budget_bn", "shared land, no extension premium", GREY, "s"),
                           ("separate_kappa0.3_budget_bn", "separate land, extension +30%", ORANGE, "^")]:
    ax.plot(t4.beta, t4[col], marker=mk, color=colr, lw=2.2, ms=8, label=lab)
sf = t4["shared_kappa0.3_shortfall_maize_t"]
for b, v, s_ in zip(t4.beta, t4["shared_kappa0.3_budget_bn"], sf):
    ax.annotate(f"{v:.1f}" + (f"\n(maize shortfall {s_ / 1e3:,.0f} kt)" if s_ > 0 else ""), (b, v), textcoords="offset points", xytext=(8, 6), fontsize=9, color=RED if s_ > 0 else BLUE)
ax.set_xlabel(r"$\beta$ (share of current area that can be added)"); ax.set_ylabel("Minimum budget, Bn FCFA")
ax.grid(alpha=.25); ax.legend(frameon=False, fontsize=9); fig.tight_layout()
fig.savefig(os.path.join(FIG, "chart10_beta_joint.png"), dpi=170); plt.close(fig)

# Fig 6 -- budget frontier (official targets)
t2 = pd.read_csv(os.path.join(R, "t02_budget_frontier.csv"))
fig, ax = plt.subplots(figsize=(8.2, 5))
ax.plot(t2.budget_bn, t2.maize_pct_official, color=BLUE, lw=2.4, marker="o", ms=4, label="maize (% of 8 Mt)")
ax.plot(t2.budget_bn, t2.rice_pct_official, color=GREEN, lw=2.4, marker="s", ms=4, label="rice (% of 750 kt)")
ax.axhline(80, color=ORANGE, ls="--", lw=1.2); ax.text(105, 81, "80% (central maize target)", color=ORANGE, fontsize=9)
ax.set_xlabel("Budget ceiling, Bn FCFA"); ax.set_ylabel("Share of the official 2030 target attained (%)")
ax.set_ylim(30, 105); ax.grid(alpha=.25); ax.legend(frameon=False, loc="center right"); fig.tight_layout()
fig.savefig(os.path.join(FIG, "chart11_frontier.png"), dpi=170); plt.close(fig)

# Fig 7 -- joint sensitivity: maize attained at the central budget
d = pd.read_csv(os.path.join(R, "t10b_joint_sensitivity_draws.csv"))
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.5))
ax[0].hist(d.maize_pct_at_B, bins=24, color=BLUE, edgecolor="white"); ax[0].axvline(100, color=RED, ls="--")
ax[0].set_xlabel("Maize target attained at the central budget (%)"); ax[0].set_ylabel("Number of draws")
ok = d[(d.shortfall_maize_t_free == 0) & (d.shortfall_rice_t_free == 0)]
ax[1].hist(ok.budget_needed_bn, bins=16, color=GREEN, edgecolor="white")
ax[1].set_xlabel("Budget needed (Bn FCFA), draws where both targets are attainable"); ax[1].set_ylabel("Number of draws")
for a in ax: a.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart12_joint.png"), dpi=170); plt.close(fig)
print("figures written")
