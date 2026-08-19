from unittest.mock import MagicMock

from petebot4.llm import DEFAULT_MODEL, chat_completion, get_reply


def _mock_client(reply_text: str) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=reply_text))]
    client.chat.completions.create.return_value = response
    return client


def test_chat_completion_sends_system_and_user_messages_and_returns_reply():
    client = _mock_client("hello there")

    result = chat_completion(client, "system prompt", "hi")

    assert result == "hello there"
    client.chat.completions.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hi"},
        ],
    )


def test_get_reply_returns_chat_completion_result(monkeypatch):
    client = _mock_client("mocked reply")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    from petebot4 import llm as llm_module

    monkeypatch.setattr(llm_module, "get_client", lambda api_key: client)

    result = get_reply("hi")

    assert result == "mocked reply"
