import json
import logging

import requests

from integrations.common.wrapper import AbstractBaseEventIntegrationWrapper

logger = logging.getLogger(__name__)

EVENTS_API_URI = "api/v2/events/ingest"


class DynatraceWrapper(AbstractBaseEventIntegrationWrapper):
    def __init__(self, base_url: str, api_key: str, entity_selector: str):
        self.base_url = base_url
        self.api_key = api_key
        self.entity_selector = entity_selector
        self.url = f"{self.base_url}{EVENTS_API_URI}?api-token={self.api_key}"

    def _track_event(self, event: dict) -> None:
        event["entitySelector"] = self.entity_selector
        response = requests.post(
            self.url, headers=self._headers(), data=json.dumps(event)
        )
        logger.debug(
            f"Sent event to Dynatrace. Response code was {response.status_code}"
        )

    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    @staticmethod
    def generate_event_data(log: str, email: str, environment_name: str) -> dict:
        flag_properties = {
            "event": f"{log} by user {email}",
            "environment": environment_name,
        }

        return {
            "title": "Flagsmith flag change.",
            "eventType": "CUSTOM_DEPLOYMENT",
            "properties": flag_properties,
        }
