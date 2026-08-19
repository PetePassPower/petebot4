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


def test_index_returns_chat_page_with_embedded_api_key():
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "test-key" in response.text
    assert "petebot4" in response.text


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
    mock_get_reply.assert_called_once_with("hi", history=[])


def test_chat_with_history_passes_it_through_to_get_reply():
    history = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
    ]
    with patch("api.get_reply", return_value="mocked reply") as mock_get_reply:
        response = client.post(
            "/chat",
            json={"message": "hi", "history": history},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    mock_get_reply.assert_called_once_with("hi", history=history)


def test_chat_with_history_longer_than_3_turns_is_truncated_to_last_3():
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"}
        for i in range(10)
    ]
    with patch("api.get_reply", return_value="mocked reply") as mock_get_reply:
        response = client.post(
            "/chat",
            json={"message": "hi", "history": history},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    mock_get_reply.assert_called_once_with("hi", history=history[-6:])


def test_chat_with_invalid_history_role_returns_422():
    response = client.post(
        "/chat",
        json={"message": "hi", "history": [{"role": "system", "content": "nope"}]},
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 422


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
