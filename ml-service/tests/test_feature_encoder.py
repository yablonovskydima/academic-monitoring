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


def test_encode_for_admission_drops_cumulative_values_from_the_dataframe():
    encoder = FeatureEncoder()
    features = make_features()

    df = encoder.encode([features], purpose=ModelPurpose.admission_classifier)

    assert "cumulative_avg_grade" not in df.columns
    assert len(df.columns) == len(FEATURE_COLUMNS) - 4
