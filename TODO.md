# TODO

Known issues found while documenting the data → features → model pipeline. Not fixed yet.

## Index scale is effectively broken
`ml-service/src/ml_service/ml/targets/target_calculator.py` — `_calculate_base_score`.

On the current synthetic dataset (10,160 student×semester rows) the computed index never reaches 70, only 0.04% of rows reach 40, the max is ~42, and **half of all rows are exactly 0**. So `IndexCategory.high` / `medium` (thresholds 70 / 40 in `index_inference_pipeline.py`) almost never fire — practically every student is `low`.

Cause: `unworked_absences_count` (×2.0) and `late_submissions_count` (×1.0) are raw per-semester **counts** (an average student has ~15 unworked absences and ~11 late submissions → ~−40 points), while the only positive term is `avg_grade × 0.5` (max +50). The penalties need to be normalized (e.g. to a percentage of sessions / submissions) or the weights rebalanced, then the category thresholds re-checked against the real distribution.

## `missing_submissions_count` is always 0 in synthetic data
`import-service/src/import_service/generator/generate_csv.py` — `generate_grades`.

The generator writes a grade for every lab/control session regardless of attendance, so `graded == expected` always. `missing_submissions_count`, `missing_submissions_delta` and `cumulative_avg_missing_submissions` are constant zeros — three dead features. The generator should skip some submissions (driven by the risk profile / absence), so this signal actually exists.

## Expulsion label is wrong for the last semester
`ml-service/src/ml_service/ml/training/risk_training_pipeline.py` — `RISK_CONFIGS`.

`expulsion_classifier` uses `requires_next_semester=False`, so rows from the last available semester get `disappeared_next_semester=False` (label 0) even though the outcome is unknown — label noise. `debt_classifier` already uses `True` for the same reason; expulsion should too.

## No SHAP explanations for risk classifiers
`ml-service/src/ml_service/ml/inference/risk_inference_pipeline.py`.

SHAP explanations are only computed and stored for `index_regression`. The three risk classifiers return a bare probability. The project vision (and thesis chapter 1) promises explanations for every prediction — add per-risk explanations.

## `course_year` is static across the 3-year window
`import-service/src/import_service/generator/generate_csv.py` — `generate_groups`.

Each group gets a random `course_year` (1–4) that never changes, although the data spans 6 semesters (3 academic years). Minor realism issue; the feature is still fed to the models.
