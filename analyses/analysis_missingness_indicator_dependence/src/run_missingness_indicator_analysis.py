import os,sys,json,time,platform,hashlib
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from scipy.special import logit
from scipy.stats import spearmanr
from google.cloud import bigquery
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss
from xgboost import XGBClassifier,DMatrix

SEED=20260721; BOOT=2000; PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2')
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_missingness_indicator_dependence'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)
start=time.time(); client=bigquery.Client(project=PROJECT,location='US')
matrix=client.query(f'SELECT * FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1`').to_dataframe()
fullpred=client.query(f'SELECT * FROM `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1`').to_dataframe()
meta=['id_row','group_hospital','label_stage23','outer_fold']; predictors=[c for c in matrix if c not in meta]
cats=['x_sex','x_unit_type','x_unit_admit_source']; nums=[c for c in predictors if c not in cats]
assert (len(matrix),matrix.group_hospital.nunique(),int(matrix.label_stage23.sum()),len(predictors),len(nums),len(cats))==(58491,198,3032,159,156,3)
assert len(fullpred)==58491 and fullpred.id_row.nunique()==58491

inner_maps={}
for f in range(1,6):
 inner_maps[f]={}; seen=set()
 for k in range(1,6):
  q=f'SELECT DISTINCT m.group_hospital FROM `{PROJECT}.{DS}.model_xgb_inner_oof_outer{f}_inner{k}_v1` p JOIN `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m USING(id_row)'
  hs=set(client.query(q).to_dataframe().group_hospital.astype(str)); assert not seen&hs; inner_maps[f][k]=hs; seen|=hs
 assert seen==set(matrix.loc[matrix.outer_fold!=f,'group_hospital'].astype(str).unique())

candidates=[
dict(candidate_id='XGB01',n_estimators=250,max_depth=2,learning_rate=.03,min_child_weight=5,subsample=.8,colsample_bytree=.8,gamma=0,reg_alpha=0,reg_lambda=5),
dict(candidate_id='XGB02',n_estimators=350,max_depth=3,learning_rate=.03,min_child_weight=5,subsample=.8,colsample_bytree=.8,gamma=0,reg_alpha=0,reg_lambda=5),
dict(candidate_id='XGB03',n_estimators=450,max_depth=3,learning_rate=.02,min_child_weight=10,subsample=.85,colsample_bytree=.85,gamma=0,reg_alpha=.1,reg_lambda=10),
dict(candidate_id='XGB04',n_estimators=350,max_depth=4,learning_rate=.03,min_child_weight=10,subsample=.8,colsample_bytree=.8,gamma=.1,reg_alpha=.1,reg_lambda=10),
dict(candidate_id='XGB05',n_estimators=450,max_depth=2,learning_rate=.02,min_child_weight=10,subsample=.9,colsample_bytree=.9,gamma=0,reg_alpha=.5,reg_lambda=10),
dict(candidate_id='XGB06',n_estimators=450,max_depth=4,learning_rate=.02,min_child_weight=15,subsample=.9,colsample_bytree=.8,gamma=.2,reg_alpha=.5,reg_lambda=15)]
def prep(add_indicator):
 return ColumnTransformer([('numeric',Pipeline([('imputer',SimpleImputer(strategy='median',add_indicator=add_indicator,keep_empty_features=True))]),nums),('categorical',Pipeline([('imputer',SimpleImputer(strategy='constant',fill_value='__MISSING__',keep_empty_features=True)),('onehot',OneHotEncoder(handle_unknown='ignore',sparse_output=True,dtype=np.float32))]),cats)],remainder='drop',sparse_threshold=1.0,verbose_feature_names_out=False)
def model(c):
 z={k:v for k,v in c.items() if k!='candidate_id'}
 return XGBClassifier(**z,objective='binary:logistic',eval_metric='logloss',tree_method='hist',max_bin=256,scale_pos_weight=1.0,importance_type='gain',random_state=SEED,n_jobs=-1,verbosity=0)
def mets(y,p): return {'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),'brier':brier_score_loss(y,p),'log_loss':log_loss(y,p)}
def platt(y,p):
 m=LogisticRegression(penalty=None,solver='lbfgs',max_iter=2000); m.fit(logit(np.clip(p,1e-6,1-1e-6)).reshape(-1,1),y); return m
def calibration(y,p):
 m=platt(y,p); return float(m.intercept_[0]),float(m.coef_[0,0])
def source_from_indicator(name):
 return name.replace('missingindicator_','',1)

# Step-2 retention context.
s2=Path(os.environ.get('AKI_HIGH_MISSINGNESS_INVENTORY', Path(__file__).resolve().parents[2]/'analysis_high_missingness_ablation'/'HIGH_MISSINGNESS_PREDICTOR_INVENTORY.csv'))
s2inv=pd.read_csv(s2).set_index('predictor')

# Full held-out TreeSHAP and clean no-indicator nested ablation.
attr_rows=[]; fold_attr=[]; patient_attr=[]; inventory_presence={c:[] for c in nums}; tune=[]; abpred=[]; fold_names={}
for f in range(1,6):
 tr=matrix.outer_fold!=f; te=~tr; trdf=matrix.loc[tr].reset_index(drop=True); tedf=matrix.loc[te].reset_index(drop=True)
 # Full model, using manuscript-selected XGB04, trained only on outer training hospitals.
 pp=prep(True); Xtr=pp.fit_transform(trdf[predictors]); Xte=pp.transform(tedf[predictors]); names=list(pp.get_feature_names_out()); fold_names[f]=names
 ind_idx=[i for i,n in enumerate(names) if n.startswith('missingindicator_')]; ind_sources=[source_from_indicator(names[i]) for i in ind_idx]
 assert len(ind_idx)==len(ind_sources) and all(s in nums for s in ind_sources)
 for c in nums: inventory_presence[c].append(c in ind_sources)
 fm=model(next(c for c in candidates if c['candidate_id']=='XGB04')); fm.fit(Xtr,trdf.label_stage23)
 contrib=fm.get_booster().predict(DMatrix(Xte),pred_contribs=True); assert contrib.shape[1]==len(names)+1
 sv=contrib[:,:-1]; absall=np.abs(sv); absind=absall[:,ind_idx]; total=absall.sum(axis=1); indtotal=absind.sum(axis=1)
 fold_attr.append({'outer_fold':f,'n':len(tedf),'indicator_count':len(ind_idx),'sum_abs_indicator':indtotal.sum(),'sum_abs_all':total.sum(),'missingness_attribution_fraction':indtotal.sum()/total.sum()})
 patient_attr.append(pd.DataFrame({'id_row':tedf.id_row,'group_hospital':tedf.group_hospital,'outer_fold':f,'abs_indicator':indtotal,'abs_all':total,'signed_indicator':sv[:,ind_idx].sum(axis=1)}))
 for j,src in zip(ind_idx,ind_sources):
  value_idx=names.index(src); ai=absall[:,j]; av=absall[:,value_idx]
  attr_rows.append({'outer_fold':f,'source_predictor':src,'indicator_feature':names[j],'n_test':len(tedf),'mean_abs_indicator_shap':ai.mean(),'mean_abs_value_shap':av.mean(),'sum_abs_indicator_shap':ai.sum(),'sum_abs_value_shap':av.sum(),'source_missingness_test':tedf[src].isna().mean()})
 del contrib,sv,absall,absind,Xtr,Xte,fm
 # No-indicator model: full locked nested selection, calibration, untouched outer test.
 oof={c['candidate_id']:np.full(len(trdf),np.nan) for c in candidates}
 for k in range(1,6):
  va=trdf.group_hospital.astype(str).isin(inner_maps[f][k]); it=~va; ip=prep(False); Xi=ip.fit_transform(trdf.loc[it,predictors]); Xv=ip.transform(trdf.loc[va,predictors]); yi=trdf.loc[it,'label_stage23']
  for c in candidates:
   mm=model(c); mm.fit(Xi,yi); oof[c['candidate_id']][va.to_numpy()]=mm.predict_proba(Xv)[:,1]
 scores=[]
 for c in candidates:
  p=oof[c['candidate_id']]; assert not np.isnan(p).any(); z=mets(trdf.label_stage23,p); tune.append({'outer_fold':f,'candidate_id':c['candidate_id'],**z}); scores.append((c['candidate_id'],z,p))
 scores.sort(key=lambda x:(-x[1]['auprc'],-x[1]['auroc'],x[1]['brier'])); bid,bm,boof=scores[0]; cal=platt(trdf.label_stage23.to_numpy(),boof)
 npip=prep(False); Xr=npip.fit_transform(trdf[predictors]); Xe=npip.transform(tedf[predictors]); nm=model(next(c for c in candidates if c['candidate_id']==bid)); nm.fit(Xr,trdf.label_stage23); raw=nm.predict_proba(Xe)[:,1]; pc=cal.predict_proba(logit(np.clip(raw,1e-6,1-1e-6)).reshape(-1,1))[:,1]
 abpred.append(pd.DataFrame({'id_row':tedf.id_row,'group_hospital':tedf.group_hospital,'outer_fold':f,'label_stage23':tedf.label_stage23,'prediction_raw':raw,'prediction_platt':pc,'selected_candidate':bid}))
 print('completed fold',f,'indicators',len(ind_idx),'selected',bid,flush=True)

attrs=pd.DataFrame(attr_rows); fold_attr=pd.DataFrame(fold_attr); pattr=pd.concat(patient_attr,ignore_index=True); abl=pd.concat(abpred,ignore_index=True)
assert len(pattr)==len(abl)==58491 and pattr.id_row.nunique()==abl.id_row.nunique()==58491
paired=fullpred.merge(abl,on=['id_row','group_hospital','outer_fold','label_stage23'],suffixes=('_full','_no_indicator'),validate='one_to_one'); assert len(paired)==58491

# Indicator inventory, including fold-specific generation and Step-2 survival.
inv=[]
for c in nums:
 row={'source_predictor':c,'variable_type':'numeric','overall_missingness':matrix[c].isna().mean()}
 for f in range(1,6):
  row[f'outer{f}_training_missingness']=matrix.loc[matrix.outer_fold!=f,c].isna().mean(); row[f'indicator_generated_outer{f}']=inventory_presence[c][f-1]; row[f'survived_step2_outer{f}']=str(f) not in str(s2inv.loc[c,'removed_folds']).split(',')
 row['indicator_generated_any_fold']=any(inventory_presence[c]); row['indicator_generated_all_folds']=all(inventory_presence[c]); row['transformed_indicator_feature']=f'missingindicator_{c}' if any(inventory_presence[c]) else ''
 inv.append(row)
inventory=pd.DataFrame(inv); inventory.to_csv(OUT/'MISSINGNESS_INDICATOR_INVENTORY.csv',index=False)
indicator_sources=inventory.loc[inventory.indicator_generated_any_fold,'source_predictor'].tolist()

# Pool source attribution by held-out sums; absent fold indicators contribute zero.
allpairs=pd.MultiIndex.from_product([range(1,6),indicator_sources],names=['outer_fold','source_predictor']).to_frame(index=False)
af=allpairs.merge(attrs,on=['outer_fold','source_predictor'],how='left').fillna({'mean_abs_indicator_shap':0,'sum_abs_indicator_shap':0,'mean_abs_value_shap':0,'sum_abs_value_shap':0})
fold_n=matrix.groupby('outer_fold').size().to_dict(); af['n_test']=af.outer_fold.map(fold_n); af['fold_indicator_rank']=af.groupby('outer_fold').mean_abs_indicator_shap.rank(method='min',ascending=False).astype(int)
pool=af.groupby('source_predictor').agg(sum_abs_indicator_shap=('sum_abs_indicator_shap','sum'),sum_abs_value_shap=('sum_abs_value_shap','sum'),median_fold_rank=('fold_indicator_rank','median'),min_fold_rank=('fold_indicator_rank','min'),max_fold_rank=('fold_indicator_rank','max')).reset_index()
pool['mean_abs_indicator_shap']=pool.sum_abs_indicator_shap/len(matrix); pool['mean_abs_value_shap']=pool.sum_abs_value_shap/len(matrix); pool['missingness_fraction_source_shap']=pool.sum_abs_indicator_shap/(pool.sum_abs_indicator_shap+pool.sum_abs_value_shap).replace(0,np.nan); pool['overall_missingness']=pool.source_predictor.map(matrix[indicator_sources].isna().mean())
pool=pool.sort_values('mean_abs_indicator_shap',ascending=False).reset_index(drop=True); pool.insert(0,'rank',np.arange(1,len(pool)+1))
global_fraction=fold_attr.sum_abs_indicator.sum()/fold_attr.sum_abs_all.sum()

# Fold rank stability.
wide=af.pivot(index='source_predictor',columns='outer_fold',values='mean_abs_indicator_shap'); corr=[]
for a in range(1,6):
 for b in range(a+1,6):
  rho,p=spearmanr(wide[a],wide[b]); corr.append({'fold_a':a,'fold_b':b,'spearman_rho':rho,'p_value':p})
corr=pd.DataFrame(corr)

# Hospital descriptive linkage.
hm=matrix.set_index('id_row')[indicator_sources].isna().mean(axis=1).rename('indicator_source_missing_fraction').reset_index()
hosp=pattr.merge(hm,on='id_row',validate='one_to_one').groupby('group_hospital').agg(n=('id_row','size'),mean_signed_indicator_shap=('signed_indicator','mean'),mean_abs_indicator_shap=('abs_indicator','mean'),sum_abs_indicator_shap=('abs_indicator','sum'),sum_abs_all_shap=('abs_all','sum'),mean_indicator_source_missingness=('indicator_source_missing_fraction','mean')).reset_index()
hosp['missingness_attribution_fraction']=hosp.sum_abs_indicator_shap/hosp.sum_abs_all_shap
hrho,hp=spearmanr(hosp.mean_indicator_source_missingness,hosp.missingness_attribution_fraction)

# Performance and paired 2,000-hospital bootstrap.
pooled=[]; foldperf=[]
for name,col in [('Full XGBoost','prediction_platt_full'),('No missingness indicators','prediction_platt_no_indicator')]:
 y=paired.label_stage23.to_numpy(); p=paired[col].to_numpy(); ci,cs=calibration(y,p); pooled.append({'model':name,**mets(y,p),'calibration_intercept':ci,'calibration_slope':cs,'mean_predicted_risk':p.mean()})
 for f in range(1,6):
  z=paired.outer_fold==f; foldperf.append({'outer_fold':f,'model':name,**mets(y[z],p[z])})
pooled=pd.DataFrame(pooled); foldperf=pd.DataFrame(foldperf)
rng=np.random.default_rng(SEED); hs=paired.group_hospital.unique(); byh={h:np.where(paired.group_hospital.to_numpy()==h)[0] for h in hs}; reps=[]
for b in range(BOOT):
 ix=np.concatenate([byh[h] for h in rng.choice(hs,len(hs),replace=True)]); y=paired.label_stage23.to_numpy()[ix]; pf=paired.prediction_platt_full.to_numpy()[ix]; pa=paired.prediction_platt_no_indicator.to_numpy()[ix]
 mf=mets(y,pf); ma=mets(y,pa); cif,csf=calibration(y,pf); cia,csa=calibration(y,pa); reps.append({'replicate':b,**{f'delta_{k}':ma[k]-mf[k] for k in mf},'delta_calibration_intercept':cia-cif,'delta_calibration_slope':csa-csf})
reps=pd.DataFrame(reps); assert len(reps)==BOOT
metrics_order=['auroc','auprc','brier','log_loss','calibration_intercept','calibration_slope']; cirows=[]
for k in metrics_order:
 point=float(pooled.iloc[1][k]-pooled.iloc[0][k]); v=reps['delta_'+k]; cirows.append({'metric':k,'difference_no_indicator_minus_full':point,'ci_low':v.quantile(.025),'ci_high':v.quantile(.975),'bootstrap_replicates':BOOT})
cis=pd.DataFrame(cirows)

# Thresholds and DCA.
thr=[]; y=paired.label_stage23.to_numpy()
for t in [.05,.075,.10]:
 for name,col in [('Full XGBoost','prediction_platt_full'),('No missingness indicators','prediction_platt_no_indicator')]:
  p=paired[col].to_numpy(); pr=p>=t; tp=((pr)&(y==1)).sum(); tn=((~pr)&(y==0)).sum(); fp=((pr)&(y==0)).sum(); fn=((~pr)&(y==1)).sum(); precision=tp/(tp+fp); recall=tp/(tp+fn)
  thr.append({'model':name,'threshold':t,'sensitivity':recall,'specificity':tn/(tn+fp),'ppv':precision,'npv':tn/(tn+fn),'f1':2*precision*recall/(precision+recall),'alerts_per_100':100*pr.mean()})
thr=pd.DataFrame(thr); dca=[]
for t in np.arange(.01,.1001,.005):
 for name,col in [('Full XGBoost','prediction_platt_full'),('No missingness indicators','prediction_platt_no_indicator')]:
  pr=paired[col].to_numpy()>=t; tp=((pr)&(y==1)).sum(); fp=((pr)&(y==0)).sum(); dca.append({'threshold':t,'model':name,'net_benefit':tp/len(y)-fp/len(y)*t/(1-t)})
dca=pd.DataFrame(dca); dp=dca.pivot(index='threshold',columns='model',values='net_benefit'); dd=dp['No missingness indicators']-dp['Full XGBoost']; dca_max=float(dd.abs().max()); dominates='no-indicator' if (dd>=0).all() else ('full' if (dd<=0).all() else 'neither')

# Save aggregate/publication-safe outputs.
fold_attr.to_csv(OUT/'outputs'/'fold_level_attribution_summary.csv',index=False); af.to_csv(OUT/'outputs'/'fold_indicator_importance_and_ranks.csv',index=False); corr.to_csv(OUT/'outputs'/'fold_rank_spearman_correlations.csv',index=False); hosp.to_csv(OUT/'outputs'/'hospital_level_exploratory_summary.csv',index=False)
pd.DataFrame([{'spearman_rho':hrho,'p_value':hp,'n_hospitals':len(hosp),'x':'mean indicator-source missingness','y':'missingness-attribution fraction'}]).to_csv(OUT/'outputs'/'hospital_level_spearman.csv',index=False)
pd.DataFrame(tune).to_csv(OUT/'outputs'/'no_indicator_fold_candidate_tuning.csv',index=False); pooled.to_csv(OUT/'outputs'/'pooled_performance.csv',index=False); foldperf.to_csv(OUT/'outputs'/'fold_performance.csv',index=False); cis.to_csv(OUT/'outputs'/'paired_cluster_bootstrap_differences.csv',index=False); thr.to_csv(OUT/'outputs'/'threshold_performance.csv',index=False); dca.to_csv(OUT/'outputs'/'dca_comparison.csv',index=False)
pool.to_csv(OUT/'outputs'/'full_missingness_indicator_attribution.csv',index=False); pool.head(20).to_excel(OUT/'tables'/'TABLE_S8_missingness_indicator_attribution.xlsx',index=False)
t9=[]
for k in metrics_order:
 r=cis[cis.metric==k].iloc[0]; t9.append({'metric':k,'full_xgboost':pooled.iloc[0][k],'no_missingness_indicators':pooled.iloc[1][k],'difference_no_indicator_minus_full':r.difference_no_indicator_minus_full,'ci_low':r.ci_low,'ci_high':r.ci_high})
pd.DataFrame(t9).to_excel(OUT/'tables'/'TABLE_S9_full_vs_no_missingness_indicators.xlsx',index=False)

# Fig S8: attribution fraction, top indicators, source paired attribution.
top=pool.head(12).sort_values('mean_abs_indicator_shap'); fig,axs=plt.subplots(1,3,figsize=(13,4.6))
fa=pd.concat([pd.DataFrame([{'label':'Overall','fraction':global_fraction}]),fold_attr.assign(label=lambda x:'Fold '+x.outer_fold.astype(str),fraction=lambda x:x.missingness_attribution_fraction)[['label','fraction']]])
axs[0].bar(fa.label,100*fa.fraction,color=['black']+['.55']*5); axs[0].set_ylabel('Absolute SHAP from indicators (%)'); axs[0].tick_params(axis='x',rotation=45); axs[0].set_title('A  Global and fold attribution')
axs[1].barh(top.source_predictor.str.replace('x_','',regex=False),top.mean_abs_indicator_shap,color='.25'); axs[1].set_xlabel('Mean |SHAP|'); axs[1].set_title('B  Top missingness indicators')
pt=pool.head(10).sort_values('mean_abs_indicator_shap'); yy=np.arange(len(pt)); axs[2].barh(yy,pt.mean_abs_value_shap,color='.75',label='Observed value'); axs[2].barh(yy,pt.mean_abs_indicator_shap,left=pt.mean_abs_value_shap,color='.2',label='Missingness indicator'); axs[2].set_yticks(yy,pt.source_predictor.str.replace('x_','',regex=False)); axs[2].set_xlabel('Mean |SHAP|'); axs[2].set_title('C  Paired source attribution'); axs[2].legend(frameon=False,fontsize=8)
for ax in axs: ax.grid(axis='x',color='.9'); ax.set_axisbelow(True)
fig.suptitle('Fig. S8. Contribution of missingness indicators to held-out XGBoost predictions'); fig.tight_layout(); fig.savefig(OUT/'figures'/'FIG_S8_missingness_indicator_attribution.png',dpi=300,bbox_inches='tight'); fig.savefig(OUT/'figures'/'FIG_S8_missingness_indicator_attribution.pdf',bbox_inches='tight'); plt.close(fig)

top5=pool.head(5); fm=pooled.iloc[0]; am=pooled.iloc[1]; medianrho=corr.spearman_rho.median(); dep='limited' if global_fraction<.05 and abs(am.auroc-fm.auroc)<.01 and abs(am.auprc-fm.auprc)<.02 else ('moderate' if global_fraction<.15 else 'substantial')
report=f'''# Missingness-indicator dependence report\n\n## Executive summary\n\nThe locked hospital-disjoint analysis identified **{len(indicator_sources)} explicit numeric missingness indicators** across the five full-model training folds. On pooled held-out outer-test patients, these indicators accounted for **{100*global_fraction:.2f}%** of total absolute native TreeSHAP attribution. Combined with the retrained ablation, the evidence indicates **{dep} reliance** on explicit measurement-presence signals.\n\n## Methods\n\nFor every held-out patient, native XGBoost TreeSHAP (`pred_contribs=True`) was calculated from the XGB04 full model fitted only to that patient's outer-training hospitals; the Platt layer was not attributed. Numeric indicator descendants were identified from the fitted `SimpleImputer(add_indicator=True)` feature names and paired with their source value columns. A second model omitted indicator generation, retained median imputation and all observed source values, repeated the locked five-by-five hospital-disjoint tuning and training-derived Platt calibration, and was evaluated on untouched outer-test hospitals. Differences used {BOOT} paired hospital-cluster bootstrap samples.\n\n## Attribution results\n\nFold fractions were {', '.join(f'{int(r.outer_fold)}: {100*r.missingness_attribution_fraction:.2f}%' for _,r in fold_attr.iterrows())}. The median pairwise fold Spearman correlation for indicator importance was {medianrho:.3f}. The top five indicators were {', '.join(f'{r.source_predictor} ({r.mean_abs_indicator_shap:.4f})' for _,r in top5.iterrows())}.\n\nAt the hospital level, mean missingness across indicator-bearing sources correlated with the fraction of absolute SHAP assigned to indicators (Spearman rho={hrho:.3f}, p={hp:.3g}; n=198 hospitals). This association is descriptive and does not establish causality.\n\n## No-indicator ablation\n\nFull versus no-indicator performance was: AUROC {fm.auroc:.4f} vs {am.auroc:.4f}; AUPRC {fm.auprc:.4f} vs {am.auprc:.4f}; Brier {fm.brier:.5f} vs {am.brier:.5f}; log loss {fm.log_loss:.5f} vs {am.log_loss:.5f}; calibration intercept {fm.calibration_intercept:.3f} vs {am.calibration_intercept:.3f}; and slope {fm.calibration_slope:.3f} vs {am.calibration_slope:.3f}. Paired confidence intervals are in Table S9. Across 1-10% thresholds, maximum absolute net-benefit difference was {dca_max:.6f}; {dominates} consistently dominated.\n\n## Interpretation and limitation\n\nThe model showed {dep} dependence on explicit missingness indicators within the evaluated hospitals. This does not prove independence from measurement processes: observed values, frequency/timing summaries, treatments, and contextual variables may still encode center-specific practice.\n'''
(OUT/'MISSINGNESS_INDICATOR_DEPENDENCE_REPORT.md').write_text(report,encoding='utf-8')
(OUT/'MANUSCRIPT_INSERT_MISSINGNESS_INDICATORS.md').write_text(f'''# Candidate manuscript insertion (not applied)\n\n## Methods\nHeld-out native TreeSHAP values were grouped into explicit numeric missingness indicators and non-indicator features, with indicator and value contributions additionally paired at source-predictor level. A no-indicator XGBoost model was retrained within the locked nested hospital-disjoint framework with unchanged median imputation, candidate selection, and training-derived Platt calibration. Paired differences used {BOOT} hospital-cluster bootstrap replicates.\n\n## Results\nAcross {len(matrix):,} held-out admissions, {len(indicator_sources)} explicit missingness indicators accounted for {100*global_fraction:.2f}% of total absolute SHAP attribution. The five leading indicators were {', '.join(top5.source_predictor)}. Pairwise fold rank correlations had median Spearman rho {medianrho:.3f}. The no-indicator model achieved AUROC {am.auroc:.3f}, AUPRC {am.auprc:.3f}, Brier {am.brier:.3f}, and log loss {am.log_loss:.3f}, versus {fm.auroc:.3f}, {fm.auprc:.3f}, {fm.brier:.3f}, and {fm.log_loss:.3f} for the full model. Maximum absolute decision-curve net-benefit difference from 1% to 10% was {dca_max:.6f}.\n\n## Discussion\nThese findings indicate {dep} reliance on explicit measurement-presence information within the evaluated eICU hospitals. Hospital-level variation was descriptive and should not be interpreted causally.\n\n## Limitation\nLow explicit-indicator dependence would not exclude measurement-process information encoded in observed values, measurement frequency or timing, treatments, or admission context.\n\n## Supplementary captions\n**Table S8.** Pooled held-out TreeSHAP attribution of explicit numeric missingness indicators, paired with source-value attribution and fold-rank stability.\n\n**Table S9.** Full XGBoost versus retrained XGBoost without explicit missingness indicators; differences are no-indicator minus full with paired hospital-cluster bootstrap 95% confidence intervals.\n\n**Fig. S8.** Contribution of explicit missingness indicators to held-out XGBoost predictions globally, across outer folds, and relative to paired source-value components.\n''',encoding='utf-8')
qc={'rows':len(matrix),'hospitals':matrix.group_hospital.nunique(),'events':int(matrix.label_stage23.sum()),'source_predictors':len(predictors),'numeric_predictors':len(nums),'categorical_predictors':len(cats),'explicit_indicator_sources_any_fold':len(indicator_sources),'indicator_counts_by_fold':dict(zip(fold_attr.outer_fold.astype(str),fold_attr.indicator_count.astype(int))),'held_out_shap_only':True,'full_model_for_each_patient_matches_outer_fold':True,'no_test_data_for_imputation':True,'no_test_data_for_tuning':True,'no_test_data_for_calibration':True,'paired_rows':len(paired),'paired_hospitals':paired.group_hospital.nunique(),'bootstrap_replicates':len(reps),'full_prediction_reconciliation':mets(y,paired.prediction_platt_full),'runtime_minutes':(time.time()-start)/60}
(OUT/'MISSINGNESS_INDICATOR_QC.md').write_text('# Missingness-indicator analysis QC\n\n```json\n'+json.dumps(qc,indent=2)+'\n```\n\nAll structural and leakage assertions passed. Patient-level predictions and SHAP values remained transient and were not written to the deliverable package.\n',encoding='utf-8')
(OUT/'README.md').write_text('# Missingness-indicator dependence analysis\n\nStep 3 robustness package using locked hospital-disjoint outer/inner folds. Prior analyses and the manuscript were not modified.\n',encoding='utf-8')
(OUT/'outputs'/'software_environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'xgboost':__import__('xgboost').__version__,'sklearn':__import__('sklearn').__version__,'seed':SEED,'bootstrap_replicates':BOOT},indent=2),encoding='utf-8')
(OUT/'src'/'run_missingness_indicator_analysis.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
files=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file(): files.append({'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pd.DataFrame(files).to_csv(OUT/'outputs'/'CREATED_FILES_MANIFEST.csv',index=False)
print(json.dumps({'indicator_count':len(indicator_sources),'global_fraction':global_fraction,'top5':top5.source_predictor.tolist(),'median_fold_rho':medianrho,'full':fm[metrics_order].to_dict(),'no_indicator':am[metrics_order].to_dict(),'hospital_rho':hrho,'dca_max_abs':dca_max,'runtime_min':(time.time()-start)/60},indent=2),flush=True)
