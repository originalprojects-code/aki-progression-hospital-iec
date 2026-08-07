-- Persistent secure table: one revised serum creatinine value per stay/offset.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.creatinine_long_v1` AS
WITH raw AS (
  SELECT
    b.patientUnitStayID,
    b.patientHealthSystemStayID,
    b.uniquePID,
    b.hospitalID,
    b.hospitalAdmitOffset,
    b.unitDischargeOffset,
    l.labID,
    l.labResultOffset,
    l.labResultRevisedOffset,
    SAFE_CAST(l.labResult AS FLOAT64) AS creatinine,
    ROW_NUMBER() OVER (
      PARTITION BY l.patientUnitStayID, l.labResultOffset
      ORDER BY COALESCE(l.labResultRevisedOffset, l.labResultOffset) DESC, l.labID DESC
    ) AS revision_rank
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1` b
  JOIN `physionet-data.eicu_crd.lab` l USING (patientUnitStayID)
  WHERE b.eligible_unit_rank_in_hospstay = 1
    AND b.n_hospitals_for_patient = 1
    AND LOWER(TRIM(l.labName)) = 'creatinine'
    AND SAFE_CAST(l.labResult AS FLOAT64) BETWEEN 0.1 AND 30.0
    AND l.labResultOffset BETWEEN GREATEST(b.hospitalAdmitOffset, -1440)
                              AND LEAST(b.unitDischargeOffset, 4320)
)
SELECT * EXCEPT(revision_rank)
FROM raw
WHERE revision_rank = 1;
