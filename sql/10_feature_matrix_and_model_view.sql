-- Final secure feature matrix.
-- The full table retains audit-only fields for subgroup and QC analyses.
-- The modelling view excludes direct identifiers, audit-only attributes
-- and the zero-variance high-flow oxygen variable.

CREATE OR REPLACE TABLE `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_v1` AS

SELECT
  s.*,
  l.* EXCEPT (patientUnitStayID),
  v.* EXCEPT (patientUnitStayID),
  c.* EXCEPT (patientUnitStayID)

FROM `{{PROJECT_ID}}.{{DATASET_ID}}.feature_static_v1` AS s

LEFT JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.feature_labs_v1` AS l
  ON l.patientUnitStayID = s.patientUnitStayID

LEFT JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.feature_vitals_v1` AS v
  ON v.patientUnitStayID = s.patientUnitStayID

LEFT JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.feature_context_v1` AS c
  ON c.patientUnitStayID = s.patientUnitStayID;


CREATE OR REPLACE VIEW
  `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_model_view_v1` AS

SELECT * EXCEPT (
  patientUnitStayID,
  hospitalID,

  audit_ethnicity,
  audit_hospital_region,
  audit_hospital_bed_category,
  audit_hospital_teaching_status,
  audit_reference_offset,

  x_resp_high_flow_oxygen
)

FROM `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_v1`;
