import requests


def send_message(message: str, api_base_url: str, api_key: str) -> dict:
    response = requests.post(
        f"{api_base_url}/chat",
        json={"message": message},
        headers={"X-API-Key": api_key},
        timeout=35,
    )
    response.raise_for_status()
    return response.json()
