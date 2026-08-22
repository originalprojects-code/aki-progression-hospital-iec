
from __future__ import annotations

from pathlib import Path
import argparse, json, math, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "figures_A25_rebuilt"
PUB = ROOT / "aggregate_outputs" / "publication_figures"

# ---------- typography ----------
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/opentype/urw-base35/NimbusSans-Bold.otf",
]

def first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None

REGULAR = first_existing(FONT_CANDIDATES)
BOLD = first_existing(FONT_BOLD_CANDIDATES)
if REGULAR:
    font_manager.fontManager.addfont(REGULAR)
    FAMILY = font_manager.FontProperties(fname=REGULAR).get_name()
else:
    FAMILY = "DejaVu Sans"
if BOLD:
    font_manager.fontManager.addfont(BOLD)

plt.rcParams.update({
    "font.family": FAMILY,
    "font.size": 10,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

def save(fig, outdir: Path, stem: str):
    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"{stem}.png"
    pdf = outdir / f"{stem}.pdf"
    fig.savefig(png, dpi=600, facecolor="white")
    fig.savefig(pdf, facecolor="white")
    plt.close(fig)
    return str(png), str(pdf)

def panel_label(ax, text):
    ax.text(0, 1.035, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=11, fontweight="bold", clip_on=False)

# ============================================================
# Fig. 1
# ============================================================
def build_fig1(outdir):
    fig=plt.figure(figsize=(11.52,8.22))
    ax=fig.add_axes([0,0,1,1]); ax.set_axis_off()
    def box(x,y,w,h,lines,fs=10):
        r=Rectangle((x,y),w,h,fill=False,linewidth=0.9,transform=ax.transAxes)
        ax.add_patch(r)
        ax.text(x+w/2,y+h/2,"\n".join(lines),ha="center",va="center",transform=ax.transAxes,fontsize=fs,linespacing=.95)
    ax.text(.045,.945,"(a)",fontsize=11,fontweight="bold",transform=ax.transAxes)
    box(.055,.775,.22,.10,["Adult ICU stays ≥12 h","172,392"])
    box(.36,.775,.22,.10,["First eligible ICU unit","154,529"])
    box(.665,.775,.22,.10,["Reference creatinine","available","94,093"])
    box(.36,.56,.22,.11,["Final landmark cohort","58,491 patients","198 hospitals"])
    box(.115,.36,.22,.10,["Stage 2–3 outcome","3,032 (5.18%)"])
    box(.605,.36,.22,.10,["No stage 2–3 outcome","55,459 (94.82%)"])
    for a0,b0 in [((.278,.825),(.358,.825)),((.582,.825),(.663,.825)),((.775,.775),(.472,.67)),((.47,.56),(.225,.46)),((.47,.56),(.715,.46))]:
        ax.add_patch(FancyArrowPatch(a0,b0,arrowstyle="->",mutation_scale=10,linewidth=.9,transform=ax.transAxes))
    ax.text(.045,.295,"(b)",fontsize=11,fontweight="bold",transform=ax.transAxes)
    y=.205
    ax.plot([.083,.858],[y,y],lw=1.0,transform=ax.transAxes)
    ticks=[(.102,"−24 h","tab:orange"),(.214,"ICU\nadmission","tab:green"),(.405,"+6 h","tab:red"),(.568,"12-h\nlandmark","tab:purple"),(.829,"72 h","tab:brown")]
    for x,t,c in ticks:
        ax.plot([x,x],[y-.016,y+.016],lw=1.1,color=c,transform=ax.transAxes)
        ax.text(x,y-.04,t,ha="center",va="top",transform=ax.transAxes,fontsize=9)
    ax.add_patch(FancyArrowPatch((.108,.08),(.40,.08),arrowstyle="<->",mutation_scale=9,linewidth=.9,transform=ax.transAxes))
    ax.text(.254,.043,"Reference-creatinine search window*",ha="center",va="center",transform=ax.transAxes,fontsize=9)
    ax.add_patch(FancyArrowPatch((.573,.08),(.825,.08),arrowstyle="<->",mutation_scale=9,linewidth=.9,transform=ax.transAxes))
    ax.text(.699,.043,"Outcome window: >12 to 72 h",ha="center",va="center",transform=ax.transAxes,fontsize=9)
    return save(fig,outdir,"FIG_1_A25")

# ============================================================
# Fig. 2 / Fig. 3 / Fig. S4 exact source guards
# ============================================================
def missing_source(name, expected):
    raise FileNotFoundError(
        f"{name} exact A25 build source is not yet repository-contained. "
        f"Required publication-safe source: {expected}"
    )

def build_fig2(outdir):
    d=pd.read_csv(PUB/"FIG_2_five_model_metrics_and_calibration.csv")
    c=pd.read_csv(PUB/"FIG_2_xgboost_calibration_deciles.csv")
    labels=d["model"].tolist()
    y=np.arange(len(d))[::-1]

    fig=plt.figure(figsize=(6.85,6.0))
    axA=fig.add_axes([.205,.595,.355,.31])
    axB=fig.add_axes([.61,.595,.355,.31])
    axC=fig.add_axes([.39,.11,.365,.30])

    axA.errorbar(d.auroc,y,xerr=[d.auroc-d.auroc_low,d.auroc_high-d.auroc],
                 fmt="o",markersize=5.2,capsize=3,elinewidth=1.0,capthick=1.0,
                 color="tab:blue")
    axA.set_yticks(y); axA.set_yticklabels(labels)
    axA.set_xlabel("AUROC (95% CI)")
    axA.set_xlim(.798,.886)
    axA.xaxis.set_major_locator(ticker.MultipleLocator(.02))
    axA.grid(axis="x",alpha=.18,linewidth=.6); axA.set_axisbelow(True)

    axB.errorbar(d.auprc,y,xerr=[d.auprc-d.auprc_low,d.auprc_high-d.auprc],
                 fmt="o",markersize=5.2,capsize=3,elinewidth=1.0,capthick=1.0,
                 color="tab:blue")
    axB.set_yticks(y); axB.set_yticklabels([]); axB.tick_params(axis='y',length=0)
    axB.set_xlabel("AUPRC (95% CI)")
    axB.set_xlim(.238,.43)
    axB.xaxis.set_major_locator(ticker.MultipleLocator(.05))
    axB.grid(axis="x",alpha=.18,linewidth=.6); axB.set_axisbelow(True)

    upper=.35
    axC.plot([0,upper],[0,upper],"--",linewidth=1.05,label="Ideal")
    axC.plot(c.mean_predicted_risk,c.observed_event_rate,"-o",linewidth=1.15,
             markersize=4.2,label="XGBoost deciles")
    axC.set_xlim(0,.36); axC.set_ylim(0,.36)
    axC.set_xlabel("Mean predicted risk"); axC.set_ylabel("Observed event rate")
    axC.set_xticks([0,.10,.20,.30,.35])
    axC.set_yticks(np.arange(0,.36,.05))
    axC.grid(alpha=.18,linewidth=.6); axC.set_axisbelow(True)
    axC.legend(loc="lower right",frameon=True)

    for ax,l in [(axA,"(a)"),(axB,"(b)"),(axC,"(c)")]: panel_label(ax,l)
    return save(fig,outdir,"FIG_2_A25")

def build_fig3(outdir):
    d=pd.read_csv(PUB/"FIG_3_decision_curve.csv")
    s=pd.read_csv(PUB/"FIG_3_grouped_treeshap.csv").sort_values("pooled_rank")

    fig=plt.figure(figsize=(6.85,7.10))
    axA=fig.add_axes([.33,.565,.50,.325])
    axB=fig.add_axes([.33,.095,.50,.385])

    axA.plot(d.threshold_percent,d.xgboost_net_benefit,"-o",markersize=4.2,
             linewidth=1.15,label="XGBoost")
    axA.plot(d.threshold_percent,d.clinical_comparator_net_benefit,"--s",markersize=3.7,
             linewidth=1.05,label="Clinical comparator")
    axA.plot(d.threshold_percent,d.treat_all_net_benefit,":",linewidth=1.1,label="Treat all")
    axA.plot(d.threshold_percent,d.treat_none_net_benefit,"-.",linewidth=1.05,label="Treat none")
    axA.set_xlim(.55,10.45); axA.set_ylim(-.06,.05)
    axA.set_xticks([1,2,4,6,8,10])
    axA.set_xlabel("Threshold probability (%)"); axA.set_ylabel("Net benefit")
    axA.grid(alpha=.18,linewidth=.6); axA.set_axisbelow(True)
    axA.legend(loc="lower left",frameon=False)

    ss=s.iloc[::-1].reset_index(drop=True)
    yy=np.arange(len(ss))
    axB.barh(yy,ss.pooled_mean_absolute_grouped_shap,
             edgecolor="black",linewidth=.55,hatch="//")
    axB.set_yticks(yy); axB.set_yticklabels(ss.display_label)
    axB.set_xlim(0,.53)
    axB.set_xlabel("Mean absolute grouped TreeSHAP attribution")
    axB.set_ylabel("Source predictor",labelpad=32)
    axB.grid(axis="x",alpha=.18,linewidth=.6); axB.set_axisbelow(True)

    panel_label(axA,"(a)"); panel_label(axB,"(b)")
    return save(fig,outdir,"FIG_3_A25")

# ============================================================
# Supplementary figures
# ============================================================
def build_s1(outdir):
    p=ROOT/"analyses/analysis_renal_trajectory_comparator/outputs/fold_performance.csv"
    d=pd.read_csv(p); d=d[d.model=="Full XGBoost"].sort_values("outer_fold")
    fig=plt.figure(figsize=(6.85,3.75)); ax=fig.add_axes([.27,.19,.68,.68])
    ax.plot(d.outer_fold,d.auroc,"-o",label="AUROC"); ax.plot(d.outer_fold,d.auprc,"-o",label="AUPRC")
    for x,y in zip(d.outer_fold,d.auroc): ax.text(x,y+.020,f"{y:.3f}",ha="center",va="bottom",fontsize=9)
    for x,y in zip(d.outer_fold,d.auprc): ax.text(x,y-.028,f"{y:.3f}",ha="center",va="top",fontsize=9)
    ax.set_xlabel("Hospital-disjoint outer fold"); ax.set_ylabel("Performance")
    ax.set_xticks(d.outer_fold); ax.set_ylim(.24,.96); ax.grid(alpha=.18); ax.legend(loc="center right",frameon=False)
    return save(fig,outdir,"FIG_S1_A25")

def build_s2(outdir):
    d=pd.read_csv(PUB/"FIG_S2_tier_b_calibration_points.csv")
    x=100*d.mean_predicted_risk; y=100*d.event_rate
    fig=plt.figure(figsize=(6.85,4.15)); ax=fig.add_axes([.27,.15,.54,.78])
    ax.scatter(x,y,s=35,edgecolors="black",linewidths=.55,alpha=.8)
    ax.plot([0,12],[0,12],"--",label="Ideal calibration")
    ax.set_xlim(0,12); ax.set_ylim(0,12); ax.set_aspect("equal",adjustable="box")
    ax.set_xlabel("Mean predicted risk (%)"); ax.set_ylabel("Observed event rate (%)")
    ax.set_xticks(np.arange(0,13,2)); ax.set_yticks(np.arange(0,13,2))
    ax.grid(alpha=.18); ax.legend(loc="lower right",frameon=False)
    return save(fig,outdir,"FIG_S2_A25")

def build_s3(outdir):
    d=pd.read_csv(PUB/"FIG_S3_operating_points_full.csv")
    x=100*d.threshold
    fig,ax=plt.subplots(figsize=(8,5.5))
    ax.plot(x,d.sensitivity,"-o",label="Sensitivity")
    ax.plot(x,d.specificity,"-o",label="Specificity")
    ax.plot(x,d.ppv,"-o",label="PPV")
    ax.set_xlabel("Prespecified probability threshold (%)"); ax.set_ylabel("Metric value")
    ax.set_xticks(x); ax.set_xticklabels([f"{v:g}" for v in x]); ax.set_ylim(0,1.02)
    ax.grid(alpha=.18); ax.legend(loc="lower right",frameon=False); fig.tight_layout()
    return save(fig,outdir,"FIG_S3_A25")

def build_s4(outdir):
    d=pd.read_csv(PUB/"FIG_S4_reference_creatinine_sensitivity.csv")
    fig=plt.figure(figsize=(6.85,4.25)); ax=fig.add_axes([.23,.20,.69,.70])
    x=np.arange(len(d)); ax.bar(x,100*d.event_rate,edgecolor="black",linewidth=.55)
    ax.set_xticks(x); ax.set_xticklabels(d.phenotype,rotation=15,ha="right")
    ax.set_ylabel("Stage 2–3 event rate (%)"); ax.set_xlabel("Reference-creatinine sensitivity phenotype")
    ax.set_ylim(0,6.35)
    for i,r in d.iterrows():
        ax.text(i,100*r.event_rate+.12,f"{100*r.event_rate:.2f}%\ncoverage {100*r.coverage:.1f}%",ha="center",va="bottom",fontsize=9)
    ax.grid(axis="y",alpha=.18); ax.set_axisbelow(True)
    return save(fig,outdir,"FIG_S4_A25")

def build_s5(outdir):
    d=pd.read_csv(ROOT/"analyses/analysis_selection_bias/outputs/cohort_group_counts.csv")
    group_col="exclusion_detail"; n_col="patients"
    order=["included_main","no_reference_creatinine","no_future_creatinine","inadequate_followup","early_death","chronic_dialysis_or_esrd","severe_aki_by_12h","acute_rrt_by_12h"]
    d=d.set_index(group_col).loc[order].reset_index()
    fig=plt.figure(figsize=(6.85,4.65)); ax=fig.add_axes([.37,.12,.58,.78])
    y=np.arange(len(d))[::-1]; ax.barh(y,d[n_col],edgecolor="black",linewidth=.55)
    ax.set_yticks(y); ax.set_yticklabels(d[group_col]); ax.set_xlabel("Patients")
    ax.set_ylabel("Cohort inclusion/exclusion group",labelpad=32)
    for yy,n in zip(y,d[n_col]): ax.text(n+700,yy,f"{int(n):,}",va="center",fontsize=9)
    ax.set_xlim(0,68000); ax.xaxis.set_major_locator(ticker.MultipleLocator(10000)); ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.grid(axis="x",alpha=.18); ax.set_axisbelow(True)
    return save(fig,outdir,"FIG_S5_A25")

def build_s6(outdir):
    raw=pd.read_csv(ROOT/"analyses/analysis_selection_bias/outputs/ranked_absolute_smds.csv")
    pv=raw.pivot(index="characteristic",columns="comparison",values="abs_smd")
    pv=pv.rename(columns={"Final vs no reference":"no_ref","Final vs other excluded":"other"})
    locked_order=[
        "Invasive mechanical ventilation by 12 h",
        "ICU admission source (maximum category-wise)",
        "Last heart rate by 12 h, beats/min",
        "Any vasopressor infusion by 12 h",
        "Hospital admission source (maximum category-wise)",
        "Last blood urea nitrogen by 12 h, mg/dL",
        "ICU type (maximum category-wise)",
        "Last systolic blood pressure by 12 h, mmHg",
        "Race/ethnicity (maximum category-wise)",
        "Age, years",
        "Last respiratory rate by 12 h, breaths/min",
        "Body mass index, kg/mÂ²",
        "Sex (maximum category-wise)",
    ]
    pv=pv.loc[locked_order]
    labels=[str(x).replace("kg/mÂ²","kg/m²") for x in pv.index]
    y=np.arange(len(pv))[::-1]
    fig=plt.figure(figsize=(7.5,5.85)); ax=fig.add_axes([.42,.12,.52,.72])
    ax.scatter(pv.no_ref,y,facecolors="white",edgecolors="black",label="Final vs no reference")
    ax.scatter(pv.other,y,marker="s",facecolors="white",edgecolors="black",label="Final vs other excluded")
    ax.axvline(.10,color="tab:blue",linestyle=(0,(7,3)),label="SMD = 0.10")
    ax.axvline(.20,color="tab:orange",linestyle="-.",label="SMD = 0.20")
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("Absolute standardized mean difference")
    ax.set_ylabel("Baseline or early-ICU characteristic",labelpad=42)
    ax.set_xlim(-.005,.405); ax.grid(axis="x",alpha=.18)
    ax.legend(loc="lower center",bbox_to_anchor=(.5,1.04),ncol=2,frameon=False)
    return save(fig,outdir,"FIG_S6_A25")

def build_s7(outdir):
    base=ROOT/"analyses/analysis_missingness_indicator_dependence/outputs"
    fold=pd.read_csv(base/"fold_level_attribution_summary.csv")
    af=pd.read_csv(base/"fold_indicator_importance_and_ranks.csv")
    N=int(fold["n"].sum())
    pool=(af.groupby("source_predictor",as_index=False)
          .agg(sum_abs_indicator_shap=("sum_abs_indicator_shap","sum"),
               sum_abs_value_shap=("sum_abs_value_shap","sum")))
    pool["mean_abs_indicator_shap"]=pool.sum_abs_indicator_shap/N
    pool["mean_abs_value_shap"]=pool.sum_abs_value_shap/N
    pool=pool.sort_values("mean_abs_indicator_shap",ascending=False).reset_index(drop=True)
    global_fraction=fold.sum_abs_indicator.sum()/fold.sum_abs_all.sum()

    fig=plt.figure(figsize=(7.5,10))
    axA=fig.add_axes([.18,.705,.72,.215]); axB=fig.add_axes([.39,.385,.51,.235]); axC=fig.add_axes([.39,.075,.51,.235])
    labels=["Overall"]+[f"Fold {int(x)}" for x in fold.outer_fold]
    vals=[100*global_fraction]+list(100*fold.missingness_attribution_fraction)
    xx=np.arange(len(labels)); axA.bar(xx,vals,width=.66,edgecolor="black",linewidth=.55)
    axA.set_xticks(xx); axA.set_xticklabels(labels); axA.set_ylabel("Absolute SHAP from indicators (%)"); axA.set_xlabel("Held-out evaluation set")
    axA.grid(axis="y",alpha=.18)
    b=pool.head(12).sort_values("mean_abs_indicator_shap"); yy=np.arange(len(b))
    axB.barh(yy,b.mean_abs_indicator_shap,edgecolor="black",linewidth=.55)
    axB.set_yticks(yy); axB.set_yticklabels(b.source_predictor.str.replace("x_","",regex=False)); axB.set_xlabel("Mean |SHAP|"); axB.set_ylabel("Source predictor",labelpad=12); axB.grid(axis="x",alpha=.18)
    c=pool.head(10).sort_values("mean_abs_indicator_shap"); yy=np.arange(len(c))
    axC.barh(yy,c.mean_abs_value_shap,edgecolor="black",linewidth=.45,label="Observed value")
    axC.barh(yy,c.mean_abs_indicator_shap,left=c.mean_abs_value_shap,edgecolor="black",linewidth=.45,hatch="///",label="Missingness indicator")
    axC.set_yticks(yy); axC.set_yticklabels(c.source_predictor.str.replace("x_","",regex=False)); axC.set_xlabel("Mean |SHAP|"); axC.set_ylabel("Source predictor",labelpad=12)
    axC.grid(axis="x",alpha=.18); axC.legend(loc="upper right",frameon=False,ncol=1)
    for ax,l in [(axA,"(a)"),(axB,"(b)"),(axC,"(c)")]: panel_label(ax,l)
    return save(fig,outdir,"FIG_S7_A25")

def build_s8(outdir):
    base=ROOT/"analyses/analysis_renal_trajectory_comparator/outputs"
    curves=pd.read_csv(base/"roc_pr_curve_data.csv"); dca=pd.read_csv(base/"decision_curve_data.csv")
    prev=3032/58491
    fig=plt.figure(figsize=(7.5,9.6)); axA=fig.add_axes([.24,.69,.52,.23]); axB=fig.add_axes([.24,.38,.52,.23]); axC=fig.add_axes([.24,.075,.52,.23])
    styles={"Full XGBoost":dict(color="black",ls="-",lw=1.35),"Comparator 2: creatinine trajectory":dict(color="tab:blue",ls="--",lw=1.25)}
    for m,st in styles.items():
        z=curves[(curves.curve=="ROC")&(curves.model==m)]; axA.plot(z.x,z.y,label="Creatinine trajectory" if m.startswith("Comparator") else m,**st)
    axA.plot([0,1],[0,1],color=".7",ls=":",lw=1,label="Chance"); axA.set(xlim=(0,1),ylim=(0,1.02),xlabel="1 - specificity",ylabel="Sensitivity"); axA.legend(loc="lower right",frameon=False); axA.grid(alpha=.18)
    for m,st in styles.items():
        z=curves[(curves.curve=="PR")&(curves.model==m)]; axB.plot(z.x,z.y,label="Creatinine trajectory" if m.startswith("Comparator") else m,**st)
    axB.axhline(prev,color=".7",ls=":",lw=1,label="Outcome prevalence"); axB.set(xlim=(0,1),ylim=(0,1.02),xlabel="Recall",ylabel="Precision"); axB.legend(loc="upper right",frameon=False); axB.grid(alpha=.18)
    dstyles={"Full XGBoost":dict(color="black",ls="-",lw=1.35),"Comparator 2: creatinine trajectory":dict(color="tab:blue",ls="--",lw=1.25),"Treat all":dict(color="tab:orange",ls=":",lw=1.25),"Treat none":dict(color=".25",ls="-.",lw=1.15)}
    for m,st in dstyles.items():
        z=dca[dca.model==m]; axC.plot(100*z.threshold,z.net_benefit,label="Creatinine trajectory" if m.startswith("Comparator") else m,**st)
    axC.set_xlim(.75,10.25); axC.set_xticks([1,2,4,6,8,10]); axC.set_xlabel("Threshold probability (%)"); axC.set_ylabel("Net benefit"); axC.legend(loc="lower left",frameon=False); axC.grid(alpha=.18)
    for ax,l in [(axA,"(a)"),(axB,"(b)"),(axC,"(c)")]: panel_label(ax,l)
    return save(fig,outdir,"FIG_S8_A25")

def build_s9(outdir):
    q=pd.read_csv(ROOT/"analyses/analysis_subgroup_fairness/outputs/subgroup_calibration_quintiles.csv")
    fig=plt.figure(figsize=(7.5,9.7)); axes=[fig.add_axes([.22,.69,.56,.23]),fig.add_axes([.22,.38,.56,.23]),fig.add_axes([.22,.075,.56,.23])]
    for ax,dom,lab in zip(axes,["Sex","Age","Recorded race/ethnicity"],["(a)","(b)","(c)"]):
        z=q[q.domain==dom]; ax.plot([0,.35],[0,.35],"--",color=".6",lw=1,label="Ideal")
        for sg,g in z.groupby("subgroup",sort=False):
            g=g.sort_values("quintile"); ax.plot(g.mean_predicted,g.observed,"-o",lw=1.15,ms=3.6,label=sg)
        ax.set_xlim(0,.35); ax.set_ylim(0,.35); ax.set_xlabel("Mean predicted risk"); ax.set_ylabel("Observed event rate")
        ax.grid(alpha=.18); ax.legend(loc="upper left",frameon=False,ncol=2 if dom=="Recorded race/ethnicity" else 1); panel_label(ax,lab)
    return save(fig,outdir,"FIG_S9_A25")

def build_s10(outdir):
    df=pd.read_csv(ROOT/"analyses/analysis_subgroup_fairness/outputs/subgroup_performance_with_cluster_ci.csv")
    d=df[df.stable_for_metrics==True].copy()
    order=[("Sex","female"),("Sex","male"),("Age","<50"),("Age","50-64"),("Age","65-79"),("Age",">=80"),
           ("Recorded race/ethnicity","Caucasian"),("Recorded race/ethnicity","African American"),("Recorded race/ethnicity","Other/Unknown"),
           ("Recorded race/ethnicity","Hispanic"),("Recorded race/ethnicity","Asian"),("Recorded race/ethnicity","Native American"),("Recorded race/ethnicity","Missing")]
    key={(r.domain,r.subgroup):r for _,r in d.iterrows()}; rows=[key[k] for k in order]
    labels=[f"{r.domain} - {r.subgroup}" for r in rows]; y=np.arange(len(rows))[::-1]
    fig=plt.figure(figsize=(7.5,9.1)); axA=fig.add_axes([.42,.55,.50,.36]); axB=fig.add_axes([.42,.09,.50,.36])
    au=np.array([r.auroc for r in rows]); lo=np.array([r.auroc_ci_low for r in rows]); hi=np.array([r.auroc_ci_high for r in rows])
    axA.errorbar(au,y,xerr=[au-lo,hi-au],fmt="o",capsize=3,color="tab:blue"); axA.set_yticks(y); axA.set_yticklabels(labels); axA.set_xlabel("AUROC"); axA.set_ylabel("Subgroup",labelpad=12); axA.grid(axis="x",alpha=.18)
    ap=np.array([r.auprc for r in rows]); lo=np.array([r.auprc_ci_low for r in rows]); hi=np.array([r.auprc_ci_high for r in rows]); prev=np.array([r.prevalence for r in rows])
    axB.errorbar(ap,y,xerr=[ap-lo,hi-ap],fmt="o",capsize=3,color="tab:orange"); axB.set_yticks(y); axB.set_yticklabels(labels); axB.set_xlabel("AUPRC"); axB.set_ylabel("Subgroup",labelpad=12); axB.grid(axis="x",alpha=.18)
    xtext=.705
    for yy,p in zip(y,prev): axB.text(xtext,yy,f"{100*p:.1f}%",va="center",ha="left",fontsize=9,clip_on=False)
    fig.text(.985,.27,"Outcome prevalence",rotation=90,va="center",ha="center",fontsize=10)
    panel_label(axA,"(a)"); panel_label(axB,"(b)")
    return save(fig,outdir,"FIG_S10_A25")

def build_s11(outdir):
    hist=pd.read_csv(PUB/"FIG_S11_event_time_histogram.csv").sort_values("bin_index")
    lead=pd.read_csv(ROOT/"tables/TABLE_S15_source.csv"); lead=lead[lead.analysis_type=="lead"].copy()
    order=["L0","L6","L12","L24"]; lead["scenario"]=pd.Categorical(lead.scenario,categories=order,ordered=True); lead=lead.sort_values("scenario")
    fig=plt.figure(figsize=(7.5,9.5)); axA=fig.add_axes([.23,.69,.54,.23]); axB=fig.add_axes([.23,.38,.54,.23]); axC=fig.add_axes([.23,.075,.54,.23])
    centers=(hist.start_hour+hist.end_hour)/2; axA.bar(centers,hist.n_events,width=3.6,edgecolor="black",linewidth=.55); axA.set_xlim(11.5,72.5); axA.set_xlabel("First stage 2–3 event (h)"); axA.set_ylabel("Events"); axA.grid(axis="y",alpha=.18)
    x=np.arange(len(lead)); au=lead.auroc.to_numpy(); lo=lead.auroc_ci_low.to_numpy(); hi=lead.auroc_ci_high.to_numpy()
    axB.errorbar(x,au,yerr=[au-lo,hi-au],fmt="o-",capsize=4,color="tab:blue"); axB.set_xticks(x); axB.set_xticklabels(order); axB.set_xlabel("Minimum lead-time scenario"); axB.set_ylabel("AUROC"); axB.grid(alpha=.18)
    ap=lead.auprc.to_numpy(); lo=lead.auprc_ci_low.to_numpy(); hi=lead.auprc_ci_high.to_numpy()
    axC.errorbar(x,ap,yerr=[ap-lo,hi-ap],fmt="o-",capsize=4,color="tab:orange"); axC.set_xticks(x); axC.set_xticklabels(order); axC.set_xlabel("Minimum lead-time scenario"); axC.set_ylabel("AUPRC"); axC.grid(alpha=.18)
    for ax,l in [(axA,"(a)"),(axB,"(b)"),(axC,"(c)")]: panel_label(ax,l)
    return save(fig,outdir,"FIG_S11_A25")

def build_s12(outdir):
    au=pd.read_csv(PUB/"FIG_S12_tier_b_auroc.csv").auroc.sort_values().to_numpy()
    cal=pd.read_csv(PUB/"FIG_S12_tier_b_calibration.csv")
    ctx=pd.read_csv(PUB/"FIG_S12_all_hospital_calibration_context.csv")
    pooled=float(pd.read_csv(ROOT/"tables/TABLE_S15_source.csv").query("scenario=='L0' and analysis_type=='lead'").auroc.iloc[0])
    fig=plt.figure(figsize=(7.5,9.7)); axA=fig.add_axes([.22,.69,.56,.23]); axB=fig.add_axes([.22,.38,.56,.23]); axC=fig.add_axes([.22,.075,.56,.23])
    y=np.arange(1,len(au)+1); axA.scatter(au,y,s=26,edgecolors="black",linewidths=.45); axA.axvline(pooled,linestyle=(0,(7,3)),label=f"Pooled AUROC = {pooled:.3f}"); axA.set_xlabel("AUROC"); axA.set_ylabel("Tier-B hospitals (ordered)"); axA.grid(alpha=.18); axA.legend(loc="upper left",frameon=False)
    bp=axB.boxplot([cal.calibration_intercept,cal.calibration_slope],tick_labels=["Intercept","Slope"],widths=.45,patch_artist=True,showfliers=True)
    for patch in bp["boxes"]: patch.set_alpha(.35)
    axB.axhline(0,color=".45",linestyle=":"); axB.axhline(1,linestyle=(0,(7,3))); axB.set_ylabel("Calibration estimate"); axB.set_xlabel("Calibration parameter"); axB.grid(axis="y",alpha=.18)
    axB.legend(handles=[Line2D([0],[0],color=".45",linestyle=":",label="Ideal intercept = 0"),Line2D([0],[0],linestyle=(0,(7,3)),label="Ideal slope = 1")],loc="lower right",frameon=False)
    x=ctx.mean_predicted_risk.to_numpy(); y=ctx.event_rate.to_numpy(); upper=max(.7,math.ceil((max(x.max(),y.max())+.015)*10)/10)
    axC.scatter(x,y,s=20,facecolors="white",edgecolors="black",linewidths=.55,alpha=.72); axC.plot([0,upper],[0,upper],linestyle=(0,(7,3)),label="Ideal calibration")
    axC.set_xlim(0,upper); axC.set_ylim(0,upper); axC.set_aspect("equal",adjustable="box"); axC.set_xlabel("Mean predicted risk"); axC.set_ylabel("Observed event prevalence"); axC.grid(alpha=.18); axC.legend(loc="lower right",frameon=False)
    for ax,l in [(axA,"(a)"),(axB,"(b)"),(axC,"(c)")]: panel_label(ax,l)
    return save(fig,outdir,"FIG_S12_A25")

BUILDERS = {
    "1":build_fig1, "2":build_fig2, "3":build_fig3,
    "S1":build_s1, "S2":build_s2, "S3":build_s3, "S4":build_s4,
    "S5":build_s5, "S6":build_s6, "S7":build_s7, "S8":build_s8,
    "S9":build_s9, "S10":build_s10, "S11":build_s11, "S12":build_s12,
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",type=Path,default=OUT_DEFAULT)
    ap.add_argument("--figures",nargs="*",default=list(BUILDERS))
    ap.add_argument("--allow-missing",action="store_true")
    args=ap.parse_args()
    report={"font_family":FAMILY,"built":{},"missing":{}}
    for key in args.figures:
        try:
            paths=BUILDERS[key](args.outdir)
            report["built"][key]=paths
            print(f"PASS Fig. {key}: {paths[0]}")
        except FileNotFoundError as e:
            report["missing"][key]=str(e)
            print(f"MISSING Fig. {key}: {e}",file=sys.stderr)
            if not args.allow_missing:
                (args.outdir/"BUILD_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
                raise
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/"BUILD_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
