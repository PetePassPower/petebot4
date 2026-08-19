# petebot4 — Unify REST API and UI into One Service Design

## Purpose

Collapse the two-service setup (`api.py` REST API + separate `app.py`
Streamlit UI, deployed as two Render services) into a single FastAPI
service that serves both the `/chat` REST endpoint and a browser chat page
at `/`. One process, one URL.

## Architecture

- `api.py` gains a new `GET /` route returning an HTML chat page
  (`text/html`), served alongside the existing `POST /chat` (unchanged
  contract: `X-API-Key` auth, `{"message": ...}` → `{"reply": ..., "model":
  ...}`).
- The page's JavaScript calls `/chat` on the same origin via `fetch`. Since
  `/chat` still requires `X-API-Key`, the server embeds the running
  service's `API_KEY` value into the rendered HTML/JS at request time.
  **Trade-off (explicitly accepted):** this key is visible to anyone who
  views the page source — equivalent in practice to calling the external
  API directly, not a stronger protection. It stops accidental/opportunistic
  abuse, not a determined caller with browser dev tools.
- The Streamlit UI (`app.py`, `petebot4/api_client.py`,
  `tests/test_api_client.py`) is removed entirely, along with the
  `petebot4-ui` Render service and `streamlit`/`requests` from
  `requirements.txt`. One UI going forward.

```
petebot4/
  api.py                  # modified: adds GET /
  petebot4/
    web_ui.py              # new: renders the chat page HTML
    llm.py                  # unchanged
    system_prompt.py        # unchanged
  app.py                    # deleted
  petebot4/api_client.py    # deleted
  tests/
    test_api.py             # modified: add GET / test
    test_api_client.py      # deleted
    test_llm.py              # unchanged
  requirements.txt          # streamlit, requests removed
  render.yaml                # petebot4-ui service removed
  README.md                  # Streamlit section replaced with Web UI section
```

## `petebot4/web_ui.py` Design

```python
import json

CHAT_PAGE_TEMPLATE = """<!doctype html>
... (full markup, see plan) ...
"""


def render_chat_page(api_key: str) -> str:
    return CHAT_PAGE_TEMPLATE.replace("__API_KEY_JSON__", json.dumps(api_key))
```

`json.dumps` safely produces a valid JS string literal regardless of the
key's exact characters (quotes, backslashes), avoiding any injection issue
even though the key is developer-controlled, not user input.

## `api.py` Changes

```python
from fastapi.responses import HTMLResponse
from petebot4.web_ui import render_chat_page

@app.get("/", response_class=HTMLResponse)
def index():
    return render_chat_page(API_KEY)
```

`docs_url`/`redoc_url`/`openapi_url` stay disabled — unrelated to this
route, no schema exposure regardless.

## Page Behavior

- Single-turn, client-side-only conversation display (same as the removed
  Streamlit UI): messages render in a scrolling list, but each `/chat` call
  sends only the current message.
- On success: render the assistant's reply plus the `model` field as a
  caption underneath.
- On failure (non-2xx `fetch` response, or a network error): render an
  error bubble with the server's `error` field when available, otherwise a
  generic "요청에 실패했습니다" message. The page never throws an unhandled
  JS error that breaks the input box.

## Testing

`tests/test_api.py` gains one new test: `GET /` returns 200,
`Content-Type: text/html`, and the body contains the configured `API_KEY`
value (proves the page is actually wired to the running service's key, not
a hardcoded placeholder).

The page's client-side JavaScript itself is not unit tested (same
rationale as the removed Streamlit code: no Python test runner exercises
browser JS). Manual verification in a real browser after implementation
is required before calling this done.

## Deployment

- `render.yaml` keeps only the single `petebot4` web service — no code
  change needed there beyond removing the `petebot4-ui` entry, since `/`
  is now part of the same FastAPI app already being deployed.
- The existing `petebot4-ui.onrender.com` Render service must be deleted
  by the human partner in the Render dashboard (deleting a cloud resource
  is not something Claude does autonomously) after this change is live.

## Out of Scope

- No login/session-based auth for the browser page — the accepted
  trade-off above stands.
- No visual redesign beyond a minimal, functional chat layout.
- No change to `/chat`'s existing contract, error shapes, or auth model.
