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

FROM `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_v1`
