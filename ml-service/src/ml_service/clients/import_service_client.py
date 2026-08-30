import httpx
from pydantic import TypeAdapter

from ml_service.config import IMPORT_SERVICE_URL
from ml_service.schemas.student_semester_features import StudentSemesterFeatures

_semester_features_adapter = TypeAdapter(list[StudentSemesterFeatures])

PAGE_SIZE = 1000


class ImportServiceClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or IMPORT_SERVICE_URL

    def get_semester_features(self, page_size: int = PAGE_SIZE,) -> list[StudentSemesterFeatures]:
        all_features: list[StudentSemesterFeatures] = []
        offset = 0

        while True:
            response = httpx.get(
                f"{self.base_url}/student-features/by-semester",
                params={"limit": page_size, "offset": offset},
                timeout=60.0,
            )
            response.raise_for_status()

            page = _semester_features_adapter.validate_json(response.content)
            if not page:
                break

            all_features.extend(page)
            offset += page_size

        return all_features

    def get_semesters(self) -> list[dict]:
        response = httpx.get(
            f"{self.base_url}/semesters/",
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()