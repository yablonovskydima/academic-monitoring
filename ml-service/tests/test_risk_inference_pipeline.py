import random
from types import SimpleNamespace

import pytest

from factories import make_features

from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.inference.risk_inference_pipeline import RISK_TYPE_BY_PURPOSE, RiskInferencePipeline
from ml_service.ml.training.risk_trainer import RiskTrainer
from ml_service.models.model_version import ModelPurpose


def _rows(n=120):
    rng = random.Random(0)
    return [
        make_features(
            student_id=i,
            avg_grade=rng.uniform(30, 95),
            absence_percent=rng.uniform(0, 80),
            lecture_absence_percent=rng.uniform(0, 80),
            lab_absence_percent=rng.uniform(0, 80),
            missing_submissions_count=rng.randint(0, 15),
            late_submissions_count=rng.randint(0, 15),
        )
        for i in range(n)
    ]


class Models:
    def __init__(self, rows):
        encoder = FeatureEncoder()
        labels = [int(r.avg_grade < 60 or r.absence_percent > 50) for r in rows]
        self.by_path = {}
        for purpose in RISK_TYPE_BY_PURPOSE:
            X = encoder.encode(rows, purpose=purpose)
            self.by_path[purpose.value] = RiskTrainer().train(
                X, labels, [r.student_id for r in rows],
                monotone_constraints=encoder.monotone_constraints_for(purpose),
            ).model

    def load(self, path):
        return self.by_path[path]


class Versions:
    def get_active_by_purpose(self, purpose):
        return SimpleNamespace(id=list(RISK_TYPE_BY_PURPOSE).index(purpose) + 1, model_file_path=purpose.value)


class Assessments:
    def bulk_create_many(self, items):
        return [SimpleNamespace(id=i, student_index_id=sid, **data.model_dump()) for i, (sid, data) in enumerate(items)]


class Explanations:
    def __init__(self):
        self.items = []

    def bulk_create_many(self, items):
        self.items.extend(items)


@pytest.fixture(scope="module")
def models():
    return Models(_rows())


def _pipeline(models, explanations):
    return RiskInferencePipeline(FeatureEncoder(), models, Versions(), Assessments(), explanations)


def test_every_risk_assessment_gets_its_top_five_explanations(models):
    explanations = Explanations()
    pipeline = _pipeline(models, explanations)
    rows = _rows()[:10]
    pipeline.set_background(_rows())

    pipeline.process_batch(rows, [SimpleNamespace(id=100 + i) for i in range(len(rows))])

    per_assessment = {}
    for assessment_id, data in explanations.items:
        per_assessment.setdefault(assessment_id, []).append(data)

    assert len(per_assessment) == len(rows) * len(RISK_TYPE_BY_PURPOSE)
    assert all([e.rank for e in items] == [1, 2, 3, 4, 5] for items in per_assessment.values())


def test_admission_explanations_only_use_admission_columns(models):
    explanations = Explanations()
    pipeline = _pipeline(models, explanations)
    pipeline.set_background(_rows())

    pipeline.process_batch(_rows()[:5], [SimpleNamespace(id=i) for i in range(5)])

    purposes = list(RISK_TYPE_BY_PURPOSE)
    admission_slot = purposes.index(ModelPurpose.admission_classifier)
    admission_names = {
        data.feature_name
        for assessment_id, data in explanations.items
        if assessment_id % len(purposes) == admission_slot
    }
    assert admission_names
    assert admission_names <= set(FeatureEncoder().columns_for(ModelPurpose.admission_classifier))


def test_process_batch_requires_a_background(models):
    pipeline = _pipeline(models, Explanations())

    with pytest.raises(ValueError, match="set_background"):
        pipeline.process_batch(_rows()[:1], [SimpleNamespace(id=1)])
