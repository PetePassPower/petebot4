import logging
import os
import secrets
from typing import Literal

# 추가
import requests
import json

# 추가



from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from petebot4.llm import DISPLAY_MODEL, get_reply
from petebot4.web_ui import render_chat_page

load_dotenv()

# 추가
AI_DEFENSE_API_URL = "https://us.api.inspect.aidefense.security.cisco.com/api/v1/inspect/chat"
AI_DEFENSE_API_KEY = os.getenv("AI_DEFENSE_API_KEY")
# 추가

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is required to start the API")

API_KEY_BYTES = API_KEY.encode("utf-8")

if not os.getenv("OPENROUTER_API_KEY"):
    raise RuntimeError("OPENROUTER_API_KEY environment variable is required to start the API")

logger = logging.getLogger(__name__)

app = FastAPI(title="petebot4", docs_url=None, redoc_url=None, openapi_url=None)


MAX_HISTORY_MESSAGES = 6  # 3 turns of (user, assistant)


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[HistoryMessage] = Field(default_factory=list)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8", "surrogateescape"), API_KEY_BYTES
    ):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.get("/", response_class=HTMLResponse)
def index():
    return render_chat_page(API_KEY)


@app.post("/chat")
def chat(body: ChatRequest, _: None = Depends(verify_api_key)):
    history = [
        {"role": h.role, "content": h.content} for h in body.history[-MAX_HISTORY_MESSAGES:]
    ]
#입력검사
    payload = json.dumps({"messages": history + [{"role": "user", "content": body.message}]})
    headers = {"Content-Type": "application/json", "X-Cisco-AI-Defense-API-Key": AI_DEFENSE_API_KEY}
    response = requests.post(AI_DEFENSE_API_URL, headers=headers, data=payload)
    if not response.json().get("is_safe", True):
        return JSONResponse(status_code=400, content={"error": "message blocked by AI Defense"})
#입력검사




    try:
        reply = get_reply(body.message, history=history)
    except Exception:
        logger.exception("get_reply failed")
        return JSONResponse(status_code=500, content={"error": "internal error"})

#출력검사
    payload = json.dumps({"messages": history + [
        {"role": "user", "content": body.message},
        {"role": "assistant", "content": reply},
    ]})
    headers = {"Content-Type": "application/json", "X-Cisco-AI-Defense-API-Key": AI_DEFENSE_API_KEY}
    response = requests.post(AI_DEFENSE_API_URL, headers=headers, data=payload)
    if not response.json().get("is_safe", True):
        reply = "죄송합니다, 이 응답은 보안 정책에 의해 차단되었습니다."
#출력검사


        

    return {"reply": reply, "model": DISPLAY_MODEL}
