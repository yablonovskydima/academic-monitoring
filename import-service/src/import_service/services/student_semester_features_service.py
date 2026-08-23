from collections import defaultdict

from sqlalchemy.orm import Session

from import_service.repositories.student_semester_features_repository import StudentSemesterFeaturesRepository
from import_service.schemas.student_semester_features import StudentSemesterFeatures
from import_service.models.class_session import SessionType


class StudentSemesterFeaturesService:
    def __init__(self, db: Session):
        self.repo = StudentSemesterFeaturesRepository(db)

    def get_all(self, limit: int = 1000, offset: int = 0) -> list[StudentSemesterFeatures]:
        student_ids = self.repo.get_student_ids_page(limit=limit, offset=offset)
        if not student_ids:
            return []

        base_info = {row["student_id"]: row for row in self.repo.get_base_info(student_ids)}
        semesters = self.repo.get_all_semesters()
        semesters_by_id = {s["semester_id"]: s for s in semesters}
        ordered_semester_ids = [s["semester_id"] for s in semesters]

        def _index_by_pair(rows: list[dict]) -> dict[tuple[int, int], dict]:
            return {(r["student_id"], r["semester_id"]): r for r in rows}

        grade_stats = _index_by_pair(self.repo.get_grade_stats_by_semester(student_ids))
        late_submissions = _index_by_pair(self.repo.get_late_submissions_by_semester(student_ids))
        attendance = _index_by_pair(self.repo.get_attendance_stats_by_semester(student_ids))
        lecture_attendance = _index_by_pair(self.repo.get_attendance_by_session_type_and_semester(student_ids, SessionType.lecture))
        lab_attendance = _index_by_pair(self.repo.get_attendance_by_session_type_and_semester(student_ids, SessionType.lab))
        expected_sessions = _index_by_pair(self.repo.get_expected_gradable_sessions_by_semester(student_ids))
        graded_sessions = _index_by_pair(self.repo.get_graded_sessions_count_by_semester(student_ids))

        enrollment_rows = self.repo.get_enrollments_by_semester(student_ids)
        subjects_by_student_semester: dict[tuple[int, int], set[int]] = defaultdict(set)
        semesters_by_student: dict[int, set[int]] = defaultdict(set)
        for row in enrollment_rows:
            key = (row["student_id"], row["semester_id"])
            subjects_by_student_semester[key].add(row["subject_id"])
            semesters_by_student[row["student_id"]].add(row["semester_id"])

        result: list[StudentSemesterFeatures] = []

        for student_id in student_ids:
            info = base_info.get(student_id)
            if info is None:
                continue

            student_semesters = semesters_by_student.get(student_id, set())

            for semester_id in ordered_semester_ids:
                if semester_id not in student_semesters:
                    continue

                key = (student_id, semester_id)
                sem = semesters_by_id[semester_id]

                g_stats = grade_stats.get(key, {})
                att = attendance.get(key, {})
                lec_att = lecture_attendance.get(key, {})
                lab_att = lab_attendance.get(key, {})
                expected = expected_sessions.get(key, {})
                graded = graded_sessions.get(key, {})
                late = late_submissions.get(key, {})

                total_sessions = att.get("total_sessions", 0) or 0
                absences_count = att.get("absences_count", 0) or 0
                absence_percent = (absences_count / total_sessions * 100) if total_sessions else 0.0

                lec_total = lec_att.get("total", 0) or 0
                lec_absences = lec_att.get("absences", 0) or 0
                lecture_absence_percent = (lec_absences / lec_total * 100) if lec_total else 0.0

                lab_total = lab_att.get("total", 0) or 0
                lab_absences = lab_att.get("absences", 0) or 0
                lab_absence_percent = (lab_absences / lab_total * 100) if lab_total else 0.0

                total_gradable = expected.get("total_gradable_sessions", 0) or 0
                graded_count = graded.get("graded_sessions_count", 0) or 0
                missing_submissions_count = max(0, total_gradable - graded_count)

                next_semester_idx = ordered_semester_ids.index(semester_id) + 1
                if next_semester_idx < len(ordered_semester_ids):
                    next_semester_id = ordered_semester_ids[next_semester_idx]
                    disappeared_next_semester = next_semester_id not in student_semesters

                    current_subjects = subjects_by_student_semester.get(key, set())
                    next_subjects = subjects_by_student_semester.get((student_id, next_semester_id), set())
                    repeated_subjects_count = len(current_subjects & next_subjects)
                else:
                    disappeared_next_semester = False
                    repeated_subjects_count = 0

                prev_semester_idx = ordered_semester_ids.index(semester_id) - 1
                if prev_semester_idx >= 0 and ordered_semester_ids[prev_semester_idx] in student_semesters:
                    prev_key = (student_id, ordered_semester_ids[prev_semester_idx])
                    prev_g_stats = grade_stats.get(prev_key, {})
                    prev_att = attendance.get(prev_key, {})
                    prev_expected = expected_sessions.get(prev_key, {})
                    prev_graded = graded_sessions.get(prev_key, {})

                    prev_total_sessions = prev_att.get("total_sessions", 0) or 0
                    prev_absences_count = prev_att.get("absences_count", 0) or 0
                    prev_absence_percent = (
                        prev_absences_count / prev_total_sessions * 100
                        if prev_total_sessions else 0.0
                    )

                    prev_total_gradable = prev_expected.get("total_gradable_sessions", 0) or 0
                    prev_graded_count = prev_graded.get("graded_sessions_count", 0) or 0
                    prev_missing_submissions_count = max(0, prev_total_gradable - prev_graded_count)

                    avg_grade_delta = round(
                        float(g_stats.get("avg_grade") or 0.0) - float(prev_g_stats.get("avg_grade") or 0.0),
                        2,
                    )
                    absence_percent_delta = round(absence_percent - prev_absence_percent, 2)
                    missing_submissions_delta = missing_submissions_count - prev_missing_submissions_count
                else:
                    avg_grade_delta = 0.0
                    absence_percent_delta = 0.0
                    missing_submissions_delta = 0

                result.append(StudentSemesterFeatures(
                    student_id=student_id,
                    semester_id=semester_id,
                    academic_year=sem["academic_year"],
                    term=sem["term"],
                    course_year=info["course_year"],
                    study_mode=info["study_mode"],

                    avg_grade=float(g_stats.get("avg_grade") or 0.0),
                    grade_stddev=float(g_stats.get("grade_stddev") or 0.0),

                    total_sessions=total_sessions,
                    absences_count=absences_count,
                    absence_percent=round(absence_percent, 2),
                    unworked_absences_count=att.get("unworked_absences_count", 0) or 0,

                    lecture_absence_percent=round(lecture_absence_percent, 2),
                    lab_absence_percent=round(lab_absence_percent, 2),

                    total_gradable_sessions=total_gradable,
                    graded_sessions_count=graded_count,
                    missing_submissions_count=missing_submissions_count,
                    late_submissions_count=late.get("late_submissions_count", 0) or 0,

                    disappeared_next_semester=disappeared_next_semester,
                    repeated_subjects_count=repeated_subjects_count,

                    avg_grade_delta=avg_grade_delta,
                    absence_percent_delta=absence_percent_delta,
                    missing_submissions_delta=missing_submissions_delta,
                ))

        return result