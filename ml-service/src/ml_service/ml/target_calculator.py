from ml_service.schemas.student_semester_features import StudentSemesterFeatures


class TargetCalculator:
    """
    Calculates target (0-100) for training the model based on ALL student indicators in a specific semester.

    Two-stage logic:
    1. Base score — a weighted combination of gradient indicators (grades, absences, failure, instability).
    2. Catastrophic rules — strictly LIMIT the base score from above (min) if
    a critical scenario has occurred (disappeared, repeats a subject, failure due to absences).
    Limitation, not fixation — therefore, a student with bad base indicators
    And catastrophe remains at his (worst) level, and does not get pulled up.
    """


    WEIGHT_AVG_GRADE = 0.5
    WEIGHT_GRADE_STDDEV = 0.35
    WEIGHT_ABSENCE_PERCENT = 0.15
    WEIGHT_UNWORKED_ABSENCES = 2.0
    WEIGHT_MISSING_SUBMISSIONS = 3.0
    WEIGHT_LATE_SUBMISSIONS = 1.0

    # catastrophic thresholds
    CRITICAL_ABSENCE_THRESHOLD = 75.0
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

    def _calculate_base_score(self, features: StudentSemesterFeatures) -> float:
        score = (
            features.avg_grade * self.WEIGHT_AVG_GRADE
            - features.grade_stddev * self.WEIGHT_GRADE_STDDEV
            - features.absence_percent * self.WEIGHT_ABSENCE_PERCENT
            - features.unworked_absences_count * self.WEIGHT_UNWORKED_ABSENCES
            - features.missing_submissions_count * self.WEIGHT_MISSING_SUBMISSIONS
            - features.late_submissions_count * self.WEIGHT_LATE_SUBMISSIONS
        )
        return max(0.0, min(100.0, score))

    def build_training_dataset(
        self,
        semester_features: list[StudentSemesterFeatures],
        all_semester_ids_ordered: list[int],
    ) -> tuple[list[StudentSemesterFeatures], list[float]]:
        """
        Forms (X, Y) for learning - excludes the last known semester of each student, because there is no reliable signal about the future for them.
        """
        last_semester_by_student: dict[int, int] = {}
        for f in semester_features:
            idx = all_semester_ids_ordered.index(f.semester_id)
            current_last_id = last_semester_by_student.get(f.student_id)
            if current_last_id is None or idx > all_semester_ids_ordered.index(current_last_id):
                last_semester_by_student[f.student_id] = f.semester_id

        X: list[StudentSemesterFeatures] = []
        y: list[float] = []

        for f in semester_features:
            if f.semester_id == last_semester_by_student.get(f.student_id):
                continue

            target = self.calculate_target(f)
            X.append(f)
            y.append(target)

        return X, y