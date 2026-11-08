"""Build Fig. 1-3 of the manuscript (International Urology and Nephrology submission).
Usage: python build_main_figures.py <repo_root_or_inputs_dir> <output_dir>
Inputs: aggregate_outputs/publication_figures/FIG_2_*.csv and FIG_3_*.csv (Fig. 1 uses the cohort counts of Table 2, hard-coded below).
Outputs: Figure_1.png/.pdf, Figure_2.png/.pdf, Figure_3.png/.pdf (PNG at 600 dpi, PDF vector)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker, font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

ROOT = Path(sys.argv[1])   # repository root (or the inputs/ folder of this package)
PUB = ROOT / "aggregate_outputs" / "publication_figures"
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
    "font.family": _FAMILY, "font.size": 8.5,
    "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "axes.linewidth": 0.7, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#333333", "xtick.color": "#333333", "ytick.color": "#333333",
    "axes.labelcolor": "#111111", "text.color": "#111111",
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})

BLUE = "#1f4e79"; ORANGE = "#d1762b"; GREY = "#6f6f6f"; LIGHT = "#bfbfbf"
ACCENT = "#c0392b"; FILL = "#eef3f8"; EDGE = "#1f4e79"
GRID = dict(color="#d9d9d9", linewidth=0.5)

def panel(ax, label, x=-0.02, y=1.04):
    ax.text(x, y, label, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=10, fontweight="bold")

def save(fig, stem):
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    fig.savefig(OUT / f"{stem}.pdf")
    plt.close(fig)
    print("saved", stem)

# ------------------------------------------------------------------ Fig. 1
def fig1():
    fig = plt.figure(figsize=(6.3, 4.6))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    def box(cx, cy, w, h, title, lines, fill=FILL):
        p = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                           boxstyle="round,pad=0,rounding_size=0.012",
                           linewidth=0.8, edgecolor=EDGE, facecolor=fill)
        ax.add_patch(p)
        n = 1 + len(lines)
        step = 0.045
        y0 = cy + step * (n - 1) / 2
        ax.text(cx, y0, title, ha="center", va="center", fontsize=8.2, fontweight="bold")
        for i, l in enumerate(lines):
            ax.text(cx, y0 - step * (i + 1), l, ha="center", va="center", fontsize=8.5)

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9,
                                     linewidth=0.8, color=EDGE, shrinkA=0, shrinkB=0))

    ax.text(0.035, 0.955, "(a)", fontsize=10, fontweight="bold", va="center")
    # top row
    xs = [0.175, 0.50, 0.825]; yt = 0.84; w = 0.285; h = 0.115
    box(xs[0], yt, w, h, "Adult ICU stays \u226512 h", ["n = 172,392"])
    box(xs[1], yt, w, h, "First eligible ICU unit", ["n = 154,529"])
    box(xs[2], yt, w, h, "Reference creatinine available", ["n = 94,093"])
    arrow((xs[0] + w / 2, yt), (xs[1] - w / 2, yt))
    arrow((xs[1] + w / 2, yt), (xs[2] - w / 2, yt))
    # middle
    ym = 0.60; hm = 0.15
    box(0.50, ym, 0.30, hm, "Final landmark cohort", ["58,491 patients", "198 hospitals"], fill="#dfe8f1")
    # elbow from top-right box down and left to middle box
    ax.plot([xs[2], xs[2], 0.50 + 0.15 + 0.03], [yt - h / 2, ym, ym], color=EDGE, lw=0.8)
    arrow((0.50 + 0.15 + 0.03, ym), (0.50 + 0.15, ym))
    # bottom
    yb = 0.385; hb = 0.115
    box(0.27, yb, 0.30, hb, "Stage 2\u20133 outcome, >12\u201372 h", ["n = 3,032 (5.18%)"], fill="#fbeadb")
    box(0.73, yb, 0.30, hb, "No stage 2\u20133 outcome", ["n = 55,459 (94.82%)"])
    yj = (ym - hm / 2 + yb + hb / 2) / 2
    ax.plot([0.50, 0.50], [ym - hm / 2, yj], color=EDGE, lw=0.8)
    ax.plot([0.27, 0.73], [yj, yj], color=EDGE, lw=0.8)
    arrow((0.27, yj), (0.27, yb + hb / 2))
    arrow((0.73, yj), (0.73, yb + hb / 2))

    # (b) timeline, drawn to scale from -24 h to 72 h
    ax.text(0.035, 0.285, "(b)", fontsize=10, fontweight="bold", va="center")
    y = 0.135; x0, x1 = 0.09, 0.93
    pos = {t: x0 + (t + 24) / 96 * (x1 - x0) for t in (-24, 0, 6, 12, 72)}
    bh = 0.075
    ax.add_patch(Rectangle((pos[-24], y + 0.012), pos[6] - pos[-24], bh, facecolor="#dfe8f1", edgecolor="none"))
    ax.add_patch(Rectangle((pos[12], y + 0.012), pos[72] - pos[12], bh, facecolor="#fbeadb", edgecolor="none"))
    ax.text((pos[-24] + pos[6]) / 2, y + 0.012 + bh / 2, "Reference-creatinine\nsearch window*",
            ha="center", va="center", fontsize=7.6, linespacing=1.1)
    ax.text((pos[12] + pos[72]) / 2, y + 0.012 + bh / 2, "Outcome window: >12 to 72 h",
            ha="center", va="center", fontsize=7.8)
    ax.annotate("", xy=(x1 + 0.02, y), xytext=(x0 - 0.01, y),
                arrowprops=dict(arrowstyle="-|>", lw=1.0, color="#333333", mutation_scale=10))
    labels = {-24: ("−24 h", 1), 0: ("ICU admission\n(0 h)", 1), 6: ("+6 h", 2), 12: ("12 h", 1), 72: ("72 h", 1)}
    for t, x in pos.items():
        lab, lvl = labels[t]
        ax.plot([x, x], [y - 0.014, y + 0.014], color="#333333", lw=1.0)
        if lvl == 2:
            ax.plot([x, x], [y - 0.014, y - 0.055], color="#999999", lw=0.6)
        ax.text(x, y - 0.03 if lvl == 1 else y - 0.062, lab, ha="center", va="top", fontsize=7.8,
                fontweight="bold" if t == 12 else "normal", linespacing=1.1, color=ACCENT if t == 12 else "#111111")
    ax.plot([pos[12], pos[12]], [y + 0.012, y + 0.012 + bh + 0.012], color=ACCENT, lw=1.2)
    ax.text(pos[12], y + 0.012 + bh + 0.02, "12-h prediction landmark", ha="center", va="bottom", fontsize=7.8, color=ACCENT, fontweight="bold")
    ax.text(x1 + 0.02, y + 0.012 + bh + 0.02, "Time axis to scale (hours from ICU admission)", ha="right", va="bottom", fontsize=7, color="#555555")
    save(fig, "Figure_1")

# ------------------------------------------------------------------ Fig. 2
def fig2():
    d = pd.read_csv(PUB / "FIG_2_five_model_metrics_and_calibration.csv")
    c = pd.read_csv(PUB / "FIG_2_xgboost_calibration_deciles.csv")
    order = ["XGBoost", "CatBoost", "Random forest", "Logistic regression", "Clinical comparator"]
    d = d.set_index("model").loc[order].reset_index()
    y = np.arange(len(d))[::-1]
    cols = [ACCENT if m == "XGBoost" else BLUE for m in d.model]

    fig = plt.figure(figsize=(6.3, 5.2))
    axA = fig.add_axes([0.22, 0.60, 0.34, 0.33])
    axB = fig.add_axes([0.63, 0.60, 0.34, 0.33])
    axC = fig.add_axes([0.22, 0.09, 0.40, 0.38])

    for ax, m, lo, hi, lab, xlim, loc in [
        (axA, d.auroc, d.auroc_low, d.auroc_high, "AUROC (95% CI)", (0.795, 0.895), 0.02),
        (axB, d.auprc, d.auprc_low, d.auprc_high, "AUPRC (95% CI)", (0.23, 0.44), 0.05)]:
        ax.grid(axis="x", **GRID); ax.set_axisbelow(True)
        for yi, mi, l, h, col in zip(y, m, lo, hi, cols):
            ax.plot([l, h], [yi, yi], color=col, lw=1.2, solid_capstyle="butt")
            ax.plot([l, l], [yi - 0.15, yi + 0.15], color=col, lw=1.0)
            ax.plot([h, h], [yi - 0.15, yi + 0.15], color=col, lw=1.0)
            ax.plot(mi, yi, "o", color=col, ms=5, mec="white", mew=0.6)
            ax.text(h + (xlim[1] - xlim[0]) * 0.03, yi, f"{mi:.3f}", va="center", ha="left",
                    fontsize=7.5, color="#333333")
        ax.set_xlim(*xlim); ax.set_ylim(-0.6, len(d) - 0.4)
        ax.set_yticks(y); ax.set_xlabel(lab)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(loc))
        ax.tick_params(axis="y", length=0)
    axA.set_yticklabels(d.model)
    axB.set_yticklabels([])
    for ax in (axA, axB):
        ax.spines["left"].set_visible(False)

    # calibration
    axC.grid(**GRID); axC.set_axisbelow(True)
    axC.plot([0, 0.36], [0, 0.36], "--", color=GREY, lw=0.9, label="Ideal")
    axC.plot(c.mean_predicted_risk, c.observed_event_rate, "-", color=ACCENT, lw=1.1)
    axC.plot(c.mean_predicted_risk, c.observed_event_rate, "o", color=ACCENT, ms=4.5,
             mec="white", mew=0.6, label="XGBoost deciles")
    axC.set_xlim(0, 0.36); axC.set_ylim(0, 0.36); axC.set_aspect("equal")
    axC.set_xticks(np.arange(0, 0.36, 0.1)); axC.set_yticks(np.arange(0, 0.36, 0.1))
    axC.set_xlabel("Mean predicted risk"); axC.set_ylabel("Observed event rate")
    axC.legend(loc="upper left", frameon=False)
    # inset
    ins = fig.add_axes([0.70, 0.13, 0.26, 0.30])
    ins.grid(**GRID); ins.set_axisbelow(True)
    ins.plot([0, 0.08], [0, 0.08], "--", color=GREY, lw=0.8)
    cc = c[c.mean_predicted_risk < 0.08]
    ins.plot(cc.mean_predicted_risk, cc.observed_event_rate, "-", color=ACCENT, lw=1.0)
    ins.plot(cc.mean_predicted_risk, cc.observed_event_rate, "o", color=ACCENT, ms=4,
             mec="white", mew=0.5)
    ins.set_xlim(0, 0.08); ins.set_ylim(0, 0.08); ins.set_aspect("equal")
    ins.set_xticks([0, 0.02, 0.04, 0.06, 0.08]); ins.set_yticks([0, 0.02, 0.04, 0.06, 0.08])
    ins.tick_params(labelsize=7)
    ins.set_title("Deciles 1\u20139 (magnified)", fontsize=7.5, pad=3)
    for lab,(x,y) in {"(a)":(0.03,0.945),"(b)":(0.585,0.945),"(c)":(0.03,0.485)}.items():
        fig.text(x, y, lab, fontsize=10, fontweight="bold", va="bottom", ha="left")
    save(fig, "Figure_2")

# ------------------------------------------------------------------ Fig. 3
def fig3():
    d = pd.read_csv(PUB / "FIG_3_decision_curve.csv")
    s = pd.read_csv(PUB / "FIG_3_grouped_treeshap.csv").sort_values("pooled_rank")
    fig = plt.figure(figsize=(6.3, 6.4))
    axA = fig.add_axes([0.14, 0.615, 0.80, 0.33])
    axB = fig.add_axes([0.40, 0.07, 0.54, 0.42])

    axA.grid(**GRID); axA.set_axisbelow(True)
    axA.axhline(0, color="#333333", lw=0.9, ls=(0, (4, 2)), label="Treat none")
    axA.plot(d.threshold_percent, d.treat_all_net_benefit, color=LIGHT, lw=1.2, ls=":", label="Treat all")
    axA.plot(d.threshold_percent, d.clinical_comparator_net_benefit, "s--", color=BLUE, lw=1.1,
             ms=3.5, mec="white", mew=0.4, label="Clinical comparator")
    axA.plot(d.threshold_percent, d.xgboost_net_benefit, "o-", color=ACCENT, lw=1.4,
             ms=4, mec="white", mew=0.5, label="XGBoost")
    axA.set_xlim(0.6, 10.4); axA.set_ylim(-0.06, 0.05)
    axA.set_xticks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    axA.set_xlabel("Threshold probability (%)"); axA.set_ylabel("Net benefit")
    h, l = axA.get_legend_handles_labels()
    axA.legend(h[::-1], l[::-1], loc="lower left", frameon=False, ncol=2)

    ss = s.iloc[::-1].reset_index(drop=True)
    yy = np.arange(len(ss))
    cols = [ACCENT if r <= 3 else BLUE for r in ss.pooled_rank]
    axB.grid(axis="x", **GRID); axB.set_axisbelow(True)
    axB.barh(yy, ss.pooled_mean_absolute_grouped_shap, color=cols, height=0.68)
    for yi, v in zip(yy, ss.pooled_mean_absolute_grouped_shap):
        axB.text(v + 0.008, yi, f"{v:.3f}", va="center", ha="left", fontsize=7, color="#333333")
    axB.set_yticks(yy); axB.set_yticklabels(ss.display_label)
    axB.set_xlim(0, 0.58); axB.set_ylim(-0.7, len(ss) - 0.3)
    axB.set_xlabel("Mean absolute grouped TreeSHAP attribution")
    axB.tick_params(axis="y", length=0); axB.spines["left"].set_visible(False)
    for lab,(x,y) in {"(a)":(0.03,0.955),"(b)":(0.03,0.50)}.items():
        fig.text(x, y, lab, fontsize=10, fontweight="bold", va="bottom", ha="left")
    save(fig, "Figure_3")

fig1(); fig2(); fig3()
