import time
from collections.abc import Callable

import httpx

from ml_service.config import INSIGHTS_SERVICE_URL

ATTEMPTS = 3
TIMEOUT_SECONDS = 120.0


class InsightsDeliveryError(Exception):
    pass


class InsightsServiceClient:
    def __init__(self, base_url: str | None = None, sleep: Callable[[float], None] = time.sleep):
        self.base_url = base_url or INSIGHTS_SERVICE_URL
        self.sleep = sleep

    def submit_run(self, payload: dict) -> dict:
        last_error = "no attempt made"

        for attempt in range(ATTEMPTS):
            if attempt:
                self.sleep(2 ** attempt)

            try:
                response = httpx.post(f"{self.base_url}/insight-runs/", json=payload, timeout=TIMEOUT_SECONDS)
            except httpx.TransportError as e:
                last_error = f"{type(e).__name__}: {e}"
                continue

            if response.status_code in (200, 201):
                return response.json()
            if response.status_code < 500:
                raise InsightsDeliveryError(f"insights-service rejected the run: {response.status_code} {response.text[:500]}")
            last_error = f"insights-service answered {response.status_code}"

        raise InsightsDeliveryError(f"insights-service unreachable after {ATTEMPTS} attempts: {last_error}")
