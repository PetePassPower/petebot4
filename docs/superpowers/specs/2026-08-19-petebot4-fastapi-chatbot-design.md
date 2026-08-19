# petebot4 — FastAPI Chatbot on gpt-oss (OpenRouter free tier) Design

## Purpose

A minimal FastAPI service exposing a single-turn, text-to-text REST endpoint
backed by OpenAI's open-weight `gpt-oss-20b` model, accessed for free via
OpenRouter. Each response includes the model name that produced it. No UI —
API only.

## Architecture

```
petebot4/
  api.py                  # FastAPI app, /chat endpoint, API key auth
  petebot4/
    __init__.py
    llm.py                # OpenRouter client wrapper, chat_completion()
    system_prompt.py      # SYSTEM_PROMPT constant
  tests/
    test_api.py
    test_llm.py
  requirements.txt
  pyproject.toml
  .env.example
  .gitignore
  README.md
```

## Model

- Model id: `openai/gpt-oss-20b:free`
- Provider: OpenRouter (OpenAI-compatible API)
  - `base_url = "https://openrouter.ai/api/v1"`
  - `api_key = OPENROUTER_API_KEY` (env var)
- `DEFAULT_MODEL = "openai/gpt-oss-20b:free"` constant in `petebot4/llm.py`,
  reused for both the API call and the value returned to the client.
- The model name reported to the client is the display form
  `"openai/gpt-oss-20b"` (the `:free` suffix is an OpenRouter routing tag,
  not part of the model's identity, so it is stripped before returning it to
  callers).

## Endpoint: `POST /chat`

- Header: `X-API-Key: <API_KEY>` — required.
- Request body: `{"message": "<text>"}` (`message` non-empty string).
- Success response (200): `{"reply": "<text>", "model": "openai/gpt-oss-20b"}`
- Errors:
  - Missing/invalid `X-API-Key` → 401 `{"error": "invalid or missing API key"}`
  - Missing/empty `message` → 422 (FastAPI/Pydantic validation default body)
  - LLM call raises → 500 `{"error": "internal error"}` (exception logged
    server-side, not leaked to the client)
- No conversation history is stored or accepted; every request is
  independent (single-turn).

## Data Flow

1. Client sends `POST /chat` with `X-API-Key` header and JSON body.
2. `verify_api_key` dependency compares the header against `API_KEY` env var
   using `secrets.compare_digest`; raises `HTTPException(401)` on mismatch.
3. `Pydantic` validates `message` is present and non-empty (`min_length=1`);
   FastAPI returns 422 automatically otherwise.
4. `api.py` calls `llm.get_reply(message)`.
5. `llm.get_reply` builds `[system_prompt, user_message]`, calls the
   OpenRouter chat completions endpoint with `DEFAULT_MODEL`, and returns the
   reply text.
6. `api.py` wraps the reply and the display model name into the response
   body.
7. Any exception from step 4–5 is caught in `api.py`, logged via
   `logger.exception`, and converted to a 500 with a generic error body.

## Environment / Config

`.env` (not committed) holds:

```
OPENROUTER_API_KEY=your-openrouter-api-key-here
API_KEY=your-chat-api-key-here
```

At startup, `api.py` raises `RuntimeError` if either `API_KEY` or
`OPENROUTER_API_KEY` is missing, so the service fails fast instead of
silently accepting requests it can't serve.

## Error Handling

- A shared `HTTPException` handler formats all HTTP errors as
  `{"error": "<detail>"}` for a consistent error shape.
- LLM/network failures are caught explicitly around the `get_reply` call so
  a provider outage returns a clean 500 instead of an unhandled traceback.

## Testing

`tests/test_api.py` (FastAPI `TestClient`, `llm.get_reply` mocked via
`unittest.mock.patch`):

- No API key → 401
- Wrong API key → 401
- Valid key + valid message → 200, body contains both `reply` and
  `model: "openai/gpt-oss-20b"`
- Missing `message` field → 422
- Empty `message` string → 422
- `get_reply` raises → 500, generic error body, no stack trace leaked
- Missing `API_KEY` env var at import time → `RuntimeError`
- Missing `OPENROUTER_API_KEY` env var at import time → `RuntimeError`

`tests/test_llm.py` (OpenRouter client mocked, no real network calls):

- `chat_completion` sends the system prompt + user message and returns the
  model's reply text.
- `get_reply` returns the reply text produced by `chat_completion`.

## Out of Scope

- No Streamlit or other UI (REST API only, per request).
- No conversation history / session state.
- No rate limiting beyond OpenRouter's own free-tier limits.
- No deployment/hosting setup — local `uvicorn` run only, matching
  petebot-test's REST API section.
