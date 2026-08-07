-- Secure one-row-per-patient static feature table.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.feature_static_v1` AS
SELECT
  c.patientUnitStayID,
  c.hospitalID,
  TO_HEX(SHA256(CONCAT('AKI_V2_STAY|', CAST(c.patientUnitStayID AS STRING)))) AS id_row,
  TO_HEX(SHA256(CONCAT('AKI_V2_HOSPITAL|', CAST(c.hospitalID AS STRING)))) AS group_hospital,
  c.outcome_creatinine_stage23 AS label_stage23,

  CASE WHEN p.age = '> 89' THEN 90 ELSE SAFE_CAST(p.age AS INT64) END AS x_age_years,
  CASE
    WHEN LOWER(TRIM(p.gender)) = 'female' THEN 'female'
    WHEN LOWER(TRIM(p.gender)) = 'male' THEN 'male'
    ELSE 'other_or_missing'
  END AS x_sex,
  CASE
    WHEN p.admissionHeight BETWEEN 100 AND 250
     AND p.admissionWeight BETWEEN 25 AND 300
     AND SAFE_DIVIDE(p.admissionWeight, POW(p.admissionHeight / 100.0, 2)) BETWEEN 10 AND 80
    THEN SAFE_DIVIDE(p.admissionWeight, POW(p.admissionHeight / 100.0, 2))
  END AS x_bmi,
  IF(p.admissionWeight BETWEEN 25 AND 300, p.admissionWeight, NULL) AS x_admission_weight_kg,
  NULLIF(TRIM(p.unitType), '') AS x_unit_type,
  NULLIF(TRIM(p.unitAdmitSource), '') AS x_unit_admit_source,
  NULLIF(TRIM(p.hospitalAdmitSource), '') AS x_hospital_admit_source,
  c.reference_creatinine AS x_reference_creatinine,
  c.stage1_at_prediction AS x_stage1_at_landmark,

  NULLIF(TRIM(p.ethnicity), '') AS audit_ethnicity,
  NULLIF(TRIM(h.region), '') AS audit_hospital_region,
  NULLIF(TRIM(h.numBedsCategory), '') AS audit_hospital_bed_category,
  h.teachingStatus AS audit_hospital_teaching_status,
  c.reference_offset AS audit_reference_offset
FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1` c
JOIN `physionet-data.eicu_crd.patient` p
  ON p.patientUnitStayID = c.patientUnitStayID
LEFT JOIN `physionet-data.eicu_crd.hospital` h
  ON h.hospitalID = c.hospitalID
WHERE c.eligible_main_cohort = 1
  AND c.deterministic_eligible_patient_stay_rank = 1;
