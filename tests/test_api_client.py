from unittest.mock import MagicMock, patch

import pytest
import requests

from petebot4.api_client import send_message


def _mock_response(json_data=None, raise_for_status_error=None):
    response = MagicMock()
    response.json.return_value = json_data or {}
    if raise_for_status_error:
        response.raise_for_status.side_effect = raise_for_status_error
    return response


def test_send_message_returns_parsed_reply_on_success():
    mock_response = _mock_response({"reply": "hi there", "model": "openai/gpt-oss-20b"})

    with patch("petebot4.api_client.requests.post", return_value=mock_response) as mock_post:
        result = send_message("hello", "http://localhost:8000", "test-key")

    assert result == {"reply": "hi there", "model": "openai/gpt-oss-20b"}
    mock_post.assert_called_once_with(
        "http://localhost:8000/chat",
        json={"message": "hello"},
        headers={"X-API-Key": "test-key"},
        timeout=35,
    )


def test_send_message_raises_http_error_on_401():
    error = requests.HTTPError("401 Client Error")
    mock_response = _mock_response(raise_for_status_error=error)

    with patch("petebot4.api_client.requests.post", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            send_message("hello", "http://localhost:8000", "wrong-key")


def test_send_message_raises_http_error_on_500():
    error = requests.HTTPError("500 Server Error")
    mock_response = _mock_response(raise_for_status_error=error)

    with patch("petebot4.api_client.requests.post", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            send_message("hello", "http://localhost:8000", "test-key")


def test_send_message_raises_connection_error_when_server_down():
    with patch(
        "petebot4.api_client.requests.post",
        side_effect=requests.ConnectionError("refused"),
    ):
        with pytest.raises(requests.ConnectionError):
            send_message("hello", "http://localhost:8000", "test-key")
