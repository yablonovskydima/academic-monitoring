from pydantic import TypeAdapter

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.schemas.student_features import StudentFeaturesRaw
from ml_service.schemas.student_semester_features import StudentSemesterFeatures

_features_adapter = TypeAdapter(list[StudentFeaturesRaw])
_semester_features_adapter = TypeAdapter(list[StudentSemesterFeatures])


class StudentFeaturesService:
    def __init__(self, client: ImportServiceClient | None = None):
        self.client = client or ImportServiceClient()

    def get_current_features(self) -> list[StudentFeaturesRaw]:
        raw = self.client.get_current_features()
        return _features_adapter.validate_python(raw)

    def get_semester_features(self) -> list[StudentSemesterFeatures]:
        raw = self.client.get_semester_features()
        return _semester_features_adapter.validate_python(raw)