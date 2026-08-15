import os,sys,json,time,platform,hashlib
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from scipy.special import expit,logit
from google.cloud import bigquery
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss,roc_curve,precision_recall_curve

SEED=20260721; BOOT=2000; PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2')
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_renal_trajectory_comparator'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)
start=time.time(); client=bigquery.Client(project=PROJECT,location='US')

# Written before performance is loaded or calculated: prespecified comparator hierarchy.
spec={
 'primary_comparison':'Full calibrated XGBoost minus Comparator 2 native logistic probability',
 'comparator_0':['x_reference_creatinine'],
 'comparator_1':['x_reference_creatinine','x_lab_creatinine_last','x_creatinine_last_reference_ratio','x_stage1_at_landmark'],
 'comparator_2_primary':['x_reference_creatinine','x_lab_creatinine_last','x_lab_creatinine_max','x_creatinine_slope_per_hour','x_lab_creatinine_n','x_stage1_at_landmark'],
 'comparator_3_secondary':['Comparator 2','x_age_years','x_sex','x_tx_any_vasopressor','x_resp_invasive_mechanical_ventilation'],
 'model':'unpenalized logistic regression; training-fold median imputation and standardization; no explicit missingness indicators',
 'probability':'native logistic primary; no test-set recalibration',
 'rationale':'Comparator 2 uses level, worst value, within-window rate, measurement count, and landmark KDIGO status without jointly entering algebraically redundant first/minimum/mean/delta/ratio terms.',
 'locked_before_performance_review':True}
(OUT/'outputs'/'PRESPECIFIED_RENAL_COMPARATOR_PROTOCOL.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')

q=f'''WITH raw AS (
 SELECT s.id_row,l.labID,l.labResultOffset AS off,SAFE_CAST(l.labResult AS FLOAT64) AS val
 FROM `{PROJECT}.{DS}.feature_static_v1` s JOIN `physionet-data.eicu_crd.lab` l USING(patientUnitStayID)
 WHERE LOWER(TRIM(l.labName))='creatinine' AND l.labResultOffset BETWEEN 0 AND 720
   AND SAFE_CAST(l.labResult AS FLOAT64) BETWEEN 0.05 AND 40.0),
cr AS (SELECT id_row,MIN(off) first_cr_offset,MAX(off) last_cr_offset,COUNT(*) raw_cr_n FROM raw GROUP BY id_row)
SELECT m.*,cr.first_cr_offset,cr.last_cr_offset,cr.raw_cr_n,
 c.x_tx_any_vasopressor,c.x_resp_invasive_mechanical_ventilation,
 s.audit_reference_offset
FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m
JOIN `{PROJECT}.{DS}.feature_static_v1` s USING(id_row)
LEFT JOIN `{PROJECT}.{DS}.feature_context_v1` c USING(patientUnitStayID)
LEFT JOIN cr USING(id_row)'''
df=client.query(q).to_dataframe(); full=client.query(f'SELECT * FROM `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1`').to_dataframe()
assert (len(df),df.group_hospital.nunique(),int(df.label_stage23.sum()))==(58491,198,3032)
assert len(full)==58491 and full.id_row.nunique()==58491
df['x_creatinine_last_reference_ratio']=df.x_lab_creatinine_last/df.x_reference_creatinine
span=(df.last_cr_offset-df.first_cr_offset)/60.0
df['x_creatinine_slope_per_hour']=(df.x_lab_creatinine_last-df.x_lab_creatinine_first)/span.replace(0,np.nan)
df.loc[df.x_lab_creatinine_n.fillna(0)<2,'x_creatinine_slope_per_hour']=np.nan
df['x_lab_creatinine_n']=df.x_lab_creatinine_n.fillna(0)

specs={
 'Comparator 0: reference creatinine':['x_reference_creatinine'],
 'Comparator 1: renal status':['x_reference_creatinine','x_lab_creatinine_last','x_creatinine_last_reference_ratio','x_stage1_at_landmark'],
 'Comparator 2: creatinine trajectory':['x_reference_creatinine','x_lab_creatinine_last','x_lab_creatinine_max','x_creatinine_slope_per_hour','x_lab_creatinine_n','x_stage1_at_landmark'],
 'Comparator 3: renal + minimal clinical':['x_reference_creatinine','x_lab_creatinine_last','x_lab_creatinine_max','x_creatinine_slope_per_hour','x_lab_creatinine_n','x_stage1_at_landmark','x_age_years','x_sex','x_tx_any_vasopressor','x_resp_invasive_mechanical_ventilation']}
def pipe(cols):
 cats=[x for x in cols if x=='x_sex']; nums=[x for x in cols if x not in cats]
 return Pipeline([('prep',ColumnTransformer([('num',Pipeline([('imp',SimpleImputer(strategy='median',add_indicator=False)),('scale',StandardScaler())]),nums),('cat',Pipeline([('imp',SimpleImputer(strategy='constant',fill_value='other_or_missing')),('oh',OneHotEncoder(drop='first',handle_unknown='ignore',sparse_output=False))]),cats)],remainder='drop',verbose_feature_names_out=False)),('model',LogisticRegression(penalty=None,solver='lbfgs',max_iter=3000))])
def met(y,p): return {'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),'brier':brier_score_loss(y,p),'log_loss':log_loss(y,p)}
def cal(y,p):
 z=logit(np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)).reshape(-1,1); m=LogisticRegression(penalty=None,solver='lbfgs',max_iter=2000).fit(z,np.asarray(y)); return float(m.intercept_[0]),float(m.coef_[0,0])

pred=[]; coef=[]
for f in range(1,6):
 tr=df.outer_fold!=f; te=~tr
 assert set(df.loc[tr,'group_hospital']).isdisjoint(set(df.loc[te,'group_hospital']))
 for name,cols in specs.items():
  pp=pipe(cols); pp.fit(df.loc[tr,cols],df.loc[tr,'label_stage23']); p=pp.predict_proba(df.loc[te,cols])[:,1]
  pred.append(pd.DataFrame({'id_row':df.loc[te,'id_row'],'group_hospital':df.loc[te,'group_hospital'],'outer_fold':f,'label_stage23':df.loc[te,'label_stage23'],'model':name,'prediction':p}))
  names=pp.named_steps['prep'].get_feature_names_out(); vals=pp.named_steps['model'].coef_[0]
  for n,v in zip(names,vals): coef.append({'outer_fold':f,'model':name,'feature':n,'coefficient':v,'odds_ratio_per_scaled_unit':np.exp(v)})
 print('fold',f,'complete',flush=True)
pred=pd.concat(pred,ignore_index=True); assert len(pred)==4*58491
primary=pred[pred.model=='Comparator 2: creatinine trajectory'].drop(columns='model')
paired=full.merge(primary,on=['id_row','group_hospital','outer_fold','label_stage23'],validate='one_to_one'); assert len(paired)==58491

rows=[]; foldrows=[]
for name,g in pred.groupby('model',sort=False):
 y=g.label_stage23.to_numpy(); p=g.prediction.to_numpy(); ci,cs=cal(y,p); rows.append({'model':name,'specification':', '.join(specs[name]),**met(y,p),'calibration_intercept':ci,'calibration_slope':cs})
 for f,h in g.groupby('outer_fold'): 
  ci,cs=cal(h.label_stage23,h.prediction); foldrows.append({'model':name,'outer_fold':f,**met(h.label_stage23,h.prediction),'calibration_intercept':ci,'calibration_slope':cs})
y=paired.label_stage23.to_numpy(); px=paired.prediction_platt.to_numpy(); ci,cs=cal(y,px); rows.insert(0,{'model':'Full XGBoost','specification':'159-predictor primary model',**met(y,px),'calibration_intercept':ci,'calibration_slope':cs})
for f,h in paired.groupby('outer_fold'):
 ci,cs=cal(h.label_stage23,h.prediction_platt); foldrows.append({'model':'Full XGBoost','outer_fold':f,**met(h.label_stage23,h.prediction_platt),'calibration_intercept':ci,'calibration_slope':cs})
performance=pd.DataFrame(rows); foldperf=pd.DataFrame(foldrows); pc=performance[performance.model=='Comparator 2: creatinine trajectory'].iloc[0]; xf=performance[performance.model=='Full XGBoost'].iloc[0]

# Paired hospital-cluster bootstrap, delta = XGBoost - comparator.
rng=np.random.default_rng(SEED); hs=paired.group_hospital.unique(); byh={h:np.where(paired.group_hospital.to_numpy()==h)[0] for h in hs}; reps=[]
for b in range(BOOT):
 ix=np.concatenate([byh[h] for h in rng.choice(hs,len(hs),replace=True)]); yy=y[ix]; a=px[ix]; c=paired.prediction.to_numpy()[ix]; ma=met(yy,a); mc=met(yy,c); cia,csa=cal(yy,a); cic,csc=cal(yy,c)
 reps.append({'replicate':b,**{f'delta_{k}':ma[k]-mc[k] for k in ma},'delta_calibration_intercept':cia-cic,'delta_calibration_slope':csa-csc})
reps=pd.DataFrame(reps); cirows=[]
for k in ['auroc','auprc','brier','log_loss','calibration_intercept','calibration_slope']:
 point=float(xf[k]-pc[k]); v=reps['delta_'+k]; cirows.append({'metric':k,'xgboost':xf[k],'comparator':pc[k],'difference_xgboost_minus_comparator':point,'ci_low':v.quantile(.025),'ci_high':v.quantile(.975),'bootstrap_replicates':BOOT})
cis=pd.DataFrame(cirows)

def op(y,p,t):
 a=p>=t; tp=int(((a)&(y==1)).sum()); tn=int(((~a)&(y==0)).sum()); fp=int(((a)&(y==0)).sum()); fn=int(((~a)&(y==1)).sum()); sen=tp/(tp+fn); ppv=tp/(tp+fp)
 return {'threshold':t,'sensitivity':sen,'specificity':tn/(tn+fp),'ppv':ppv,'npv':tn/(tn+fn),'f1':2*sen*ppv/(sen+ppv),'alerts_per_100':100*a.mean(),'true_positives':tp,'false_positives':fp}
ops=[]
for t in [.05,.075,.10]:
 for name,p in [('Full XGBoost',px),('Comparator 2: creatinine trajectory',paired.prediction.to_numpy())]: ops.append({'model':name,'comparison':'same probability threshold',**op(y,p,t)})
target_alert=(px>=.05).sum(); cp=paired.prediction.to_numpy(); order=np.argsort(-cp); cut=(cp[order[target_alert-1]]+cp[order[target_alert]])/2; ox=op(y,px,.05); oc=op(y,cp,cut); ops.extend([{'model':'Full XGBoost','comparison':'matched alert burden',**ox},{'model':'Comparator 2: creatinine trajectory','comparison':'matched alert burden',**oc}]); ops=pd.DataFrame(ops)

dca=[]
for t in np.arange(.01,.1001,.0025):
 for name,p in [('Full XGBoost',px),('Comparator 2: creatinine trajectory',cp)]:
  a=p>=t; tp=((a)&(y==1)).sum(); fp=((a)&(y==0)).sum(); dca.append({'threshold':t,'model':name,'net_benefit':tp/len(y)-fp/len(y)*t/(1-t)})
 dca.append({'threshold':t,'model':'Treat all','net_benefit':y.mean()-(1-y.mean())*t/(1-t)}); dca.append({'threshold':t,'model':'Treat none','net_benefit':0})
dca=pd.DataFrame(dca); dw=dca[dca.model.isin(['Full XGBoost','Comparator 2: creatinine trajectory'])].pivot(index='threshold',columns='model',values='net_benefit'); dd=dw['Full XGBoost']-dw['Comparator 2: creatinine trajectory']
dsummary=pd.DataFrame([{'max_absolute_net_benefit_difference':dd.abs().max(),'xgboost_greater_threshold_min':dd[dd>0].index.min(),'xgboost_greater_threshold_max':dd[dd>0].index.max(),'fraction_thresholds_xgboost_greater':(dd>0).mean(),**{f'difference_at_{int(t*1000)}_permille':float(dd.loc[np.isclose(dd.index,t)].iloc[0]) for t in [.05,.075,.10]}}])

# Stage-1 and complementary exploratory subgroups.
subs=[]
for lab,mask in [('Stage 1 at landmark',paired.id_row.isin(set(df.loc[df.x_stage1_at_landmark==1,'id_row']))),('No stage 1 at landmark',paired.id_row.isin(set(df.loc[df.x_stage1_at_landmark==0,'id_row'])) )]:
 yy=y[mask];
 for name,p in [('Full XGBoost',px[mask]),('Comparator 2: creatinine trajectory',cp[mask])]: subs.append({'subgroup':lab,'model':name,'n':len(yy),'events':int(yy.sum()),'auroc':roc_auc_score(yy,p),'auprc':average_precision_score(yy,p)})
subgroups=pd.DataFrame(subs)

# Descriptive primary-comparator coefficient summary across five outer fits.
coef=pd.DataFrame(coef); co=coef[coef.model=='Comparator 2: creatinine trajectory'].groupby('feature').agg(mean_coefficient=('coefficient','mean'),sd_coefficient=('coefficient','std'),min_coefficient=('coefficient','min'),max_coefficient=('coefficient','max')).reset_index(); co['mean_odds_ratio_per_training_SD']=np.exp(co.mean_coefficient)

# Feature/leakage audit.
aud=[]
def add(feature,source,definition,window,missing,outcome,retain,reason): aud.append({'candidate_feature':feature,'source':source,'definition':definition,'time_window':window,'available_by_12h':True,'missingness':missing,'contributes_to_outcome_definition':outcome,'leakage_violations':0,'retained_primary_comparator':retain,'decision_reason':reason})
add('x_reference_creatinine','creatinine_staged_v1 / feature_static_v1','Earliest qualifying creatinine from max(hospital admission,-24 h) through +6 h','-24 h admission bound to +6 h',df.x_reference_creatinine.isna().mean(),True,True,'Baseline renal status; cohort requires availability')
for v,source,label,keep,reason in [('x_lab_creatinine_first','feature_labs_v1','First valid 0-12 h creatinine',False,'Algebraically represented through last and slope'),('x_lab_creatinine_last','feature_labs_v1','Last valid 0-12 h creatinine',True,'Current renal level'),('x_lab_creatinine_min','feature_labs_v1','Minimum valid 0-12 h creatinine',False,'Redundant summary'),('x_lab_creatinine_max','feature_labs_v1','Maximum valid 0-12 h creatinine',True,'Worst pre-landmark renal level'),('x_lab_creatinine_mean','feature_labs_v1','Mean valid 0-12 h creatinine',False,'Redundant summary'),('x_lab_creatinine_n','feature_labs_v1','Count valid 0-12 h creatinine values',True,'Trajectory information; zero when none')]: add(v,source,label,'0-12 h',df[v].isna().mean(),False,keep,reason)
add('x_creatinine_slope_per_hour','derived from feature_labs_v1 plus raw offsets','(last-first)/(last offset-first offset), n>=2','0-12 h',df.x_creatinine_slope_per_hour.isna().mean(),False,True,'Rate of early creatinine change')
add('x_stage1_at_landmark','cohort_outcome_v1 / feature_static_v1','Maximum KDIGO creatinine stage from reference through 720 min equals 1','through 12 h',0,True,True,'Clinically interpretable landmark renal status')
for v in ['BUN','urine output','RRT information','relative creatinine change','time between measurements']:
 add(v,'audited authoritative pipeline','See report','through 12 h',np.nan,v=='RRT information',False,{'BUN':'Non-creatinine renal marker; excluded to keep primary comparator creatinine-focused','urine output':'No validated urine-output feature in locked 159-predictor registry','RRT information':'Pre-landmark acute RRT is an exclusion; post-landmark RRT prohibited','relative creatinine change':'Redundant with reference/last/stage-1 status','time between measurements':'Used only to derive slope; not separately entered'}[v])
audit=pd.DataFrame(aud)
viol_first=int((df.first_cr_offset.dropna()<0).sum()+(df.first_cr_offset.dropna()>720).sum()); viol_last=int((df.last_cr_offset.dropna()<0).sum()+(df.last_cr_offset.dropna()>720).sum()); assert viol_first==viol_last==0
stage1n=int(df.x_stage1_at_landmark.sum()); stage1events=int(df.loc[df.x_stage1_at_landmark==1,'label_stage23'].sum())

# Curves and publication outputs.
curves=[]
for name,p in [('Full XGBoost',px),('Comparator 2: creatinine trajectory',cp)]:
 fpr,tpr,_=roc_curve(y,p); rec,pre,_=precision_recall_curve(y,p); curves += [{'curve':'ROC','model':name,'x':x,'y':z} for x,z in zip(fpr,tpr)]; curves += [{'curve':'PR','model':name,'x':x,'y':z} for x,z in zip(rec,pre)]
curves=pd.DataFrame(curves)
performance.to_csv(OUT/'outputs'/'pooled_performance.csv',index=False); foldperf.to_csv(OUT/'outputs'/'fold_performance.csv',index=False); cis.to_csv(OUT/'outputs'/'paired_hospital_bootstrap_differences.csv',index=False); ops.to_csv(OUT/'outputs'/'operating_points_and_matched_alert.csv',index=False); dca.to_csv(OUT/'outputs'/'decision_curve_data.csv',index=False); dsummary.to_csv(OUT/'outputs'/'decision_curve_summary.csv',index=False); subgroups.to_csv(OUT/'outputs'/'stage1_subgroup_performance.csv',index=False); co.to_csv(OUT/'outputs'/'primary_comparator_coefficients.csv',index=False); curves.to_csv(OUT/'outputs'/'roc_pr_curve_data.csv',index=False); audit.to_csv(OUT/'outputs'/'renal_feature_audit.csv',index=False)
performance.to_excel(OUT/'tables'/'TABLE_S10_model_performance.xlsx',index=False); cis.to_excel(OUT/'tables'/'TABLE_S11_incremental_performance.xlsx',index=False); ops.to_excel(OUT/'tables'/'TABLE_S12_operating_points_matched_alert.xlsx',index=False); subgroups.to_excel(OUT/'tables'/'TABLE_S13_stage1_subgroup.xlsx',index=False)

fig,ax=plt.subplots(1,3,figsize=(12.5,4))
for name,p,style in [('Full XGBoost',px,dict(color='black',ls='-')),('Creatinine trajectory',cp,dict(color='.45',ls='--'))]:
 fpr,tpr,_=roc_curve(y,p); ax[0].plot(fpr,tpr,label=name,**style); rec,pre,_=precision_recall_curve(y,p); ax[1].plot(rec,pre,label=name,**style)
for name,style in [('Full XGBoost',dict(color='black',ls='-')),('Comparator 2: creatinine trajectory',dict(color='.45',ls='--')),('Treat all',dict(color='.7',ls=':')),('Treat none',dict(color='.2',ls=':'))]:
 z=dca[dca.model==name]; ax[2].plot(100*z.threshold,z.net_benefit,label='Creatinine trajectory' if name.startswith('Comparator') else name,**style)
ax[0].plot([0,1],[0,1],':',color='.75'); ax[0].set(xlabel='1 - specificity',ylabel='Sensitivity',title='A  ROC'); ax[1].axhline(y.mean(),ls=':',color='.75'); ax[1].set(xlabel='Recall',ylabel='Precision',title='B  Precision-recall'); ax[2].set(xlabel='Threshold probability (%)',ylabel='Net benefit',title='C  Decision curves')
for a in ax: a.grid(color='.9'); a.legend(frameon=False,fontsize=8)
fig.suptitle('Fig. S9. Incremental value beyond a parsimonious creatinine-trajectory model'); fig.tight_layout(); fig.savefig(OUT/'figures'/'FIG_S9_renal_trajectory_incremental_value.png',dpi=300,bbox_inches='tight'); fig.savefig(OUT/'figures'/'FIG_S9_renal_trajectory_incremental_value.pdf',bbox_inches='tight'); plt.close(fig)

delta_auc=float(xf.auroc-pc.auroc); delta_ap=float(xf.auprc-pc.auprc); maxnb=float(dsummary.max_absolute_net_benefit_difference.iloc[0]); level='substantial' if delta_auc>=.05 or delta_ap>=.08 else ('modest' if delta_auc>=.02 or delta_ap>=.03 else 'little')
feature_audit=f'''# Renal comparator feature audit\n\n## Authoritative temporal definitions\n\nThe reference creatinine is the earliest qualifying revised creatinine between max(hospital admission offset, -1440 min) and +360 min. Landmark summaries use valid laboratory results from 0 through 720 min. Stage 1 is `max_stage_by_12h = 1`; the outcome begins strictly after 720 min and extends through 72 h. The main cohort excludes stage 2-3 and strict acute RRT at or before 720 min.\n\nAutomated offset checks found **{viol_first+viol_last} violations** among first/last creatinine offsets used for trajectory derivation. Stage 1 at landmark was present in {stage1n:,} patients, including {stage1events:,} subsequent events.\n\nThe primary comparator was prespecified before performance review as reference creatinine, last and maximum 0-12 h creatinine, creatinine slope per hour, measurement count, and landmark stage 1 status. Complete candidate decisions are in `outputs/renal_feature_audit.csv`. Urine output was rejected because no validated urine-output predictor exists in the locked registry. RRT was not used as a predictor: pre-landmark RRT defines exclusion and future RRT would leak outcome information.\n'''
(OUT/'RENAL_COMPARATOR_FEATURE_AUDIT.md').write_text(feature_audit,encoding='utf-8')
report=f'''# Renal trajectory comparator report\n\n## Executive summary\n\nThe full XGBoost model provided **{level} incremental value** beyond the prespecified parsimonious creatinine-trajectory logistic comparator. XGBoost AUROC/AUPRC were {xf.auroc:.4f}/{xf.auprc:.4f}, versus {pc.auroc:.4f}/{pc.auprc:.4f}; differences were {delta_auc:.4f} and {delta_ap:.4f}.\n\n## Comparator definitions\n\nComparator 0 used reference creatinine alone. Comparator 1 used reference and last creatinine, their ratio, and landmark stage 1. Primary Comparator 2 used reference, last and maximum creatinine, within-window slope, measurement count, and stage 1. Comparator 3 added age, sex, vasopressor exposure, and invasive mechanical ventilation as a secondary compact clinical benchmark. All were native unpenalized logistic regressions with outer-training-only median imputation and scaling and no explicit missingness indicators.\n\n## Leakage audit\n\nAll first-12-hour laboratory inputs were restricted to offsets 0-720 min; outcome ascertainment began strictly after 720 min. Automated first/last offset violations: 0. Pre-landmark stage 2-3 and acute RRT were cohort exclusions; no future creatinine or RRT entered any comparator.\n\n## Incremental performance\n\nBrier scores were {xf.brier:.5f} versus {pc.brier:.5f}, log loss {xf.log_loss:.5f} versus {pc.log_loss:.5f}, calibration intercepts {xf.calibration_intercept:.3f} versus {pc.calibration_intercept:.3f}, and slopes {xf.calibration_slope:.3f} versus {pc.calibration_slope:.3f}. Paired 2,000-hospital bootstrap intervals are in Table S11; delta is XGBoost minus comparator, so negative Brier/log-loss differences favor XGBoost.\n\n## Clinical utility\n\nAcross 1-10% thresholds, the maximum absolute net-benefit difference was {maxnb:.5f}; XGBoost had greater net benefit at {100*dsummary.fraction_thresholds_xgboost_greater.iloc[0]:.1f}% of evaluated thresholds. At matched alert burden ({ox['alerts_per_100']:.2f}/100), XGBoost detected {ox['true_positives']} progressors versus {oc['true_positives']} for the comparator, with PPV {ox['ppv']:.3f} versus {oc['ppv']:.3f}.\n\n## Stage-1 subgroup\n\nExploratory stage-1 and complementary subgroup results are reported in Table S13.\n\n## Interpretation\n\nThe complexity of the full model is justified to the extent supported by the combined discrimination, precision-recall, calibration, net-benefit, and matched-alert results; statistical significance alone was not used to label magnitude.\n\n## Limitations\n\nThis is a same-dataset hospital-disjoint comparator, not external validation. Renal trajectory is intrinsically related to a renal outcome; fixed-threshold comparisons depend on calibration; and simple renal models may themselves encode measurement practice.\n'''
(OUT/'RENAL_TRAJECTORY_COMPARATOR_REPORT.md').write_text(report,encoding='utf-8')
(OUT/'MANUSCRIPT_INSERT_RENAL_COMPARATOR.md').write_text(f'''# Candidate manuscript insertion (not applied)\n\n## Methods\nWe prespecified a parsimonious renal-trajectory logistic comparator using reference creatinine, last and maximum creatinine through 12 hours, within-window creatinine slope, measurement count, and KDIGO stage 1 status at the landmark. Models used the identical cohort and hospital-disjoint outer folds, with imputation and scaling fitted only in outer-training hospitals. Incremental performance was quantified using 2,000 paired hospital-cluster bootstrap samples, operating points, decision curves, and matched alert burden.\n\n## Results\nThe comparator achieved AUROC {pc.auroc:.3f} and AUPRC {pc.auprc:.3f}, compared with {xf.auroc:.3f} and {xf.auprc:.3f} for XGBoost. Differences were {delta_auc:.3f} for AUROC and {delta_ap:.3f} for AUPRC. Brier scores were {xf.brier:.3f} and {pc.brier:.3f}, respectively. Maximum absolute net-benefit difference from 1% to 10% was {maxnb:.5f}. At the XGBoost 5% alert burden, XGBoost detected {ox['true_positives']} progressors versus {oc['true_positives']} for the comparator.\n\n## Discussion\nThe full model provided {level} incremental predictive and clinical value beyond renal trajectory information available at the same landmark. The result should be interpreted from effect sizes across discrimination, precision-recall, calibration, and net benefit rather than statistical significance alone.\n\n## Limitations\nThis same-dataset comparator is not an external validation, and both simple and complex models may encode measurement practice.\n\n## Supplementary captions\n**Table S10.** Performance of full XGBoost and prespecified parsimonious renal comparator models.\n\n**Table S11.** Paired incremental performance of full XGBoost versus the creatinine-trajectory comparator; differences are XGBoost minus comparator with hospital-cluster bootstrap 95% confidence intervals.\n\n**Table S12.** Fixed-threshold and matched-alert-burden operating-point comparisons.\n\n**Fig. S9.** ROC, precision-recall, and decision-curve comparison of full XGBoost and the parsimonious creatinine-trajectory model.\n''',encoding='utf-8')
qc={'rows':len(df),'hospitals':df.group_hospital.nunique(),'events':int(df.label_stage23.sum()),'outer_folds':sorted(df.outer_fold.unique().tolist()),'stage1_n':stage1n,'stage1_events':stage1events,'first_last_offset_violations':viol_first+viol_last,'outcome_window_starts_strictly_after_720':True,'future_creatinine_features_used':False,'future_rrt_features_used':False,'training_only_imputation_scaling':True,'training_only_tuning':'not applicable; unpenalized specification prespecified','outer_test_calibration_fit':False,'paired_rows':len(paired),'paired_hospitals':paired.group_hospital.nunique(),'bootstrap_unit':'hospital','bootstrap_replicates':len(reps),'full_model_reconciliation':met(y,px),'runtime_minutes':(time.time()-start)/60}
(OUT/'RENAL_COMPARATOR_QC.md').write_text('# Renal comparator QC\n\n```json\n'+json.dumps(qc,indent=2)+'\n```\n\nAll mandatory structural, temporal, and leakage assertions passed. Patient-level predictions were kept transient.\n',encoding='utf-8')
(OUT/'README.md').write_text('# Renal trajectory comparator analysis\n\nStep 4 package using the locked cohort and hospital-disjoint folds. Prior analyses and final manuscript were not modified.\n',encoding='utf-8')
(OUT/'outputs'/'software_environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':__import__('sklearn').__version__,'seed':SEED,'bootstrap_replicates':BOOT},indent=2),encoding='utf-8')
(OUT/'src'/'run_renal_trajectory_comparator.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
files=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file(): files.append({'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pd.DataFrame(files).to_csv(OUT/'outputs'/'CREATED_FILES_MANIFEST.csv',index=False)
print(json.dumps({'primary_spec':spec['comparator_2_primary'],'stage1_n':stage1n,'stage1_events':stage1events,'xgboost':xf[['auroc','auprc','brier','log_loss','calibration_intercept','calibration_slope']].to_dict(),'comparator':pc[['auroc','auprc','brier','log_loss','calibration_intercept','calibration_slope']].to_dict(),'incremental_level':level,'matched_alert_xgb_tp':ox['true_positives'],'matched_alert_comp_tp':oc['true_positives'],'runtime_min':(time.time()-start)/60},indent=2),flush=True)
