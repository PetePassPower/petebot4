import importlib
import os
from unittest.mock import patch

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")

import pytest
from fastapi.testclient import TestClient

import api
from api import app

client = TestClient(app)


def test_chat_without_api_key_returns_401():
    response = client.post("/chat", json={"message": "hi"})

    assert response.status_code == 401
    assert response.json() == {"error": "invalid or missing API key"}


def test_chat_with_wrong_api_key_returns_401():
    response = client.post(
        "/chat", json={"message": "hi"}, headers={"X-API-Key": "wrong-key"}
    )

    assert response.status_code == 401
    assert response.json() == {"error": "invalid or missing API key"}


def test_chat_with_valid_key_returns_reply_and_model():
    with patch("api.get_reply", return_value="mocked reply") as mock_get_reply:
        response = client.post(
            "/chat", json={"message": "hi"}, headers={"X-API-Key": "test-key"}
        )

    assert response.status_code == 200
    assert response.json() == {"reply": "mocked reply", "model": "openai/gpt-oss-20b"}
    mock_get_reply.assert_called_once_with("hi")


def test_chat_missing_message_returns_422():
    response = client.post("/chat", json={}, headers={"X-API-Key": "test-key"})

    assert response.status_code == 422


def test_chat_empty_message_returns_422():
    response = client.post(
        "/chat", json={"message": ""}, headers={"X-API-Key": "test-key"}
    )

    assert response.status_code == 422


def test_chat_llm_failure_returns_500():
    with patch("api.get_reply", side_effect=RuntimeError("boom")):
        response = client.post(
            "/chat", json={"message": "hi"}, headers={"X-API-Key": "test-key"}
        )

    assert response.status_code == 500
    assert response.json() == {"error": "internal error"}


def test_chat_with_non_ascii_api_key_returns_401():
    response = client.post(
        "/chat",
        json={"message": "hi"},
        headers={"X-API-Key": "wrong-é-key".encode("latin-1")},
    )

    assert response.status_code == 401
    assert response.json() == {"error": "invalid or missing API key"}


def test_chat_without_api_key_and_invalid_body_returns_401():
    response = client.post("/chat", json={})

    assert response.status_code == 401
    assert response.json() == {"error": "invalid or missing API key"}


def test_api_fails_to_start_without_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "some-key")

    with pytest.raises(RuntimeError, match="API_KEY"):
        importlib.reload(api)


def test_api_fails_to_start_without_openrouter_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        importlib.reload(api)
