-- Persistent secure table: adult stays and identifier structure.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1` AS
WITH adults AS (
  SELECT
    patientUnitStayID,
    patientHealthSystemStayID,
    uniquePID,
    hospitalID,
    unitVisitNumber,
    hospitalAdmitOffset,
    unitDischargeOffset,
    LOWER(TRIM(unitDischargeStatus)) AS unit_discharge_status,
    LOWER(TRIM(hospitalDischargeStatus)) AS hospital_discharge_status,
    CASE WHEN age = '> 89' THEN 90 ELSE SAFE_CAST(age AS INT64) END AS age_num
  FROM `physionet-data.eicu_crd.patient`
  WHERE (CASE WHEN age = '> 89' THEN 90 ELSE SAFE_CAST(age AS INT64) END) >= 18
    AND unitDischargeOffset >= 720
),
patient_structure AS (
  -- Use the full patient table, not only eligible 12 h stays, to detect cross-hospital patients.
  SELECT
    uniquePID,
    COUNT(DISTINCT hospitalID) AS n_hospitals_for_patient,
    COUNT(DISTINCT patientHealthSystemStayID) AS n_hospital_stays_for_patient,
    COUNT(DISTINCT patientUnitStayID) AS n_unit_stays_for_patient
  FROM `physionet-data.eicu_crd.patient`
  GROUP BY uniquePID
),
ranked AS (
  SELECT
    a.*,
    s.n_hospitals_for_patient,
    s.n_hospital_stays_for_patient,
    s.n_unit_stays_for_patient,
    ROW_NUMBER() OVER (
      PARTITION BY a.patientHealthSystemStayID
      ORDER BY COALESCE(a.unitVisitNumber, 999999), a.patientUnitStayID
    ) AS eligible_unit_rank_in_hospstay
  FROM adults a
  JOIN patient_structure s USING (uniquePID)
)
SELECT * FROM ranked;
