import logging

from custom_auth.oauth.exceptions import GithubError

logger = logging.getLogger(__name__)


def convert_response_data_to_dictionary(text: str) -> dict:
    try:
        return dict([param.split("=") for param in text.split("&")])
    except ValueError:
        logger.warning(f"Malformed data received from Github ({text})")
        raise GithubError("Malformed data received from Github")


def get_first_and_last_name(full_name: str) -> list:
    if not full_name:
        return ["", ""]

    names = full_name.strip().split(" ")
    return names if len(names) == 2 else [full_name, ""]
