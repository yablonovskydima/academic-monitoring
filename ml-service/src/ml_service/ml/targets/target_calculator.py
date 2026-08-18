from collections.abc import Callable

from ml_service.schemas.student_semester_features import StudentSemesterFeatures


class TargetCalculator:
    # ---------- regression target ----------

    WEIGHT_AVG_GRADE = 0.5
    WEIGHT_GRADE_STDDEV = 0.35
    WEIGHT_LECTURE_ABSENCE = 0.1
    WEIGHT_LAB_ABSENCE = 0.15
    WEIGHT_UNWORKED_ABSENCES = 2.0
    WEIGHT_MISSING_SUBMISSIONS = 3.0
    WEIGHT_LATE_SUBMISSIONS = 1.0

    # ---------- classification thresholds ----------

    CRITICAL_ABSENCE_THRESHOLD = 75.0

    # ---------- special target values ----------

    DISAPPEARED_TARGET = 0.0
    REPEATED_SUBJECT_CAP = 30.0
    CRITICAL_ABSENCE_CAP = 20.0

    # ------------------------------------------------------------------
    # Regression
    # ------------------------------------------------------------------

    def calculate_target(self, features: StudentSemesterFeatures) -> float:
        """
        Calculate the student's current academic index.

        This target is based only on the current semester features,
        with special penalties for dropout, repeated subjects and
        critical absence.
        """
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

    # ------------------------------------------------------------------
    # Classification labels
    # ------------------------------------------------------------------

    def calculate_expulsion_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        """
        1 if the student disappears in the following semester.
        """
        return int(features.disappeared_next_semester)

    def calculate_debt_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        """
        1 if the student has repeated subjects in the next semester.

        Important:
        repeated_subjects_count can only be calculated when a next
        semester exists, so the training dataset for this target must
        exclude the student's last available semester.
        """
        return int(features.repeated_subjects_count > 0)

    def calculate_admission_denial_label(
        self,
        features: StudentSemesterFeatures,
    ) -> int:
        """
        1 if a full-time student has critical lecture/lab absence.
        """
        if features.study_mode != "full_time":
            return 0

        return int(
            features.lecture_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
            or features.lab_absence_percent >= self.CRITICAL_ABSENCE_THRESHOLD
        )

    # ------------------------------------------------------------------
    # Dataset helpers
    # ------------------------------------------------------------------

    def _get_last_semester_by_student(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> dict[int, int]:
        """
        Return the last available semester for every student.

        Example:

            student 1: [1, 2, 3] -> 3
            student 2: [1, 2]    -> 2
        """
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
        """
        Exclude each student's last available semester.

        This is required for targets that depend on the NEXT semester,
        e.g. repeated subjects / debt.
        """
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

    # ------------------------------------------------------------------
    # Current-semester regression dataset
    # ------------------------------------------------------------------

    def build_training_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[float],
    ]:
        """
        Build dataset for the current-semester index model.

        The target is calculated from the same semester, therefore
        the student's last available semester is still valid.
        """
        X = semester_features
        y = [self.calculate_target(features) for features in X]

        return X, y

    # ------------------------------------------------------------------
    # Classification datasets
    # ------------------------------------------------------------------

    def build_expulsion_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[int],
    ]:
        """
        Build dataset for expulsion classification.

        IMPORTANT:
        Do NOT remove the last semester.

        For a dropout student, the last available semester is exactly
        the semester where:

            disappeared_next_semester == True

        Example:

            S1 -> False
            S2 -> False
            S3 -> True   <- training example
            S4 -> missing

        Removing S3 would remove every positive dropout example.
        """
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
        """
        Build dataset for admission-denial classification.

        The target depends only on the current semester's attendance,
        so the last available semester is a valid training example.
        """
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
        """
        Build dataset for repeated-subject / debt classification.

        repeated_subjects_count compares current subjects with the
        following semester, therefore the student's last available
        semester cannot be used.
        """
        X = self._filter_last_semester(
            semester_features,
            all_semester_ids_ordered,
        )

        y = [self.calculate_debt_label(features) for features in X]

        return X, y

    # ------------------------------------------------------------------
    # Generic classification dataset
    # ------------------------------------------------------------------

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
        """
        Generic classification dataset builder.

        requires_next_semester=True:
            exclude the student's last available semester.

        requires_next_semester=False:
            keep the student's last available semester.

        This method is kept for compatibility with existing pipelines.
        For clarity, the dedicated builders above are preferred.
        """
        if requires_next_semester:
            X = self._filter_last_semester(
                semester_features,
                all_semester_ids_ordered,
            )
        else:
            X = semester_features

        y = [label_fn(features) for features in X]

        return X, y

    # ------------------------------------------------------------------
    # Forecast datasets
    # ------------------------------------------------------------------

    def build_horizon_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
        horizon: int,
    ) -> tuple[
        list[StudentSemesterFeatures],
        list[float],
    ]:
        """
        Build a forecast dataset.

        X:
            current semester features

        y:
            target/index from N semesters in the future

        A sample is created only when the target semester actually
        exists for the student.

        We must NOT assign 0.0 when the future semester is missing,
        because that would incorrectly turn "no future data" into
        "student has index 0".
        """
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
                # The student does not have data for the target semester.
                # There is no valid regression target.
                continue

            X.append(features)
            y.append(self.calculate_target(future_features))

        return X, y