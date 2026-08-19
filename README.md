# petebot4

OpenAI의 공개형(open-weight) 모델 `gpt-oss-20b`를 OpenRouter 무료 티어로 호출하는
FastAPI 기반 챗봇입니다. REST API와 브라우저 채팅 화면이 하나의 서버(하나의 URL)로
함께 제공됩니다.

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

브라우저에서 `http://localhost:8000`을 열면 채팅 화면이 나옵니다.

## Web UI

`GET /`에서 제공되는 채팅 화면입니다. 최근 3턴(사용자+챗봇 대화 6개 메시지)을
브라우저가 기억해서 매 요청마다 함께 보내므로, 바로 전 대화 맥락을 이어서
답변합니다. 페이지의 JavaScript는 같은 서버의 `/chat`을 호출하며, 이때 필요한
`X-API-Key` 값은 서버가 페이지를 렌더링할 때 `.env`의 `API_KEY`를 그대로
심어서 내려줍니다.

> **주의:** 이 방식은 페이지 소스를 보면 누구나 `API_KEY` 값을 확인할 수
> 있습니다 — 외부에서 `/chat`을 직접 호출하는 것과 사실상 동일한 수준의
> 보호입니다. 우발적인 남용을 막는 정도이지, 강한 보안 경계는 아닙니다.

## REST API

text-to-text `/chat` 엔드포인트입니다. 서버 자체는 대화 이력을 저장하지
않는 무상태(stateless) API이며, 맥락을 이어가려면 호출하는 쪽에서 최근 대화를
`history`로 함께 보내야 합니다. 매 응답에 사용된 모델 이름도 함께 반환됩니다.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <.env의 API_KEY 값>" \
  -d '{
    "message": "내 이름이 뭐라고 했지?",
    "history": [
      {"role": "user", "content": "내 이름은 민준이야"},
      {"role": "assistant", "content": "네, 민준님! 기억할게요."}
    ]
  }'
# -> {"reply": "...", "model": "openai/gpt-oss-20b"}
```

`history`는 선택 항목이며(생략하면 단일 턴으로 동작), `role`은 `user` 또는
`assistant`만 허용됩니다. 최근 3턴(6개 메시지)을 넘겨 보내도 서버가 마지막
6개만 사용하도록 자릅니다.

`X-API-Key`가 없거나 틀리면 401, `message`가 없거나 빈 문자열이면 422,
`history`의 `role`이 `user`/`assistant`가 아니면 422를 반환합니다.

## Deploy (Render)

`render.yaml`을 사용해 [Render](https://render.com)의 무료 웹 서비스 티어에
배포할 수 있습니다. REST API와 Web UI가 같은 서비스에서 함께 제공되므로
서비스는 하나만 있으면 됩니다.

1. 이 저장소를 GitHub에 올립니다.
2. Render 대시보드에서 "New" → "Blueprint"로 이 저장소를 연결하면
   `render.yaml`을 자동으로 인식합니다.
3. `OPENROUTER_API_KEY`, `API_KEY` 환경변수 값을 Render 대시보드에서
   직접 입력합니다(`render.yaml`에는 값이 들어있지 않습니다).
4. 배포가 끝나면 `https://<서비스명>.onrender.com`이 Web UI, 같은 주소의
   `/chat`이 REST API 엔드포인트입니다.

무료 티어는 일정 시간 요청이 없으면 슬립 상태가 되어 첫 요청 응답이
느릴 수 있습니다.

## Tests

```bash
python -m pytest tests/ -v
```
