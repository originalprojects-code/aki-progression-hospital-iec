-- Paper 1 D-005 P3-C paired outcome-composition audit.
-- Static preparation only. Read-only aggregate output; no persistent objects.
-- Identifier ordering is a nonchronological technical sensitivity.  It is not
-- prospective indexing, chronological admission order, or deployment logic.
-- E_frozen_reconstruction is a retrospective frozen-reconstruction comparator,
-- not clinically availability-confirmed information at the 720-minute landmark.

WITH
base_key_counts AS (
  SELECT patientUnitStayID, COUNT(*) AS n
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1`
  GROUP BY patientUnitStayID
),
outcome_key_counts AS (
  SELECT patientUnitStayID, COUNT(*) AS n
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1`
  GROUP BY patientUnitStayID
),
base_singletons AS (
  SELECT b.*
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1` AS b
  JOIN base_key_counts AS k USING (patientUnitStayID)
  WHERE k.n = 1
),
outcome_singletons AS (
  SELECT o.*
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1` AS o
  JOIN outcome_key_counts AS k USING (patientUnitStayID)
  WHERE k.n = 1
),
-- Same frozen-restricted landmark universe as the approved P3-C audit.
frozen_restricted_base AS (
  SELECT *
  FROM base_singletons
  WHERE uniquePID IS NOT NULL
    AND eligible_unit_rank_in_hospstay = 1
    AND n_hospitals_for_patient = 1
),
frozen_rows AS (
  SELECT
    b.patientUnitStayID,
    b.uniquePID,
    b.patientHealthSystemStayID,
    b.unitVisitNumber,
    o.reference_creatinine,
    o.max_stage_by_12h,
    o.strict_chronic_dialysis_esrd,
    o.first_acute_rrt_strict_offset,
    o.outcome_creatinine_stage23,
    o.observation_class,
    o.incident_stage23_offset,
    o.eligible_main_cohort,
    o.deterministic_eligible_patient_stay_rank
  FROM frozen_restricted_base AS b
  JOIN outcome_singletons AS o USING (patientUnitStayID)
),
e_frozen_reconstruction AS (
  -- Exact approved Option A comparator definition; not a D-001 availability rule.
  SELECT *
  FROM frozen_rows
  WHERE reference_creatinine IS NOT NULL
    AND COALESCE(strict_chronic_dialysis_esrd, 0) = 0
    AND COALESCE(max_stage_by_12h, 0) < 2
    AND NOT (
      first_acute_rrt_strict_offset IS NOT NULL
      AND first_acute_rrt_strict_offset <= 720
    )
),
frozen_selected_details AS (
  -- Exact frozen selection fields and predicate; no ranking is recomputed here.
  SELECT
    uniquePID,
    patientUnitStayID AS frozen_selected_stay,
    outcome_creatinine_stage23 AS frozen_outcome,
    observation_class AS frozen_observation_class,
    incident_stage23_offset AS frozen_incident_stage23_offset
  FROM frozen_rows
  WHERE eligible_main_cohort = 1
    AND deterministic_eligible_patient_stay_rank = 1
),
technical_ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY uniquePID
      ORDER BY patientHealthSystemStayID,
               COALESCE(unitVisitNumber, 999999),
               patientUnitStayID
    ) AS technical_rank
  FROM e_frozen_reconstruction
),
technical_selected_details AS (
  SELECT
    uniquePID,
    patientUnitStayID AS technical_selected_stay,
    outcome_creatinine_stage23 AS technical_outcome,
    observation_class AS technical_observation_class,
    incident_stage23_offset AS technical_incident_stage23_offset
  FROM technical_ranked
  WHERE technical_rank = 1
),
matched_patient_universe AS (
  SELECT DISTINCT uniquePID FROM e_frozen_reconstruction
),
p3c_matched_pairs AS (
  -- Exactly one internal pair per patient is expected and QCed below.
  SELECT
    u.uniquePID,
    f.frozen_selected_stay,
    t.technical_selected_stay,
    CASE
      WHEN f.frozen_selected_stay IS NOT NULL
       AND t.technical_selected_stay IS NOT NULL
       AND f.frozen_selected_stay = t.technical_selected_stay THEN 'same_stay'
      WHEN f.frozen_selected_stay IS NOT NULL
       AND t.technical_selected_stay IS NOT NULL THEN 'different_stay'
      WHEN f.frozen_selected_stay IS NOT NULL THEN 'frozen_only'
      WHEN t.technical_selected_stay IS NOT NULL THEN 'technical_only'
      ELSE 'neither'
    END AS pair_category
  FROM matched_patient_universe AS u
  LEFT JOIN frozen_selected_details AS f USING (uniquePID)
  LEFT JOIN technical_selected_details AS t USING (uniquePID)
),
different_stay_pairs AS (
  SELECT *
  FROM p3c_matched_pairs
  WHERE pair_category = 'different_stay'
),
paired_details AS (
  -- The paired grain is one different-selected-stay pair within one uniquePID.
  SELECT
    p.uniquePID,
    p.frozen_selected_stay AS paired_frozen_selected_stay,
    p.technical_selected_stay AS paired_technical_selected_stay,
    f.frozen_selected_stay AS frozen_detail_selected_stay,
    t.technical_selected_stay AS technical_detail_selected_stay,
    f.frozen_outcome,
    f.frozen_observation_class,
    f.frozen_incident_stage23_offset,
    t.technical_outcome,
    t.technical_observation_class,
    t.technical_incident_stage23_offset
  FROM different_stay_pairs AS p
  LEFT JOIN frozen_selected_details AS f
    ON p.uniquePID = f.uniquePID
   AND p.frozen_selected_stay = f.frozen_selected_stay
  LEFT JOIN technical_selected_details AS t
    ON p.uniquePID = t.uniquePID
   AND p.technical_selected_stay = t.technical_selected_stay
),
classified_pairs AS (
  -- Keep every different-stay pair in the transition denominator. Missing
  -- fields are classified explicitly below rather than silently dropped.
  SELECT *,
    CASE
      WHEN frozen_outcome = 1 THEN 'positive'
      WHEN frozen_outcome = 0 THEN 'negative'
      WHEN frozen_outcome IS NULL THEN 'indeterminate_null'
      ELSE 'unexpected_outcome_value'
    END AS frozen_outcome_category,
    CASE
      WHEN technical_outcome = 1 THEN 'positive'
      WHEN technical_outcome = 0 THEN 'negative'
      WHEN technical_outcome IS NULL THEN 'indeterminate_null'
      ELSE 'unexpected_outcome_value'
    END AS technical_outcome_category,
    CASE
      WHEN frozen_observation_class IN (
        'positive_creatinine',
        'indeterminate_early_death',
        'negative_late_creatinine',
        'negative_live_discharge_recent_creatinine',
        'indeterminate_no_future_creatinine',
        'indeterminate_inadequate_followup'
      ) THEN frozen_observation_class
      WHEN frozen_observation_class IS NULL THEN 'unknown_null_observation_class'
      ELSE 'unexpected_observation_class'
    END AS frozen_observation_category,
    CASE
      WHEN technical_observation_class IN (
        'positive_creatinine',
        'indeterminate_early_death',
        'negative_late_creatinine',
        'negative_live_discharge_recent_creatinine',
        'indeterminate_no_future_creatinine',
        'indeterminate_inadequate_followup'
      ) THEN technical_observation_class
      WHEN technical_observation_class IS NULL THEN 'unknown_null_observation_class'
      ELSE 'unexpected_observation_class'
    END AS technical_observation_category,
    IF(frozen_incident_stage23_offset IS NULL,
       'no_observed_stage23_event', 'observed_stage23_event')
       AS frozen_event_category,
    IF(technical_incident_stage23_offset IS NULL,
       'no_observed_stage23_event', 'observed_stage23_event')
       AS technical_event_category
  FROM paired_details
),
outcome_categories AS (
  SELECT 'positive' AS category UNION ALL SELECT 'negative'
  UNION ALL SELECT 'indeterminate_null' UNION ALL SELECT 'unexpected_outcome_value'
),
observation_categories AS (
  SELECT 'positive_creatinine' AS category
  UNION ALL SELECT 'indeterminate_early_death'
  UNION ALL SELECT 'negative_late_creatinine'
  UNION ALL SELECT 'negative_live_discharge_recent_creatinine'
  UNION ALL SELECT 'indeterminate_no_future_creatinine'
  UNION ALL SELECT 'indeterminate_inadequate_followup'
  UNION ALL SELECT 'unknown_null_observation_class'
  UNION ALL SELECT 'unexpected_observation_class'
),
event_categories AS (
  SELECT 'observed_stage23_event' AS category
  UNION ALL SELECT 'no_observed_stage23_event'
),
transition_category_definitions AS (
  SELECT 'paired_primary_outcome_transition' AS section,
         CONCAT('frozen_', f.category, '_to_technical_', t.category) AS category
  FROM outcome_categories AS f CROSS JOIN outcome_categories AS t
  UNION ALL
  SELECT 'paired_observation_class_transition',
         CONCAT('frozen_', f.category, '_to_technical_', t.category)
  FROM observation_categories AS f CROSS JOIN observation_categories AS t
  UNION ALL
  SELECT 'paired_observed_stage23_event_transition',
         CONCAT('frozen_', f.category, '_to_technical_', t.category)
  FROM event_categories AS f CROSS JOIN event_categories AS t
),
observed_transition_rows AS (
  SELECT 'paired_primary_outcome_transition' AS section,
         CONCAT('frozen_', frozen_outcome_category, '_to_technical_',
                technical_outcome_category) AS category
  FROM classified_pairs
  UNION ALL
  SELECT 'paired_observation_class_transition',
         CONCAT('frozen_', frozen_observation_category, '_to_technical_',
                technical_observation_category)
  FROM classified_pairs
  UNION ALL
  SELECT 'paired_observed_stage23_event_transition',
         CONCAT('frozen_', frozen_event_category, '_to_technical_',
                technical_event_category)
  FROM classified_pairs
),
observed_transition_counts AS (
  SELECT section, category, COUNT(*) AS value
  FROM observed_transition_rows
  GROUP BY section, category
),
transition_counts AS (
  SELECT d.section, 'patients' AS unit, d.category, COALESCE(o.value, 0) AS value
  FROM transition_category_definitions AS d
  LEFT JOIN observed_transition_counts AS o USING (section, category)
),
detailed_transition_gate AS (
  -- One common gate avoids reconstructing a small cell from a related paired
  -- outcome, observation-class, or observed-event partition.
  SELECT COUNTIF(value BETWEEN 1 AND 10) = 0 AS releasable
  FROM transition_counts
),
integrity_qc AS (
  SELECT 'base_duplicate_stay_key_groups' AS category, COUNTIF(n > 1) AS value
  FROM base_key_counts
  UNION ALL
  SELECT 'outcome_duplicate_stay_key_groups', COUNTIF(n > 1)
  FROM outcome_key_counts
  UNION ALL
  SELECT 'frozen_restricted_base_missing_singleton_outcome_record', COUNT(*)
  FROM frozen_restricted_base AS b
  LEFT JOIN outcome_singletons AS o USING (patientUnitStayID)
  WHERE o.patientUnitStayID IS NULL
  UNION ALL
  SELECT 'frozen_selected_duplicate_uniquePID_groups', COUNT(*)
  FROM (
    SELECT uniquePID
    FROM frozen_selected_details
    GROUP BY uniquePID
    HAVING COUNT(*) > 1
  )
  UNION ALL
  SELECT 'technical_selected_duplicate_uniquePID_groups', COUNT(*)
  FROM (
    SELECT uniquePID
    FROM technical_selected_details
    GROUP BY uniquePID
    HAVING COUNT(*) > 1
  )
  UNION ALL
  SELECT 'p3c_matched_pair_duplicate_uniquePID_groups', COUNT(*)
  FROM (
    SELECT uniquePID
    FROM p3c_matched_pairs
    GROUP BY uniquePID
    HAVING COUNT(*) > 1
  )
  UNION ALL
  SELECT 'p3c_different_stay_pairs', COUNT(*) FROM different_stay_pairs
  UNION ALL
  SELECT 'paired_detail_rows', COUNT(*) FROM paired_details
  UNION ALL
  SELECT 'p3c_different_stay_pairs_minus_paired_detail_rows',
         (SELECT COUNT(*) FROM different_stay_pairs) - (SELECT COUNT(*) FROM paired_details)
  UNION ALL
  SELECT 'p3c_different_stay_set_minus_paired_detail_set', COUNT(*)
  FROM (
    SELECT uniquePID FROM different_stay_pairs
    EXCEPT DISTINCT
    SELECT uniquePID FROM paired_details
  ) AS p3c_minus_detail
  UNION ALL
  SELECT 'paired_detail_set_minus_p3c_different_stay_set', COUNT(*)
  FROM (
    SELECT uniquePID FROM paired_details
    EXCEPT DISTINCT
    SELECT uniquePID FROM different_stay_pairs
  ) AS detail_minus_p3c
  UNION ALL
  -- Join integrity is checked only with the selected-stay keys.  A NULL
  -- clinical field is a valid outcome/observation category, not a missing join.
  SELECT 'paired_detail_rows_without_frozen_selected_stay_key_match', COUNT(*)
  FROM paired_details
  WHERE frozen_detail_selected_stay IS NULL
     OR paired_frozen_selected_stay IS NULL
     OR frozen_detail_selected_stay != paired_frozen_selected_stay
  UNION ALL
  SELECT 'paired_detail_rows_without_technical_selected_stay_key_match', COUNT(*)
  FROM paired_details
  WHERE technical_detail_selected_stay IS NULL
     OR paired_technical_selected_stay IS NULL
     OR technical_detail_selected_stay != paired_technical_selected_stay
  UNION ALL
  -- Valid combinations are positive with an observed event, negative without
  -- an observed event, and indeterminate NULL without an observed event.
  -- All other combinations, including observed event plus NULL/negative label,
  -- are contradictions. This CASE is deliberately NULL-safe.
  SELECT 'frozen_primary_label_event_contradictions', COUNTIF(
    CASE
      WHEN frozen_outcome = 1
       AND frozen_incident_stage23_offset IS NOT NULL THEN FALSE
      WHEN frozen_outcome = 0
       AND frozen_incident_stage23_offset IS NULL THEN FALSE
      WHEN frozen_outcome IS NULL
       AND frozen_incident_stage23_offset IS NULL THEN FALSE
      ELSE TRUE
    END
  )
  FROM paired_details
  UNION ALL
  SELECT 'technical_primary_label_event_contradictions', COUNTIF(
    CASE
      WHEN technical_outcome = 1
       AND technical_incident_stage23_offset IS NOT NULL THEN FALSE
      WHEN technical_outcome = 0
       AND technical_incident_stage23_offset IS NULL THEN FALSE
      WHEN technical_outcome IS NULL
       AND technical_incident_stage23_offset IS NULL THEN FALSE
      ELSE TRUE
    END
  )
  FROM paired_details
),
public_transition_rows AS (
  SELECT section, unit, category, value, 'released' AS release_status
  FROM transition_counts
  CROSS JOIN detailed_transition_gate
  WHERE releasable
),
suppressed_transition_rows AS (
  SELECT section, 'patients' AS unit, 'all_categories' AS category,
         CAST(NULL AS INT64) AS value,
         'suppressed_common_partition_contains_small_nonzero_cell' AS release_status
  FROM (SELECT DISTINCT section FROM transition_counts)
  CROSS JOIN detailed_transition_gate
  WHERE NOT releasable
),
public_qc AS (
  SELECT 'integrity_qc' AS section, 'technical_qc' AS unit, category,
    CASE WHEN value = 0 OR value >= 11 THEN value ELSE CAST(NULL AS INT64) END AS value,
    CASE
      WHEN value = 0 THEN 'released_zero_technical_qc'
      WHEN value >= 11 THEN 'released_broad_technical_qc'
      ELSE 'suppressed_small_technical_qc'
    END AS release_status
  FROM integrity_qc
)
SELECT * FROM public_transition_rows
UNION ALL
SELECT * FROM suppressed_transition_rows
UNION ALL
SELECT * FROM public_qc
ORDER BY section, unit, category;
