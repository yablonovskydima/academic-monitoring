import httpx

from auth_service.config import IMPORT_SERVICE_URL


class ImportServiceUnavailable(Exception):
    pass


class ImportServiceClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or IMPORT_SERVICE_URL

    def get_group(self, group_id: int) -> dict | None:
        return self._get_or_none(f"/groups/{group_id}")

    def get_faculty(self, faculty_id: int) -> dict | None:
        return self._get_or_none(f"/faculties/{faculty_id}")

    def _get_or_none(self, path: str) -> dict | None:
        try:
            response = httpx.get(f"{self.base_url}{path}", timeout=10.0)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ImportServiceUnavailable(f"import-service request failed: {e}") from e
