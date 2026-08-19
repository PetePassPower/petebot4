# petebot4 — Streamlit Chat UI Design

## Purpose

Add a browser-based chat UI on top of the existing `petebot4` REST API
(`api.py`), so the chatbot can be used interactively instead of only via
`curl`/HTTP clients. The REST API itself is unchanged.

## Architecture

Two independent processes, run separately:

- `uvicorn api:app --host 127.0.0.1 --port 8000` (existing, unchanged)
- `streamlit run app.py` (new)

`app.py` talks to `api.py` purely over HTTP, the same way any external
client would — it does not import `petebot4.llm` directly. This keeps the
REST API as the single source of truth for auth, error shaping, and model
selection.

```
petebot4/
  app.py                   # new: Streamlit chat UI (rendering only)
  api.py                   # unchanged
  petebot4/
    api_client.py           # new: send_message() HTTP helper, importable without Streamlit
    llm.py                  # unchanged
    system_prompt.py        # unchanged
  tests/
    test_api_client.py      # new: tests for send_message()
    test_api.py             # unchanged
    test_llm.py             # unchanged
  requirements.txt          # add streamlit, requests
  .env.example               # add API_BASE_URL
  README.md                 # add "Streamlit UI" section
```

`send_message` is extracted into `petebot4/api_client.py` rather than
living in `app.py` itself. Importing `app.py` for a test would execute its
top-level Streamlit calls (`st.title`, `st.chat_input`, ...) outside a real
Streamlit runtime, which is unreliable to assert against. Keeping the
testable HTTP logic in a plain module — importable with no Streamlit
side effects — mirrors how `petebot4/llm.py` is already kept independent
of `api.py`.

## `app.py` Design

- Reads `API_KEY` and `API_BASE_URL` (default `http://localhost:8000`) from
  `.env` via `python-dotenv`, same `.env` file the REST API already uses.
- `st.session_state.messages: list[dict]` holds the on-screen conversation
  (`{"role": "user"|"assistant", "content": str}`), display-only. It is
  never sent back to the server — each `/chat` call sends only the current
  message, since the REST API is single-turn by design.
- `st.chat_input` collects the user's message; on submit it's appended to
  session state, rendered, then passed to `send_message`.
- The actual HTTP call lives in `petebot4/api_client.py`:

  ```python
  def send_message(message: str, api_base_url: str, api_key: str) -> dict:
      response = requests.post(
          f"{api_base_url}/chat",
          json={"message": message},
          headers={"X-API-Key": api_key},
          timeout=35,
      )
      response.raise_for_status()
      return response.json()
  ```

  Raises `requests.HTTPError` on non-2xx (401/422/500) and
  `requests.ConnectionError`/`requests.Timeout` on network failures — all
  handled by `app.py`. `app.py` imports it as
  `from petebot4.api_client import send_message`.
- The Streamlit rendering loop calls `send_message` and catches:
  - `requests.HTTPError` — shows the server's `error` field (or the raw
    body) as a chat error bubble.
  - `requests.ConnectionError` — shows "서버에 연결할 수 없습니다. api.py가
    실행 중인지 확인하세요."
  - `requests.Timeout` — shows "응답이 지연되고 있습니다. 잠시 후 다시
    시도해주세요."
  - Any of these leave the chat usable — the app never crashes on a bad
    call, and the user's message stays visible so they can retry.
- On success, the assistant's reply is rendered as a chat bubble, with the
  `model` field from the response shown as a small caption underneath (e.g.
  "openai/gpt-oss-20b"), consistent with the REST API always surfacing the
  model name.

## Testing

`tests/test_api_client.py` mocks `requests.post` (no real network, no
Streamlit runtime) and tests only `send_message`:

- Success: returns the parsed `{"reply": ..., "model": ...}` dict.
- 401 response: `send_message` raises `requests.HTTPError`.
- 500 response: `send_message` raises `requests.HTTPError`.
- Connection refused: `send_message` raises `requests.ConnectionError`.

The Streamlit rendering/session-state code itself is not unit tested,
matching the existing pattern in the sibling `petebot-test`/`p_chatbot`
projects, where Streamlit UI code is verified manually rather than via
pytest.

## Out of Scope

- No conversation history sent to the server (single-turn API is
  unchanged).
- No new REST API changes.
- No authentication UI (API key is read from `.env`, not entered in the
  browser).
- No deployment/hosting changes — local `streamlit run` only.
