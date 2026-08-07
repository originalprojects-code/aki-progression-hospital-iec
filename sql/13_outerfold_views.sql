CREATE OR REPLACE VIEW
  `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_core_outerfold_v1` AS

SELECT
  m.*,
  f.outer_fold

FROM `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_core_view_v1` AS m

INNER JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.hospital_outer_fold_v1` AS f
  USING (group_hospital);


CREATE OR REPLACE VIEW
  `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_extended_outerfold_v1` AS

SELECT
  m.*,
  f.outer_fold

FROM `{{PROJECT_ID}}.{{DATASET_ID}}.feature_matrix_extended_view_v1` AS m

INNER JOIN `{{PROJECT_ID}}.{{DATASET_ID}}.hospital_outer_fold_v1` AS f
  USING (group_hospital);
