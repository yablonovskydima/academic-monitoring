import csv
from pathlib import Path

from import_service.importer.sources.base import DataSource


class CsvSource(DataSource):
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _read_csv(self, filename: str) -> list[dict]:
        filepath = self.data_dir / filename
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def load_groups(self) -> list[dict]: #todo до праци, туво є написано по варєтски, цево видов поміняти тре
        return self._read_csv("groups.csv")

    def load_students(self) -> list[dict]:
        return self._read_csv("students.csv")

    def load_semesters(self) -> list[dict]:
        return self._read_csv("semesters.csv")

    def load_teachers(self) -> list[dict]:
        return self._read_csv("teachers.csv")

    def load_subjects(self) -> list[dict]:
        return self._read_csv("subjects.csv")

    def load_subject_offerings(self) -> list[dict]:
        return self._read_csv("subject_offerings.csv")

    def load_enrollments(self) -> list[dict]:
        return self._read_csv("enrollments.csv")

    def load_class_sessions(self) -> list[dict]:
        return self._read_csv("class_sessions.csv")

    def load_attendance(self) -> list[dict]:
        return self._read_csv("attendance.csv")

    def load_grades(self) -> list[dict]:
        return self._read_csv("grades.csv")