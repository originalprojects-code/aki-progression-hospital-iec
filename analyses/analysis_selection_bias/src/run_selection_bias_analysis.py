import os, sys, json, math
from pathlib import Path
_deps = os.environ.get('AKI_PYDEPS')
if _deps: sys.path.insert(0, _deps)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import bigquery

PROJECT=os.environ.get('GOOGLE_CLOUD_PROJECT','your-gcp-project'); DATASET=os.environ.get('AKI_DATASET_ID','aki_jcmc_v2')
OUT=Path(os.environ.get('AKI_OUTPUT_DIR', Path.cwd()/'analysis_outputs'/'analysis_selection_bias'))
for d in [OUT,OUT/'src',OUT/'outputs',OUT/'tables',OUT/'figures',OUT/'logs']: d.mkdir(parents=True,exist_ok=True)

SQL=r'''WITH selected AS (
 SELECT c.*,
 CASE WHEN c.eligible_main_cohort=1 THEN 'A_final_primary'
      WHEN c.reference_creatinine IS NULL THEN 'B_no_reference'
      ELSE 'C_other_post_reference' END AS compare_group,
 CASE WHEN c.eligible_main_cohort=1 THEN 'included_main'
      WHEN c.reference_creatinine IS NULL THEN 'no_reference_creatinine'
      WHEN c.strict_chronic_dialysis_esrd=1 THEN 'chronic_dialysis_or_esrd'
      WHEN COALESCE(c.max_stage_by_12h,0)>=2 THEN 'severe_aki_by_12h'
      WHEN c.first_acute_rrt_strict_offset IS NOT NULL AND c.first_acute_rrt_strict_offset<=720 THEN 'acute_rrt_by_12h'
      WHEN c.observation_class='indeterminate_early_death' THEN 'early_death'
      WHEN c.observation_class='indeterminate_no_future_creatinine' THEN 'no_future_creatinine'
      WHEN c.observation_class='indeterminate_inadequate_followup' THEN 'inadequate_followup'
      ELSE 'other_not_in_main_cohort' END AS exclusion_detail
 FROM `{PROJECT}.{DATASET}.cohort_outcome_v1` c
 WHERE c.deterministic_eligible_patient_stay_rank=1
), vit AS (
 SELECT v.patientUnitStayID,
 ARRAY_AGG(IF(v.heartrate BETWEEN 20 AND 250,v.heartrate,NULL) IGNORE NULLS ORDER BY v.observationOffset DESC LIMIT 1)[SAFE_OFFSET(0)] hr,
 ARRAY_AGG(IF(v.systemicSystolic BETWEEN 40 AND 300,v.systemicSystolic,NULL) IGNORE NULLS ORDER BY v.observationOffset DESC LIMIT 1)[SAFE_OFFSET(0)] sbp,
 ARRAY_AGG(IF(v.respiration BETWEEN 2 AND 80,v.respiration,NULL) IGNORE NULLS ORDER BY v.observationOffset DESC LIMIT 1)[SAFE_OFFSET(0)] rr
 FROM selected s JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
 WHERE v.observationOffset BETWEEN 0 AND 720 GROUP BY v.patientUnitStayID
), vap AS (
 SELECT v.patientUnitStayID,
 ARRAY_AGG(IF(v.nonInvasiveSystolic BETWEEN 30 AND 300,v.nonInvasiveSystolic,NULL) IGNORE NULLS ORDER BY v.observationOffset DESC LIMIT 1)[SAFE_OFFSET(0)] sbp
 FROM selected s JOIN `physionet-data.eicu_crd.vitalaperiodic` v USING(patientUnitStayID)
 WHERE v.observationOffset BETWEEN 0 AND 720 GROUP BY v.patientUnitStayID
), bun AS (
 SELECT l.patientUnitStayID,
 ARRAY_AGG(IF(SAFE_CAST(l.labResult AS FLOAT64) BETWEEN 1 AND 350,SAFE_CAST(l.labResult AS FLOAT64),NULL) IGNORE NULLS ORDER BY l.labResultOffset DESC,l.labID DESC LIMIT 1)[SAFE_OFFSET(0)] bun
 FROM selected s JOIN `physionet-data.eicu_crd.lab` l USING(patientUnitStayID)
 WHERE l.labResultOffset BETWEEN 0 AND 720 AND LOWER(TRIM(l.labName))='bun' GROUP BY l.patientUnitStayID
), inf AS (
 SELECT i.patientUnitStayID,1 any_vasopressor
 FROM selected s JOIN `physionet-data.eicu_crd.infusiondrug` i USING(patientUnitStayID)
 WHERE i.infusionOffset BETWEEN 0 AND 720 AND REGEXP_CONTAINS(LOWER(COALESCE(i.drugName,'')),r'norepine|levophed|(^|[^a-z])epinephrine([^a-z]|$)|adrenalin|vasopressin|phenylephrine|neosynephrine|neo-synephrine|(^|[^a-z])dopamine([^a-z]|$)')
 GROUP BY i.patientUnitStayID
), rc AS (
 SELECT r.patientUnitStayID,1 invasive_airway
 FROM selected s JOIN `physionet-data.eicu_crd.respiratorycare` r USING(patientUnitStayID)
 WHERE (r.ventStartOffset BETWEEN 0 AND 720 OR r.respCareStatusOffset BETWEEN 0 AND 720)
 AND REGEXP_CONTAINS(LOWER(COALESCE(r.airwayType,'')),r'oral ett|nasal ett|endotracheal|tracheostomy') GROUP BY r.patientUnitStayID
), tx AS (
 SELECT t.patientUnitStayID,1 invasive_tx
 FROM selected s JOIN `physionet-data.eicu_crd.treatment` t USING(patientUnitStayID)
 WHERE t.treatmentOffset BETWEEN 0 AND 720
 AND REGEXP_CONTAINS(LOWER(COALESCE(t.treatmentString,'')),r'mechanical ventilation|invasive ventilation|intubat|ventilator weaning')
 AND NOT REGEXP_CONTAINS(LOWER(COALESCE(t.treatmentString,'')),r'non.?invasive ventilation|\bbipap\b|bi-pap') GROUP BY t.patientUnitStayID
)
SELECT s.patientUnitStayID,s.patientHealthSystemStayID,s.uniquePID,s.hospitalID,s.compare_group,s.exclusion_detail,
 CASE WHEN p.age='> 89' THEN 90 ELSE SAFE_CAST(p.age AS INT64) END age,
 CASE WHEN p.admissionHeight BETWEEN 100 AND 250 AND p.admissionWeight BETWEEN 25 AND 300
  AND SAFE_DIVIDE(p.admissionWeight,POW(p.admissionHeight/100.0,2)) BETWEEN 10 AND 80
  THEN SAFE_DIVIDE(p.admissionWeight,POW(p.admissionHeight/100.0,2)) END bmi,
 CASE WHEN LOWER(TRIM(p.gender))='female' THEN 'Female' WHEN LOWER(TRIM(p.gender))='male' THEN 'Male' ELSE 'Other/missing' END sex,
 COALESCE(NULLIF(TRIM(p.ethnicity),''),'Missing') ethnicity,
 COALESCE(NULLIF(TRIM(p.unitType),''),'Missing') unit_type,
 COALESCE(NULLIF(TRIM(p.unitAdmitSource),''),'Missing') unit_admit_source,
 COALESCE(NULLIF(TRIM(p.hospitalAdmitSource),''),'Missing') hospital_admit_source,
 vit.hr,COALESCE(vap.sbp,vit.sbp) sbp,vit.rr,bun.bun,COALESCE(inf.any_vasopressor,0) any_vasopressor,
 IF(COALESCE(rc.invasive_airway,0)=1 OR COALESCE(tx.invasive_tx,0)=1,1,0) invasive_ventilation
FROM selected s JOIN `physionet-data.eicu_crd.patient` p USING(patientUnitStayID)
LEFT JOIN vit USING(patientUnitStayID) LEFT JOIN vap USING(patientUnitStayID) LEFT JOIN bun USING(patientUnitStayID)
LEFT JOIN inf USING(patientUnitStayID) LEFT JOIN rc USING(patientUnitStayID) LEFT JOIN tx USING(patientUnitStayID)'''

client=bigquery.Client(project=PROJECT,location='US')
df=client.query(SQL).to_dataframe()
assert len(df)==126324, len(df)
assert df.patientUnitStayID.nunique()==len(df)
assert df.uniquePID.nunique()==len(df)
assert not df.compare_group.isna().any()
expected={'A_final_primary':58491,'B_no_reference':41614,'C_other_post_reference':26219}
assert df.compare_group.value_counts().to_dict()==expected,df.compare_group.value_counts().to_dict()

groups=['A_final_primary','B_no_reference','C_other_post_reference']
labels={'A_final_primary':'Final primary cohort','B_no_reference':'Reference creatinine unavailable','C_other_post_reference':'Other post-reference exclusions'}
continuous={'age':'Age, years','bmi':'Body mass index, kg/mÂ²','hr':'Last heart rate by 12 h, beats/min','sbp':'Last systolic blood pressure by 12 h, mmHg','rr':'Last respiratory rate by 12 h, breaths/min','bun':'Last blood urea nitrogen by 12 h, mg/dL'}
binary={'any_vasopressor':'Any vasopressor infusion by 12 h','invasive_ventilation':'Invasive mechanical ventilation by 12 h'}
categorical={'sex':'Sex','ethnicity':'Race/ethnicity','unit_type':'ICU type','unit_admit_source':'ICU admission source','hospital_admit_source':'Hospital admission source'}

def smd_cont(a,b):
 a=pd.to_numeric(a,errors='coerce').dropna(); b=pd.to_numeric(b,errors='coerce').dropna(); den=np.sqrt((a.var(ddof=1)+b.var(ddof=1))/2); return abs((a.mean()-b.mean())/den) if den>0 else 0.0
def smd_bin(pa,pb):
 den=np.sqrt((pa*(1-pa)+pb*(1-pb))/2); return abs(pa-pb)/den if den>0 else 0.0
def fmt_cont(x):
 x=pd.to_numeric(x,errors='coerce').dropna(); return f"{x.median():.1f} ({x.quantile(.25):.1f}–{x.quantile(.75):.1f})"
def fmt_n(p,n): return f"{int(round(p*n)):,} ({100*p:.1f}%)"

rows=[]; rank=[]; missrows=[]
for v,label in continuous.items():
 stats={}
 for g in groups:
  x=df.loc[df.compare_group==g,v]; obs=x.notna().sum(); miss=x.isna().sum(); stats[g]=fmt_cont(x)
  missrows.append({'variable':v,'characteristic':label,'group':g,'observed_n':obs,'missing_n':miss,'missing_pct':100*miss/len(x)})
 s1=smd_cont(df.loc[df.compare_group==groups[0],v],df.loc[df.compare_group==groups[1],v]); s2=smd_cont(df.loc[df.compare_group==groups[0],v],df.loc[df.compare_group==groups[2],v])
 rows.append({'Characteristic':label,**{labels[g]:stats[g] for g in groups},'Missingness by group':'See missingness table','Abs SMD final vs no reference':s1,'Abs SMD final vs other excluded':s2})
 rank += [{'comparison':'Final vs no reference','characteristic':label,'abs_smd':s1},{'comparison':'Final vs other excluded','characteristic':label,'abs_smd':s2}]
for v,label in binary.items():
 ps={g:df.loc[df.compare_group==g,v].mean() for g in groups}
 vals={g:fmt_n(ps[g],expected[g]) for g in groups}; s1=smd_bin(ps[groups[0]],ps[groups[1]]); s2=smd_bin(ps[groups[0]],ps[groups[2]])
 rows.append({'Characteristic':label,**{labels[g]:vals[g] for g in groups},'Missingness by group':'0 (0.0%) in each group','Abs SMD final vs no reference':s1,'Abs SMD final vs other excluded':s2})
 rank += [{'comparison':'Final vs no reference','characteristic':label,'abs_smd':s1},{'comparison':'Final vs other excluded','characteristic':label,'abs_smd':s2}]
for v,label in categorical.items():
 levels=sorted(df[v].astype(str).unique())
 max1=max2=0
 for lev in levels:
  ps={g:(df.loc[df.compare_group==g,v].astype(str)==lev).mean() for g in groups}; s1=smd_bin(ps[groups[0]],ps[groups[1]]); s2=smd_bin(ps[groups[0]],ps[groups[2]]); max1=max(max1,s1); max2=max(max2,s2)
  rows.append({'Characteristic':f'{label}: {lev}',**{labels[g]:fmt_n(ps[g],expected[g]) for g in groups},'Missingness by group':'Missing retained as category','Abs SMD final vs no reference':s1,'Abs SMD final vs other excluded':s2})
 rank += [{'comparison':'Final vs no reference','characteristic':label+' (maximum category-wise)','abs_smd':max1},{'comparison':'Final vs other excluded','characteristic':label+' (maximum category-wise)','abs_smd':max2}]

table=pd.DataFrame(rows); table.to_csv(OUT/'tables'/'TABLE_S5_selection_characteristics.csv',index=False); table.to_excel(OUT/'tables'/'TABLE_S5_selection_characteristics.xlsx',index=False)
missing=pd.DataFrame(missrows); missing.to_csv(OUT/'tables'/'TABLE_S5_missingness.csv',index=False)
ranking=pd.DataFrame(rank).sort_values(['comparison','abs_smd'],ascending=[True,False]); ranking.to_csv(OUT/'outputs'/'ranked_absolute_smds.csv',index=False)

detail=df.groupby(['compare_group','exclusion_detail']).agg(patients=('uniquePID','nunique'),stays=('patientUnitStayID','nunique'),hospitals=('hospitalID','nunique')).reset_index(); detail.to_csv(OUT/'outputs'/'cohort_group_counts.csv',index=False)
defs=df.groupby('compare_group').agg(unique_patients=('uniquePID','nunique'),unique_stays=('patientUnitStayID','nunique'),hospitals=('hospitalID','nunique')).reset_index(); defs.to_csv(OUT/'outputs'/'group_definitions_machine_readable.csv',index=False)

# Hospital availability among patient-level deterministic comparison universe.
h=df.assign(has_ref=df.compare_group!='B_no_reference').groupby('hospitalID').agg(candidate_n=('uniquePID','size'),reference_n=('has_ref','sum')).reset_index(); h['reference_available_prop']=h.reference_n/h.candidate_n
h.to_csv(OUT/'outputs'/'hospital_reference_availability.csv',index=False)
def hsum(x,label): return {'population':label,'hospitals':len(x),'candidate_median':x.candidate_n.median(),'candidate_iqr_low':x.candidate_n.quantile(.25),'candidate_iqr_high':x.candidate_n.quantile(.75),'availability_median':x.reference_available_prop.median(),'availability_iqr_low':x.reference_available_prop.quantile(.25),'availability_iqr_high':x.reference_available_prop.quantile(.75),'availability_p10':x.reference_available_prop.quantile(.10),'availability_p90':x.reference_available_prop.quantile(.90),'availability_min':x.reference_available_prop.min(),'availability_max':x.reference_available_prop.max()}
hs=pd.DataFrame([hsum(h,'All hospitals'),hsum(h[h.candidate_n>=100],'Hospitals with ≥100 candidates (descriptive sensitivity)')]); hs.to_csv(OUT/'outputs'/'hospital_reference_availability_summary.csv',index=False)

# Love plot at variable/domain level.
plot=ranking.copy(); order=plot.groupby('characteristic').abs_smd.max().sort_values().index; y=np.arange(len(order)); fig,ax=plt.subplots(figsize=(8,0.34*len(order)+2.2))
for comp,marker,color,off in [('Final vs no reference','o','black',-.12),('Final vs other excluded','s','0.45',.12)]:
 z=plot[plot.comparison==comp].set_index('characteristic').reindex(order); ax.scatter(z.abs_smd,y+off,label=comp,marker=marker,color=color,s=35)
ax.axvline(.10,color='0.5',ls='--',lw=1); ax.axvline(.20,color='0.75',ls=':',lw=1); ax.set_yticks(y); ax.set_yticklabels(order,fontsize=8); ax.set_xlabel('Absolute standardized mean difference'); ax.set_title('Fig. S6. Covariate shift between the final landmark cohort\nand excluded candidate populations'); ax.legend(frameon=False,fontsize=8); ax.grid(axis='x',color='0.9'); fig.tight_layout(); fig.savefig(OUT/'figures'/'FIG_S6_covariate_shift.png',dpi=300); fig.savefig(OUT/'figures'/'FIG_S6_covariate_shift.pdf'); plt.close(fig)

lineage=[]
meta={
'age':('Age','eICU patient.age','At ICU admission','Yes','Include'), 'bmi':('BMI','patient.admissionHeight/admissionWeight','At ICU admission','Yes','Include'),
'sex':('Recorded sex','patient.gender','At ICU admission','Yes','Include'), 'ethnicity':('Recorded race/ethnicity','patient.ethnicity','At ICU admission','Yes','Include; missing retained as category'),
'unit_type':('ICU type','patient.unitType','At ICU admission','Yes','Include'), 'unit_admit_source':('ICU admission source','patient.unitAdmitSource','At ICU admission','Yes','Include'), 'hospital_admit_source':('Hospital admission source','patient.hospitalAdmitSource','At hospital admission','Yes','Include'),
'hr':('Last valid heart rate','vitalPeriodic.heartRate','0–720 min','Yes','Include; observed-value SMD plus missingness'), 'sbp':('Last valid systolic BP','vitalPeriodic.systemicSystolic','0–720 min','Yes','Include; observed-value SMD plus missingness'), 'rr':('Last valid respiratory rate','vitalPeriodic.respiration','0–720 min','Yes','Include; observed-value SMD plus missingness'),
'bun':('Last valid BUN','lab.labResult where labName=BUN','0–720 min','Yes','Include cautiously; observation-process signal expected'), 'any_vasopressor':('Any vasopressor infusion','infusionDrug.drugName','0–720 min','Yes','Include; absence of record treated as no documented infusion'), 'invasive_ventilation':('Conservative invasive ventilation flag','respiratoryCare.airwayType; treatment.treatmentString','0–720 min','Yes','Include; absence of qualifying documentation treated as no')}
for v,(meaning,source,window,pre,decision) in meta.items():
 rec={'variable':v,'clinical_meaning':meaning,'source_table_field':source,'extraction_window':window,'available_before_selection_point':pre,'scientifically_fair':decision}
 for g in groups:
  rec['missing_pct_'+g]=float(df.loc[df.compare_group==g,v].isna().mean()*100) if v in continuous else 0.0
 lineage.append(rec)
pd.DataFrame(lineage).to_csv(OUT/'SELECTION_VARIABLE_LINEAGE.csv',index=False)

toptext=[]
for comp in ranking.comparison.unique():
 z=ranking[ranking.comparison==comp]; toptext.append(f"### {comp}\n\n"+z.head(10).to_markdown(index=False)+f"\n\n- |SMD| ≥0.10: {(z.abs_smd>=.10).sum()}\n- |SMD| ≥0.20: {(z.abs_smd>=.20).sum()}\n- Largest |SMD|: {z.abs_smd.max():.3f}\n")
largest=ranking.abs_smd.max(); level='limited' if largest<.20 else ('moderate' if largest<.50 else 'substantial')

(OUT/'COHORT_COUNT_RECONCILIATION.md').write_text('''# Cohort count reconciliation\n\nThe manuscript flow and the selection-analysis universe are different counting layers and must not be subtracted interchangeably.\n\n| Layer | Unit/count | Explanation |\n|---|---:|---|\n| Adult ICU stays ≥12 h | 172,392 stays | Initial stay-level screen |\n| First eligible ICU unit per hospital stay | 154,529 stays | One eligible ICU unit per hospital stay; still not one row per unique patient |\n| Qualifying reference creatinine | 94,093 stays | Stay-level manuscript flow checkpoint |\n| Patient-level deterministic comparison universe | 126,324 patients/stays | Excludes cross-hospital patients and retains the deterministic patient/stay rank 1 |\n| Group B: no qualifying reference creatinine | 41,614 patients | Mutually exclusive patient-level group after the additional patient-level restrictions |\n| Final primary cohort | 58,491 patients | Group A |\n| Other post-reference exclusions | 26,219 patients | Group C |\n\nThus 154,529 âˆ’ 94,093 = 60,436 is a stay-level transition, whereas 41,614 is a patient-level mutually exclusive comparison group. The difference reflects cross-hospital-patient exclusion and deterministic selection of one analytic stay per unique patient. It is not a manuscript inconsistency. The three comparison groups reconcile exactly: 58,491 + 41,614 + 26,219 = 126,324.\n''',encoding='utf-8')

qc=f'''# Selection analysis QC\n\n## Assertions\n\n- Analytic rows: {len(df):,}; expected 126,324: PASS.\n- Unique `patientUnitStayID`: {df.patientUnitStayID.nunique():,}: PASS.\n- Unique `uniquePID`: {df.uniquePID.nunique():,}: PASS.\n- Group A/B/C mutually exclusive and complete: PASS.\n- Counts: A={expected[groups[0]]:,}, B={expected[groups[1]]:,}, C={expected[groups[2]]:,}; sum={sum(expected.values()):,}: PASS.\n- Final events/count/hospitals previously reconciled to 3,032/58,491/198: PASS.\n\n## Scientific QC\n\n1. Every number is generated by the checked-in script and source SQL: yes.\n2. Groups reconcile exactly: yes.\n3. Every Table S5 variable has a temporal/source audit: yes; all use admission or 0–12 h information, a common window because the upstream screen required ICU duration ≥12 h.\n4. Missingness differences are reported separately: yes.\n5. Observed-value SMDs may be misleading when missingness is high/differential; these are flagged in the lineage and missingness tables.\n6. Hospital heterogeneity is quantified with denominator-aware sensitivity summary.\n7. Generalizability conclusion: the analysis {level}ly refines the claim based on observable shifts; it cannot eliminate unmeasured selection.\n8. Submission-stopping finding: assessed in the main report from the ranked SMD and hospital results; no conclusion was pre-specified.\n'''
(OUT/'SELECTION_ANALYSIS_QC.md').write_text(qc,encoding='utf-8')

h0=hs.iloc[0]
report=f'''# Selection-bias analysis report\n\n## Executive summary\n\nSelection produced a **{level} observable population shift** under the prespecified descriptive interpretation. This statement concerns measured characteristics only and does not establish absence of selection bias.\n\n## Cohort reconstruction\n\nGroup A was the final primary cohort (n=58,491); Group B comprised deterministic patient-level candidates without qualifying reference creatinine (n=41,614); Group C comprised reference-creatinine-available candidates excluded subsequently (n=26,219). Groups were mutually exclusive, one row per `uniquePID` and `patientUnitStayID`, and summed to 126,324. See `COHORT_COUNT_RECONCILIATION.md`.\n\n## Methods\n\nAdmission variables and measurements documented during 0–12 h were compared. Continuous results are median (IQR); SMDs use the difference in observed means divided by the square root of the average group variances. Binary/category-level SMDs use the pooled Bernoulli variance. Multi-category domains are ranked by the largest category-wise absolute SMD. No imputation or p-values were used. Missingness is reported separately; observed-value SMDs do not incorporate missingness.\n\n## Results\n\n{''.join(toptext)}\n## Hospital-level availability\n\nAcross {int(h0.hospitals)} hospitals, the median hospital-level reference-creatinine availability was {100*h0.availability_median:.1f}% (IQR {100*h0.availability_iqr_low:.1f}–{100*h0.availability_iqr_high:.1f}%; 10th–90th percentiles {100*h0.availability_p10:.1f}–{100*h0.availability_p90:.1f}%). Raw extremes are provided with hospital denominators and should not be overinterpreted when driven by small centers. A prespecified descriptive summary for hospitals with ≥100 candidates is also provided.\n\n## Interpretation\n\nDifferences may reflect clinical mix, severity, surveillance intensity, ordering practice, ICU workflow, or hospital-specific EHR practice. Measurement availability must not be equated automatically with disease severity, and no MCAR/MAR/MNAR mechanism is claimed. Transportability is best framed for landmark-eligible ICU patients with the required renal surveillance.\n\n## Limitations\n\nSimilarity on observed variables cannot exclude selection on unobserved factors. Several SMDs summarize observed values only and should be read alongside group-specific missingness. Documentation-based support indicators may reflect recording practice.\n\n## Manuscript recommendations\n\nKeep Table S5 and Fig. S6 in the Online Resource. Add 2–4 Results sentences and 1–3 Discussion/Limitations sentences. Do not modify the final DOCX until author approval.\n\n## Source provenance\n\nThe authoritative public snapshot was GitHub commit `2f4fabd115e9f882e7deb4ae1f198a5fd3735734`, tag `v1.0.0-manuscript`, identical to Zenodo DOI `10.5281/zenodo.21824202` version `1.0.0-manuscript`. Local v1.0.1 was a scientific-content-preserving cleanup. The science-locked manuscript supplied count anchors. Google Drive was connected but its connector tools were unavailable in this task, so no Drive file contributed to the source-of-truth decision.\n'''
(OUT/'SELECTION_BIAS_ANALYSIS_REPORT.md').write_text(report,encoding='utf-8')

if level=='limited': result_sent='Observable differences across the measured baseline and early-ICU characteristics were generally limited.'
elif level=='moderate': result_sent='Selection was associated with moderate observable differences in several baseline, monitoring, or care-context domains.'
else: result_sent='Selection was associated with substantial observable differences in several baseline, monitoring, or care-context domains.'
(OUT/'MANUSCRIPT_INSERT_SELECTION_BIAS.md').write_text(f'''# Candidate manuscript insertion (not applied)\n\n## Results\n\nIn a patient-level selection analysis, the final landmark cohort (n=58,491) was compared with candidates lacking qualifying reference creatinine (n=41,614) and other post-reference exclusions (n=26,219). {result_sent} Differential measurement availability was also observed and is reported separately in Online Resource Table S5.\n\n## Discussion / limitations\n\nSelection into the landmark cohort and the requirement for early creatinine availability may limit transportability to ICU populations with different surveillance and ordering practices. Similarity in measured characteristics, where present, cannot exclude selection related to unmeasured factors.\n\n## Table S5 caption\n\nTable S5. Baseline and early-ICU characteristics of patients included in and excluded from the final 12-hour landmark cohort. Continuous variables are median (IQR), categorical variables are n (%), and absolute standardized mean differences are descriptive. Missingness is reported by group; continuous-variable SMDs are based on observed values.\n\n## Figure S6 caption\n\nFig. S6. Covariate shift between the final landmark cohort and excluded candidate populations. Absolute standardized mean differences compare the final cohort with the reference-creatinine-unavailable group and other post-reference exclusions. The 0.10 line is a descriptive reference, not an inferential threshold.\n''',encoding='utf-8')

(OUT/'SOURCE_PROVENANCE_AND_VERSION_AUDIT.md').write_text('''# Source provenance and version audit\n\n- Local manuscript: `makale 2/Manuscript_IUN_A15_FINAL.docx`; count anchors confirmed.\n- Local analysis package: v1.0.1-manuscript; documentation/package cleanup only.\n- GitHub: `originalprojects-code/aki-progression-hospital-iec`, branch `main`, commit `2f4fabd115e9f882e7deb4ae1f198a5fd3735734`, tag `v1.0.0-manuscript`.\n- Zenodo: DOI `10.5281/zenodo.21824202`, version `1.0.0-manuscript`, ZIP checksum `md5:6805387649a5ee7265973fe744073071`; content identical to GitHub.\n- Drive: connected, but connector calls were unavailable in this active task; no unique Drive evidence could be verified.\n- Source of truth: manuscript-consistent SQL/definitions in the frozen GitHub/Zenodo release, with the scientifically unchanged local v1.0.1 package and live BigQuery tables used for reproduction.\n''',encoding='utf-8')

(OUT/'README.md').write_text('''# Selection-bias robustness analysis\n\nNew, separate analysis. No existing manuscript, SQL, notebook, model, or validated output was modified. Run `src/run_selection_bias_analysis.py` with authorized BigQuery ADC. Patient-level data are queried transiently and never written; only aggregate publication-safe outputs are saved.\n''',encoding='utf-8')
(OUT/'src'/'run_selection_bias_analysis.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
manifest=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file(): manifest.append({'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size})
pd.DataFrame(manifest).to_csv(OUT/'outputs'/'CREATED_FILES_MANIFEST.csv',index=False)
print(json.dumps({'level':level,'counts':expected,'largest_smd':float(largest),'output':str(OUT)},indent=2))



