-- Structured first-12-hour treatment, respiratory-support
-- and past-history features.
--
-- Respiratory definitions are intentionally conservative:
-- 1. ventStartOffset alone is NOT treated as proof of invasive ventilation.
-- 2. Explicit non-invasive ventilation terms are excluded from the
--    invasive-mechanical-ventilation definition.
-- 3. Direct airway documentation and explicit treatment documentation
--    are retained separately.

CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.feature_context_v1` AS

WITH main AS (
  SELECT
    patientUnitStayID
  FROM `{{PROJECT_ID}}.{{DATASET_ID}}.cohort_outcome_v1`
  WHERE eligible_main_cohort = 1
    AND deterministic_eligible_patient_stay_rank = 1
),

/* ============================================================
   PAST MEDICAL HISTORY
   ============================================================ */

ph_raw AS (
  SELECT
    p.patientUnitStayID,
    LOWER(COALESCE(p.pastHistoryPath, '')) AS path,
    LOWER(COALESCE(p.pastHistoryValue, '')) AS value
  FROM main AS m
  INNER JOIN `physionet-data.eicu_crd.pasthistory` AS p
    USING (patientUnitStayID)
  WHERE p.pastHistoryOffset <= 720
),

ph AS (
  SELECT
    patientUnitStayID,

    1 AS x_hx_past_history_documented,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'hypertension'
        ),
        1,
        0
      )
    ) AS x_hx_hypertension,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'diabet|insulin dependent'
        )
        OR (
          REGEXP_CONTAINS(path, r'diabet')
          AND value = 'medication dependent'
        ),
        1,
        0
      )
    ) AS x_hx_diabetes,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'congestive heart failure|\bchf\b'
        ),
        1,
        0
      )
    ) AS x_hx_chf,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'coronary artery|myocardial infarction|\bmi\b|angina|cabg|ptca|pci'
        ),
        1,
        0
      )
    ) AS x_hx_cad,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'copd|chronic obstructive|emphysema|chronic bronchitis'
        ),
        1,
        0
      )
    ) AS x_hx_chronic_pulmonary,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'cirrhosis|portal hypertension|hepatic failure|chronic liver'
        ),
        1,
        0
      )
    ) AS x_hx_chronic_liver,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'/cancer/|hematologic malignancy|leukemia|lymphoma|myeloma|metastases'
        ),
        1,
        0
      )
    ) AS x_hx_malignancy,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'immunosupp|chemotherapy|radiation therapy|transplant|\baids\b'
        ),
        1,
        0
      )
    ) AS x_hx_immunosuppression,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'stroke|cerebrovascular|\bcva\b|\btia\b'
        ),
        1,
        0
      )
    ) AS x_hx_cerebrovascular,

    MAX(
      IF(
        REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'renal insufficiency|chronic kidney|\bckd\b'
        )
        AND NOT REGEXP_CONTAINS(
          CONCAT(path, '|', value),
          r'dialysis|esrd|end stage'
        ),
        1,
        0
      )
    ) AS x_hx_chronic_kidney_non_esrd

  FROM ph_raw
  GROUP BY patientUnitStayID
),

/* ============================================================
   INFUSION DRUGS
   ============================================================ */

inf_raw AS (
  SELECT
    i.patientUnitStayID,
    LOWER(TRIM(i.drugName)) AS drug
  FROM main AS m
  INNER JOIN `physionet-data.eicu_crd.infusiondrug` AS i
    USING (patientUnitStayID)
  WHERE i.infusionOffset BETWEEN 0 AND 720
    AND NULLIF(TRIM(i.drugName), '') IS NOT NULL
),

inf AS (
  SELECT
    patientUnitStayID,

    MAX(
      IF(
        REGEXP_CONTAINS(drug, r'norepine|levophed'),
        1,
        0
      )
    ) AS x_tx_norepinephrine,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'(^|[^a-z])epinephrine([^a-z]|$)|adrenalin'
        ),
        1,
        0
      )
    ) AS x_tx_epinephrine,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'vasopressin'), 1, 0)
    ) AS x_tx_vasopressin,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'phenylephrine|neosynephrine|neo-synephrine'
        ),
        1,
        0
      )
    ) AS x_tx_phenylephrine,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'(^|[^a-z])dopamine([^a-z]|$)'
        ),
        1,
        0
      )
    ) AS x_tx_dopamine,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'dobutamine'), 1, 0)
    ) AS x_tx_dobutamine,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'milrinone'), 1, 0)
    ) AS x_tx_milrinone,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'propofol'), 1, 0)
    ) AS x_tx_propofol,

    MAX(
      IF(
        REGEXP_CONTAINS(drug, r'midazolam|versed'),
        1,
        0
      )
    ) AS x_tx_midazolam,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'dexmedetomidine|precedex'
        ),
        1,
        0
      )
    ) AS x_tx_dexmedetomidine,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'insulin'), 1, 0)
    ) AS x_tx_insulin_infusion,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'furosemide|lasix|bumetanide|bumex'
        ),
        1,
        0
      )
    ) AS x_tx_loop_diuretic_infusion,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'bicarbonate'), 1, 0)
    ) AS x_tx_bicarbonate_infusion,

    MAX(
      IF(REGEXP_CONTAINS(drug, r'heparin'), 1, 0)
    ) AS x_tx_heparin_infusion,

    MAX(
      IF(
        REGEXP_CONTAINS(
          drug,
          r'nicardipine|clevidipine|nitroprusside'
        ),
        1,
        0
      )
    ) AS x_tx_antihypertensive_infusion

  FROM inf_raw
  GROUP BY patientUnitStayID
),

/* ============================================================
   RESPIRATORY CARE: DIRECT AIRWAY DOCUMENTATION
   ============================================================ */

rc_raw AS (
  SELECT
    r.patientUnitStayID,
    LOWER(TRIM(COALESCE(r.airwayType, ''))) AS airway,
    r.ventStartOffset,
    r.respCareStatusOffset
  FROM main AS m
  INNER JOIN `physionet-data.eicu_crd.respiratorycare` AS r
    USING (patientUnitStayID)
  WHERE r.ventStartOffset BETWEEN 0 AND 720
     OR r.respCareStatusOffset BETWEEN 0 AND 720
),

rc AS (
  SELECT
    patientUnitStayID,

    MAX(
      IF(
        REGEXP_CONTAINS(
          airway,
          r'oral ett|nasal ett|endotracheal'
        ),
        1,
        0
      )
    ) AS rc_endotracheal_airway,

    MAX(
      IF(
        REGEXP_CONTAINS(airway, r'tracheostomy'),
        1,
        0
      )
    ) AS rc_tracheostomy,

    -- An invasive airway documented during the first 12 hours
    -- is considered direct evidence of invasive support.
    MAX(
      IF(
        REGEXP_CONTAINS(
          airway,
          r'oral ett|nasal ett|endotracheal|tracheostomy'
        ),
        1,
        0
      )
    ) AS rc_direct_invasive_support,

    -- Blank airway attached to an actual respiratory-care status
    -- entry in the first 12 hours. ventStartOffset alone is not used.
    MAX(
      IF(
        respCareStatusOffset BETWEEN 0 AND 720
        AND airway = '',
        1,
        0
      )
    ) AS rc_uncertain

  FROM rc_raw
  GROUP BY patientUnitStayID
),

/* ============================================================
   TREATMENT: EXPLICIT RESPIRATORY SUPPORT TERMS
   ============================================================ */

tx_raw AS (
  SELECT
    t.patientUnitStayID,
    LOWER(TRIM(t.treatmentString)) AS item
  FROM main AS m
  INNER JOIN `physionet-data.eicu_crd.treatment` AS t
    USING (patientUnitStayID)
  WHERE t.treatmentOffset BETWEEN 0 AND 720
    AND NULLIF(TRIM(t.treatmentString), '') IS NOT NULL
),

tx AS (
  SELECT
    patientUnitStayID,

    -- Explicit invasive ventilation terms.
    -- Records containing an explicit non-invasive designation
    -- are excluded even if they also contain "mechanical ventilation".
    MAX(
      IF(
        (
          REGEXP_CONTAINS(
            item,
            r'mechanical ventilation|invasive ventilation|intubat|ventilator weaning'
          )
          AND NOT REGEXP_CONTAINS(
            item,
            r'non.?invasive ventilation|\bbipap\b|bi-pap'
          )
        ),
        1,
        0
      )
    ) AS tx_invasive_vent,

    -- Conservative NIV definition: only explicit NIV or BiPAP terms.
    -- Generic CPAP/PEEP therapy is not automatically classified as NIV,
    -- because PEEP may also be used during invasive ventilation.
    MAX(
      IF(
        REGEXP_CONTAINS(
          item,
          r'non.?invasive ventilation|\bbipap\b|bi-pap'
        ),
        1,
        0
      )
    ) AS tx_noninvasive_vent,

    MAX(
      IF(
        REGEXP_CONTAINS(
          item,
          r'high flow|high-flow|\bhfnc\b'
        ),
        1,
        0
      )
    ) AS tx_high_flow,

    MAX(
      IF(
        REGEXP_CONTAINS(
          item,
          r'oxygen therapy|supplemental oxygen|nasal cannula|face mask|non-rebreather'
        ),
        1,
        0
      )
    ) AS tx_oxygen

  FROM tx_raw
  GROUP BY patientUnitStayID
)

/* ============================================================
   FINAL ONE-ROW-PER-PATIENT CONTEXT TABLE
   ============================================================ */

SELECT
  m.patientUnitStayID,

  COALESCE(
    ph.x_hx_past_history_documented,
    0
  ) AS x_hx_past_history_documented,

  COALESCE(ph.x_hx_hypertension, 0)
    AS x_hx_hypertension,

  COALESCE(ph.x_hx_diabetes, 0)
    AS x_hx_diabetes,

  COALESCE(ph.x_hx_chf, 0)
    AS x_hx_chf,

  COALESCE(ph.x_hx_cad, 0)
    AS x_hx_cad,

  COALESCE(ph.x_hx_chronic_pulmonary, 0)
    AS x_hx_chronic_pulmonary,

  COALESCE(ph.x_hx_chronic_liver, 0)
    AS x_hx_chronic_liver,

  COALESCE(ph.x_hx_malignancy, 0)
    AS x_hx_malignancy,

  COALESCE(ph.x_hx_immunosuppression, 0)
    AS x_hx_immunosuppression,

  COALESCE(ph.x_hx_cerebrovascular, 0)
    AS x_hx_cerebrovascular,

  COALESCE(ph.x_hx_chronic_kidney_non_esrd, 0)
    AS x_hx_chronic_kidney_non_esrd,

  IF(
    COALESCE(inf.x_tx_norepinephrine, 0)
    + COALESCE(inf.x_tx_epinephrine, 0)
    + COALESCE(inf.x_tx_vasopressin, 0)
    + COALESCE(inf.x_tx_phenylephrine, 0)
    + COALESCE(inf.x_tx_dopamine, 0) > 0,
    1,
    0
  ) AS x_tx_any_vasopressor,

  COALESCE(inf.x_tx_norepinephrine, 0)
    AS x_tx_norepinephrine,

  COALESCE(inf.x_tx_epinephrine, 0)
    AS x_tx_epinephrine,

  COALESCE(inf.x_tx_vasopressin, 0)
    AS x_tx_vasopressin,

  COALESCE(inf.x_tx_phenylephrine, 0)
    AS x_tx_phenylephrine,

  COALESCE(inf.x_tx_dopamine, 0)
    AS x_tx_dopamine,

  COALESCE(inf.x_tx_dobutamine, 0)
    AS x_tx_dobutamine,

  COALESCE(inf.x_tx_milrinone, 0)
    AS x_tx_milrinone,

  COALESCE(inf.x_tx_propofol, 0)
    AS x_tx_propofol,

  COALESCE(inf.x_tx_midazolam, 0)
    AS x_tx_midazolam,

  COALESCE(inf.x_tx_dexmedetomidine, 0)
    AS x_tx_dexmedetomidine,

  COALESCE(inf.x_tx_insulin_infusion, 0)
    AS x_tx_insulin_infusion,

  COALESCE(inf.x_tx_loop_diuretic_infusion, 0)
    AS x_tx_loop_diuretic_infusion,

  COALESCE(inf.x_tx_bicarbonate_infusion, 0)
    AS x_tx_bicarbonate_infusion,

  COALESCE(inf.x_tx_heparin_infusion, 0)
    AS x_tx_heparin_infusion,

  COALESCE(inf.x_tx_antihypertensive_infusion, 0)
    AS x_tx_antihypertensive_infusion,

  IF(
    COALESCE(rc.rc_endotracheal_airway, 0) = 1
    OR COALESCE(rc.rc_tracheostomy, 0) = 1,
    1,
    0
  ) AS x_resp_invasive_airway,

  COALESCE(rc.rc_tracheostomy, 0)
    AS x_resp_tracheostomy,

  IF(
    COALESCE(rc.rc_direct_invasive_support, 0) = 1
    OR COALESCE(tx.tx_invasive_vent, 0) = 1,
    1,
    0
  ) AS x_resp_invasive_mechanical_ventilation,

  COALESCE(tx.tx_noninvasive_vent, 0)
    AS x_resp_noninvasive_ventilation,

  COALESCE(tx.tx_high_flow, 0)
    AS x_resp_high_flow_oxygen,

  COALESCE(tx.tx_oxygen, 0)
    AS x_resp_oxygen_therapy,

  IF(
    COALESCE(rc.rc_uncertain, 0) = 1
    AND COALESCE(tx.tx_invasive_vent, 0) = 0
    AND COALESCE(tx.tx_noninvasive_vent, 0) = 0,
    1,
    0
  ) AS x_resp_respiratory_documented_uncertain

FROM main AS m

LEFT JOIN ph
  USING (patientUnitStayID)

LEFT JOIN inf
  USING (patientUnitStayID)

LEFT JOIN rc
  USING (patientUnitStayID)

LEFT JOIN tx
  USING (patientUnitStayID);
