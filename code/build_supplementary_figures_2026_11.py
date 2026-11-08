"""Build Figs. S1-S12 of Online Resource 1.
Usage: python build_supplementary_figures.py <repo_root_or_inputs_dir> <output_dir>
Outputs: Figure_S1..Figure_S12 as .png (600 dpi) and .pdf (vector)."""
import sys, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker, font_manager
from matplotlib.lines import Line2D

ROOT = Path(sys.argv[1]); PUB = ROOT / "aggregate_outputs" / "publication_figures"
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
import os
_FONT_DIR = os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts"
_added = 0
for _f in ["arial.ttf", "arialbd.ttf", "ariali.ttf"]:
    _p = os.path.join(_FONT_DIR, _f)
    if os.path.exists(_p):
        font_manager.fontManager.addfont(_p); _added += 1
_FAMILY = "Arial" if _added else "DejaVu Sans"   # fallback keeps the script runnable on non-Windows systems
if not _added:
    print("WARNING: Arial not found; falling back to DejaVu Sans (text metrics will differ slightly)")
plt.rcParams.update({
    "font.family": _FAMILY, "font.size": 8.5, "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "axes.linewidth": 0.7, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#333333", "xtick.color": "#333333", "ytick.color": "#333333",
    "axes.labelcolor": "#111111", "text.color": "#111111",
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})
BLUE = "#1f4e79"; ORANGE = "#d1762b"; GREY = "#6f6f6f"; LIGHT = "#bfbfbf"; ACCENT = "#c0392b"
GRID = dict(color="#d9d9d9", linewidth=0.5)

def save(fig, stem):
    fig.savefig(OUT / f"{stem}.png", dpi=600); fig.savefig(OUT / f"{stem}.pdf"); plt.close(fig); print("saved", stem)

def grid(ax, axis="both"):
    ax.grid(axis=axis, **GRID); ax.set_axisbelow(True)

def labels(fig, pos):
    for lab, (x, y) in pos.items():
        fig.text(x, y, lab, fontsize=10, fontweight="bold", va="bottom", ha="left")

def pretty(name):
    return (str(name).replace("x_", "", 1).replace("_", " ")
            .replace("noninvasive ", "noninvasive ").replace("sd", "SD").replace("bp", "BP")
            .replace("lab ", "").replace("vital ", "").replace("inr", "INR").replace("bun", "BUN"))

# S1 ---------------------------------------------------------------
def s1():
    d = pd.read_csv(ROOT / "analyses/analysis_renal_trajectory_comparator/outputs/fold_performance.csv")
    d = d[d.model == "Full XGBoost"].sort_values("outer_fold")
    fig = plt.figure(figsize=(6.1, 3.4)); ax = fig.add_axes([0.11, 0.17, 0.85, 0.78])
    grid(ax, "y")
    ax.plot(d.outer_fold, d.auroc, "-o", color=ACCENT, lw=1.3, ms=5, mec="white", mew=0.6, label="AUROC")
    ax.plot(d.outer_fold, d.auprc, "-s", color=BLUE, lw=1.3, ms=4.5, mec="white", mew=0.6, label="AUPRC")
    for x, y in zip(d.outer_fold, d.auroc): ax.text(x, y + 0.025, f"{y:.3f}", ha="center", va="bottom", fontsize=7.5)
    for x, y in zip(d.outer_fold, d.auprc): ax.text(x, y - 0.03, f"{y:.3f}", ha="center", va="top", fontsize=7.5)
    ax.set_xlabel("Hospital-disjoint outer fold"); ax.set_ylabel("Performance")
    ax.set_xticks(d.outer_fold); ax.set_xlim(0.6, 5.4); ax.set_ylim(0.2, 1.0)
    ax.legend(loc="center right", frameon=False)
    save(fig, "Figure_S1")

# S2 ---------------------------------------------------------------
def s2():
    d = pd.read_csv(PUB / "FIG_S2_tier_b_calibration_points.csv")
    x = 100 * d.mean_predicted_risk; y = 100 * d.event_rate
    fig = plt.figure(figsize=(6.1, 4.3)); ax = fig.add_axes([0.14, 0.14, 0.60, 0.82])
    grid(ax)
    ax.plot([0, 12], [0, 12], "--", color=GREY, lw=0.9, label="Ideal calibration")
    ax.scatter(x, y, s=28, color=BLUE, edgecolors="white", linewidths=0.6, alpha=0.9, label="Hospital (Tier B)")
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Mean predicted risk (%)"); ax.set_ylabel("Observed event rate (%)")
    ax.set_xticks(np.arange(0, 13, 2)); ax.set_yticks(np.arange(0, 13, 2))
    ax.legend(loc="upper left", frameon=False)
    save(fig, "Figure_S2")

# S3 ---------------------------------------------------------------
def s3():
    d = pd.read_csv(PUB / "FIG_S3_operating_points_full.csv"); x = 100 * d.threshold
    fig = plt.figure(figsize=(6.1, 3.8)); ax = fig.add_axes([0.10, 0.16, 0.86, 0.80])
    grid(ax)
    ax.plot(x, d.sensitivity, "-o", color=ACCENT, lw=1.3, ms=4.5, mec="white", mew=0.6, label="Sensitivity")
    ax.plot(x, d.specificity, "-s", color=BLUE, lw=1.3, ms=4.2, mec="white", mew=0.6, label="Specificity")
    ax.plot(x, d.ppv, "-^", color=ORANGE, lw=1.3, ms=4.5, mec="white", mew=0.6, label="PPV")
    ax.set_xlabel("Prespecified probability threshold (%)"); ax.set_ylabel("Metric value")
    ax.set_xticks(x); ax.set_xticklabels([f"{v:g}" for v in x]); ax.set_ylim(0, 1.03)
    ax.legend(loc="center right", frameon=False)
    save(fig, "Figure_S3")

# S4 ---------------------------------------------------------------
def s4():
    d = pd.read_csv(PUB / "FIG_S4_reference_creatinine_sensitivity.csv")
    fig = plt.figure(figsize=(6.1, 3.9)); ax = fig.add_axes([0.11, 0.24, 0.85, 0.72])
    grid(ax, "y"); x = np.arange(len(d))
    ax.bar(x, 100 * d.event_rate, color=BLUE, width=0.62)
    ax.set_xticks(x); ax.set_xticklabels(d.phenotype, rotation=12, ha="right")
    ax.set_ylabel("Stage 2\u20133 event rate (%)"); ax.set_xlabel("Reference-creatinine sensitivity phenotype")
    ax.set_ylim(0, 6.6)
    for i, r in d.iterrows():
        ax.text(i, 100 * r.event_rate + 0.12, f"{100*r.event_rate:.2f}%\ncoverage {100*r.coverage:.1f}%",
                ha="center", va="bottom", fontsize=7.5)
    save(fig, "Figure_S4")

# S5 ---------------------------------------------------------------
def s5():
    d = pd.read_csv(ROOT / "analyses/analysis_selection_bias/outputs/cohort_group_counts.csv")
    order = ["included_main", "no_reference_creatinine", "no_future_creatinine", "inadequate_followup",
             "early_death", "chronic_dialysis_or_esrd", "severe_aki_by_12h", "acute_rrt_by_12h"]
    d = d.set_index("exclusion_detail").loc[order].reset_index()
    fig = plt.figure(figsize=(6.1, 3.9)); ax = fig.add_axes([0.34, 0.14, 0.62, 0.82])
    grid(ax, "x"); y = np.arange(len(d))[::-1]
    cols = [ACCENT if g == "included_main" else BLUE for g in d.exclusion_detail]
    ax.barh(y, d.patients, color=cols, height=0.66)
    ax.set_yticks(y); ax.set_yticklabels(d.exclusion_detail); ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Patients")
    for yy, n in zip(y, d.patients): ax.text(n + 800, yy, f"{int(n):,}", va="center", fontsize=7.5)
    ax.set_xlim(0, 70000); ax.xaxis.set_major_locator(ticker.MultipleLocator(10000))
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    save(fig, "Figure_S5")

# S6 ---------------------------------------------------------------
def s6():
    raw = pd.read_csv(ROOT / "analyses/analysis_selection_bias/outputs/ranked_absolute_smds.csv")
    pv = raw.pivot(index="characteristic", columns="comparison", values="abs_smd")
    pv = pv.rename(columns={"Final vs no reference": "no_ref", "Final vs other excluded": "other"})
    order = ["Invasive mechanical ventilation by 12 h", "ICU admission source (maximum category-wise)",
             "Last heart rate by 12 h, beats/min", "Any vasopressor infusion by 12 h",
             "Hospital admission source (maximum category-wise)", "Last blood urea nitrogen by 12 h, mg/dL",
             "ICU type (maximum category-wise)", "Last systolic blood pressure by 12 h, mmHg",
             "Race/ethnicity (maximum category-wise)", "Age, years", "Last respiratory rate by 12 h, breaths/min",
             "Body mass index, kg/m\u00c2\u00b2", "Sex (maximum category-wise)"]
    pv = pv.loc[order]
    labs = [str(x).replace("kg/m\u00c2\u00b2", "kg/m\u00b2") for x in pv.index]
    y = np.arange(len(pv))[::-1]
    fig = plt.figure(figsize=(6.1, 4.6)); ax = fig.add_axes([0.47, 0.12, 0.50, 0.76])
    grid(ax, "x")
    ax.axvline(0.10, color=GREY, ls=(0, (5, 3)), lw=0.9, label="SMD = 0.10")
    ax.axvline(0.20, color=GREY, ls="-.", lw=0.9, label="SMD = 0.20")
    ax.scatter(pv.no_ref, y, s=34, facecolors="white", edgecolors=ACCENT, linewidths=1.1, label="Final vs no reference", zorder=3)
    ax.scatter(pv.other, y, s=30, marker="s", facecolors="white", edgecolors=BLUE, linewidths=1.1, label="Final vs other excluded", zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(labs); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
    ax.set_xlabel("Absolute standardized mean difference"); ax.set_xlim(-0.005, 0.41)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=False)
    save(fig, "Figure_S6")

# S7 ---------------------------------------------------------------
def s7():
    base = ROOT / "analyses/analysis_missingness_indicator_dependence/outputs"
    fold = pd.read_csv(base / "fold_level_attribution_summary.csv")
    af = pd.read_csv(base / "fold_indicator_importance_and_ranks.csv")
    N = int(fold["n"].sum())
    pool = (af.groupby("source_predictor", as_index=False)
            .agg(sum_abs_indicator_shap=("sum_abs_indicator_shap", "sum"), sum_abs_value_shap=("sum_abs_value_shap", "sum")))
    pool["mean_abs_indicator_shap"] = pool.sum_abs_indicator_shap / N
    pool["mean_abs_value_shap"] = pool.sum_abs_value_shap / N
    pool = pool.sort_values("mean_abs_indicator_shap", ascending=False).reset_index(drop=True)
    gf = fold.sum_abs_indicator.sum() / fold.sum_abs_all.sum()
    fig = plt.figure(figsize=(6.1, 8.2))
    axA = fig.add_axes([0.12, 0.735, 0.84, 0.21]); axB = fig.add_axes([0.40, 0.395, 0.56, 0.255]); axC = fig.add_axes([0.40, 0.055, 0.56, 0.255])
    labs = ["Overall"] + [f"Fold {int(x)}" for x in fold.outer_fold]
    vals = [100 * gf] + list(100 * fold.missingness_attribution_fraction)
    xx = np.arange(len(labs)); grid(axA, "y")
    axA.bar(xx, vals, width=0.62, color=[ACCENT] + [BLUE] * (len(labs) - 1))
    for x, v in zip(xx, vals): axA.text(x, v + 0.03, f"{v:.2f}%", ha="center", va="bottom", fontsize=7.5)
    axA.set_xticks(xx); axA.set_xticklabels(labs); axA.set_ylabel("Absolute SHAP from\nindicators (%)"); axA.set_xlabel("Held-out evaluation set"); axA.set_ylim(0, 2.5)
    b = pool.head(12).sort_values("mean_abs_indicator_shap"); yy = np.arange(len(b)); grid(axB, "x")
    axB.barh(yy, b.mean_abs_indicator_shap, color=BLUE, height=0.66)
    axB.set_yticks(yy); axB.set_yticklabels([pretty(s) for s in b.source_predictor]); axB.tick_params(axis="y", length=0); axB.spines["left"].set_visible(False)
    axB.set_xlabel("Mean |SHAP| of missingness indicator")
    c = pool.head(10).sort_values("mean_abs_indicator_shap"); yy = np.arange(len(c)); grid(axC, "x")
    axC.barh(yy, c.mean_abs_value_shap, color=LIGHT, height=0.66, label="Observed value")
    axC.barh(yy, c.mean_abs_indicator_shap, left=c.mean_abs_value_shap, color=ACCENT, height=0.66, label="Missingness indicator")
    axC.set_yticks(yy); axC.set_yticklabels([pretty(s) for s in c.source_predictor]); axC.tick_params(axis="y", length=0); axC.spines["left"].set_visible(False)
    axC.set_xlabel("Mean |SHAP|"); axC.legend(loc="lower right", frameon=False)
    labels(fig, {"(a)": (0.02, 0.955), "(b)": (0.02, 0.655), "(c)": (0.02, 0.315)})
    save(fig, "Figure_S7")

# S8 ---------------------------------------------------------------
def s8():
    base = ROOT / "analyses/analysis_renal_trajectory_comparator/outputs"
    curves = pd.read_csv(base / "roc_pr_curve_data.csv"); dca = pd.read_csv(base / "decision_curve_data.csv")
    prev = 3032 / 58491
    fig = plt.figure(figsize=(6.1, 8.4))
    axA = fig.add_axes([0.13, 0.715, 0.50, 0.245]); axB = fig.add_axes([0.13, 0.385, 0.50, 0.245]); axC = fig.add_axes([0.13, 0.06, 0.78, 0.245])
    st = {"Full XGBoost": dict(color=ACCENT, ls="-", lw=1.4, label="Full XGBoost"),
          "Comparator 2: creatinine trajectory": dict(color=BLUE, ls="--", lw=1.3, label="Creatinine trajectory (Comparator 2)")}
    for m, s in st.items():
        z = curves[(curves.curve == "ROC") & (curves.model == m)]; axA.plot(z.x, z.y, **s)
    axA.plot([0, 1], [0, 1], color=GREY, ls=":", lw=0.9, label="Chance")
    axA.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="1 \u2212 specificity", ylabel="Sensitivity"); axA.set_aspect("equal"); grid(axA)
    axA.legend(loc="lower right", frameon=False)
    for m, s in st.items():
        z = curves[(curves.curve == "PR") & (curves.model == m)]; axB.plot(z.x, z.y, **s)
    axB.axhline(prev, color=GREY, ls=":", lw=0.9, label="Outcome prevalence")
    axB.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="Recall", ylabel="Precision"); axB.set_aspect("equal"); grid(axB)
    axB.legend(loc="upper right", frameon=False)
    ds = {"Full XGBoost": dict(color=ACCENT, ls="-", lw=1.4, label="Full XGBoost"),
          "Comparator 2: creatinine trajectory": dict(color=BLUE, ls="--", lw=1.3, label="Creatinine trajectory (Comparator 2)"),
          "Treat all": dict(color=LIGHT, ls=":", lw=1.3, label="Treat all"),
          "Treat none": dict(color="#333333", ls=(0, (4, 2)), lw=0.9, label="Treat none")}
    for m, s in ds.items():
        z = dca[dca.model == m]; axC.plot(100 * z.threshold, z.net_benefit, **s)
    axC.set_xlim(0.75, 10.25); axC.set_xticks(range(1, 11)); axC.set_xlabel("Threshold probability (%)"); axC.set_ylabel("Net benefit"); grid(axC)
    axC.legend(loc="lower left", frameon=False, ncol=2)
    labels(fig, {"(a)": (0.02, 0.965), "(b)": (0.02, 0.635), "(c)": (0.02, 0.31)})
    save(fig, "Figure_S8")

# S9 ---------------------------------------------------------------
def s9():
    q = pd.read_csv(ROOT / "analyses/analysis_subgroup_fairness/outputs/subgroup_calibration_quintiles.csv")
    fig = plt.figure(figsize=(6.1, 8.4))
    axes = [fig.add_axes([0.13, 0.715, 0.78, 0.245]), fig.add_axes([0.13, 0.385, 0.78, 0.245]), fig.add_axes([0.13, 0.055, 0.78, 0.245])]
    pal = [ACCENT, BLUE, ORANGE, "#5b9bd5", "#7f7f7f", "#9e480e", "#2e8b57"]
    nice = {"female": "Female", "male": "Male", "<50": "<50 years", "50-64": "50\u201364 years", "65-79": "65\u201379 years", ">=80": "\u226580 years"}
    for ax, dom in zip(axes, ["Sex", "Age", "Recorded race/ethnicity"]):
        z = q[q.domain == dom]; grid(ax)
        ax.plot([0, 0.35], [0, 0.35], "--", color=GREY, lw=0.9, label="Ideal")
        for i, (sg, g) in enumerate(z.groupby("subgroup", sort=False)):
            g = g.sort_values("quintile")
            ax.plot(g.mean_predicted, g.observed, "-o", color=pal[i % len(pal)], lw=1.2, ms=3.8, mec="white", mew=0.5, label=nice.get(sg, sg))
        ax.set_xlim(0, 0.35); ax.set_ylim(0, 0.35); ax.set_aspect("equal")
        ax.set_xlabel("Mean predicted risk"); ax.set_ylabel("Observed event rate")
        ax.legend(loc="upper left", frameon=False, ncol=1, fontsize=7)
    labels(fig, {"(a)": (0.02, 0.965), "(b)": (0.02, 0.635), "(c)": (0.02, 0.305)})
    save(fig, "Figure_S9")

# S10 --------------------------------------------------------------
def s10():
    df = pd.read_csv(ROOT / "analyses/analysis_subgroup_fairness/outputs/subgroup_performance_with_cluster_ci.csv")
    d = df[df.stable_for_metrics == True].copy()
    order = [("Sex", "female"), ("Sex", "male"), ("Age", "<50"), ("Age", "50-64"), ("Age", "65-79"), ("Age", ">=80"),
             ("Recorded race/ethnicity", "Caucasian"), ("Recorded race/ethnicity", "African American"),
             ("Recorded race/ethnicity", "Other/Unknown"), ("Recorded race/ethnicity", "Hispanic"),
             ("Recorded race/ethnicity", "Asian"), ("Recorded race/ethnicity", "Native American"), ("Recorded race/ethnicity", "Missing")]
    key = {(r.domain, r.subgroup): r for _, r in d.iterrows()}; rows = [key[k] for k in order]
    nice = {"female": "Female", "male": "Male", "50-64": "50\u201364", "65-79": "65\u201379", ">=80": "\u226580"}
    labs = [f"{'Race/ethnicity' if r.domain.startswith('Recorded') else r.domain}: {nice.get(r.subgroup, r.subgroup)}" for r in rows]
    y = np.arange(len(rows))[::-1]
    fig = plt.figure(figsize=(6.1, 7.6)); axA = fig.add_axes([0.36, 0.565, 0.60, 0.40]); axB = fig.add_axes([0.36, 0.07, 0.50, 0.40])
    def dots(ax, m, lo, hi, col):
        grid(ax, "x")
        for yi, mi, l, h in zip(y, m, lo, hi):
            ax.plot([l, h], [yi, yi], color=col, lw=1.2); ax.plot([l, l], [yi - 0.18, yi + 0.18], color=col, lw=1.0); ax.plot([h, h], [yi - 0.18, yi + 0.18], color=col, lw=1.0)
            ax.plot(mi, yi, "o", color=col, ms=4.5, mec="white", mew=0.6)
        ax.set_yticks(y); ax.set_yticklabels(labs); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
        ax.set_ylim(-0.7, len(y) - 0.3)
    au = np.array([r.auroc for r in rows]); dots(axA, au, [r.auroc_ci_low for r in rows], [r.auroc_ci_high for r in rows], ACCENT); axA.set_xlabel("AUROC (95% CI)")
    ap = np.array([r.auprc for r in rows]); dots(axB, ap, [r.auprc_ci_low for r in rows], [r.auprc_ci_high for r in rows], BLUE); axB.set_xlabel("AUPRC (95% CI)")
    prev = [r.prevalence for r in rows]
    for yy, p in zip(y, prev): axB.text(1.03, yy, f"{100*p:.1f}%", transform=axB.get_yaxis_transform(), va="center", ha="left", fontsize=7.5)
    fig.text(0.965, 0.27, "Outcome prevalence", rotation=90, va="center", ha="center", fontsize=8.5)
    labels(fig, {"(a)": (0.02, 0.965), "(b)": (0.02, 0.47)})
    save(fig, "Figure_S10")

# S11 --------------------------------------------------------------
def s11():
    hist = pd.read_csv(PUB / "FIG_S11_event_time_histogram.csv").sort_values("bin_index")
    lead = pd.read_csv(ROOT / "tables/TABLE_S15_source.csv"); lead = lead[lead.analysis_type == "lead"].copy()
    order = ["L0", "L6", "L12", "L24"]; lead["scenario"] = pd.Categorical(lead.scenario, categories=order, ordered=True); lead = lead.sort_values("scenario")
    fig = plt.figure(figsize=(6.1, 7.8)); axA = fig.add_axes([0.13, 0.72, 0.83, 0.24]); axB = fig.add_axes([0.13, 0.39, 0.83, 0.24]); axC = fig.add_axes([0.13, 0.06, 0.83, 0.24])
    centers = (hist.start_hour + hist.end_hour) / 2; grid(axA, "y")
    axA.bar(centers, hist.n_events, width=3.5, color=BLUE)
    axA.set_xlim(11.5, 72.5); axA.set_xlabel("Time of first stage 2\u20133 event after ICU admission (h)"); axA.set_ylabel("Events")
    axA.set_xticks([12, 24, 36, 48, 60, 72])
    x = np.arange(len(lead))
    def band(ax, m, lo, hi, col, lab):
        grid(ax, "y")
        ax.plot(x, m, "-", color=col, lw=1.2)
        for xi, mi, l, h in zip(x, m, lo, hi):
            ax.plot([xi, xi], [l, h], color=col, lw=1.2); ax.plot([xi - 0.06, xi + 0.06], [l, l], color=col, lw=1.0); ax.plot([xi - 0.06, xi + 0.06], [h, h], color=col, lw=1.0)
            ax.plot(xi, mi, "o", color=col, ms=5, mec="white", mew=0.6); ax.text(xi + 0.08, mi, f"{mi:.3f}", va="center", ha="left", fontsize=7.5)
        ax.set_xticks(x); ax.set_xticklabels(order); ax.set_xlim(-0.4, 3.6); ax.set_xlabel("Minimum lead-time scenario"); ax.set_ylabel(lab)
    band(axB, lead.auroc.to_numpy(), lead.auroc_ci_low.to_numpy(), lead.auroc_ci_high.to_numpy(), ACCENT, "AUROC (95% CI)")
    band(axC, lead.auprc.to_numpy(), lead.auprc_ci_low.to_numpy(), lead.auprc_ci_high.to_numpy(), BLUE, "AUPRC (95% CI)")
    labels(fig, {"(a)": (0.02, 0.965), "(b)": (0.02, 0.635), "(c)": (0.02, 0.305)})
    save(fig, "Figure_S11")

# S12 --------------------------------------------------------------
def s12():
    au = pd.read_csv(PUB / "FIG_S12_tier_b_auroc.csv").auroc.sort_values().to_numpy()
    cal = pd.read_csv(PUB / "FIG_S12_tier_b_calibration.csv"); ctx = pd.read_csv(PUB / "FIG_S12_all_hospital_calibration_context.csv")
    pooled = float(pd.read_csv(ROOT / "tables/TABLE_S15_source.csv").query("scenario=='L0' and analysis_type=='lead'").auroc.iloc[0])
    fig = plt.figure(figsize=(6.1, 8.4)); axA = fig.add_axes([0.13, 0.715, 0.80, 0.245]); axB = fig.add_axes([0.13, 0.385, 0.80, 0.245]); axC = fig.add_axes([0.13, 0.055, 0.50, 0.245])
    y = np.arange(1, len(au) + 1); grid(axA)
    axA.scatter(au, y, s=24, color=BLUE, edgecolors="white", linewidths=0.5)
    axA.axvline(pooled, color=ACCENT, ls=(0, (5, 3)), lw=1.0, label=f"Pooled AUROC = {pooled:.3f}")
    axA.set_xlabel("AUROC"); axA.set_ylabel("Tier-B hospitals (ordered)"); axA.legend(loc="upper left", frameon=False)
    bp = axB.boxplot([cal.calibration_intercept, cal.calibration_slope], tick_labels=["Intercept", "Slope"], widths=0.42, patch_artist=True,
                     showfliers=True, medianprops=dict(color=ACCENT, lw=1.3), boxprops=dict(facecolor="#dfe8f1", edgecolor=BLUE, lw=0.9),
                     whiskerprops=dict(color=BLUE, lw=0.9), capprops=dict(color=BLUE, lw=0.9), flierprops=dict(marker="o", ms=3.5, mfc="white", mec=BLUE, mew=0.7))
    axB.axhline(0, color=GREY, ls=":", lw=0.9); axB.axhline(1, color=GREY, ls=(0, (5, 3)), lw=0.9)
    axB.set_ylabel("Calibration estimate"); axB.set_xlabel("Calibration parameter"); grid(axB, "y")
    axB.legend(handles=[Line2D([0], [0], color=GREY, ls=":", label="Ideal intercept = 0"), Line2D([0], [0], color=GREY, ls=(0, (5, 3)), label="Ideal slope = 1")], loc="lower right", frameon=False)
    x = ctx.mean_predicted_risk.to_numpy(); yy = ctx.event_rate.to_numpy(); upper = max(0.7, math.ceil((max(x.max(), yy.max()) + 0.015) * 10) / 10)
    grid(axC); axC.scatter(x, yy, s=18, facecolors="white", edgecolors=BLUE, linewidths=0.7, alpha=0.8)
    axC.plot([0, upper], [0, upper], ls=(0, (5, 3)), color=GREY, lw=0.9, label="Ideal calibration")
    axC.set_xlim(0, upper); axC.set_ylim(0, upper); axC.set_aspect("equal", adjustable="box"); axC.set_xlabel("Mean predicted risk"); axC.set_ylabel("Observed event prevalence"); axC.legend(loc="lower right", frameon=False)
    labels(fig, {"(a)": (0.02, 0.965), "(b)": (0.02, 0.635), "(c)": (0.02, 0.305)})
    save(fig, "Figure_S12")

for f in [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12]:
    f()
