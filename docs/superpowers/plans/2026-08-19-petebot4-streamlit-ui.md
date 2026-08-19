# petebot4 Streamlit UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Streamlit chat UI (`app.py`) that calls the existing `petebot4` REST API (`api.py`) over HTTP, so the chatbot is usable interactively in a browser.

**Architecture:** `petebot4/api_client.py` holds a small testable `send_message()` HTTP helper; `app.py` is a thin Streamlit rendering layer that imports it. Two independent processes (`uvicorn api:app`, `streamlit run app.py`).

**Tech Stack:** Streamlit, `requests`, existing FastAPI service (unchanged).

## Global Constraints

- `app.py` must not import `petebot4.llm` directly — it talks to `api.py` only over HTTP (from spec).
- Each `/chat` call sends only the current message — no conversation history sent to the server (from spec).
- `API_KEY` and `API_BASE_URL` (default `http://localhost:8000`) are read from `.env` via `python-dotenv` (from spec).
- Every assistant reply displays the `model` field from the API response (from spec).
- `send_message` signature: `send_message(message: str, api_base_url: str, api_key: str) -> dict`, using a 35-second timeout (from spec).

---

### Task 1: HTTP client helper (`petebot4/api_client.py`)

**Files:**
- Create: `petebot4/api_client.py`
- Test: `tests/test_api_client.py`

**Interfaces:**
- Consumes: nothing (calls the REST API defined in `api.py` at runtime, no import-time dependency on it).
- Produces: `petebot4.api_client.send_message(message: str, api_base_url: str, api_key: str) -> dict`, used by Task 2's `app.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_api_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'petebot4.api_client'`.

- [ ] **Step 3: Implement `petebot4/api_client.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api_client.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add petebot4/api_client.py tests/test_api_client.py
git commit -m "feat: add send_message HTTP client for the Streamlit UI"
```

---

### Task 2: Streamlit UI (`app.py`) and project config

**Files:**
- Create: `app.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Consumes: `petebot4.api_client.send_message(message: str, api_base_url: str, api_key: str) -> dict` (from Task 1).
- Produces: nothing consumed by other tasks (final task); `app.py` is run directly via `streamlit run app.py`, not imported by tests.

- [ ] **Step 1: Implement `app.py`**

```python
import os

import requests
import streamlit as st
from dotenv import load_dotenv

from petebot4.api_client import send_message

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.title("petebot4")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("model"):
            st.caption(msg["model"])

user_input = st.chat_input("메시지를 입력하세요")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        try:
            result = send_message(user_input, API_BASE_URL, API_KEY)
            reply = result["reply"]
            model = result.get("model")
            st.write(reply)
            if model:
                st.caption(model)
            st.session_state.messages.append(
                {"role": "assistant", "content": reply, "model": model}
            )
        except requests.ConnectionError:
            error_text = "서버에 연결할 수 없습니다. api.py가 실행 중인지 확인하세요."
            st.error(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
        except requests.Timeout:
            error_text = "응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요."
            st.error(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
        except requests.HTTPError as exc:
            try:
                detail = exc.response.json().get("error", exc.response.text)
            except ValueError:
                detail = exc.response.text
            error_text = f"오류가 발생했습니다: {detail}"
            st.error(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
```

This file is not unit tested (matches the sibling `petebot-test`/`p_chatbot`
projects' pattern of verifying Streamlit UI code manually).

- [ ] **Step 2: Add `streamlit` and `requests` to `requirements.txt`**

Append these two lines to the existing `requirements.txt`:

```
streamlit>=1.32
requests>=2.31
```

- [ ] **Step 3: Add `API_BASE_URL` to `.env.example`**

Append this line to the existing `.env.example`:

```
API_BASE_URL=http://localhost:8000
```

- [ ] **Step 4: Add a "Streamlit UI" section to `README.md`**

Insert this section into `README.md`, directly after the existing "## REST API" section and before "## Tests":

```markdown
## Streamlit UI

REST API 위에 브라우저 채팅 화면을 제공합니다. `api.py`가 먼저 실행 중이어야
합니다.

```bash
uvicorn api:app --host 127.0.0.1 --port 8000   # 별도 터미널에서 REST API 실행
streamlit run app.py
```

`.env`의 `API_KEY`를 그대로 사용하며, REST API 주소는 `API_BASE_URL`
(기본값 `http://localhost:8000`)로 설정할 수 있습니다. 화면에는 이전 대화가
계속 표시되지만, 서버에는 매번 현재 메시지만 전송됩니다(단일 턴 API).
```

- [ ] **Step 5: Install new dependencies and run the full test suite**

Run: `pip install -r requirements.txt`
Run: `python -m pytest tests/ -v`
Expected: PASS (15 existing + 4 from Task 1 = 19 tests; Task 2 adds no new tests).

- [ ] **Step 6: Commit**

```bash
git add app.py requirements.txt .env.example README.md
git commit -m "feat: add Streamlit chat UI calling the /chat REST API"
```

- [ ] **Step 7: Manual verification**

```bash
uvicorn api:app --host 127.0.0.1 --port 8000 &
streamlit run app.py
```

Open the printed local URL, send a message, and confirm: the reply appears,
the model name (`openai/gpt-oss-20b`) is shown as a caption, and stopping
`api.py` before sending a message produces the "서버에 연결할 수 없습니다"
error instead of a crash.
