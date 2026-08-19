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
