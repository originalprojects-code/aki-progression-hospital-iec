import os,sys,json,time,platform
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from scipy.special import expit,logit
from google.cloud import bigquery
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
from xgboost import XGBClassifier

SEED=20260721; BOOT=2000; PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DS=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2')
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_high_missingness_ablation'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']:d.mkdir(parents=True,exist_ok=True)
client=bigquery.Client(project=PROJECT,location='US'); start=time.time()
matrix=client.query(f'SELECT * FROM `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1`').to_dataframe()
full=client.query(f'SELECT * FROM `{PROJECT}.{DS}.model_xgb_outer_predictions_all5_v1`').to_dataframe()
meta=['id_row','group_hospital','label_stage23','outer_fold']; predictors=[c for c in matrix.columns if c not in meta]
cats=['x_sex','x_unit_type','x_unit_admit_source']; nums=[c for c in predictors if c not in cats]
assert len(matrix)==58491 and matrix.group_hospital.nunique()==198 and matrix.label_stage23.sum()==3032
assert len(predictors)==159 and len(nums)==156 and len(cats)==3
assert len(full)==58491 and full.id_row.nunique()==58491

# Exact locked inner validation-hospital maps recovered from manuscript checkpoint tables.
inner_maps={}
for f in range(1,6):
 inner_maps[f]={}
 seen=set()
 for k in range(1,6):
  q=f'SELECT DISTINCT m.group_hospital FROM `{PROJECT}.{DS}.model_xgb_inner_oof_outer{f}_inner{k}_v1` p JOIN `{PROJECT}.{DS}.feature_matrix_core_outerfold_v1` m USING(id_row)'
  hs=set(client.query(q).to_dataframe().group_hospital.astype(str)); inner_maps[f][k]=hs; assert not seen&hs;seen|=hs
 assert seen==set(matrix.loc[matrix.outer_fold!=f,'group_hospital'].astype(str).unique())

candidates=[
dict(candidate_id='XGB01',n_estimators=250,max_depth=2,learning_rate=.03,min_child_weight=5,subsample=.8,colsample_bytree=.8,gamma=0,reg_alpha=0,reg_lambda=5),
dict(candidate_id='XGB02',n_estimators=350,max_depth=3,learning_rate=.03,min_child_weight=5,subsample=.8,colsample_bytree=.8,gamma=0,reg_alpha=0,reg_lambda=5),
dict(candidate_id='XGB03',n_estimators=450,max_depth=3,learning_rate=.02,min_child_weight=10,subsample=.85,colsample_bytree=.85,gamma=0,reg_alpha=.1,reg_lambda=10),
dict(candidate_id='XGB04',n_estimators=350,max_depth=4,learning_rate=.03,min_child_weight=10,subsample=.8,colsample_bytree=.8,gamma=.1,reg_alpha=.1,reg_lambda=10),
dict(candidate_id='XGB05',n_estimators=450,max_depth=2,learning_rate=.02,min_child_weight=10,subsample=.9,colsample_bytree=.9,gamma=0,reg_alpha=.5,reg_lambda=10),
dict(candidate_id='XGB06',n_estimators=450,max_depth=4,learning_rate=.02,min_child_weight=15,subsample=.9,colsample_bytree=.8,gamma=.2,reg_alpha=.5,reg_lambda=15)]
def prep(cols):
 n=[c for c in cols if c not in cats]; ca=[c for c in cols if c in cats]
 return ColumnTransformer([('numeric',Pipeline([('imputer',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True))]),n),('categorical',Pipeline([('imputer',SimpleImputer(strategy='constant',fill_value='__MISSING__',keep_empty_features=True)),('onehot',OneHotEncoder(handle_unknown='ignore',sparse_output=True,dtype=np.float32))]),ca)],remainder='drop',sparse_threshold=1.0,verbose_feature_names_out=False)
def model(c):
 z={k:v for k,v in c.items() if k!='candidate_id'}
 return XGBClassifier(**z,objective='binary:logistic',eval_metric='logloss',tree_method='hist',max_bin=256,scale_pos_weight=1.0,importance_type='gain',random_state=SEED,n_jobs=-1,verbosity=0)
def metrics(y,p):return {'auroc':roc_auc_score(y,p),'auprc':average_precision_score(y,p),'brier':brier_score_loss(y,p)}
def platt_fit(y,p):
 m=LogisticRegression(penalty=None,solver='lbfgs',max_iter=2000);m.fit(logit(np.clip(p,1e-6,1-1e-6)).reshape(-1,1),y);return m
def calis(y,p):
 m=platt_fit(y,p);return float(m.intercept_[0]),float(m.coef_[0,0])

fold_sparse={}; tune_rows=[]; pred_rows=[]
for f in range(1,6):
 tr=matrix.outer_fold!=f;te=~tr; miss=matrix.loc[tr,predictors].isna().mean(); sparse=sorted(miss[miss>=.5].index); retained=[c for c in predictors if c not in sparse];fold_sparse[f]=sparse
 assert set(sparse).isdisjoint(retained) and len(sparse)+len(retained)==159
 oof={c['candidate_id']:np.full(tr.sum(),np.nan) for c in candidates};trdf=matrix.loc[tr].reset_index(drop=True)
 for k in range(1,6):
  va=trdf.group_hospital.astype(str).isin(inner_maps[f][k]);it=~va
  pp=prep(retained);Xit=pp.fit_transform(trdf.loc[it,retained]);Xva=pp.transform(trdf.loc[va,retained]);yit=trdf.loc[it,'label_stage23'].to_numpy();yva=trdf.loc[va,'label_stage23'].to_numpy()
  for c in candidates:
   m=model(c);m.fit(Xit,yit);oof[c['candidate_id']][va.to_numpy()]=m.predict_proba(Xva)[:,1]
 scores=[]
 for c in candidates:
  p=oof[c['candidate_id']];assert not np.isnan(p).any();z=metrics(trdf.label_stage23,p);scores.append((c['candidate_id'],z,p));tune_rows.append({'outer_fold':f,'candidate_id':c['candidate_id'],**z})
 scores.sort(key=lambda x:(-x[1]['auprc'],-x[1]['auroc'],x[1]['brier']));best_id,bestmet,bestoof=scores[0];best=next(c for c in candidates if c['candidate_id']==best_id);cal=platt_fit(trdf.label_stage23.to_numpy(),bestoof)
 pp=prep(retained);Xtr=pp.fit_transform(matrix.loc[tr,retained]);Xte=pp.transform(matrix.loc[te,retained]);m=model(best);m.fit(Xtr,matrix.loc[tr,'label_stage23']);raw=m.predict_proba(Xte)[:,1];pc=cal.predict_proba(logit(np.clip(raw,1e-6,1-1e-6)).reshape(-1,1))[:,1]
 for idx,r,p0,p1 in zip(matrix.index[te],matrix.loc[te].itertuples(),raw,pc):pred_rows.append({'id_row':r.id_row,'group_hospital':r.group_hospital,'outer_fold':f,'label_stage23':r.label_stage23,'prediction_raw':p0,'prediction_platt':p1,'selected_candidate':best_id,'removed_predictors':len(sparse)})
 pd.DataFrame({'predictor':sparse,'training_missingness':[miss[x] for x in sparse]}).to_csv(OUT/'outputs'/f'fold{f}_sparse_predictors.csv',index=False)

abl=pd.DataFrame(pred_rows);assert len(abl)==58491 and abl.id_row.nunique()==58491
paired=full.merge(abl,on=['id_row','group_hospital','outer_fold','label_stage23'],suffixes=('_full','_ablation'),validate='one_to_one');assert len(paired)==58491
# Save publication-safe aggregate results only; patient predictions stay transient.
pd.DataFrame(tune_rows).to_csv(OUT/'outputs'/'fold_candidate_tuning_results.csv',index=False)

# Predictor inventory and hospital availability.
inv=[]
for c in predictors:
 overall=matrix[c].isna().mean(); hm=matrix.groupby('group_hospital')[c].apply(lambda x:x.isna().mean())
 domain='Demographics/context' if c in ['x_age_years','x_sex','x_bmi','x_unit_type','x_unit_admit_source'] else ('Laboratory' if c.startswith('x_lab_') or c in ['x_reference_creatinine','x_stage1_at_landmark'] else 'Vitals')
 source='feature_static_v1' if domain=='Demographics/context' or c in ['x_reference_creatinine','x_stage1_at_landmark'] else ('feature_labs_v1' if domain=='Laboratory' else 'feature_vitals_v1')
 removed=[str(f) for f in range(1,6) if c in fold_sparse[f]]
 inv.append({'predictor':c,'clinical_domain':domain,'data_type':'categorical' if c in cats else 'numeric','source_table_field':source,'extraction_window':'admission/0–12 h','overall_missingness':overall,'min_hospital_missingness':hm.min(),'max_hospital_missingness':hm.max(),'hospitals_completely_unavailable':int((hm==1).sum()),'missingness_indicator_generated':'No; missing level' if c in cats else 'Yes when missing in training','removed_folds':','.join(removed),'removed_fold_count':len(removed),'retained_all_folds':len(removed)==0})
inventory=pd.DataFrame(inv);assert len(inventory)==159;inventory.to_csv(OUT/'HIGH_MISSINGNESS_PREDICTOR_INVENTORY.csv',index=False)
global_sparse=inventory.loc[inventory.overall_missingness>=.5,'predictor'].tolist()
foldtab=inventory[inventory.removed_fold_count>0].copy();foldtab.to_csv(OUT/'tables'/'TABLE_S7_sparse_predictors.csv',index=False)

# Metrics.
pooled=[];foldperf=[]
for name,col in [('Full XGBoost','prediction_platt_full'),('High-missingness ablation','prediction_platt_ablation')]:
 y=paired.label_stage23.to_numpy();p=paired[col].to_numpy();ci,cs=calis(y,p);pooled.append({'model':name,**metrics(y,p),'calibration_intercept':ci,'calibration_slope':cs,'mean_predicted_risk':p.mean()})
 for f in range(1,6):
  z=paired.outer_fold==f;foldperf.append({'outer_fold':f,'model':name,**metrics(y[z],p[z])})
pooled=pd.DataFrame(pooled);foldperf=pd.DataFrame(foldperf);pooled.to_csv(OUT/'outputs'/'pooled_performance.csv',index=False);foldperf.to_csv(OUT/'outputs'/'fold_specific_performance.csv',index=False)

# Paired hospital cluster bootstrap, exact 2000 replicates.
rng=np.random.default_rng(SEED);hosp=paired.group_hospital.unique();byh={h:np.where(paired.group_hospital.to_numpy()==h)[0] for h in hosp};breps=[]
for b in range(BOOT):
 sampled=rng.choice(hosp,size=len(hosp),replace=True);ix=np.concatenate([byh[h] for h in sampled]);y=paired.label_stage23.to_numpy()[ix];pf=paired.prediction_platt_full.to_numpy()[ix];pa=paired.prediction_platt_ablation.to_numpy()[ix]
 if len(np.unique(y))<2:continue
 mf=metrics(y,pf);ma=metrics(y,pa);cif,csf=calis(y,pf);cia,csa=calis(y,pa);breps.append({'replicate':b,**{f'delta_{k}':ma[k]-mf[k] for k in mf},'delta_calibration_intercept':cia-cif,'delta_calibration_slope':csa-csf})
breps=pd.DataFrame(breps);assert len(breps)==BOOT
point={k:pooled.iloc[1][k]-pooled.iloc[0][k] for k in ['auroc','auprc','brier','calibration_intercept','calibration_slope']}
cirows=[]
for k,v in point.items():
 vals=breps['delta_'+k];cirows.append({'metric':k,'difference_ablation_minus_full':v,'ci_low':vals.quantile(.025),'ci_high':vals.quantile(.975),'bootstrap_replicates':BOOT})
cis=pd.DataFrame(cirows);cis.to_csv(OUT/'outputs'/'paired_cluster_bootstrap_differences.csv',index=False)

# Threshold 5% and DCA/calibration data.
thr=[]
for name,col in [('Full XGBoost','prediction_platt_full'),('High-missingness ablation','prediction_platt_ablation')]:
 y=paired.label_stage23.to_numpy();p=paired[col].to_numpy();pr=p>=.05;tp=((pr)&(y==1)).sum();tn=((~pr)&(y==0)).sum();fp=((pr)&(y==0)).sum();fn=((~pr)&(y==1)).sum();thr.append({'model':name,'threshold':.05,'sensitivity':tp/(tp+fn),'specificity':tn/(tn+fp),'ppv':tp/(tp+fp),'npv':tn/(tn+fn),'alerts_per_100':100*pr.mean()})
pd.DataFrame(thr).to_csv(OUT/'outputs'/'threshold_5pct_performance.csv',index=False)
dca=[];y=paired.label_stage23.to_numpy();n=len(y)
for t in np.arange(.005,.1501,.005):
 for name,col in [('Full XGBoost','prediction_platt_full'),('High-missingness ablation','prediction_platt_ablation')]:
  pr=paired[col].to_numpy()>=t;tp=((pr)&(y==1)).sum();fp=((pr)&(y==0)).sum();dca.append({'threshold':t,'model':name,'net_benefit':tp/n-fp/n*t/(1-t)})
 dca += [{'threshold':t,'model':'Treat all','net_benefit':y.mean()-(1-y.mean())*t/(1-t)},{'threshold':t,'model':'Treat none','net_benefit':0}]
pd.DataFrame(dca).to_csv(OUT/'outputs'/'dca_comparison.csv',index=False)
cal=[]
for name,col in [('Full XGBoost','prediction_platt_full'),('High-missingness ablation','prediction_platt_ablation')]:
 z=pd.DataFrame({'y':y,'p':paired[col]});z['bin']=pd.qcut(z.p,10,duplicates='drop');g=z.groupby('bin',observed=True).agg(n=('y','size'),mean_predicted=('p','mean'),observed=('y','mean')).reset_index(drop=True);g['model']=name;g['decile']=range(1,len(g)+1);cal.append(g)
pd.concat(cal).to_csv(OUT/'outputs'/'calibration_deciles.csv',index=False)

# Tables and figure.
display={'auroc':'AUROC','auprc':'AUPRC','brier':'Brier score','calibration_intercept':'Calibration intercept','calibration_slope':'Calibration slope'};t6=[]
for k,label in display.items():
 r=cis[cis.metric==k].iloc[0];t6.append({'Metric':label,'Full XGBoost':pooled.iloc[0][k],'High-missingness ablation':pooled.iloc[1][k],'Difference (ablation − full)':r.difference_ablation_minus_full,'95% CI low':r.ci_low,'95% CI high':r.ci_high})
pd.DataFrame(t6).to_csv(OUT/'tables'/'TABLE_S6_full_vs_ablation.csv',index=False);pd.DataFrame(t6).to_excel(OUT/'tables'/'TABLE_S6_full_vs_ablation.xlsx',index=False)
fig,axs=plt.subplots(1,2,figsize=(8,4));
for ax,met,title in zip(axs,['auroc','auprc'],['AUROC','AUPRC']):
 piv=foldperf.pivot(index='outer_fold',columns='model',values=met);ax.plot(piv.index,piv['Full XGBoost'],'o-',color='black',label='Full');ax.plot(piv.index,piv['High-missingness ablation'],'s--',color='.45',label='Ablation');ax.set_xlabel('Outer fold');ax.set_ylabel(title);ax.set_xticks(range(1,6));ax.grid(color='.9');ax.legend(frameon=False)
fig.suptitle('Fig. S7. Effect of removing highly sparse predictors');fig.tight_layout();fig.savefig(OUT/'figures'/'FIG_S7_fold_performance.png',dpi=300);fig.savefig(OUT/'figures'/'FIG_S7_fold_performance.pdf');plt.close(fig)

# Interpretation and reports.
always=inventory.loc[inventory.removed_fold_count==5,'predictor'].tolist();variable=inventory.loc[inventory.removed_fold_count.between(1,4),'predictor'].tolist();dauc=point['auroc'];dap=point['auprc'];db=point['brier'];dep='little' if abs(dauc)<.01 and abs(dap)<.02 and abs(db)<.005 else ('moderate' if abs(dauc)<.03 and abs(dap)<.05 else 'substantial')
fold_counts={f:len(fold_sparse[f]) for f in fold_sparse};fullm=pooled.iloc[0];ablm=pooled.iloc[1]
report=f'''# High-missingness predictor ablation report\n\n## Executive summary\n\nThe analysis found **{dep} dependence** of primary XGBoost performance on source predictors with ≥50% training-fold missingness. This does not establish independence from measurement-process signals among retained predictors.\n\n## Predictor inventory\n\nThe locked registry reconciled exactly to 159 source predictors (156 numeric, 3 categorical). The manuscript-level full-cohort list contained {len(global_sparse)} predictors with ≥50% missingness. Training-only fold removal counts were {fold_counts}. {len(always)} predictors were removed in every fold and {len(variable)} were threshold-dependent across folds.\n\nConsistently removed predictors: {', '.join(always)}.\n\nFold-variable predictors: {', '.join(variable) if variable else 'None'}.\n\n## Methods\n\nFor each locked outer fold, missingness was calculated only in outer-training hospitals. Predictors with training missingness ≥50% were removed before preprocessing, including all descendants. The original six-candidate XGBoost grid was retuned by pooled inner hospital-disjoint OOF AUPRC, with AUROC and Brier tie-breakers. Numeric median imputation with missing indicators, categorical constant imputation/one-hot encoding, and independent Platt calibration from selected-candidate inner OOF logits reproduced the manuscript architecture. Evaluation used untouched outer-test hospitals. Paired uncertainty used {BOOT} hospital-cluster bootstrap replicates.\n\n## Results\n\n- Full calibrated XGBoost: AUROC {fullm.auroc:.4f}, AUPRC {fullm.auprc:.4f}, Brier {fullm.brier:.5f}, calibration intercept {fullm.calibration_intercept:.3f}, slope {fullm.calibration_slope:.3f}.\n- Ablation: AUROC {ablm.auroc:.4f}, AUPRC {ablm.auprc:.4f}, Brier {ablm.brier:.5f}, calibration intercept {ablm.calibration_intercept:.3f}, slope {ablm.calibration_slope:.3f}.\n\nPaired differences and 95% CIs are in Table S6. Fold-specific performance, 5% threshold behavior, DCA data, and calibration deciles are provided as reproducible aggregate outputs.\n\n## Interpretation\n\nThe observed changes indicate {dep} incremental dependence on highly sparse predictors. Conclusions are restricted to the locked cohort and hospital-disjoint design.\n\n## Limitations\n\nAblation at one missingness threshold does not prove that retained predictors or their missingness indicators are free of measurement-process information. XGBoost was rerun with the recorded protocol but current software versions; this is documented in QC. Dedicated missingness-indicator attribution was not performed.\n'''
(OUT/'HIGH_MISSINGNESS_ABLATION_REPORT.md').write_text(report,encoding='utf-8')
(OUT/'MANUSCRIPT_INSERT_HIGH_MISSINGNESS_ABLATION.md').write_text(f'''# Candidate manuscript insertion (not applied)\n\n## Methods\n\nIn each outer training fold, source predictors with ≥50% training-fold missingness were removed before preprocessing and model development. The original nested hospital-disjoint tuning and training-derived Platt calibration procedures were repeated, and paired differences were estimated with {BOOT} hospital-cluster bootstrap replicates.\n\n## Results\n\nThe high-missingness ablation achieved AUROC {ablm.auroc:.3f}, AUPRC {ablm.auprc:.3f}, and Brier score {ablm.brier:.3f}, compared with {fullm.auroc:.3f}, {fullm.auprc:.3f}, and {fullm.brier:.3f} for the full model. The results indicated {dep} dependence on predictors meeting the prespecified sparsity threshold.\n\n## Discussion\n\nRemoving highly sparse source predictors produced {dep} performance change, informing transportability to settings where these measurements are unavailable. This analysis does not determine the contribution of missingness indicators among retained predictors.\n\n## Table S6 caption\n\nTable S6. Performance of the full XGBoost model and training-fold-specific high-missingness predictor ablation. Differences are ablation minus full model with paired hospital-cluster bootstrap 95% confidence intervals.\n\n## Table S7 caption\n\nTable S7. Source predictors excluded when outer-training-fold missingness was ≥50%.\n\n## Figure S7 caption\n\nFig. S7. Fold-specific AUROC and AUPRC for full and high-missingness-ablation XGBoost models under locked hospital-disjoint validation.\n''',encoding='utf-8')
qc={'rows':len(matrix),'hospitals':matrix.group_hospital.nunique(),'events':int(matrix.label_stage23.sum()),'predictors':len(predictors),'folds':sorted(matrix.outer_fold.unique().tolist()),'full_prediction_rows':len(full),'paired_rows':len(paired),'bootstrap_replicates':len(breps),'test_data_used_for_threshold':False,'test_data_used_for_preprocessing':False,'test_data_used_for_tuning':False,'test_data_used_for_calibration':False,'fold_removed_counts':fold_counts,'runtime_minutes':(time.time()-start)/60}
(OUT/'HIGH_MISSINGNESS_ABLATION_QC.md').write_text('# High-missingness ablation QC\n\n```json\n'+json.dumps(qc,indent=2)+'\n```\n\nAll mandatory structural assertions passed. Patient-level predictions were not written to the local manuscript package; only aggregate publication-safe outputs were saved.\n',encoding='utf-8')
(OUT/'README.md').write_text('# High-missingness predictor ablation\n\nSeparate robustness package. The prior selection-bias analysis and primary manuscript were not modified. Run `src/run_high_missingness_ablation.py` with authorized BigQuery ADC.\n',encoding='utf-8')
(OUT/'outputs'/'software_environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'xgboost':__import__('xgboost').__version__,'sklearn':__import__('sklearn').__version__,'seed':SEED,'bootstrap_replicates':BOOT},indent=2),encoding='utf-8')
(OUT/'src'/'run_high_missingness_ablation.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
files=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file():files.append({'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size})
pd.DataFrame(files).to_csv(OUT/'outputs'/'CREATED_FILES_MANIFEST.csv',index=False)
print(json.dumps({'fold_removed_counts':fold_counts,'always_removed':len(always),'variable_removed':len(variable),'full':fullm[['auroc','auprc','brier']].to_dict(),'ablation':ablm[['auroc','auprc','brier']].to_dict(),'interpretation':dep,'runtime_min':(time.time()-start)/60},indent=2))
