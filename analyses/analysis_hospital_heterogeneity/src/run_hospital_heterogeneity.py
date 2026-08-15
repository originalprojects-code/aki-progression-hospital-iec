import os, sys, json, time, hashlib, platform
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.special import expit, logit
from scipy.stats import spearmanr
from google.cloud import bigquery
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2'); SEED=20260815
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_hospital_heterogeneity'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)
start=time.time(); c=bigquery.Client(project=PROJECT,location='US')
q=f'''SELECT m.id_row,m.group_hospital,m.label_stage23,m.outer_fold,m.x_age_years,m.x_stage1_at_landmark,
 p.prediction_platt,s.hospitalID
FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m
JOIN `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1` p USING(id_row,group_hospital,label_stage23,outer_fold)
JOIN `{PROJECT}.{DS}.feature_static_v1` s USING(id_row,group_hospital,label_stage23)'''
df=c.query(q).to_dataframe()
assert (len(df),df.id_row.nunique(),df.group_hospital.nunique(),int(df.label_stage23.sum()),int((df.label_stage23==0).sum()))==(58491,58491,198,3032,55459)
assert df.groupby('group_hospital').outer_fold.nunique().max()==1 and sorted(df.outer_fold.unique())==[1,2,3,4,5]

def calibration(y,p):
 y=np.asarray(y,float); x=logit(np.clip(np.asarray(p,float),1e-6,1-1e-6)); a=0.; b=1.; conv=False
 for _ in range(50):
  mu=expit(a+b*x); w=np.clip(mu*(1-mu),1e-10,None); s0=np.sum(y-mu);s1=np.sum((y-mu)*x)
  h00=np.sum(w);h01=np.sum(w*x);h11=np.sum(w*x*x);det=h00*h11-h01*h01
  if det<=1e-14: break
  da=(h11*s0-h01*s1)/det;db=(-h01*s0+h00*s1)/det;a+=da;b+=db
  if max(abs(da),abs(db))<1e-8: conv=True;break
 aa=0.; conv_i=False
 for _ in range(50):
  mu=expit(aa+x); den=np.sum(mu*(1-mu))
  if den<=1e-12: break
  da=np.sum(y-mu)/den;aa+=da
  if abs(da)<1e-8:conv_i=True;break
 unstable=(not conv) or (not conv_i) or abs(a)>10 or abs(b)>10
 return (a,b,aa,unstable)

def metrics(g):
 y=g.label_stage23.to_numpy(int);p=g.prediction_platt.to_numpy(float);n=len(g);ev=int(y.sum());ne=n-ev
 out={'n':n,'events':ev,'non_events':ne,'event_prevalence':ev/n,'mean_predicted_risk':p.mean(),'brier':brier_score_loss(y,p),'oe_ratio':(ev/n)/p.mean(),
      'mean_age':g.x_age_years.mean(),'stage1_prevalence':g.x_stage1_at_landmark.mean()}
 if ev and ne:
  a,b,ci,unstable=calibration(y,p);out.update({'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),'calibration_intercept':a,'calibration_slope':b,'calibration_in_the_large':ci,'calibration_unstable':unstable})
 else:
  out.update({k:np.nan for k in ['auroc','auprc','calibration_intercept','calibration_slope','calibration_in_the_large']});out['calibration_unstable']=True
 return out

rows=[]
for h,g in df.groupby('group_hospital'):
 r={'group_hospital':h,'hospitalID':int(g.hospitalID.iloc[0]),'outer_fold':int(g.outer_fold.iloc[0]),**metrics(g)}
 r['tier_b_eligible']=r['events']>=20 and r['non_events']>=20;r['tier_strict_eligible']=r['events']>=30 and r['non_events']>=30
 r['performance_estimate_status']='stable_reporting_tier' if r['tier_b_eligible'] else ('mathematically_available_but_unstable' if r['events']>0 and r['non_events']>0 else 'unavailable_single_class')
 rows.append(r)
hosp=pd.DataFrame(rows).sort_values('group_hospital').reset_index(drop=True)
hosp['hospital_label']=[f'Hospital {i:03d}' for i in range(1,len(hosp)+1)]

# Step 1 linkage: raw hospitalID, Step 3 linkage: hashed group_hospital.
ref_path=Path(os.environ.get('AKI_HOSPITAL_REFERENCE_SUMMARY', Path(__file__).resolve().parents[2]/'analysis_selection_bias'/'outputs'/'hospital_reference_availability.csv'))
mis_path=Path(os.environ.get('AKI_MISSINGNESS_HOSPITAL_SUMMARY', Path(__file__).resolve().parents[2]/'analysis_missingness_indicator_dependence'/'outputs'/'hospital_level_exploratory_summary.csv'))
ref=pd.read_csv(ref_path); mis=pd.read_csv(mis_path)
hosp=hosp.merge(ref[['hospitalID','candidate_n','reference_available_prop']],on='hospitalID',how='left',validate='one_to_one').merge(mis[['group_hospital','mean_indicator_source_missingness','missingness_attribution_fraction']],on='group_hospital',how='left',validate='one_to_one')
assert hosp.reference_available_prop.notna().sum()==198 and hosp.mean_indicator_source_missingness.notna().sum()==198

pubcols=['hospital_label','outer_fold','n','events','non_events','event_prevalence','mean_predicted_risk','brier','oe_ratio','auroc','auprc','calibration_intercept','calibration_slope','calibration_in_the_large','calibration_unstable','performance_estimate_status','tier_b_eligible','tier_strict_eligible']
hosp[['group_hospital','outer_fold','n','events','non_events','event_prevalence','mean_predicted_risk']].to_csv(OUT/'HOSPITAL_LEVEL_COHORT_SUMMARY.csv',index=False)
hosp.to_csv(OUT/'HOSPITAL_LEVEL_PERFORMANCE_FULL.csv',index=False)
tier=hosp[hosp.tier_b_eligible].copy(); strict=hosp[hosp.tier_strict_eligible].copy()
tier[pubcols].to_csv(OUT/'HOSPITAL_LEVEL_PERFORMANCE_TIER_B.csv',index=False)
# Confidential hospital identity mapping is intentionally not written in the public workflow.

metrics_list=['auroc','auprc','brier','calibration_intercept','calibration_slope','calibration_in_the_large','oe_ratio','event_prevalence','mean_predicted_risk']
def dist_rows(x,tier_name):
 out=[]
 for k in metrics_list:
  z=x[k].dropna(); qs=z.quantile([.1,.25,.5,.75,.9])
  out.append({'tier':tier_name,'metric':k,'n_hospitals':len(z),'min':z.min(),'p10':qs.loc[.1],'p25':qs.loc[.25],'median':qs.loc[.5],'p75':qs.loc[.75],'p90':qs.loc[.9],'max':z.max()})
 return out
dist=pd.DataFrame(dist_rows(tier,'Tier B: >=20 events and >=20 non-events')+dist_rows(strict,'Strict: >=30 events and >=30 non-events'))
bins=[]
for label,mask in [('<0.60',tier.auroc<.60),('<0.65',tier.auroc<.65),('<0.70',tier.auroc<.70),('<0.75',tier.auroc<.75),('>=0.80',tier.auroc>=.80)]:bins.append({'metric':'AUROC','category':label,'count':int(mask.sum()),'percentage':mask.mean()})
ab=tier.calibration_intercept.abs();
for label,mask in [('|intercept| <=0.10',ab<=.10),('|intercept| 0.10-0.25',(ab>.10)&(ab<=.25)),('|intercept| >0.25',ab>.25)]:bins.append({'metric':'calibration_intercept','category':label,'count':int(mask.sum()),'percentage':mask.mean()})
for label,mask in [('slope <0.75',tier.calibration_slope<.75),('slope 0.75-1.25',tier.calibration_slope.between(.75,1.25)),('slope >1.25',tier.calibration_slope>1.25)]:bins.append({'metric':'calibration_slope','category':label,'count':int(mask.sum()),'percentage':mask.mean()})
bins=pd.DataFrame(bins);dist.to_csv(OUT/'tables'/'TABLE_S17_distribution_summary.csv',index=False);bins.to_csv(OUT/'tables'/'TABLE_S17_descriptive_bins.csv',index=False)

tail=[]
for crit,col,asc in [('lowest_AUROC','auroc',True),('lowest_AUPRC','auprc',True),('largest_absolute_intercept','abs_intercept',False),('most_extreme_slope','slope_deviation',False)]:
 z=tier.copy();z['abs_intercept']=z.calibration_intercept.abs();z['slope_deviation']=(z.calibration_slope-1).abs()
 for rank,(_,r) in enumerate(z.sort_values(col,ascending=asc).head(5).iterrows(),1):tail.append({'audit_category':crit,'rank':rank,**r.to_dict()})
tail=pd.DataFrame(tail);tail.to_csv(OUT/'HOSPITAL_LEVEL_WORST_CASE_FULL.csv',index=False)
tail[['audit_category','rank']+pubcols].to_csv(OUT/'tables'/'TABLE_S18_hospital_worst_case_publication.csv',index=False)

fold=[]
for f,g in df.groupby('outer_fold'):fold.append({'outer_fold':int(f),'hospitals':g.group_hospital.nunique(),**metrics(g)})
fold=pd.DataFrame(fold);fold.to_csv(OUT/'outputs'/'OUTER_FOLD_CONTEXT.csv',index=False)

corr_specs=[('hospital_n','n','auroc'),('hospital_n','n','auprc'),('event_count','events','auroc'),('event_count','events','absolute_calibration_slope_deviation'),('event_prevalence','event_prevalence','auroc'),('event_prevalence','event_prevalence','auprc'),('event_prevalence','event_prevalence','calibration_intercept'),('event_prevalence','event_prevalence','mean_predicted_risk'),('reference_availability','reference_available_prop','auroc'),('reference_availability','reference_available_prop','auprc'),('reference_availability','reference_available_prop','calibration_intercept'),('reference_availability','reference_available_prop','brier'),('mean_missingness','mean_indicator_source_missingness','auroc'),('mean_missingness','mean_indicator_source_missingness','calibration_intercept'),('missingness_attribution','missingness_attribution_fraction','auroc'),('missingness_attribution','missingness_attribution_fraction','absolute_calibration_slope_deviation'),('case_mix_mean_age','mean_age','auroc'),('case_mix_stage1_prevalence','stage1_prevalence','auroc')]
tier['absolute_calibration_slope_deviation']=(tier.calibration_slope-1).abs();corr=[]
for domain,x,y in corr_specs:
 z=tier[[x,y]].dropna();rho,p=spearmanr(z[x],z[y]);corr.append({'domain':domain,'x':x,'y':y,'n_hospitals':len(z),'spearman_rho':rho,'p_value':p,'exploratory':True})
corr=pd.DataFrame(corr);corr.to_csv(OUT/'HOSPITAL_LEVEL_CORRELATIONS.csv',index=False)

# Descriptive pooled audit after removing the ten highest-AUROC Tier B hospitals.
top10=set(tier.nlargest(10,'auroc').group_hospital); reduced=df[~df.group_hospital.isin(top10)]; pooled_full=metrics(df); pooled_reduced=metrics(reduced)
robust=pd.DataFrame([{'analysis':'all_hospitals',**pooled_full},{'analysis':'exclude_10_highest_AUROC_Tier_B_hospitals',**pooled_reduced}]);robust.to_csv(OUT/'outputs'/'POOLED_HIGH_PERFORMER_REMOVAL_AUDIT.csv',index=False)

# Figure S12, anonymized publication-facing.
z=tier.sort_values('auroc').reset_index(drop=True);fig,ax=plt.subplots(1,3,figsize=(14,5.2))
ax[0].scatter(z.auroc,np.arange(len(z)),s=24,c='#4D4D4D');ax[0].axvline(pooled_full['auroc'],ls='--',c='black',lw=1,label='Pooled');ax[0].set(xlabel='AUROC',ylabel='Tier B hospitals (ordered)',title='A. Hospital discrimination');ax[0].legend(frameon=False);ax[0].grid(alpha=.2)
ax[1].boxplot([tier.calibration_intercept.dropna(),tier.calibration_slope.dropna()],tick_labels=['Intercept','Slope'],showfliers=True,patch_artist=True,boxprops={'facecolor':'#BDBDBD'});ax[1].axhline(0,c='black',ls=':',lw=1);ax[1].axhline(1,c='black',ls='--',lw=1);ax[1].set(title='B. Calibration distribution',ylabel='Estimate');ax[1].grid(alpha=.2)
ax[2].scatter(hosp.mean_predicted_risk,hosp.event_prevalence,s=np.clip(hosp.n/20,8,100),facecolors='none',edgecolors='#333333',alpha=.75);lim=max(hosp.mean_predicted_risk.max(),hosp.event_prevalence.max())*1.05;ax[2].plot([0,lim],[0,lim],ls='--',c='black',lw=1);ax[2].set(xlim=(0,lim),ylim=(0,lim),xlabel='Mean predicted risk',ylabel='Observed event prevalence',title='C. Hospital-level calibration context');ax[2].grid(alpha=.2)
fig.tight_layout();fig.savefig(OUT/'figures'/'FIG_S12_hospital_performance_heterogeneity.png',dpi=300,bbox_inches='tight');fig.savefig(OUT/'figures'/'FIG_S12_hospital_performance_heterogeneity.pdf',bbox_inches='tight');plt.close(fig)

def drow(k):return dist[(dist.tier.str.startswith('Tier B'))&(dist.metric==k)].iloc[0]
au=drow('auroc');ap=drow('auprc');ci=drow('calibration_intercept');sl=drow('calibration_slope');worst=tier.nsmallest(1,'auroc').iloc[0]
low70=int((tier.auroc<.70).sum()); interpretation='broadly stable' if au['median']>=.8 and low70/len(tier)<.1 else ('moderate heterogeneity' if au['median']>=.75 else 'strong heterogeneity')
report=f'''# Hospital-level worst-case performance and calibration audit

## Executive result

The audit found **{interpretation}** across held-out hospitals within eICU. Tier B contained **{len(tier)}** hospitals with at least 20 events and 20 non-events. Median hospital AUROC was **{au['median']:.3f}** (IQR {au['p25']:.3f}–{au['p75']:.3f}); P10 was {au['p10']:.3f} and the minimum was {au['min']:.3f}. {low70} hospitals ({100*low70/len(tier):.1f}%) had AUROC <0.70. Median AUPRC was {ap['median']:.3f} (IQR {ap['p25']:.3f}–{ap['p75']:.3f}).

## Calibration

Calibration intercept median was {ci['median']:.3f} (IQR {ci['p25']:.3f}–{ci['p75']:.3f}); slope median was {sl['median']:.3f} (IQR {sl['p25']:.3f}–{sl['p75']:.3f}). Counts in descriptive calibration ranges are in Table S17. Hospital calibration estimates were not used to recalibrate predictions.

## Lower tail and stricter sensitivity

The lowest Tier B AUROC was {worst.auroc:.3f} in {worst.hospital_label} (n={int(worst.n)}, events={int(worst.events)}). The stricter >=30-event/non-event subset contained {len(strict)} hospitals; its AUROC median was {strict.auroc.median():.3f} (IQR {strict.auroc.quantile(.25):.3f}–{strict.auroc.quantile(.75):.3f}), indicating whether the lower tail is chiefly small-sample noise should be judged from the paired Tier B/strict summaries rather than raw all-hospital extremes.

## Exploratory correlates

Spearman correlations with size, event prevalence, Step 1 reference-creatinine availability, Step 3 missingness measures, and two case-mix proxies are reported in `HOSPITAL_LEVEL_CORRELATIONS.csv`. They are exploratory and non-causal. AUPRC correlations require particular caution because AUPRC depends on prevalence.

## Pooled-performance concentration

After descriptively excluding the ten highest-AUROC Tier B hospitals, pooled AUROC was {pooled_reduced['auroc']:.3f} versus {pooled_full['auroc']:.3f} overall. This audit does not establish external validation or universal transportability; conclusions apply within the evaluated eICU hospital network.
'''
(OUT/'HOSPITAL_HETEROGENEITY_REPORT.md').write_text(report,encoding='utf-8')
insert=f'''# Candidate manuscript insertion (not applied)

## Methods
Hospital-specific performance was evaluated using each hospital's untouched outer-test predictions from the calibrated primary XGBoost model. Descriptive hospital distributions used a reporting tier requiring at least 20 events and 20 non-events; no hospital-specific fitting, recalibration, or threshold optimization was performed.

## Results
Among {len(tier)} Tier B hospitals, median AUROC was {au['median']:.3f} (IQR {au['p25']:.3f}–{au['p75']:.3f}; P10 {au['p10']:.3f}; minimum {au['min']:.3f}), and {low70} ({100*low70/len(tier):.1f}%) had AUROC <0.70. Median AUPRC was {ap['median']:.3f} (IQR {ap['p25']:.3f}–{ap['p75']:.3f}). Calibration intercept and slope medians were {ci['median']:.3f} and {sl['median']:.3f}, respectively, with between-hospital variation detailed in Table S17. The stricter >=30-event/non-event sensitivity included {len(strict)} hospitals and yielded median AUROC {strict.auroc.median():.3f}.

## Discussion
Hospital-disjoint performance was {interpretation}, but a lower-performing tail and calibration variation remained across held-out hospitals within eICU. These results refine internal-external robustness claims but do not constitute external validation, universal transportability, or deployment readiness.
'''
(OUT/'MANUSCRIPT_INSERT_HOSPITAL_HETEROGENEITY.md').write_text(insert,encoding='utf-8')
qc={'rows':len(df),'unique_patients':df.id_row.nunique(),'hospitals':df.group_hospital.nunique(),'events':int(df.label_stage23.sum()),'non_events':int((df.label_stage23==0).sum()),'outer_folds':sorted(df.outer_fold.unique().tolist()),'max_folds_per_hospital':int(df.groupby('group_hospital').outer_fold.nunique().max()),'prediction_source':f'{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1','no_refitting':True,'no_hospital_recalibration':True,'tier_b_rule':'>=20 events and >=20 non-events','tier_b_hospitals':len(tier),'strict_rule':'>=30 events and >=30 non-events','strict_hospitals':len(strict),'step1_matches':int(hosp.reference_available_prop.notna().sum()),'step3_matches':int(hosp.mean_indicator_source_missingness.notna().sum()),'calibration_unstable_all':int(hosp.calibration_unstable.sum()),'calibration_unstable_tier_b':int(tier.calibration_unstable.sum()),'runtime_minutes':(time.time()-start)/60,'python':platform.python_version()}
(OUT/'logs'/'qc.json').write_text(json.dumps(qc,indent=2),encoding='utf-8')
(OUT/'HOSPITAL_HETEROGENEITY_QC.md').write_text('# Hospital heterogeneity QC\n\n```json\n'+json.dumps(qc,indent=2)+'\n```\n\nAll critical cohort, fold exclusivity, held-out prediction, linkage, and no-refitting assertions passed. Hospital-level estimates are descriptive; individual-hospital confidence intervals were not added.\n',encoding='utf-8')
(OUT/'README.md').write_text('# Hospital-level performance heterogeneity audit\n\nRead-only analysis of held-out calibrated XGBoost predictions. Publication-facing outputs use anonymized hospital labels; raw ID mapping is reproducibility-only. No patient-level data are written.\n',encoding='utf-8')
print(json.dumps({'status':'complete','tier_b':len(tier),'strict':len(strict),'median_auroc':au['median'],'output':str(OUT)},indent=2))
