-- Paper 1 reference reconstruction. Frozen source: sql/04_creatinine_staged.sql.
-- reference_run_id={{RUN_ID}}
CREATE OR REPLACE TABLE `{{DESTINATION_PROJECT_ID}}.{{DESTINATION_DATASET}}.creatinine_staged_v1` AS
WITH refs AS (
  SELECT
    c.patientUnitStayID,
    ARRAY_AGG(STRUCT(c.labResultOffset AS ref_offset, c.creatinine AS ref_creatinine)
              ORDER BY c.labResultOffset LIMIT 1)[OFFSET(0)] AS ref
  FROM `{{DESTINATION_PROJECT_ID}}.{{DESTINATION_DATASET}}.creatinine_long_v1` c
  JOIN `{{DESTINATION_PROJECT_ID}}.{{DESTINATION_DATASET}}.base_stays_v1` b USING(patientUnitStayID)
  WHERE c.labResultOffset BETWEEN GREATEST(b.hospitalAdmitOffset,-1440) AND 360
  GROUP BY c.patientUnitStayID
),
trajectory AS (
  SELECT
    c.*,
    r.ref.ref_offset AS reference_offset,
    r.ref.ref_creatinine AS reference_creatinine,
    SAFE_DIVIDE(c.creatinine, r.ref.ref_creatinine) AS creatinine_ratio,
    MIN(c.creatinine) OVER (
      PARTITION BY c.patientUnitStayID
      ORDER BY c.labResultOffset
      RANGE BETWEEN 2880 PRECEDING AND 1 PRECEDING
    ) AS prior_min_creatinine_48h
  FROM `{{DESTINATION_PROJECT_ID}}.{{DESTINATION_DATASET}}.creatinine_long_v1` c
  JOIN refs r USING(patientUnitStayID)
),
classified AS (
  SELECT *,
    (creatinine_ratio >= 1.5
      OR (prior_min_creatinine_48h IS NOT NULL
          AND creatinine - prior_min_creatinine_48h >= 0.3)) AS aki_definition_met
  FROM trajectory
)
SELECT *,
  CASE
    WHEN creatinine_ratio >= 3.0
      OR (creatinine >= 4.0 AND aki_definition_met) THEN 3
    WHEN creatinine_ratio >= 2.0 THEN 2
    WHEN aki_definition_met THEN 1
    ELSE 0
  END AS kdigo_creatinine_stage
FROM classified;
