from collections import defaultdict

from sqlalchemy.orm import Session

from import_service.repositories.student_features_repository import StudentFeaturesRepository
from import_service.schemas.student_features import StudentFeaturesRaw, SemesterAvgGrade
from import_service.models.class_session import SessionType


class StudentFeaturesService:
    def __init__(self, db: Session):
        self.repo = StudentFeaturesRepository(db)

    def get_all_features(self, limit: int = 1000, offset: int = 0) -> list[StudentFeaturesRaw]:
        student_ids = self.repo.get_student_ids_page(limit=limit, offset=offset)
        if not student_ids:
            return []

        base_info = {row["student_id"]: row for row in self.repo.get_base_info(student_ids)}
        grade_stats = {row["student_id"]: row for row in self.repo.get_grade_stats(student_ids)}
        late_submissions = {row["student_id"]: row for row in self.repo.get_late_submissions(student_ids)}
        attendance = {row["student_id"]: row for row in self.repo.get_attendance_stats(student_ids)}
        lecture_attendance = {row["student_id"]: row for row in
                              self.repo.get_attendance_by_session_type(student_ids, SessionType.lecture)}
        lab_attendance = {row["student_id"]: row for row in
                          self.repo.get_attendance_by_session_type(student_ids, SessionType.lab)}
        expected_sessions = {row["student_id"]: row for row in self.repo.get_expected_gradable_sessions(student_ids)}
        graded_sessions = {row["student_id"]: row for row in self.repo.get_graded_sessions_count(student_ids)}

        trend_rows = self.repo.get_grade_trend(student_ids)
        trend_by_student: dict[int, list[SemesterAvgGrade]] = defaultdict(list)
        for row in trend_rows:
            trend_by_student[row["student_id"]].append(
                SemesterAvgGrade(
                    semester_id=row["semester_id"],
                    academic_year=row["academic_year"],
                    term=row["term"],
                    avg_grade=float(row["avg_grade"]),
                )
            )

        result = []
        for student_id in student_ids:
            info = base_info.get(student_id)
            if info is None:
                continue

            g_stats = grade_stats.get(student_id, {})
            att = attendance.get(student_id, {})
            lec_att = lecture_attendance.get(student_id, {})
            lab_att = lab_attendance.get(student_id, {})
            expected = expected_sessions.get(student_id, {})
            graded = graded_sessions.get(student_id, {})
            late = late_submissions.get(student_id, {})

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

            result.append(StudentFeaturesRaw(
                student_id=student_id,
                course_year=info["course_year"],
                study_mode=info["study_mode"],

                avg_grade_overall=float(g_stats.get("avg_grade_overall") or 0.0),
                grade_stddev=float(g_stats.get("grade_stddev") or 0.0),
                grade_trend=trend_by_student.get(student_id, []),

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
            ))

        return result