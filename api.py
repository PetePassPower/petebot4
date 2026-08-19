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

API_KEY_BYTES = API_KEY.encode("utf-8")

if not os.getenv("OPENROUTER_API_KEY"):
    raise RuntimeError("OPENROUTER_API_KEY environment variable is required to start the API")

logger = logging.getLogger(__name__)

app = FastAPI(title="petebot4", docs_url=None, redoc_url=None, openapi_url=None)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8", "surrogateescape"), API_KEY_BYTES
    ):
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
