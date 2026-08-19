# petebot4 FastAPI Chatbot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build petebot4, a FastAPI service exposing a single-turn text-to-text `/chat` REST endpoint backed by OpenAI's open-weight `gpt-oss-20b` model via OpenRouter's free tier, with the model name included in every response.

**Architecture:** Two Python modules — `petebot4/llm.py` (OpenRouter client wrapper) and `api.py` (FastAPI app, auth, error handling) — plus project config/docs. No UI.

**Tech Stack:** Python, FastAPI, uvicorn, `openai` SDK (used as an OpenAI-compatible client against OpenRouter), python-dotenv, pytest, httpx (FastAPI `TestClient` dependency).

## Global Constraints

- Model id for API calls: `openai/gpt-oss-20b:free` (from spec).
- Model id shown to clients: `openai/gpt-oss-20b` (from spec).
- OpenRouter base URL: `https://openrouter.ai/api/v1` (from spec).
- Env vars: `OPENROUTER_API_KEY`, `API_KEY` — both required at startup, else `RuntimeError` (from spec).
- Auth: `X-API-Key` header, compared with `secrets.compare_digest` (from spec).
- Single-turn only — no server-side conversation history (from spec).
- `HTTPException`-based errors (401, 500) return `{"error": "<detail>"}`; 422 validation errors keep FastAPI/Pydantic's default body shape (from spec — this is a deliberate carve-out, not an omission).
- No Streamlit or other UI (from spec).

---

### Task 1: LLM wrapper module (`petebot4/llm.py`)

**Files:**
- Create: `petebot4/__init__.py`
- Create: `petebot4/system_prompt.py`
- Create: `petebot4/llm.py`
- Test: `tests/test_llm.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `petebot4.llm.DEFAULT_MODEL: str` = `"openai/gpt-oss-20b:free"`
  - `petebot4.llm.DISPLAY_MODEL: str` = `"openai/gpt-oss-20b"`
  - `petebot4.llm.get_client(api_key: str) -> OpenAI`
  - `petebot4.llm.chat_completion(client, system_prompt: str, user_input: str, model: str = DEFAULT_MODEL) -> str`
  - `petebot4.llm.get_reply(user_message: str) -> str` — reads `OPENROUTER_API_KEY` from env, used by Task 2's `api.py`.
  - `petebot4.system_prompt.SYSTEM_PROMPT: str`

- [ ] **Step 1: Create package files and empty test dirs**

Create `petebot4/__init__.py` (empty file).

Create `tests/__init__.py` (empty file).

Create `petebot4/system_prompt.py`:

```python
SYSTEM_PROMPT = """당신은 "petebot4"라는 이름의 친근한 챗봇입니다.
사용자의 질문에 한국어로 간결하고 정확하게 답변하세요.
모르는 내용은 모른다고 솔직하게 말하세요.
"""
```

- [ ] **Step 2: Write the failing tests for `petebot4/llm.py`**

Create `tests/test_llm.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'petebot4.llm'` (or `ImportError`).

- [ ] **Step 4: Implement `petebot4/llm.py`**

```python
import os

from openai import OpenAI

from petebot4.system_prompt import SYSTEM_PROMPT

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b:free"
DISPLAY_MODEL = "openai/gpt-oss-20b"


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


def chat_completion(client, system_prompt: str, user_input: str, model: str = DEFAULT_MODEL) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def get_reply(user_message: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    client = get_client(api_key)
    return chat_completion(client, SYSTEM_PROMPT, user_message)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_llm.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add petebot4/__init__.py petebot4/system_prompt.py petebot4/llm.py tests/__init__.py tests/test_llm.py
git commit -m "feat: add OpenRouter gpt-oss-20b client wrapper"
```

---

### Task 2: FastAPI app (`api.py`)

**Files:**
- Create: `api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `petebot4.llm.get_reply(user_message: str) -> str`, `petebot4.llm.DISPLAY_MODEL: str` (from Task 1).
- Produces:
  - `api.app` — the FastAPI instance, importable for `TestClient(app)` and for `uvicorn api:app`.
  - `POST /chat` endpoint: request `{"message": str}`, response `{"reply": str, "model": str}` on success.

- [ ] **Step 1: Write the failing tests for `api.py`**

Create `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api'`.

- [ ] **Step 3: Implement `api.py`**

```python
import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from petebot4.llm import DISPLAY_MODEL, get_reply

load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is required to start the API")

if not os.getenv("OPENROUTER_API_KEY"):
    raise RuntimeError("OPENROUTER_API_KEY environment variable is required to start the API")

logger = logging.getLogger(__name__)

app = FastAPI(title="petebot4", docs_url=None, redoc_url=None, openapi_url=None)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.post("/chat")
def chat(body: ChatRequest, _: None = Depends(verify_api_key)):
    try:
        reply = get_reply(body.message)
    except Exception:
        logger.exception("get_reply failed")
        return JSONResponse(status_code=500, content={"error": "internal error"})

    return {"reply": reply, "model": DISPLAY_MODEL}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add api.py tests/test_api.py
git commit -m "feat: add /chat FastAPI endpoint with API key auth"
```

---

### Task 3: Project config and docs

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Consumes: `api.py` (Task 2), `petebot4/llm.py` (Task 1) — referenced only in run/curl instructions, no code interface.
- Produces: nothing consumed by other tasks (final task).

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi>=0.115
uvicorn>=0.30
openai>=1.0
python-dotenv>=1.0
pytest>=7.0
httpx>=0.27
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

- [ ] **Step 3: Create `.env.example`**

```
OPENROUTER_API_KEY=your-openrouter-api-key-here
API_KEY=your-chat-api-key-here
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
.pytest_cache/
```

- [ ] **Step 5: Create `README.md`**

```markdown
# petebot4

OpenAI의 공개형(open-weight) 모델 `gpt-oss-20b`를 OpenRouter 무료 티어로 호출하는
FastAPI 기반 text-to-text 챗봇 REST API입니다.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# .env를 열어 OPENROUTER_API_KEY(OpenRouter에서 무료 발급)와
# API_KEY(원하는 값으로 직접 지정)를 채워주세요.
```

## Run

```bash
uvicorn api:app --host 127.0.0.1 --port 8000
```

## REST API

단일 턴 text-to-text `/chat` 엔드포인트입니다. 서버는 대화 이력을 저장하지 않으며,
매 응답에 사용된 모델 이름이 함께 반환됩니다.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <.env의 API_KEY 값>" \
  -d '{"message": "안녕"}'
# -> {"reply": "...", "model": "openai/gpt-oss-20b"}
```

`X-API-Key`가 없거나 틀리면 401, `message`가 없거나 빈 문자열이면 422를 반환합니다.

## Tests

```bash
python -m pytest tests/ -v
```
```

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: PASS (all tests from Task 1 and Task 2).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pyproject.toml .env.example .gitignore README.md
git commit -m "chore: add project config, env template, and README"
```

- [ ] **Step 8: Manual smoke test (requires a real free OpenRouter API key)**

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env: set OPENROUTER_API_KEY to a real key from https://openrouter.ai/keys
#            set API_KEY to any value you choose
uvicorn api:app --host 127.0.0.1 --port 8000 &
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY value from .env>" \
  -d '{"message": "hello"}'
```

Expected: JSON response with a non-empty `reply` and `"model": "openai/gpt-oss-20b"`.
