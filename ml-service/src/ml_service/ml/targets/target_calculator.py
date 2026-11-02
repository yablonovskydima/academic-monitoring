import enum
from collections.abc import Callable

from ml_service.schemas.student_semester_features import StudentSemesterFeatures


class LabelWindow(str, enum.Enum):
    current_semester = "current_semester"
    next_semester = "next_semester"
    next_semester_enrolled = "next_semester_enrolled"


class TargetCalculator:
    WEIGHT_GRADE = 0.45
    WEIGHT_ATTENDANCE = 0.20
    WEIGHT_SUBMISSIONS = 0.15
    WEIGHT_UNWORKED_ABSENCES = 0.10
    WEIGHT_PUNCTUALITY = 0.05
    WEIGHT_CONSISTENCY = 0.05

    LECTURE_ATTENDANCE_SHARE = 0.4
    LAB_ATTENDANCE_SHARE = 0.6
    GRADE_STDDEV_PENALTY = 2.0

    CRITICAL_ABSENCE_THRESHOLD = 75.0
    CRITICAL_GRADE_THRESHOLD = 50.0

    DROPPED_OUT_TARGET = 0.0
    CRITICAL_ABSENCE_CAP = 20.0

    def calculate_target(self, features: StudentSemesterFeatures) -> float:
        base = self._calculate_base_score(features)

        if features.study_mode == "full_time":
            if (
                features.lecture_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
                or features.lab_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            ):
                base = min(base, self.CRITICAL_ABSENCE_CAP)

        return round(base, 2)

    def _calculate_base_score(self, features: StudentSemesterFeatures) -> float:
        attendance = 100.0 - (
            features.lecture_absence_percent * self.LECTURE_ATTENDANCE_SHARE
            + features.lab_absence_percent * self.LAB_ATTENDANCE_SHARE
        )
        unworked_absences = 100.0 - _percent(features.unworked_absences_count, features.total_sessions)
        submissions = 100.0 - _percent(features.missing_submissions_count, features.total_gradable_sessions)
        punctuality = 100.0 - _percent(features.late_submissions_count, features.total_gradable_sessions)
        consistency = 100.0 - features.grade_stddev * self.GRADE_STDDEV_PENALTY

        score = (
            _clamp(features.avg_grade) * self.WEIGHT_GRADE
            + _clamp(attendance) * self.WEIGHT_ATTENDANCE
            + _clamp(submissions) * self.WEIGHT_SUBMISSIONS
            + _clamp(unworked_absences) * self.WEIGHT_UNWORKED_ABSENCES
            + _clamp(punctuality) * self.WEIGHT_PUNCTUALITY
            + _clamp(consistency) * self.WEIGHT_CONSISTENCY
        )

        return _clamp(score)

    def calculate_expulsion_label(self, features: StudentSemesterFeatures) -> int:
        return int(features.disappeared_next_semester)

    def calculate_debt_label(self, features: StudentSemesterFeatures) -> int:
        return int(features.repeated_subjects_count > 0)

    def calculate_admission_denial_label(self, features: StudentSemesterFeatures) -> int:
        if features.study_mode != "full_time":
            return 0

        return int(
            features.lecture_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            or features.lab_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            or features.avg_grade < self.CRITICAL_GRADE_THRESHOLD
        )

    def build_classification_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
        label_fn: Callable[[StudentSemesterFeatures], int],
        label_window: LabelWindow = LabelWindow.current_semester,
    ) -> tuple[list[StudentSemesterFeatures], list[int]]:
        last_semester_id = all_semester_ids_ordered[-1]

        X = [
            features
            for features in semester_features
            if self._label_is_observed(features, last_semester_id, label_window)
        ]
        y = [label_fn(features) for features in X]

        return X, y

    def _label_is_observed(
        self,
        features: StudentSemesterFeatures,
        last_semester_id: int,
        label_window: LabelWindow,
    ) -> bool:
        if label_window == LabelWindow.current_semester:
            return True

        if features.semester_id == last_semester_id:
            return False

        if label_window == LabelWindow.next_semester_enrolled:
            return not features.disappeared_next_semester

        return True

    def build_horizon_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
        horizon: int,
    ) -> tuple[list[StudentSemesterFeatures], list[float]]:
        features_by_key = {
            (features.student_id, features.semester_id): features
            for features in semester_features
        }

        semester_index = {
            semester_id: index
            for index, semester_id in enumerate(all_semester_ids_ordered)
        }

        last_index_by_student: dict[int, int] = {}
        for features in semester_features:
            idx = semester_index[features.semester_id]
            if idx > last_index_by_student.get(features.student_id, -1):
                last_index_by_student[features.student_id] = idx

        X: list[StudentSemesterFeatures] = []
        y: list[float] = []

        for features in semester_features:
            target_idx = semester_index[features.semester_id] + horizon

            if target_idx >= len(all_semester_ids_ordered):
                continue

            future_features = features_by_key.get(
                (features.student_id, all_semester_ids_ordered[target_idx])
            )

            if future_features is not None:
                target = self.calculate_target(future_features)
            elif last_index_by_student[features.student_id] < target_idx:
                target = self.DROPPED_OUT_TARGET
            else:
                continue

            X.append(features)
            y.append(target)

        return X, y


def _percent(part: int, total: int) -> float:
    return part / total * 100.0 if total else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
