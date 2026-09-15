import httpx

from auth_service.config import IMPORT_SERVICE_URL


class ImportServiceClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or IMPORT_SERVICE_URL

    def get_group(self, group_id: int) -> dict | None:
        response = httpx.get(
            f"{self.base_url}/groups/{group_id}",
            timeout=10.0,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    def get_faculty(self, faculty_id: int) -> dict | None:
#TODO ADD A FACULTY TABLE TO IMPORT SERVICE
        response = httpx.get(
            f"{self.base_url}/faculties/{faculty_id}",
            timeout=10.0,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()
