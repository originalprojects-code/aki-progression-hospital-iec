-- Paper 1 D-005 P3-A / P3-C aggregate comparison.
-- Static preparation only. This query is read-only and aggregate-only.
-- P3-A uses E_frozen_reconstruction by explicit Option A approval: it is a
-- retrospective frozen-reconstruction comparator, not a 720-minute clinical-
-- availability claim. P3-C identifier ordering is nonchronological technical
-- sensitivity only and must not be described as prospective indexing.

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
-- base_stays_v1 already encodes adult stays reaching the 720-minute landmark.
broad_landmark_base AS (
  SELECT *
  FROM base_singletons
  WHERE uniquePID IS NOT NULL
    AND eligible_unit_rank_in_hospstay = 1
),
frozen_restricted_base AS (
  SELECT *
  FROM broad_landmark_base
  WHERE n_hospitals_for_patient = 1
),
frozen_rows AS (
  SELECT b.*, o.reference_creatinine, o.max_stage_by_12h,
         o.strict_chronic_dialysis_esrd, o.first_acute_rrt_strict_offset,
         o.incident_stage23_offset, o.n_creatinine_48_72h,
         o.last_future_creatinine_offset, o.outcome_creatinine_stage23,
         o.eligible_main_cohort, o.deterministic_eligible_patient_stay_rank
  FROM frozen_restricted_base AS b
  JOIN outcome_singletons AS o USING (patientUnitStayID)
),
e_frozen_reconstruction AS (
  -- Deliberately frozen-reconstruction eligibility, not availability-confirmed
  -- landmark eligibility. See D-001 and the static review.
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
p3a_flags AS (
  SELECT *,
    (
      (unitDischargeOffset >= 4320 AND n_creatinine_48_72h > 0)
      OR (
        unitDischargeOffset > 720
        AND unitDischargeOffset < 4320
        AND unit_discharge_status = 'alive'
        AND last_future_creatinine_offset IS NOT NULL
        AND last_future_creatinine_offset >= unitDischargeOffset - 1440
      )
    ) AS p3a_surveillance_eligible,
    eligible_main_cohort = 1 AS frozen_main_member,
    incident_stage23_offset IS NOT NULL AS observed_stage23_event
  FROM e_frozen_reconstruction
),
p3a_stay_membership AS (
  SELECT patientUnitStayID, uniquePID,
    CASE
      WHEN frozen_main_member AND p3a_surveillance_eligible THEN 'both'
      WHEN frozen_main_member AND NOT p3a_surveillance_eligible THEN 'frozen_only'
      WHEN NOT frozen_main_member AND p3a_surveillance_eligible THEN 'p3a_only'
      ELSE 'neither'
    END AS category
  FROM p3a_flags
),
p3a_patient_membership AS (
  SELECT uniquePID,
    CASE
      WHEN LOGICAL_OR(frozen_main_member) AND LOGICAL_OR(p3a_surveillance_eligible) THEN 'both'
      WHEN LOGICAL_OR(frozen_main_member) AND NOT LOGICAL_OR(p3a_surveillance_eligible) THEN 'frozen_only'
      WHEN NOT LOGICAL_OR(frozen_main_member) AND LOGICAL_OR(p3a_surveillance_eligible) THEN 'p3a_only'
      ELSE 'neither'
    END AS category
  FROM p3a_flags
  GROUP BY uniquePID
),
p3a_common_label_stays AS (
  SELECT patientUnitStayID, uniquePID,
    CONCAT(
      'frozen_', CAST(outcome_creatinine_stage23 AS STRING),
      '_p3a_', CAST(IF(observed_stage23_event, 1, 0) AS STRING)
    ) AS category
  FROM p3a_flags
  WHERE frozen_main_member AND p3a_surveillance_eligible
),
p3a_observed_positive_exclusions AS (
  SELECT patientUnitStayID, uniquePID,
    IF(p3a_surveillance_eligible, 'retained_under_p3a', 'excluded_under_p3a') AS category
  FROM p3a_flags
  WHERE observed_stage23_event
),
frozen_selected AS (
  SELECT uniquePID, patientUnitStayID AS frozen_selected_stay
  FROM frozen_rows
  WHERE eligible_main_cohort = 1
    AND deterministic_eligible_patient_stay_rank = 1
),
technical_matched_ranked AS (
  SELECT uniquePID, patientUnitStayID,
    ROW_NUMBER() OVER (
      PARTITION BY uniquePID
      ORDER BY patientHealthSystemStayID,
               COALESCE(unitVisitNumber, 999999),
               patientUnitStayID
    ) AS technical_rank
  FROM e_frozen_reconstruction
),
technical_matched_selected AS (
  SELECT uniquePID, patientUnitStayID AS technical_selected_stay
  FROM technical_matched_ranked
  WHERE technical_rank = 1
),
matched_patient_universe AS (
  SELECT DISTINCT uniquePID FROM e_frozen_reconstruction
),
p3c_matched_pairs AS (
  SELECT u.uniquePID, f.frozen_selected_stay, t.technical_selected_stay,
    CASE
      WHEN f.frozen_selected_stay IS NOT NULL
       AND t.technical_selected_stay IS NOT NULL
       AND f.frozen_selected_stay = t.technical_selected_stay THEN 'same_stay'
      WHEN f.frozen_selected_stay IS NOT NULL
       AND t.technical_selected_stay IS NOT NULL THEN 'different_stay'
      WHEN f.frozen_selected_stay IS NOT NULL THEN 'frozen_only'
      WHEN t.technical_selected_stay IS NOT NULL THEN 'technical_only'
      ELSE 'neither'
    END AS category
  FROM matched_patient_universe AS u
  LEFT JOIN frozen_selected AS f USING (uniquePID)
  LEFT JOIN technical_matched_selected AS t USING (uniquePID)
),
broad_technical_ranked AS (
  -- This section isolates the n_hospitals_for_patient restriction only. It is
  -- not E_frozen_reconstruction because frozen staged/outcome fields do not
  -- exist for cross-hospital candidates.
  SELECT uniquePID, patientUnitStayID,
    ROW_NUMBER() OVER (
      PARTITION BY uniquePID
      ORDER BY patientHealthSystemStayID,
               COALESCE(unitVisitNumber, 999999),
               patientUnitStayID
    ) AS technical_rank
  FROM broad_landmark_base
),
broad_technical_selected AS (
  SELECT uniquePID, patientUnitStayID AS broad_selected_stay
  FROM broad_technical_ranked
  WHERE technical_rank = 1
),
restricted_technical_ranked AS (
  SELECT uniquePID, patientUnitStayID,
    ROW_NUMBER() OVER (
      PARTITION BY uniquePID
      ORDER BY patientHealthSystemStayID,
               COALESCE(unitVisitNumber, 999999),
               patientUnitStayID
    ) AS technical_rank
  FROM frozen_restricted_base
),
restricted_technical_selected AS (
  SELECT uniquePID, patientUnitStayID AS restricted_selected_stay
  FROM restricted_technical_ranked
  WHERE technical_rank = 1
),
broad_patient_universe AS (
  SELECT DISTINCT uniquePID FROM broad_landmark_base
),
p3c_cross_hospital_pairs AS (
  SELECT u.uniquePID, r.restricted_selected_stay, b.broad_selected_stay,
    CASE
      WHEN r.restricted_selected_stay IS NOT NULL
       AND b.broad_selected_stay IS NOT NULL
       AND r.restricted_selected_stay = b.broad_selected_stay THEN 'same_stay'
      WHEN r.restricted_selected_stay IS NOT NULL
       AND b.broad_selected_stay IS NOT NULL THEN 'different_stay'
      WHEN r.restricted_selected_stay IS NOT NULL THEN 'restricted_only'
      WHEN b.broad_selected_stay IS NOT NULL THEN 'broad_only'
      ELSE 'neither'
    END AS category
  FROM broad_patient_universe AS u
  LEFT JOIN restricted_technical_selected AS r USING (uniquePID)
  LEFT JOIN broad_technical_selected AS b USING (uniquePID)
),
partition_rows AS (
  SELECT 'p3a_stay_membership' AS section, 'stays' AS unit, category,
         CAST(patientUnitStayID AS STRING) AS entity_id
  FROM p3a_stay_membership
  UNION ALL
  SELECT 'p3a_patient_membership', 'patients', category, CAST(uniquePID AS STRING)
  FROM p3a_patient_membership
  UNION ALL
  SELECT 'p3a_common_member_label_agreement', 'stays', category,
         CAST(patientUnitStayID AS STRING)
  FROM p3a_common_label_stays
  UNION ALL
  SELECT 'p3a_observed_positive_surveillance_effect', 'stays', category,
         CAST(patientUnitStayID AS STRING)
  FROM p3a_observed_positive_exclusions
  UNION ALL
  SELECT 'p3a_observed_positive_surveillance_effect', 'patients', category,
         CAST(uniquePID AS STRING)
  FROM p3a_observed_positive_exclusions
  UNION ALL
  SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', category,
         CAST(uniquePID AS STRING)
  FROM p3c_matched_pairs
  UNION ALL
  SELECT 'p3c_cross_hospital_restriction_effect', 'patients', category,
         CAST(uniquePID AS STRING)
  FROM p3c_cross_hospital_pairs
),
partition_category_definitions AS (
  SELECT 'p3a_stay_membership' AS section, 'stays' AS unit, 'both' AS category
  UNION ALL SELECT 'p3a_stay_membership', 'stays', 'frozen_only'
  UNION ALL SELECT 'p3a_stay_membership', 'stays', 'p3a_only'
  UNION ALL SELECT 'p3a_stay_membership', 'stays', 'neither'
  UNION ALL SELECT 'p3a_patient_membership', 'patients', 'both'
  UNION ALL SELECT 'p3a_patient_membership', 'patients', 'frozen_only'
  UNION ALL SELECT 'p3a_patient_membership', 'patients', 'p3a_only'
  UNION ALL SELECT 'p3a_patient_membership', 'patients', 'neither'
  UNION ALL SELECT 'p3a_common_member_label_agreement', 'stays', 'frozen_0_p3a_0'
  UNION ALL SELECT 'p3a_common_member_label_agreement', 'stays', 'frozen_0_p3a_1'
  UNION ALL SELECT 'p3a_common_member_label_agreement', 'stays', 'frozen_1_p3a_0'
  UNION ALL SELECT 'p3a_common_member_label_agreement', 'stays', 'frozen_1_p3a_1'
  UNION ALL SELECT 'p3a_observed_positive_surveillance_effect', 'stays', 'retained_under_p3a'
  UNION ALL SELECT 'p3a_observed_positive_surveillance_effect', 'stays', 'excluded_under_p3a'
  UNION ALL SELECT 'p3a_observed_positive_surveillance_effect', 'patients', 'retained_under_p3a'
  UNION ALL SELECT 'p3a_observed_positive_surveillance_effect', 'patients', 'excluded_under_p3a'
  UNION ALL SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', 'same_stay'
  UNION ALL SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', 'different_stay'
  UNION ALL SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', 'frozen_only'
  UNION ALL SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', 'technical_only'
  UNION ALL SELECT 'p3c_matched_frozen_vs_identifier_order', 'patients', 'neither'
  UNION ALL SELECT 'p3c_cross_hospital_restriction_effect', 'patients', 'same_stay'
  UNION ALL SELECT 'p3c_cross_hospital_restriction_effect', 'patients', 'different_stay'
  UNION ALL SELECT 'p3c_cross_hospital_restriction_effect', 'patients', 'restricted_only'
  UNION ALL SELECT 'p3c_cross_hospital_restriction_effect', 'patients', 'broad_only'
  UNION ALL SELECT 'p3c_cross_hospital_restriction_effect', 'patients', 'neither'
),
observed_partition_counts AS (
  SELECT section, unit, category, COUNT(*) AS value
  FROM partition_rows
  GROUP BY section, unit, category
),
partition_counts AS (
  SELECT d.section, d.unit, d.category, COALESCE(o.value, 0) AS value
  FROM partition_category_definitions AS d
  LEFT JOIN observed_partition_counts AS o USING (section, unit, category)
),
partition_gate AS (
  -- Release a complete partition only if every nonzero cell is >=11. This
  -- permits zero-count categories but prevents reconstruction of 1–10 cells
  -- from a reported total and the other categories.
  SELECT section, unit,
    COUNTIF(value BETWEEN 1 AND 10) = 0 AS releasable
  FROM partition_counts
  GROUP BY section, unit
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
  SELECT 'null_uniquePID_in_broad_landmark_base', COUNT(*)
  FROM base_singletons
  WHERE eligible_unit_rank_in_hospstay = 1 AND uniquePID IS NULL
),
public_partitions AS (
  SELECT p.section, p.unit, p.category, p.value, 'released' AS release_status
  FROM partition_counts AS p
  JOIN partition_gate AS g USING (section, unit)
  WHERE g.releasable
),
suppressed_partitions AS (
  SELECT section, unit, 'all_categories' AS category,
         CAST(NULL AS INT64) AS value,
         'suppressed_partition_contains_small_nonzero_cell' AS release_status
  FROM partition_gate
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
SELECT * FROM public_partitions
UNION ALL
SELECT * FROM suppressed_partitions
UNION ALL
SELECT * FROM public_qc
ORDER BY section, unit, category;
