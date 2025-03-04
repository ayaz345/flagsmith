import json
import logging
import typing

import requests

from environments.identities.models import Identity
from environments.identities.traits.models import Trait
from features.models import FeatureState
from integrations.common.wrapper import AbstractBaseIdentityIntegrationWrapper

from .models import AmplitudeConfiguration

logger = logging.getLogger(__name__)

AMPLITUDE_API_URL = "https://api.amplitude.com"


class AmplitudeWrapper(AbstractBaseIdentityIntegrationWrapper):
    def __init__(self, config: AmplitudeConfiguration):
        self.api_key = config.api_key
        self.url = f"{AMPLITUDE_API_URL}/identify"

    def _identify_user(self, user_data: dict) -> None:
        payload = {"api_key": self.api_key, "identification": json.dumps([user_data])}

        response = requests.post(self.url, data=payload)
        logger.debug(
            f"Sent event to Amplitude. Response code was: {response.status_code}"
        )

    def generate_user_data(
        self,
        identity: Identity,
        feature_states: typing.List[FeatureState],
        trait_models: typing.List[Trait] = None,
    ) -> dict:
        feature_properties = {}

        for feature_state in feature_states:
            value = feature_state.get_feature_state_value(identity=identity)
            feature_properties[feature_state.feature.name] = (
                value if (feature_state.enabled and value) else feature_state.enabled
            )

        return {
            "user_id": identity.identifier,
            "user_properties": feature_properties,
        }
