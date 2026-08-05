import httpx
from pydantic import TypeAdapter

from ml_service.config import IMPORT_SERVICE_URL
from ml_service.schemas.student_features import StudentFeaturesRaw
from ml_service.schemas.student_semester_features import StudentSemesterFeatures

_features_adapter = TypeAdapter(list[StudentFeaturesRaw])
_semester_features_adapter = TypeAdapter(list[StudentSemesterFeatures])


class ImportServiceClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or IMPORT_SERVICE_URL

    def get_current_features(self) -> list[StudentFeaturesRaw]:
        response = httpx.get(f"{self.base_url}/student-features/", timeout=30.0)
        response.raise_for_status()
        return _features_adapter.validate_json(response.content)

    def get_semester_features(self) -> list[StudentSemesterFeatures]:
        response = httpx.get(f"{self.base_url}/student-features/by-semester", timeout=60.0)
        response.raise_for_status()
        return _semester_features_adapter.validate_json(response.content)