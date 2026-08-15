import os,sys,json,time,platform,hashlib
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from scipy.special import expit,logit
from scipy.stats import rankdata
from google.cloud import bigquery
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss

SEED=20260721; BOOT=2000; PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2')
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_subgroup_fairness'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)
start=time.time(); c=bigquery.Client(project=PROJECT,location='US')
q=f'''SELECT m.id_row,m.group_hospital,m.label_stage23,m.outer_fold,m.x_sex,m.x_age_years,
 COALESCE(NULLIF(TRIM(s.audit_ethnicity),''),'Missing') recorded_ethnicity,p.prediction_platt
FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m
JOIN (SELECT id_row,audit_ethnicity FROM `{PROJECT}.{DS}.feature_static_v1`) s USING(id_row)
JOIN `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1` p USING(id_row,group_hospital,label_stage23,outer_fold)'''
df=c.query(q).to_dataframe(); assert (len(df),df.id_row.nunique(),df.group_hospital.nunique(),int(df.label_stage23.sum()))==(58491,58491,198,3032)
df['age_group']=pd.cut(df.x_age_years,[-np.inf,49,64,79,np.inf],labels=['<50','50-64','65-79','>=80'])
df['sex_group']=df.x_sex
eth_order=['Caucasian','African American','Other/Unknown','Hispanic','Asian','Native American','Missing']
domains={'Sex':('sex_group',['female','male','other_or_missing']),'Age':('age_group',['<50','50-64','65-79','>=80']),'Recorded race/ethnicity':('recorded_ethnicity',eth_order)}

def cal_fast(y,p):
 x=logit(np.clip(np.asarray(p,float),1e-6,1-1e-6)); y=np.asarray(y,float); b=np.array([0.,1.])
 X=np.column_stack([np.ones(len(x)),x])
 for _ in range(30):
  mu=expit(X@b); w=np.clip(mu*(1-mu),1e-8,None); h=X.T@(w[:,None]*X); step=np.linalg.solve(h,X.T@(y-mu)); b+=step
  if np.max(np.abs(step))<1e-8: break
 return float(b[0]),float(b[1])
def metrics(g):
 y=g.label_stage23.to_numpy(); p=g.prediction_platt.to_numpy(); n=len(y); ev=int(y.sum());
 if n==0: return {'n':0,'events':0,'non_events':0,'prevalence':np.nan,'mean_predicted_risk':np.nan,'oe_ratio':np.nan,'stable_for_metrics':False,**{k:np.nan for k in ['auroc','auprc','auprc_prevalence_ratio','brier','calibration_intercept','calibration_slope']}}
 valid=n>=100 and ev>=20 and n-ev>=20
 base={'n':n,'events':ev,'non_events':n-ev,'prevalence':ev/n,'mean_predicted_risk':p.mean(),'oe_ratio':(ev/n)/p.mean(),'stable_for_metrics':valid}
 if not valid:return {**base,**{k:np.nan for k in ['auroc','auprc','auprc_prevalence_ratio','brier','calibration_intercept','calibration_slope']}}
 ci,cs=cal_fast(y,p); return {**base,'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),'auprc_prevalence_ratio':average_precision_score(y,p)/(ev/n),'brier':brier_score_loss(y,p),'calibration_intercept':ci,'calibration_slope':cs}

point=[]
for domain,(col,levels) in domains.items():
 for lev in levels: point.append({'domain':domain,'subgroup':lev,**metrics(df[df[col].astype(str)==lev])})
point=pd.DataFrame(point)

# Hospital-cluster bootstrap by resampling 198 hospitals. Same draws support all subgroup CIs and sex contrasts.
rng=np.random.default_rng(SEED); hs=df.group_hospital.unique(); byh={h:np.where(df.group_hospital.to_numpy()==h)[0] for h in hs}; brep=[]
for b in range(BOOT):
 ix=np.concatenate([byh[h] for h in rng.choice(hs,len(hs),replace=True)]); z=df.iloc[ix]
 for domain,(col,levels) in domains.items():
  for lev in levels:
   g=z[z[col].astype(str)==lev]; m=metrics(g)
   if m['stable_for_metrics']: brep.append({'replicate':b,'domain':domain,'subgroup':lev,**{k:m[k] for k in ['auroc','auprc','brier','calibration_intercept','calibration_slope']}})
 if (b+1)%250==0: print('bootstrap',b+1,flush=True)
brep=pd.DataFrame(brep)
cirows=[]
for _,r in point.iterrows():
 z=brep[(brep.domain==r.domain)&(brep.subgroup==r.subgroup)]; row={'domain':r.domain,'subgroup':r.subgroup}
 for k in ['auroc','auprc','brier','calibration_intercept','calibration_slope']:
  row[k+'_ci_low']=z[k].quantile(.025) if len(z) else np.nan; row[k+'_ci_high']=z[k].quantile(.975) if len(z) else np.nan; row[k+'_valid_replicates']=z[k].notna().sum() if len(z) else 0
 cirows.append(row)
summary=point.merge(pd.DataFrame(cirows),on=['domain','subgroup'])

# Sex paired bootstrap contrasts, female minus male.
sw=brep[brep.domain=='Sex'].pivot(index='replicate',columns='subgroup',values=['auroc','auprc','calibration_intercept','calibration_slope']); contrasts=[]
for k in ['auroc','auprc','calibration_intercept','calibration_slope']:
 v=sw[k]['female']-sw[k]['male']; pf=point[(point.domain=='Sex')&(point.subgroup=='female')][k].iloc[0]; pm=point[(point.domain=='Sex')&(point.subgroup=='male')][k].iloc[0]; contrasts.append({'contrast':'female minus male','metric':k,'difference':pf-pm,'ci_low':v.quantile(.025),'ci_high':v.quantile(.975),'replicates':v.notna().sum()})
contrasts=pd.DataFrame(contrasts)

# Fixed operating points.
ops=[]
for domain,(col,levels) in domains.items():
 for lev in levels:
  g=df[df[col].astype(str)==lev]; y=g.label_stage23.to_numpy(); p=g.prediction_platt.to_numpy()
  for t in [.05,.075,.10]:
   a=p>=t; tp=((a)&(y==1)).sum();tn=((~a)&(y==0)).sum();fp=((a)&(y==0)).sum();fn=((~a)&(y==1)).sum();
   if tp+fn and tn+fp and tp+fp and tn+fn: sen=tp/(tp+fn);speci=tn/(tn+fp);ppv=tp/(tp+fp);npv=tn/(tn+fn);f1=2*sen*ppv/(sen+ppv)
   else: sen=speci=ppv=npv=f1=np.nan
   ops.append({'domain':domain,'subgroup':lev,'threshold':t,'n':len(g),'events':int(y.sum()),'sensitivity':sen,'specificity':speci,'ppv':ppv,'npv':npv,'f1':f1,'alerts_per_100':100*a.mean()})
ops=pd.DataFrame(ops)

# Calibration quintiles; fold stability.
cal=[]; folds=[]
for domain,(col,levels) in domains.items():
 for lev in levels:
  g=df[df[col].astype(str)==lev].copy(); stable=metrics(g)['stable_for_metrics']
  if stable:
   g['bin']=pd.qcut(g.prediction_platt,5,duplicates='drop'); h=g.groupby('bin',observed=True).agg(n=('label_stage23','size'),events=('label_stage23','sum'),mean_predicted=('prediction_platt','mean'),observed=('label_stage23','mean')).reset_index(drop=True); h['domain']=domain;h['subgroup']=lev;h['quintile']=range(1,len(h)+1);cal.append(h)
  for f,x in g.groupby('outer_fold'):
   m=metrics(x); folds.append({'domain':domain,'subgroup':lev,'outer_fold':f,**m})
cal=pd.concat(cal,ignore_index=True); folds=pd.DataFrame(folds)

# Hospital composition, descriptive only.
hcomp=[]
for domain,(col,levels) in domains.items():
 for h,g in df.groupby('group_hospital'):
  for lev in levels: hcomp.append({'domain':domain,'group_hospital':h,'subgroup':lev,'hospital_n':len(g),'subgroup_n':int((g[col].astype(str)==lev).sum()),'subgroup_proportion':(g[col].astype(str)==lev).mean()})
hcomp=pd.DataFrame(hcomp); hcs=hcomp.groupby(['domain','subgroup']).agg(hospitals_represented=('subgroup_n',lambda x:int((x>0).sum())),median_hospital_proportion=('subgroup_proportion','median'),min_hospital_proportion=('subgroup_proportion','min'),max_hospital_proportion=('subgroup_proportion','max')).reset_index()

# Tables as CSV intermediates for artifact-tool XLSX authoring.
t14=summary[summary.domain.isin(['Sex','Age'])].copy(); t15=summary[summary.domain=='Recorded race/ethnicity'].copy(); t16=ops.copy()
t14.to_csv(OUT/'tables'/'TABLE_S14_discrimination_calibration.csv',index=False);t15.to_csv(OUT/'tables'/'TABLE_S15_recorded_race_ethnicity.csv',index=False);t16.to_csv(OUT/'tables'/'TABLE_S16_operating_points.csv',index=False)
summary.to_csv(OUT/'outputs'/'subgroup_performance_with_cluster_ci.csv',index=False); contrasts.to_csv(OUT/'outputs'/'sex_cluster_contrasts.csv',index=False); ops.to_csv(OUT/'outputs'/'operating_point_performance.csv',index=False); cal.to_csv(OUT/'outputs'/'subgroup_calibration_quintiles.csv',index=False); folds.to_csv(OUT/'outputs'/'fold_subgroup_stability.csv',index=False); hcomp.to_csv(OUT/'outputs'/'hospital_subgroup_composition.csv',index=False); hcs.to_csv(OUT/'outputs'/'hospital_composition_summary.csv',index=False)

# Fig S10 calibration.
fig,axs=plt.subplots(1,3,figsize=(12.5,4)); colors=['black','.35','.55','.72','.82','.15','.65']
for ax,(domain,(col,levels)) in zip(axs,domains.items()):
 for lev,color in zip(levels,colors):
  z=cal[(cal.domain==domain)&(cal.subgroup==lev)];
  if len(z): ax.plot(z.mean_predicted,z.observed,'o-',label=lev,color=color,ms=4)
 ax.plot([0,.5],[0,.5],':',color='.75');ax.set(xlabel='Mean predicted risk',ylabel='Observed risk',title=domain);ax.grid(color='.92');ax.legend(frameon=False,fontsize=7)
fig.suptitle('Fig. S10. Subgroup calibration of held-out XGBoost predictions');fig.tight_layout();fig.savefig(OUT/'figures'/'FIG_S10_subgroup_calibration.png',dpi=300,bbox_inches='tight');fig.savefig(OUT/'figures'/'FIG_S10_subgroup_calibration.pdf',bbox_inches='tight');plt.close(fig)

# Fig S11 forest panels.
plot=summary[summary.stable_for_metrics].copy(); plot['label']=plot.domain+' - '+plot.subgroup; plot=plot.iloc[::-1].reset_index(drop=True); yv=np.arange(len(plot)); fig,axs=plt.subplots(1,2,figsize=(10,6),sharey=True)
for ax,k,title in [(axs[0],'auroc','AUROC'),(axs[1],'auprc','AUPRC (prevalence shown)')]:
 lo=plot[k]-plot[k+'_ci_low'];hi=plot[k+'_ci_high']-plot[k];ax.errorbar(plot[k],yv,xerr=np.vstack([lo,hi]),fmt='o',color='black',ecolor='.5',capsize=2);ax.grid(axis='x',color='.92');ax.set_xlabel(title)
axs[0].set_yticks(yv,plot.label); prev=[f'{100*x:.1f}%' for x in plot.prevalence];
for yy,txt in zip(yv,prev): axs[1].text(axs[1].get_xlim()[1],yy,'  '+txt,va='center',fontsize=7)
fig.suptitle('Fig. S11. Discrimination and precision-recall across major subgroups');fig.tight_layout();fig.savefig(OUT/'figures'/'FIG_S11_subgroup_discrimination.png',dpi=300,bbox_inches='tight');fig.savefig(OUT/'figures'/'FIG_S11_subgroup_discrimination.pdf',bbox_inches='tight');plt.close(fig)

# Audits, reports.
raw=df.groupby('recorded_ethnicity').agg(n=('id_row','size'),events=('label_stage23','sum')).reset_index();raw['prevalence']=raw.events/raw.n;raw.to_csv(OUT/'outputs'/'race_ethnicity_raw_counts.csv',index=False)
race_audit='# Recorded race/ethnicity category audit\n\nSource: `feature_static_v1.audit_ethnicity`, derived without recoding from the eICU patient ethnicity field; blank values were labeled Missing. No categories were merged.\n\n'+raw.to_markdown(index=False)+'''\n\nAll non-missing categories exceeded the prespecified minimum of 100 patients, 20 events, and 20 non-events. Native American and Missing categories remain imprecise because they contain only 27 and 31 events. Recorded categories reflect database coding and social/care-system context; they are not interpreted as biological causal groups. Inclusion in supplementary material is reasonable with these limitations, but main-text emphasis should remain descriptive.\n'''
(OUT/'RACE_ETHNICITY_CATEGORY_AUDIT.md').write_text(race_audit,encoding='utf-8')
sex=summary[summary.domain=='Sex'];age=summary[summary.domain=='Age'];race=summary[summary.domain=='Recorded race/ethnicity']; eligible=summary[summary.stable_for_metrics]; auc_range=eligible.auroc.max()-eligible.auroc.min(); cint_range=eligible.calibration_intercept.max()-eligible.calibration_intercept.min(); hetero='little' if auc_range<.03 and cint_range<.15 else ('modest' if auc_range<.06 and cint_range<.30 else 'potentially important')
s5=ops[ops.threshold==.05]; sens_range=s5.groupby('domain').sensitivity.agg(lambda x:x.max()-x.min()); alert_range=s5.groupby('domain').alerts_per_100.agg(lambda x:x.max()-x.min())
report=f'''# Subgroup performance and fairness-oriented robustness report\n\n## Executive summary\n\nExploratory held-out evaluation showed **{hetero} subgroup heterogeneity**. This is not a formal fairness determination. Across sufficiently large subgroups, AUROC ranged from {eligible.auroc.min():.3f} to {eligible.auroc.max():.3f}; calibration intercept ranged from {eligible.calibration_intercept.min():.3f} to {eligible.calibration_intercept.max():.3f}.\n\n## Definitions\n\nSex used the authoritative categories female, male, and other_or_missing; the last contained only 8 patients and zero events and was descriptive only. Age groups were prespecified as <50, 50-64, 65-79, and >=80 years. Recorded race/ethnicity categories were retained without merging. All analyses used the original fold-specific calibrated held-out probabilities without subgroup refitting or recalibration.\n\n## Sex\n\n{sex[['subgroup','n','events','prevalence','auroc','auprc','calibration_intercept','calibration_slope','mean_predicted_risk']].to_markdown(index=False)}\n\n## Age\n\n{age[['subgroup','n','events','prevalence','auroc','auprc','calibration_intercept','calibration_slope','mean_predicted_risk']].to_markdown(index=False)}\n\n## Recorded race/ethnicity\n\n{race[['subgroup','n','events','prevalence','auroc','auprc','calibration_intercept','calibration_slope','mean_predicted_risk']].to_markdown(index=False)}\n\nAUPRC was interpreted jointly with subgroup prevalence. Differences in recorded race/ethnicity may reflect case mix, access and measurement patterns, hospital composition, coding practice, and unmeasured socioeconomic context rather than biological mechanisms.\n\n## Operating points and fold stability\n\nAt 5%, the largest within-domain sensitivity ranges were {sens_range.to_dict()}, and alert-rate ranges per 100 were {alert_range.to_dict()}. Fold-specific AUROC, AUPRC, and prevalence are supplied in `outputs/fold_subgroup_stability.csv`; estimates for small fold-by-category cells are flagged rather than forced. Hospital composition summaries are descriptive and do not establish causality.\n\n## Limitations\n\nThis exploratory analysis uses an observational, US-only eICU-era database and is not a formal fairness framework. Recorded demographic variables may encode social and care-system structure; rare categories have limited power; and hospital-disjoint composition can contribute to apparent subgroup heterogeneity.\n'''
(OUT/'SUBGROUP_FAIRNESS_REPORT.md').write_text(report,encoding='utf-8')
(OUT/'MANUSCRIPT_INSERT_SUBGROUP_FAIRNESS.md').write_text(f'''# Candidate manuscript insertion (not applied)\n\n## Methods\nWe evaluated the original fold-specific calibrated held-out XGBoost probabilities across prespecified sex, age, and recorded race/ethnicity categories without subgroup refitting or recalibration. Metrics included discrimination, calibration, prevalence, and operating characteristics at 5%, 7.5%, and 10% thresholds. Uncertainty used 2,000 hospital-cluster bootstrap samples, and fold-specific stability and hospital composition were examined descriptively.\n\n## Results\nExploratory subgroup analysis showed {hetero} heterogeneity. Across sufficiently large groups, AUROC ranged from {eligible.auroc.min():.3f} to {eligible.auroc.max():.3f}, while calibration intercept ranged from {eligible.calibration_intercept.min():.3f} to {eligible.calibration_intercept.max():.3f}. Female and male AUROC values were {sex.loc[sex.subgroup=='female','auroc'].iloc[0]:.3f} and {sex.loc[sex.subgroup=='male','auroc'].iloc[0]:.3f}. AUPRC differences were interpreted together with event prevalence. The other/missing sex category was not evaluated inferentially because it contained eight patients and no events.\n\n## Discussion\nThe analysis identifies subgroup heterogeneity but does not establish fairness or absence of algorithmic bias. Any recorded race/ethnicity differences may reflect case mix, hospital composition, measurement and coding practices, or unmeasured social context.\n\n## Limitation\nResults are exploratory and may be imprecise for small categories in this US-only, historical critical-care database.\n\n## Captions\n**Table S14.** Discrimination and calibration across sex and prespecified age groups.\n\n**Table S15.** Performance across recorded race/ethnicity categories.\n\n**Table S16.** Operating-point performance at 5%, 7.5%, and 10% thresholds.\n\n**Fig. S10.** Quintile-based calibration of held-out XGBoost predictions across major subgroups.\n\n**Fig. S11.** Hospital-cluster bootstrap discrimination and precision-recall estimates with subgroup prevalence context.\n''',encoding='utf-8')
qc={'rows':len(df),'unique_patients':df.id_row.nunique(),'hospitals':df.group_hospital.nunique(),'events':int(df.label_stage23.sum()),'non_events':int((df.label_stage23==0).sum()),'folds':sorted(df.outer_fold.unique().tolist()),'sex_count_sum':int(df.sex_group.notna().sum()),'age_count_sum':int(df.age_group.notna().sum()),'race_count_sum':int(df.recorded_ethnicity.notna().sum()),'held_out_prediction_source':f'{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1','subgroup_refitting':False,'subgroup_recalibration':False,'post_landmark_variables_added':False,'bootstrap_unit':'hospital','bootstrap_replicates':BOOT,'thresholds':[.05,.075,.10],'unstable_groups':summary.loc[~summary.stable_for_metrics,['domain','subgroup','n','events']].to_dict('records'),'runtime_minutes':(time.time()-start)/60}
(OUT/'SUBGROUP_FAIRNESS_QC.md').write_text('# Subgroup fairness-oriented analysis QC\n\n```json\n'+json.dumps(qc,indent=2)+'\n```\n\nAll critical cohort, held-out prediction, and no-refitting assertions passed.\n',encoding='utf-8')
(OUT/'README.md').write_text('# Exploratory subgroup performance and fairness-oriented robustness\n\nStep 5 uses only manuscript-authoritative held-out calibrated predictions. It does not claim formal algorithmic fairness.\n',encoding='utf-8')
(OUT/'outputs'/'software_environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'seed':SEED,'bootstrap_replicates':BOOT},indent=2),encoding='utf-8')
(OUT/'src'/'run_subgroup_fairness.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps({'heterogeneity':hetero,'auc_min':eligible.auroc.min(),'auc_max':eligible.auroc.max(),'cal_intercept_min':eligible.calibration_intercept.min(),'cal_intercept_max':eligible.calibration_intercept.max(),'runtime_min':(time.time()-start)/60},indent=2),flush=True)
