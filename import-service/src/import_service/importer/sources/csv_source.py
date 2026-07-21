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

    def load_groups(self) -> list[dict]: #todo this is hardcoded as fak, need to change ts
        return self._read_csv("groups.csv")

    def load_students(self) -> list[dict]:
        return self._read_csv("students.csv")