-- Persistent secure table: strict chronic dialysis/ESRD and RRT timing flags.
CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.renal_flags_v1` AS
WITH base AS (
  SELECT *
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.base_stays_v1`
  WHERE eligible_unit_rank_in_hospstay = 1
    AND n_hospitals_for_patient = 1
),
ph AS (
  SELECT
    patientUnitStayID,
    MAX(IF(
      REGEXP_CONTAINS(LOWER(CONCAT(COALESCE(pastHistoryPath,''),' ',COALESCE(pastHistoryValue,''),' ',COALESCE(pastHistoryValueText,''))),
        r'end.?stage renal|esrd|dialysis.?dependent|chronic dialysis|maintenance dialysis|for chronic renal failure'),
      1, 0)) AS strict_chronic_ph,
    MAX(IF(
      REGEXP_CONTAINS(LOWER(CONCAT(COALESCE(pastHistoryPath,''),' ',COALESCE(pastHistoryValue,''),' ',COALESCE(pastHistoryValueText,''))),
        r'arteriovenous shunt|dialysis access|renal failure|chronic kidney'),
      1, 0)) AS broad_chronic_ph
  FROM `physionet-data.eicu_crd.pasthistory`
  WHERE pastHistoryOffset <= 720
  GROUP BY patientUnitStayID
),
dx AS (
  SELECT
    patientUnitStayID,
    MAX(IF(REGEXP_CONTAINS(LOWER(diagnosisString),
      r'end.?stage renal|esrd|dialysis.?dependent|chronic dialysis|maintenance dialysis'),1,0)) AS strict_chronic_dx,
    MAX(IF(REGEXP_CONTAINS(LOWER(diagnosisString),
      r'chronic renal|chronic kidney|dialysis access|arteriovenous shunt'),1,0)) AS broad_chronic_dx
  FROM `physionet-data.eicu_crd.diagnosis`
  WHERE diagnosisOffset <= 720
  GROUP BY patientUnitStayID
),
tx AS (
  SELECT
    patientUnitStayID,
    MAX(IF(treatmentOffset <= 720 AND REGEXP_CONTAINS(LOWER(treatmentString),
      r'for chronic renal failure|chronic dialysis|maintenance dialysis|dialysis.?dependent'),1,0)) AS strict_chronic_tx,
    MAX(IF(treatmentOffset <= 720 AND REGEXP_CONTAINS(LOWER(treatmentString),
      r'dialysis access|arteriovenous shunt|for chronic renal failure'),1,0)) AS broad_chronic_tx,
    MIN(IF(
      treatmentOffset >= 0
      AND NOT REGEXP_CONTAINS(LOWER(treatmentString), r'for chronic renal failure|dialysis access|arteriovenous shunt|catheter')
      AND REGEXP_CONTAINS(LOWER(treatmentString),
        r'for acute renal failure|hemodialysis\|emergent|peritoneal dialysis\|emergent|c v v h|c v v h d|c a v h d|sled|crrt|hemofiltration|renal replacement'),
      treatmentOffset, NULL)) AS first_acute_rrt_strict_offset,
    MIN(IF(
      treatmentOffset >= 0
      AND NOT REGEXP_CONTAINS(LOWER(treatmentString), r'for chronic renal failure|dialysis access|arteriovenous shunt|catheter')
      AND REGEXP_CONTAINS(LOWER(treatmentString), r'dialy|hemofil|renal replacement|cvvh|crrt|sled'),
      treatmentOffset, NULL)) AS first_acute_rrt_broad_offset
  FROM `physionet-data.eicu_crd.treatment`
  GROUP BY patientUnitStayID
),
io AS (
  SELECT
    patientUnitStayID,
    MIN(IF(dialysisTotal != 0, intakeOutputOffset, NULL)) AS first_nonzero_dialysis_io_offset
  FROM `physionet-data.eicu_crd.intakeoutput`
  GROUP BY patientUnitStayID
)
SELECT
  b.patientUnitStayID,
  GREATEST(COALESCE(ph.strict_chronic_ph,0),COALESCE(dx.strict_chronic_dx,0),COALESCE(tx.strict_chronic_tx,0)) AS strict_chronic_dialysis_esrd,
  GREATEST(COALESCE(ph.broad_chronic_ph,0),COALESCE(dx.broad_chronic_dx,0),COALESCE(tx.broad_chronic_tx,0)) AS broad_chronic_renal_support,
  tx.first_acute_rrt_strict_offset,
  tx.first_acute_rrt_broad_offset,
  io.first_nonzero_dialysis_io_offset
FROM base b
LEFT JOIN ph USING(patientUnitStayID)
LEFT JOIN dx USING(patientUnitStayID)
LEFT JOIN tx USING(patientUnitStayID)
LEFT JOIN io USING(patientUnitStayID);
