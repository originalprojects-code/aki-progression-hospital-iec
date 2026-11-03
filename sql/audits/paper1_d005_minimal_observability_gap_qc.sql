-- Paper 1 D-005 minimal observability-gap QC.
--
-- Read-only, aggregate-only audit.  This is not a cohort or outcome definition.
-- It reuses frozen selected creatinine records in creatinine_long_v1 and frozen
-- observation_class labels in cohort_outcome_v1.  No raw laboratory versions
-- are read and no alternative record-selection rule is introduced.
--
-- Disclosure rule: an indicator is released only when its numerator AND its
-- non-numerator set each contain at least 11 stays and 11 distinct non-null
-- uniquePID values.  Patient sets are screened directly (they are not inferred
-- by subtracting distinct-patient totals, because patients can have >1 stay).
-- No hospital or cross-tabulated output is returned.

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
selected_offset_key_counts AS (
  SELECT patientUnitStayID, labResultOffset, COUNT(*) AS n
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.creatinine_long_v1`
  GROUP BY patientUnitStayID, labResultOffset
),
base_singletons AS (
  SELECT b.*
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1` AS b
  JOIN base_key_counts AS k USING (patientUnitStayID)
  WHERE k.n = 1
),
structural_base AS (
  SELECT *
  FROM base_singletons
  WHERE eligible_unit_rank_in_hospstay = 1
    AND n_hospitals_for_patient = 1
),
outcome_singletons AS (
  SELECT o.patientUnitStayID, o.observation_class
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1` AS o
  JOIN outcome_key_counts AS k USING (patientUnitStayID)
  WHERE k.n = 1
),
ambiguous_selected_stays AS (
  SELECT DISTINCT patientUnitStayID
  FROM selected_offset_key_counts
  WHERE n > 1
),
usable_selected AS (
  SELECT c.patientUnitStayID, c.labResultOffset
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.creatinine_long_v1` AS c
  JOIN selected_offset_key_counts AS k
    USING (patientUnitStayID, labResultOffset)
  LEFT JOIN ambiguous_selected_stays AS a USING (patientUnitStayID)
  WHERE k.n = 1
    AND a.patientUnitStayID IS NULL
),
measurement_base AS (
  -- Exclude an entire stay from measurement-based metrics if any supposedly
  -- selected stay-offset group is duplicate.  It is counted in integrity_qc.
  SELECT b.*
  FROM structural_base AS b
  LEFT JOIN ambiguous_selected_stays AS a USING (patientUnitStayID)
  WHERE a.patientUnitStayID IS NULL
),
measurement_flags AS (
  SELECT
    b.patientUnitStayID,
    b.uniquePID,
    b.unitDischargeOffset,
    b.unit_discharge_status,
    COUNTIF(c.labResultOffset > 2880 AND c.labResultOffset <= 4320) > 0
      AS has_selected_creatinine_48_72,
    COUNTIF(
      c.labResultOffset > 720
      AND c.labResultOffset <= b.unitDischargeOffset
      AND c.labResultOffset >= b.unitDischargeOffset - 1440
    ) > 0 AS has_recent_selected_creatinine_before_exit
  FROM measurement_base AS b
  LEFT JOIN usable_selected AS c USING (patientUnitStayID)
  GROUP BY b.patientUnitStayID, b.uniquePID, b.unitDischargeOffset,
           b.unit_discharge_status
),
early_alive_class_flags AS (
  SELECT
    b.patientUnitStayID,
    b.uniquePID,
    b.unitDischargeOffset,
    b.unit_discharge_status,
    o.observation_class,
    m.has_recent_selected_creatinine_before_exit
  -- This indicator depends on selected-creatinine timing; apply the same
  -- whole-stay ambiguity exclusion as the other measurement metrics.
  FROM measurement_base AS b
  LEFT JOIN outcome_singletons AS o USING (patientUnitStayID)
  LEFT JOIN measurement_flags AS m USING (patientUnitStayID)
),
outcome_class_flags AS (
  -- Early-death class reconciliation does not depend on a new timing count,
  -- so it retains the structural singleton universe.
  SELECT b.patientUnitStayID, b.uniquePID, o.observation_class
  FROM structural_base AS b
  LEFT JOIN outcome_singletons AS o USING (patientUnitStayID)
),
metric_rows AS (
  -- The first row establishes the complete structural stay/patient denominator.
  SELECT 'structural_candidates' AS metric,
         'full_structural_singleton_candidates' AS denominator_population,
         TRUE AS denominator_member, TRUE AS numerator_member,
         patientUnitStayID, uniquePID
  FROM structural_base

  UNION ALL

  SELECT 'selected_creatinine_48_72_all_structural_nonambiguous' AS metric,
         'nonambiguous_selected_creatinine_analysis_stays' AS denominator_population,
         TRUE, has_selected_creatinine_48_72, patientUnitStayID, uniquePID
  FROM measurement_flags

  UNION ALL

  SELECT 'selected_creatinine_48_72_among_valid_72h_in_icu_nonambiguous' AS metric,
         'nonambiguous_selected_creatinine_analysis_stays' AS denominator_population,
         unitDischargeOffset >= 4320, has_selected_creatinine_48_72,
         patientUnitStayID, uniquePID
  FROM measurement_flags

  UNION ALL

  SELECT 'recent_selected_creatinine_among_early_alive_discharge_nonambiguous' AS metric,
         'nonambiguous_selected_creatinine_analysis_stays' AS denominator_population,
         unitDischargeOffset > 720
           AND unitDischargeOffset < 4320
           AND unit_discharge_status = 'alive',
         has_recent_selected_creatinine_before_exit,
         patientUnitStayID, uniquePID
  FROM measurement_flags

  UNION ALL

  SELECT 'frozen_early_alive_negative_with_recent_selected_creatinine' AS metric,
         'nonambiguous_selected_creatinine_analysis_stays' AS denominator_population,
         unitDischargeOffset > 720
           AND unitDischargeOffset < 4320
           AND unit_discharge_status = 'alive',
         has_recent_selected_creatinine_before_exit
           AND observation_class = 'negative_live_discharge_recent_creatinine',
         patientUnitStayID, uniquePID
  FROM early_alive_class_flags

  UNION ALL

  SELECT 'frozen_early_death_without_observed_stage23' AS metric,
         'full_structural_singleton_candidates' AS denominator_population,
         TRUE,
         observation_class = 'indeterminate_early_death',
         patientUnitStayID, uniquePID
  FROM outcome_class_flags
),
metric_counts AS (
  SELECT
    metric,
    denominator_population,
    COUNTIF(denominator_member) AS denominator_stays,
    COUNT(DISTINCT IF(denominator_member, uniquePID, NULL))
      AS denominator_patients,
    COUNTIF(denominator_member AND numerator_member) AS numerator_stays,
    COUNT(DISTINCT IF(denominator_member AND numerator_member, uniquePID, NULL))
      AS numerator_patients,
    COUNTIF(denominator_member AND NOT numerator_member) AS nonnumerator_stays,
    COUNT(DISTINCT IF(denominator_member AND NOT numerator_member, uniquePID, NULL))
      AS nonnumerator_patients
  FROM metric_rows
  GROUP BY metric, denominator_population
),
release_gate AS (
  SELECT
    metric,
    denominator_population,
    CASE
      WHEN metric = 'structural_candidates'
        THEN numerator_stays >= 11 AND numerator_patients >= 11
      ELSE numerator_stays >= 11
        AND numerator_patients >= 11
        AND nonnumerator_stays >= 11
        AND nonnumerator_patients >= 11
    END AS releasable
  FROM metric_counts
),
integrity_qc AS (
  SELECT 'base_duplicate_stay_key_groups' AS metric, 'stay_key_groups' AS unit,
         COUNTIF(n > 1) AS value
  FROM base_key_counts
  UNION ALL
  SELECT 'outcome_duplicate_stay_key_groups', 'stay_key_groups', COUNTIF(n > 1)
  FROM outcome_key_counts
  UNION ALL
  SELECT 'duplicate_selected_creatinine_stay_offset_groups', 'stay_offset_groups',
         COUNTIF(n > 1)
  FROM selected_offset_key_counts
  UNION ALL
  SELECT 'structural_stays_excluded_for_ambiguous_selected_creatinine', 'stays',
         COUNT(*)
  FROM structural_base AS b
  JOIN ambiguous_selected_stays AS a USING (patientUnitStayID)
  UNION ALL
  SELECT 'structural_stays_missing_singleton_outcome_record', 'stays', COUNT(*)
  FROM structural_base AS b
  LEFT JOIN outcome_singletons AS o USING (patientUnitStayID)
  WHERE o.patientUnitStayID IS NULL
  UNION ALL
  SELECT 'structural_stays_with_null_uniquePID', 'stays', COUNT(*)
  FROM structural_base
  WHERE uniquePID IS NULL
),
public_metrics AS (
  SELECT
    'observability_metric' AS section,
    m.metric,
    m.denominator_population,
    'stays' AS unit,
    m.denominator_stays,
    m.denominator_patients,
    m.numerator_stays,
    m.numerator_patients,
    CAST(NULL AS INT64) AS value,
    'released' AS release_status
  FROM metric_counts AS m
  JOIN release_gate AS g USING (metric, denominator_population)
  WHERE g.releasable
),
suppressed_metrics AS (
  SELECT
    'suppression_qc' AS section,
    metric,
    denominator_population,
    'no_counts_released' AS unit,
    CAST(NULL AS INT64) AS denominator_stays,
    CAST(NULL AS INT64) AS denominator_patients,
    CAST(NULL AS INT64) AS numerator_stays,
    CAST(NULL AS INT64) AS numerator_patients,
    CAST(NULL AS INT64) AS value,
    'suppressed_under_stay_and_patient_complement_rule' AS release_status
  FROM release_gate
  WHERE NOT releasable
),
public_qc AS (
  -- Technical QC counts of 1–10 are not released: even non-clinical key
  -- anomalies can become reconstructable when combined with known totals.
  -- Zero is released as an explicit integrity finding; counts >=11 are broad.
  SELECT
    'integrity_qc' AS section,
    metric,
    'not_applicable' AS denominator_population,
    unit,
    CAST(NULL AS INT64) AS denominator_stays,
    CAST(NULL AS INT64) AS denominator_patients,
    CAST(NULL AS INT64) AS numerator_stays,
    CAST(NULL AS INT64) AS numerator_patients,
    CASE WHEN value = 0 OR value >= 11 THEN value ELSE CAST(NULL AS INT64) END AS value,
    CASE
      WHEN value = 0 THEN 'released_zero_technical_qc'
      WHEN value >= 11 THEN 'released_broad_technical_qc'
      ELSE 'suppressed_small_technical_qc'
    END AS release_status
  FROM integrity_qc
)
SELECT * FROM public_metrics
UNION ALL
SELECT * FROM suppressed_metrics
UNION ALL
SELECT * FROM public_qc
ORDER BY section, metric;
