from collections.abc import Callable

from ml_service.schemas.student_semester_features import StudentSemesterFeatures


class TargetCalculator:
    WEIGHT_AVG_GRADE = 0.5
    WEIGHT_GRADE_STDDEV = 0.35
    WEIGHT_LECTURE_ABSENCE = 0.1
    WEIGHT_LAB_ABSENCE = 0.15
    WEIGHT_UNWORKED_ABSENCES = 2.0
    WEIGHT_MISSING_SUBMISSIONS = 3.0
    WEIGHT_LATE_SUBMISSIONS = 1.0

    CRITICAL_ABSENCE_THRESHOLD = 75.0
    CRITICAL_GRADE_THRESHOLD = 50.0

    DISAPPEARED_TARGET = 0.0
    REPEATED_SUBJECT_CAP = 30.0
    CRITICAL_ABSENCE_CAP = 20.0


    def calculate_target(self, features: StudentSemesterFeatures) -> float:
        if features.disappeared_next_semester:
            return self.DISAPPEARED_TARGET

        base = self._calculate_base_score(features)

        if features.repeated_subjects_count > 0:
            base = min(base, self.REPEATED_SUBJECT_CAP)

        if features.study_mode == "full_time":
            if (
                features.lecture_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
                or features.lab_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            ):
                base = min(base, self.CRITICAL_ABSENCE_CAP)

        return round(base, 2)

    def _calculate_base_score(
        self,
        features: StudentSemesterFeatures,
    ) -> float:
        score = (
            features.avg_grade * self.WEIGHT_AVG_GRADE
            - features.grade_stddev * self.WEIGHT_GRADE_STDDEV
            - features.lecture_absence_percent * self.WEIGHT_LECTURE_ABSENCE
            - features.lab_absence_percent * self.WEIGHT_LAB_ABSENCE
            - features.unworked_absences_count * self.WEIGHT_UNWORKED_ABSENCES
            - features.missing_submissions_count * self.WEIGHT_MISSING_SUBMISSIONS
            - features.late_submissions_count * self.WEIGHT_LATE_SUBMISSIONS
        )

        return max(0.0, min(100.0, score))

    def calculate_expulsion_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        return int(features.disappeared_next_semester)

    def calculate_debt_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        return int(features.repeated_subjects_count > 0)

    def calculate_admission_denial_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        if features.study_mode != "full_time":
            return 0

        return int(
            features.lecture_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            or features.lab_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            or features.avg_grade < self.CRITICAL_GRADE_THRESHOLD
        )

    def _get_last_semester_by_student(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> dict[int, int]:
        semester_order = {
            semester_id: index
            for index, semester_id in enumerate(all_semester_ids_ordered)
        }

        last_semester_by_student: dict[int, int] = {}

        for features in semester_features:
            current_last = last_semester_by_student.get(features.student_id)

            if current_last is None:
                last_semester_by_student[features.student_id] = features.semester_id
                continue

            if semester_order[features.semester_id] > semester_order[current_last]:
                last_semester_by_student[features.student_id] = features.semester_id

        return last_semester_by_student

    def _filter_last_semester(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> list[StudentSemesterFeatures]:
        last_semester_by_student = self._get_last_semester_by_student(
            semester_features,
            all_semester_ids_ordered,
        )

        return [
            features
            for features in semester_features
            if features.semester_id
            != last_semester_by_student.get(features.student_id)
        ]

    def build_expulsion_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[int],
    ]:
        X = semester_features
        y = [self.calculate_expulsion_label(features) for features in X]

        return X, y

    def build_admission_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[int],
    ]:
        X = semester_features
        y = [
            self.calculate_admission_denial_label(features)
            for features in X
        ]

        return X, y

    def build_debt_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[int],
    ]:
        X = self._filter_last_semester(
            semester_features,
            all_semester_ids_ordered,
        )

        y = [self.calculate_debt_label(features) for features in X]

        return X, y

    def build_classification_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
        label_fn: Callable[[StudentSemesterFeatures], int],
        requires_next_semester: bool = False,
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[int],
    ]:
        if requires_next_semester:
            X = self._filter_last_semester(
                semester_features,
                all_semester_ids_ordered,
            )
        else:
            X = semester_features

        y = [label_fn(features) for features in X]

        return X, y

    def build_horizon_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
        horizon: int,
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[float],
    ]:

        features_by_key = {
            (features.student_id, features.semester_id): features
            for features in semester_features
        }

        semester_index = {
            semester_id: index
            for index, semester_id in enumerate(all_semester_ids_ordered)
        }

        X: list[StudentSemesterFeatures] = []
        y: list[float] = []

        for features in semester_features:
            current_idx = semester_index[features.semester_id]
            target_idx = current_idx + horizon

            if target_idx >= len(all_semester_ids_ordered):
                continue

            target_semester_id = all_semester_ids_ordered[target_idx]

            future_features = features_by_key.get(
                (features.student_id, target_semester_id)
            )

            if future_features is None:
                continue

            X.append(features)
            y.append(self.calculate_target(future_features))

        return X, y