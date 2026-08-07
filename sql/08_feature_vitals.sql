-- First-12-hour vital-sign summaries after broad plausibility QC.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.feature_vitals_v1` AS
WITH main AS (
  SELECT patientUnitStayID
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1`
  WHERE eligible_main_cohort = 1
    AND deterministic_eligible_patient_stay_rank = 1
),
long_raw AS (
  SELECT v.patientUnitStayID, v.vitalPeriodicID AS record_id, v.observationOffset AS offset_min,
         'heart_rate' AS feature, SAFE_CAST(v.heartRate AS FLOAT64) AS raw_value
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'sao2', SAFE_CAST(v.saO2 AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'respiratory_rate', SAFE_CAST(v.respiration AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'temperature_c', SAFE_CAST(v.temperature AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'invasive_systolic_bp', SAFE_CAST(v.systemicSystolic AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'invasive_diastolic_bp', SAFE_CAST(v.systemicDiastolic AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalPeriodicID, v.observationOffset,
         'invasive_mean_bp', SAFE_CAST(v.systemicMean AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalAperiodicID, v.observationOffset,
         'noninvasive_systolic_bp', SAFE_CAST(v.nonInvasiveSystolic AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalaperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalAperiodicID, v.observationOffset,
         'noninvasive_diastolic_bp', SAFE_CAST(v.nonInvasiveDiastolic AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalaperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
  UNION ALL
  SELECT v.patientUnitStayID, v.vitalAperiodicID, v.observationOffset,
         'noninvasive_mean_bp', SAFE_CAST(v.nonInvasiveMean AS FLOAT64)
  FROM main m JOIN `physionet-data.eicu_crd.vitalaperiodic` v USING(patientUnitStayID)
  WHERE v.observationOffset BETWEEN 0 AND 720
),
clean AS (
  SELECT *,
    CASE feature
      WHEN 'heart_rate' THEN IF(raw_value BETWEEN 20 AND 250, raw_value, NULL)
      WHEN 'sao2' THEN IF(raw_value BETWEEN 30 AND 100, raw_value, NULL)
      WHEN 'respiratory_rate' THEN IF(raw_value BETWEEN 2 AND 80, raw_value, NULL)
      WHEN 'temperature_c' THEN IF(raw_value BETWEEN 25 AND 45, raw_value, NULL)
      WHEN 'invasive_systolic_bp' THEN IF(raw_value BETWEEN 30 AND 300, raw_value, NULL)
      WHEN 'invasive_diastolic_bp' THEN IF(raw_value BETWEEN 10 AND 200, raw_value, NULL)
      WHEN 'invasive_mean_bp' THEN IF(raw_value BETWEEN 20 AND 250, raw_value, NULL)
      WHEN 'noninvasive_systolic_bp' THEN IF(raw_value BETWEEN 30 AND 300, raw_value, NULL)
      WHEN 'noninvasive_diastolic_bp' THEN IF(raw_value BETWEEN 10 AND 200, raw_value, NULL)
      WHEN 'noninvasive_mean_bp' THEN IF(raw_value BETWEEN 20 AND 250, raw_value, NULL)
    END AS value
  FROM long_raw
),
valid AS (
  SELECT * FROM clean WHERE value IS NOT NULL
),
grouped AS (
  SELECT
    patientUnitStayID,
    feature,
    ARRAY_AGG(value ORDER BY offset_min, record_id LIMIT 1)[OFFSET(0)] AS first_value,
    ARRAY_AGG(value ORDER BY offset_min DESC, record_id DESC LIMIT 1)[OFFSET(0)] AS last_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    AVG(value) AS mean_value,
    STDDEV_SAMP(value) AS sd_value,
    COUNT(*) AS n_values
  FROM valid
  GROUP BY patientUnitStayID, feature
)
SELECT
  patientUnitStayID,
  MAX(IF(feature = 'heart_rate', first_value, NULL)) AS x_vital_heart_rate_first,
  MAX(IF(feature = 'heart_rate', last_value, NULL)) AS x_vital_heart_rate_last,
  MAX(IF(feature = 'heart_rate', min_value, NULL)) AS x_vital_heart_rate_min,
  MAX(IF(feature = 'heart_rate', max_value, NULL)) AS x_vital_heart_rate_max,
  MAX(IF(feature = 'heart_rate', mean_value, NULL)) AS x_vital_heart_rate_mean,
  MAX(IF(feature = 'heart_rate', sd_value, NULL)) AS x_vital_heart_rate_sd,
  MAX(IF(feature = 'heart_rate', n_values, NULL)) AS x_vital_heart_rate_n,
  MAX(IF(feature = 'sao2', first_value, NULL)) AS x_vital_sao2_first,
  MAX(IF(feature = 'sao2', last_value, NULL)) AS x_vital_sao2_last,
  MAX(IF(feature = 'sao2', min_value, NULL)) AS x_vital_sao2_min,
  MAX(IF(feature = 'sao2', max_value, NULL)) AS x_vital_sao2_max,
  MAX(IF(feature = 'sao2', mean_value, NULL)) AS x_vital_sao2_mean,
  MAX(IF(feature = 'sao2', sd_value, NULL)) AS x_vital_sao2_sd,
  MAX(IF(feature = 'sao2', n_values, NULL)) AS x_vital_sao2_n,
  MAX(IF(feature = 'respiratory_rate', first_value, NULL)) AS x_vital_respiratory_rate_first,
  MAX(IF(feature = 'respiratory_rate', last_value, NULL)) AS x_vital_respiratory_rate_last,
  MAX(IF(feature = 'respiratory_rate', min_value, NULL)) AS x_vital_respiratory_rate_min,
  MAX(IF(feature = 'respiratory_rate', max_value, NULL)) AS x_vital_respiratory_rate_max,
  MAX(IF(feature = 'respiratory_rate', mean_value, NULL)) AS x_vital_respiratory_rate_mean,
  MAX(IF(feature = 'respiratory_rate', sd_value, NULL)) AS x_vital_respiratory_rate_sd,
  MAX(IF(feature = 'respiratory_rate', n_values, NULL)) AS x_vital_respiratory_rate_n,
  MAX(IF(feature = 'temperature_c', first_value, NULL)) AS x_vital_temperature_c_first,
  MAX(IF(feature = 'temperature_c', last_value, NULL)) AS x_vital_temperature_c_last,
  MAX(IF(feature = 'temperature_c', min_value, NULL)) AS x_vital_temperature_c_min,
  MAX(IF(feature = 'temperature_c', max_value, NULL)) AS x_vital_temperature_c_max,
  MAX(IF(feature = 'temperature_c', mean_value, NULL)) AS x_vital_temperature_c_mean,
  MAX(IF(feature = 'temperature_c', sd_value, NULL)) AS x_vital_temperature_c_sd,
  MAX(IF(feature = 'temperature_c', n_values, NULL)) AS x_vital_temperature_c_n,
  MAX(IF(feature = 'invasive_systolic_bp', first_value, NULL)) AS x_vital_invasive_systolic_bp_first,
  MAX(IF(feature = 'invasive_systolic_bp', last_value, NULL)) AS x_vital_invasive_systolic_bp_last,
  MAX(IF(feature = 'invasive_systolic_bp', min_value, NULL)) AS x_vital_invasive_systolic_bp_min,
  MAX(IF(feature = 'invasive_systolic_bp', max_value, NULL)) AS x_vital_invasive_systolic_bp_max,
  MAX(IF(feature = 'invasive_systolic_bp', mean_value, NULL)) AS x_vital_invasive_systolic_bp_mean,
  MAX(IF(feature = 'invasive_systolic_bp', sd_value, NULL)) AS x_vital_invasive_systolic_bp_sd,
  MAX(IF(feature = 'invasive_systolic_bp', n_values, NULL)) AS x_vital_invasive_systolic_bp_n,
  MAX(IF(feature = 'invasive_diastolic_bp', first_value, NULL)) AS x_vital_invasive_diastolic_bp_first,
  MAX(IF(feature = 'invasive_diastolic_bp', last_value, NULL)) AS x_vital_invasive_diastolic_bp_last,
  MAX(IF(feature = 'invasive_diastolic_bp', min_value, NULL)) AS x_vital_invasive_diastolic_bp_min,
  MAX(IF(feature = 'invasive_diastolic_bp', max_value, NULL)) AS x_vital_invasive_diastolic_bp_max,
  MAX(IF(feature = 'invasive_diastolic_bp', mean_value, NULL)) AS x_vital_invasive_diastolic_bp_mean,
  MAX(IF(feature = 'invasive_diastolic_bp', sd_value, NULL)) AS x_vital_invasive_diastolic_bp_sd,
  MAX(IF(feature = 'invasive_diastolic_bp', n_values, NULL)) AS x_vital_invasive_diastolic_bp_n,
  MAX(IF(feature = 'invasive_mean_bp', first_value, NULL)) AS x_vital_invasive_mean_bp_first,
  MAX(IF(feature = 'invasive_mean_bp', last_value, NULL)) AS x_vital_invasive_mean_bp_last,
  MAX(IF(feature = 'invasive_mean_bp', min_value, NULL)) AS x_vital_invasive_mean_bp_min,
  MAX(IF(feature = 'invasive_mean_bp', max_value, NULL)) AS x_vital_invasive_mean_bp_max,
  MAX(IF(feature = 'invasive_mean_bp', mean_value, NULL)) AS x_vital_invasive_mean_bp_mean,
  MAX(IF(feature = 'invasive_mean_bp', sd_value, NULL)) AS x_vital_invasive_mean_bp_sd,
  MAX(IF(feature = 'invasive_mean_bp', n_values, NULL)) AS x_vital_invasive_mean_bp_n,
  MAX(IF(feature = 'noninvasive_systolic_bp', first_value, NULL)) AS x_vital_noninvasive_systolic_bp_first,
  MAX(IF(feature = 'noninvasive_systolic_bp', last_value, NULL)) AS x_vital_noninvasive_systolic_bp_last,
  MAX(IF(feature = 'noninvasive_systolic_bp', min_value, NULL)) AS x_vital_noninvasive_systolic_bp_min,
  MAX(IF(feature = 'noninvasive_systolic_bp', max_value, NULL)) AS x_vital_noninvasive_systolic_bp_max,
  MAX(IF(feature = 'noninvasive_systolic_bp', mean_value, NULL)) AS x_vital_noninvasive_systolic_bp_mean,
  MAX(IF(feature = 'noninvasive_systolic_bp', sd_value, NULL)) AS x_vital_noninvasive_systolic_bp_sd,
  MAX(IF(feature = 'noninvasive_systolic_bp', n_values, NULL)) AS x_vital_noninvasive_systolic_bp_n,
  MAX(IF(feature = 'noninvasive_diastolic_bp', first_value, NULL)) AS x_vital_noninvasive_diastolic_bp_first,
  MAX(IF(feature = 'noninvasive_diastolic_bp', last_value, NULL)) AS x_vital_noninvasive_diastolic_bp_last,
  MAX(IF(feature = 'noninvasive_diastolic_bp', min_value, NULL)) AS x_vital_noninvasive_diastolic_bp_min,
  MAX(IF(feature = 'noninvasive_diastolic_bp', max_value, NULL)) AS x_vital_noninvasive_diastolic_bp_max,
  MAX(IF(feature = 'noninvasive_diastolic_bp', mean_value, NULL)) AS x_vital_noninvasive_diastolic_bp_mean,
  MAX(IF(feature = 'noninvasive_diastolic_bp', sd_value, NULL)) AS x_vital_noninvasive_diastolic_bp_sd,
  MAX(IF(feature = 'noninvasive_diastolic_bp', n_values, NULL)) AS x_vital_noninvasive_diastolic_bp_n,
  MAX(IF(feature = 'noninvasive_mean_bp', first_value, NULL)) AS x_vital_noninvasive_mean_bp_first,
  MAX(IF(feature = 'noninvasive_mean_bp', last_value, NULL)) AS x_vital_noninvasive_mean_bp_last,
  MAX(IF(feature = 'noninvasive_mean_bp', min_value, NULL)) AS x_vital_noninvasive_mean_bp_min,
  MAX(IF(feature = 'noninvasive_mean_bp', max_value, NULL)) AS x_vital_noninvasive_mean_bp_max,
  MAX(IF(feature = 'noninvasive_mean_bp', mean_value, NULL)) AS x_vital_noninvasive_mean_bp_mean,
  MAX(IF(feature = 'noninvasive_mean_bp', sd_value, NULL)) AS x_vital_noninvasive_mean_bp_sd,
  MAX(IF(feature = 'noninvasive_mean_bp', n_values, NULL)) AS x_vital_noninvasive_mean_bp_n
FROM grouped
GROUP BY patientUnitStayID;
