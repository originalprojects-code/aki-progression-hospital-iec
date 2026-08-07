-- Persistent secure table: final cohort/outcome flags and observation adequacy.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1` AS
WITH stage_summary AS (
  SELECT
    b.patientUnitStayID,
    b.patientHealthSystemStayID,
    b.uniquePID,
    b.hospitalID,
    b.unitDischargeOffset,
    b.unit_discharge_status,
    b.n_hospitals_for_patient,
    b.n_hospital_stays_for_patient,
    b.eligible_unit_rank_in_hospstay,
    ANY_VALUE(s.reference_offset) AS reference_offset,
    ANY_VALUE(s.reference_creatinine) AS reference_creatinine,
    MAX(IF(s.labResultOffset BETWEEN s.reference_offset AND 720, s.kdigo_creatinine_stage, NULL)) AS max_stage_by_12h,
    MIN(IF(s.labResultOffset > 720 AND s.labResultOffset <= LEAST(b.unitDischargeOffset,4320)
           AND s.kdigo_creatinine_stage >= 2, s.labResultOffset, NULL)) AS incident_stage23_offset,
    MAX(IF(s.labResultOffset > 720 AND s.labResultOffset <= LEAST(b.unitDischargeOffset,4320),
           s.kdigo_creatinine_stage, NULL)) AS max_stage_12_72h,
    MAX(IF(s.labResultOffset > 720 AND s.labResultOffset <= LEAST(b.unitDischargeOffset,4320),
           s.labResultOffset, NULL)) AS last_future_creatinine_offset,
    COUNTIF(s.labResultOffset > 2880 AND s.labResultOffset <= LEAST(b.unitDischargeOffset,4320)) AS n_creatinine_48_72h
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1` b
  LEFT JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.creatinine_staged_v1` s USING(patientUnitStayID)
  WHERE b.eligible_unit_rank_in_hospstay = 1
    AND b.n_hospitals_for_patient = 1
  GROUP BY b.patientUnitStayID,b.patientHealthSystemStayID,b.uniquePID,b.hospitalID,
           b.unitDischargeOffset,b.unit_discharge_status,b.n_hospitals_for_patient,
           b.n_hospital_stays_for_patient,b.eligible_unit_rank_in_hospstay
),
joined AS (
  SELECT s.*, r.strict_chronic_dialysis_esrd, r.broad_chronic_renal_support,
         r.first_acute_rrt_strict_offset, r.first_acute_rrt_broad_offset,
         r.first_nonzero_dialysis_io_offset,
    CASE
      WHEN s.incident_stage23_offset IS NOT NULL THEN 1
      WHEN s.unitDischargeOffset >= 4320 AND s.n_creatinine_48_72h > 0 THEN 0
      WHEN s.unitDischargeOffset > 720 AND s.unitDischargeOffset < 4320
        AND s.unit_discharge_status = 'alive'
        AND s.last_future_creatinine_offset IS NOT NULL
        AND s.last_future_creatinine_offset >= s.unitDischargeOffset - 1440 THEN 0
      ELSE NULL
    END AS outcome_creatinine_stage23,
    CASE
      WHEN s.incident_stage23_offset IS NOT NULL THEN 'positive_creatinine'
      WHEN s.unitDischargeOffset > 720 AND s.unitDischargeOffset < 4320
        AND s.unit_discharge_status = 'expired' THEN 'indeterminate_early_death'
      WHEN s.unitDischargeOffset >= 4320 AND s.n_creatinine_48_72h > 0 THEN 'negative_late_creatinine'
      WHEN s.unitDischargeOffset > 720 AND s.unitDischargeOffset < 4320
        AND s.unit_discharge_status = 'alive'
        AND s.last_future_creatinine_offset >= s.unitDischargeOffset - 1440 THEN 'negative_live_discharge_recent_creatinine'
      WHEN s.last_future_creatinine_offset IS NULL THEN 'indeterminate_no_future_creatinine'
      ELSE 'indeterminate_inadequate_followup'
    END AS observation_class
  FROM stage_summary s
  LEFT JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.renal_flags_v1` r USING(patientUnitStayID)
),
finalized AS (
  SELECT *,
    CASE
      WHEN outcome_creatinine_stage23 = 1 THEN 1
      WHEN first_acute_rrt_strict_offset > 720
       AND first_acute_rrt_strict_offset <= LEAST(unitDischargeOffset,4320) THEN 1
      ELSE outcome_creatinine_stage23
    END AS outcome_stage23_or_strict_rrt,
    CASE WHEN max_stage_by_12h = 1 THEN 1 ELSE 0 END AS stage1_at_prediction,
    CASE
      WHEN reference_creatinine IS NOT NULL
       AND COALESCE(strict_chronic_dialysis_esrd,0) = 0
       AND COALESCE(max_stage_by_12h,0) < 2
       AND NOT (first_acute_rrt_strict_offset IS NOT NULL AND first_acute_rrt_strict_offset <= 720)
       AND outcome_creatinine_stage23 IS NOT NULL
      THEN 1 ELSE 0
    END AS eligible_main_cohort,
    CASE
      WHEN reference_creatinine IS NOT NULL
       AND COALESCE(strict_chronic_dialysis_esrd,0) = 0
       AND COALESCE(max_stage_by_12h,0) < 2
       AND NOT (first_acute_rrt_strict_offset IS NOT NULL AND first_acute_rrt_strict_offset <= 720)
       AND (outcome_creatinine_stage23 IS NOT NULL
            OR (first_acute_rrt_strict_offset > 720
                AND first_acute_rrt_strict_offset <= LEAST(unitDischargeOffset,4320)))
      THEN 1 ELSE 0
    END AS eligible_rrt_composite_cohort
  FROM joined
)
SELECT *,
  ROW_NUMBER() OVER (
    PARTITION BY uniquePID
    ORDER BY eligible_main_cohort DESC, patientHealthSystemStayID, patientUnitStayID
  ) AS deterministic_eligible_patient_stay_rank
FROM finalized;
