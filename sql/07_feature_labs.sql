-- First-12-hour laboratory summaries after broad plausibility QC.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.feature_labs_v1` AS
WITH main AS (
  SELECT patientUnitStayID
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1`
  WHERE eligible_main_cohort = 1
    AND deterministic_eligible_patient_stay_rank = 1
),
raw AS (
  SELECT
    l.patientUnitStayID,
    l.labID,
    l.labResultOffset AS offset_min,
    LOWER(TRIM(l.labName)) AS lab_name,
    SAFE_CAST(l.labResult AS FLOAT64) AS raw_value
  FROM main m
  JOIN `physionet-data.eicu_crd.lab` l USING(patientUnitStayID)
  WHERE l.labResultOffset BETWEEN 0 AND 720
    AND l.labResult IS NOT NULL
),
mapped AS (
  SELECT *,
    CASE lab_name
      WHEN 'creatinine' THEN 'creatinine'
      WHEN 'bun' THEN 'bun'
      WHEN 'bicarbonate' THEN 'bicarbonate'
      WHEN 'potassium' THEN 'potassium'
      WHEN 'sodium' THEN 'sodium'
      WHEN 'chloride' THEN 'chloride'
      WHEN 'glucose' THEN 'glucose_serum'
      WHEN 'bedside glucose' THEN 'glucose_bedside'
      WHEN 'calcium' THEN 'calcium'
      WHEN 'magnesium' THEN 'magnesium'
      WHEN 'phosphate' THEN 'phosphate'
      WHEN 'hgb' THEN 'hgb'
      WHEN 'hct' THEN 'hct'
      WHEN 'platelets x 1000' THEN 'platelets'
      WHEN 'wbc x 1000' THEN 'wbc'
      WHEN 'albumin' THEN 'albumin'
      WHEN 'total bilirubin' THEN 'bilirubin_total'
      WHEN 'ast (sgot)' THEN 'ast'
      WHEN 'alt (sgpt)' THEN 'alt'
      WHEN 'pt - inr' THEN 'inr'
      WHEN 'lactate' THEN 'lactate'
      WHEN 'anion gap' THEN 'anion_gap'
      ELSE NULL
    END AS feature
  FROM raw
),
clean AS (
  SELECT patientUnitStayID, labID, offset_min, feature,
    CASE feature
      WHEN 'creatinine' THEN IF(raw_value BETWEEN 0.05 AND 40.0, raw_value, NULL)
      WHEN 'bun' THEN IF(raw_value BETWEEN 1.0 AND 350.0, raw_value, NULL)
      WHEN 'bicarbonate' THEN IF(raw_value BETWEEN 2.0 AND 80.0, raw_value, NULL)
      WHEN 'potassium' THEN IF(raw_value BETWEEN 1.0 AND 12.5, raw_value, NULL)
      WHEN 'sodium' THEN IF(raw_value BETWEEN 80.0 AND 200.0, raw_value, NULL)
      WHEN 'chloride' THEN IF(raw_value BETWEEN 50.0 AND 170.0, raw_value, NULL)
      WHEN 'glucose_serum' THEN IF(raw_value BETWEEN 10.0 AND 1800.0, raw_value, NULL)
      WHEN 'glucose_bedside' THEN IF(raw_value BETWEEN 10.0 AND 700.0, raw_value, NULL)
      WHEN 'calcium' THEN IF(raw_value BETWEEN 2.0 AND 20.0, raw_value, NULL)
      WHEN 'magnesium' THEN IF(raw_value BETWEEN 0.3 AND 10.0, raw_value, NULL)
      WHEN 'phosphate' THEN IF(raw_value BETWEEN 0.1 AND 20.0, raw_value, NULL)
      WHEN 'hgb' THEN IF(raw_value BETWEEN 2.0 AND 25.0, raw_value, NULL)
      WHEN 'hct' THEN IF(raw_value BETWEEN 5.0 AND 75.0, raw_value, NULL)
      WHEN 'platelets' THEN IF(raw_value BETWEEN 1.0 AND 1500.0, raw_value, NULL)
      WHEN 'wbc' THEN IF(raw_value BETWEEN 0.1 AND 200.0, raw_value, NULL)
      WHEN 'albumin' THEN IF(raw_value BETWEEN 0.5 AND 7.0, raw_value, NULL)
      WHEN 'bilirubin_total' THEN IF(raw_value BETWEEN 0.0 AND 70.0, raw_value, NULL)
      WHEN 'ast' THEN IF(raw_value BETWEEN 1.0 AND 50000.0, raw_value, NULL)
      WHEN 'alt' THEN IF(raw_value BETWEEN 1.0 AND 50000.0, raw_value, NULL)
      WHEN 'inr' THEN IF(raw_value BETWEEN 0.5 AND 20.0, raw_value, NULL)
      WHEN 'lactate' THEN IF(raw_value BETWEEN 0.1 AND 30.0, raw_value, NULL)
      WHEN 'anion_gap' THEN IF(raw_value BETWEEN -10.0 AND 60.0, raw_value, NULL)
      ELSE NULL
    END AS value
  FROM mapped
  WHERE feature IS NOT NULL
),
valid AS (
  SELECT * FROM clean WHERE value IS NOT NULL
),
grouped AS (
  SELECT
    patientUnitStayID,
    feature,
    ARRAY_AGG(value ORDER BY offset_min, labID LIMIT 1)[OFFSET(0)] AS first_value,
    ARRAY_AGG(value ORDER BY offset_min DESC, labID DESC LIMIT 1)[OFFSET(0)] AS last_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    AVG(value) AS mean_value,
    COUNT(*) AS n_values
  FROM valid
  GROUP BY patientUnitStayID, feature
)
SELECT
  patientUnitStayID,
  MAX(IF(feature = 'creatinine', first_value, NULL)) AS x_lab_creatinine_first,
  MAX(IF(feature = 'creatinine', last_value, NULL)) AS x_lab_creatinine_last,
  MAX(IF(feature = 'creatinine', min_value, NULL)) AS x_lab_creatinine_min,
  MAX(IF(feature = 'creatinine', max_value, NULL)) AS x_lab_creatinine_max,
  MAX(IF(feature = 'creatinine', mean_value, NULL)) AS x_lab_creatinine_mean,
  MAX(IF(feature = 'creatinine', n_values, NULL)) AS x_lab_creatinine_n,
  MAX(IF(feature = 'creatinine' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_creatinine_delta,
  MAX(IF(feature = 'bun', first_value, NULL)) AS x_lab_bun_first,
  MAX(IF(feature = 'bun', last_value, NULL)) AS x_lab_bun_last,
  MAX(IF(feature = 'bun', min_value, NULL)) AS x_lab_bun_min,
  MAX(IF(feature = 'bun', max_value, NULL)) AS x_lab_bun_max,
  MAX(IF(feature = 'bun', mean_value, NULL)) AS x_lab_bun_mean,
  MAX(IF(feature = 'bun', n_values, NULL)) AS x_lab_bun_n,
  MAX(IF(feature = 'bun' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_bun_delta,
  MAX(IF(feature = 'bicarbonate', first_value, NULL)) AS x_lab_bicarbonate_first,
  MAX(IF(feature = 'bicarbonate', last_value, NULL)) AS x_lab_bicarbonate_last,
  MAX(IF(feature = 'bicarbonate', min_value, NULL)) AS x_lab_bicarbonate_min,
  MAX(IF(feature = 'bicarbonate', max_value, NULL)) AS x_lab_bicarbonate_max,
  MAX(IF(feature = 'bicarbonate', mean_value, NULL)) AS x_lab_bicarbonate_mean,
  MAX(IF(feature = 'bicarbonate', n_values, NULL)) AS x_lab_bicarbonate_n,
  MAX(IF(feature = 'bicarbonate' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_bicarbonate_delta,
  MAX(IF(feature = 'potassium', first_value, NULL)) AS x_lab_potassium_first,
  MAX(IF(feature = 'potassium', last_value, NULL)) AS x_lab_potassium_last,
  MAX(IF(feature = 'potassium', min_value, NULL)) AS x_lab_potassium_min,
  MAX(IF(feature = 'potassium', max_value, NULL)) AS x_lab_potassium_max,
  MAX(IF(feature = 'potassium', mean_value, NULL)) AS x_lab_potassium_mean,
  MAX(IF(feature = 'potassium', n_values, NULL)) AS x_lab_potassium_n,
  MAX(IF(feature = 'potassium' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_potassium_delta,
  MAX(IF(feature = 'sodium', first_value, NULL)) AS x_lab_sodium_first,
  MAX(IF(feature = 'sodium', last_value, NULL)) AS x_lab_sodium_last,
  MAX(IF(feature = 'sodium', min_value, NULL)) AS x_lab_sodium_min,
  MAX(IF(feature = 'sodium', max_value, NULL)) AS x_lab_sodium_max,
  MAX(IF(feature = 'sodium', mean_value, NULL)) AS x_lab_sodium_mean,
  MAX(IF(feature = 'sodium', n_values, NULL)) AS x_lab_sodium_n,
  MAX(IF(feature = 'sodium' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_sodium_delta,
  MAX(IF(feature = 'chloride', first_value, NULL)) AS x_lab_chloride_first,
  MAX(IF(feature = 'chloride', last_value, NULL)) AS x_lab_chloride_last,
  MAX(IF(feature = 'chloride', min_value, NULL)) AS x_lab_chloride_min,
  MAX(IF(feature = 'chloride', max_value, NULL)) AS x_lab_chloride_max,
  MAX(IF(feature = 'chloride', mean_value, NULL)) AS x_lab_chloride_mean,
  MAX(IF(feature = 'chloride', n_values, NULL)) AS x_lab_chloride_n,
  MAX(IF(feature = 'glucose_serum', first_value, NULL)) AS x_lab_glucose_serum_first,
  MAX(IF(feature = 'glucose_serum', last_value, NULL)) AS x_lab_glucose_serum_last,
  MAX(IF(feature = 'glucose_serum', min_value, NULL)) AS x_lab_glucose_serum_min,
  MAX(IF(feature = 'glucose_serum', max_value, NULL)) AS x_lab_glucose_serum_max,
  MAX(IF(feature = 'glucose_serum', mean_value, NULL)) AS x_lab_glucose_serum_mean,
  MAX(IF(feature = 'glucose_serum', n_values, NULL)) AS x_lab_glucose_serum_n,
  MAX(IF(feature = 'glucose_serum' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_glucose_serum_delta,
  MAX(IF(feature = 'glucose_bedside', first_value, NULL)) AS x_lab_glucose_bedside_first,
  MAX(IF(feature = 'glucose_bedside', last_value, NULL)) AS x_lab_glucose_bedside_last,
  MAX(IF(feature = 'glucose_bedside', min_value, NULL)) AS x_lab_glucose_bedside_min,
  MAX(IF(feature = 'glucose_bedside', max_value, NULL)) AS x_lab_glucose_bedside_max,
  MAX(IF(feature = 'glucose_bedside', mean_value, NULL)) AS x_lab_glucose_bedside_mean,
  MAX(IF(feature = 'glucose_bedside', n_values, NULL)) AS x_lab_glucose_bedside_n,
  MAX(IF(feature = 'calcium', first_value, NULL)) AS x_lab_calcium_first,
  MAX(IF(feature = 'calcium', last_value, NULL)) AS x_lab_calcium_last,
  MAX(IF(feature = 'calcium', min_value, NULL)) AS x_lab_calcium_min,
  MAX(IF(feature = 'calcium', max_value, NULL)) AS x_lab_calcium_max,
  MAX(IF(feature = 'calcium', mean_value, NULL)) AS x_lab_calcium_mean,
  MAX(IF(feature = 'calcium', n_values, NULL)) AS x_lab_calcium_n,
  MAX(IF(feature = 'magnesium', first_value, NULL)) AS x_lab_magnesium_first,
  MAX(IF(feature = 'magnesium', last_value, NULL)) AS x_lab_magnesium_last,
  MAX(IF(feature = 'magnesium', min_value, NULL)) AS x_lab_magnesium_min,
  MAX(IF(feature = 'magnesium', max_value, NULL)) AS x_lab_magnesium_max,
  MAX(IF(feature = 'magnesium', mean_value, NULL)) AS x_lab_magnesium_mean,
  MAX(IF(feature = 'magnesium', n_values, NULL)) AS x_lab_magnesium_n,
  MAX(IF(feature = 'phosphate', first_value, NULL)) AS x_lab_phosphate_first,
  MAX(IF(feature = 'phosphate', last_value, NULL)) AS x_lab_phosphate_last,
  MAX(IF(feature = 'phosphate', min_value, NULL)) AS x_lab_phosphate_min,
  MAX(IF(feature = 'phosphate', max_value, NULL)) AS x_lab_phosphate_max,
  MAX(IF(feature = 'phosphate', mean_value, NULL)) AS x_lab_phosphate_mean,
  MAX(IF(feature = 'phosphate', n_values, NULL)) AS x_lab_phosphate_n,
  MAX(IF(feature = 'hgb', first_value, NULL)) AS x_lab_hgb_first,
  MAX(IF(feature = 'hgb', last_value, NULL)) AS x_lab_hgb_last,
  MAX(IF(feature = 'hgb', min_value, NULL)) AS x_lab_hgb_min,
  MAX(IF(feature = 'hgb', max_value, NULL)) AS x_lab_hgb_max,
  MAX(IF(feature = 'hgb', mean_value, NULL)) AS x_lab_hgb_mean,
  MAX(IF(feature = 'hgb', n_values, NULL)) AS x_lab_hgb_n,
  MAX(IF(feature = 'hct', first_value, NULL)) AS x_lab_hct_first,
  MAX(IF(feature = 'hct', last_value, NULL)) AS x_lab_hct_last,
  MAX(IF(feature = 'hct', min_value, NULL)) AS x_lab_hct_min,
  MAX(IF(feature = 'hct', max_value, NULL)) AS x_lab_hct_max,
  MAX(IF(feature = 'hct', mean_value, NULL)) AS x_lab_hct_mean,
  MAX(IF(feature = 'hct', n_values, NULL)) AS x_lab_hct_n,
  MAX(IF(feature = 'platelets', first_value, NULL)) AS x_lab_platelets_first,
  MAX(IF(feature = 'platelets', last_value, NULL)) AS x_lab_platelets_last,
  MAX(IF(feature = 'platelets', min_value, NULL)) AS x_lab_platelets_min,
  MAX(IF(feature = 'platelets', max_value, NULL)) AS x_lab_platelets_max,
  MAX(IF(feature = 'platelets', mean_value, NULL)) AS x_lab_platelets_mean,
  MAX(IF(feature = 'platelets', n_values, NULL)) AS x_lab_platelets_n,
  MAX(IF(feature = 'wbc', first_value, NULL)) AS x_lab_wbc_first,
  MAX(IF(feature = 'wbc', last_value, NULL)) AS x_lab_wbc_last,
  MAX(IF(feature = 'wbc', min_value, NULL)) AS x_lab_wbc_min,
  MAX(IF(feature = 'wbc', max_value, NULL)) AS x_lab_wbc_max,
  MAX(IF(feature = 'wbc', mean_value, NULL)) AS x_lab_wbc_mean,
  MAX(IF(feature = 'wbc', n_values, NULL)) AS x_lab_wbc_n,
  MAX(IF(feature = 'albumin', first_value, NULL)) AS x_lab_albumin_first,
  MAX(IF(feature = 'albumin', last_value, NULL)) AS x_lab_albumin_last,
  MAX(IF(feature = 'albumin', min_value, NULL)) AS x_lab_albumin_min,
  MAX(IF(feature = 'albumin', max_value, NULL)) AS x_lab_albumin_max,
  MAX(IF(feature = 'albumin', mean_value, NULL)) AS x_lab_albumin_mean,
  MAX(IF(feature = 'albumin', n_values, NULL)) AS x_lab_albumin_n,
  MAX(IF(feature = 'bilirubin_total', first_value, NULL)) AS x_lab_bilirubin_total_first,
  MAX(IF(feature = 'bilirubin_total', last_value, NULL)) AS x_lab_bilirubin_total_last,
  MAX(IF(feature = 'bilirubin_total', min_value, NULL)) AS x_lab_bilirubin_total_min,
  MAX(IF(feature = 'bilirubin_total', max_value, NULL)) AS x_lab_bilirubin_total_max,
  MAX(IF(feature = 'bilirubin_total', mean_value, NULL)) AS x_lab_bilirubin_total_mean,
  MAX(IF(feature = 'bilirubin_total', n_values, NULL)) AS x_lab_bilirubin_total_n,
  MAX(IF(feature = 'ast', first_value, NULL)) AS x_lab_ast_first,
  MAX(IF(feature = 'ast', last_value, NULL)) AS x_lab_ast_last,
  MAX(IF(feature = 'ast', min_value, NULL)) AS x_lab_ast_min,
  MAX(IF(feature = 'ast', max_value, NULL)) AS x_lab_ast_max,
  MAX(IF(feature = 'ast', mean_value, NULL)) AS x_lab_ast_mean,
  MAX(IF(feature = 'ast', n_values, NULL)) AS x_lab_ast_n,
  MAX(IF(feature = 'alt', first_value, NULL)) AS x_lab_alt_first,
  MAX(IF(feature = 'alt', last_value, NULL)) AS x_lab_alt_last,
  MAX(IF(feature = 'alt', min_value, NULL)) AS x_lab_alt_min,
  MAX(IF(feature = 'alt', max_value, NULL)) AS x_lab_alt_max,
  MAX(IF(feature = 'alt', mean_value, NULL)) AS x_lab_alt_mean,
  MAX(IF(feature = 'alt', n_values, NULL)) AS x_lab_alt_n,
  MAX(IF(feature = 'inr', first_value, NULL)) AS x_lab_inr_first,
  MAX(IF(feature = 'inr', last_value, NULL)) AS x_lab_inr_last,
  MAX(IF(feature = 'inr', min_value, NULL)) AS x_lab_inr_min,
  MAX(IF(feature = 'inr', max_value, NULL)) AS x_lab_inr_max,
  MAX(IF(feature = 'inr', mean_value, NULL)) AS x_lab_inr_mean,
  MAX(IF(feature = 'inr', n_values, NULL)) AS x_lab_inr_n,
  MAX(IF(feature = 'lactate', first_value, NULL)) AS x_lab_lactate_first,
  MAX(IF(feature = 'lactate', last_value, NULL)) AS x_lab_lactate_last,
  MAX(IF(feature = 'lactate', min_value, NULL)) AS x_lab_lactate_min,
  MAX(IF(feature = 'lactate', max_value, NULL)) AS x_lab_lactate_max,
  MAX(IF(feature = 'lactate', mean_value, NULL)) AS x_lab_lactate_mean,
  MAX(IF(feature = 'lactate', n_values, NULL)) AS x_lab_lactate_n,
  MAX(IF(feature = 'lactate' AND n_values >= 2, last_value - first_value, NULL)) AS x_lab_lactate_delta,
  MAX(IF(feature = 'anion_gap', first_value, NULL)) AS x_lab_anion_gap_first,
  MAX(IF(feature = 'anion_gap', last_value, NULL)) AS x_lab_anion_gap_last,
  MAX(IF(feature = 'anion_gap', min_value, NULL)) AS x_lab_anion_gap_min,
  MAX(IF(feature = 'anion_gap', max_value, NULL)) AS x_lab_anion_gap_max,
  MAX(IF(feature = 'anion_gap', mean_value, NULL)) AS x_lab_anion_gap_mean,
  MAX(IF(feature = 'anion_gap', n_values, NULL)) AS x_lab_anion_gap_n
FROM grouped
GROUP BY patientUnitStayID;
