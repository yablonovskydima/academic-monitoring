from factories import make_features

from ml_service.ml.encoding.feature_encoder import FeatureEncoder, FEATURE_COLUMNS
from ml_service.models.model_version import ModelPurpose


def test_admission_classifier_excludes_cumulative_columns():
    encoder = FeatureEncoder()
    columns = encoder.columns_for(ModelPurpose.admission_classifier)

    for excluded in [
        "cumulative_avg_grade",
        "cumulative_absence_percent",
        "cumulative_avg_missing_submissions",
        "cumulative_avg_late_submissions",
    ]:
        assert excluded not in columns

    # semesters_completed_count is not a duplicate of the label's own inputs, so it stays
    assert "semesters_completed_count" in columns


def test_other_purposes_get_the_full_column_set():
    encoder = FeatureEncoder()

    assert encoder.columns_for(ModelPurpose.index_regression) == FEATURE_COLUMNS
    assert encoder.columns_for(None) == FEATURE_COLUMNS


def test_encode_produces_one_row_per_feature_with_expected_values():
    encoder = FeatureEncoder()
    features = make_features(avg_grade=72.5, study_mode="part_time")

    df = encoder.encode([features], purpose=ModelPurpose.index_regression)

    assert len(df) == 1
    assert list(df.columns) == FEATURE_COLUMNS
    assert df.iloc[0]["avg_grade"] == 72.5
    assert df.iloc[0]["study_mode_full_time"] == 0
    assert df.iloc[0]["study_mode_part_time"] == 1
    assert df.iloc[0]["study_mode_individual_schedule"] == 0


def test_index_models_must_rise_with_grades_and_fall_with_absence():
    constraints = FeatureEncoder().monotone_constraints_for(ModelPurpose.index_regression)

    assert constraints["avg_grade"] == 1
    assert constraints["absence_percent"] == -1
    assert constraints["missing_submissions_count"] == -1


def test_risk_models_get_the_opposite_directions():
    encoder = FeatureEncoder()
    index = encoder.monotone_constraints_for(ModelPurpose.index_forecast_horizon_2)

    for purpose in (ModelPurpose.expulsion_classifier, ModelPurpose.debt_classifier):
        risk = encoder.monotone_constraints_for(purpose)
        assert risk == {column: -direction for column, direction in index.items()}


def test_trend_and_context_features_are_left_unconstrained():
    constraints = FeatureEncoder().monotone_constraints_for(ModelPurpose.index_regression)

    for column in ("avg_grade_delta", "course_year", "study_mode_full_time", "semesters_completed_count"):
        assert column not in constraints


def test_constraints_only_name_columns_the_model_actually_gets():
    encoder = FeatureEncoder()

    constraints = encoder.monotone_constraints_for(ModelPurpose.admission_classifier)

    assert set(constraints) <= set(encoder.columns_for(ModelPurpose.admission_classifier))
    assert "cumulative_avg_grade" not in constraints


def test_encode_for_admission_drops_cumulative_values_from_the_dataframe():
    encoder = FeatureEncoder()
    features = make_features()

    df = encoder.encode([features], purpose=ModelPurpose.admission_classifier)

    assert "cumulative_avg_grade" not in df.columns
    assert len(df.columns) == len(FEATURE_COLUMNS) - 4
