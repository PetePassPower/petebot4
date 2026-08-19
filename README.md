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

## Tests

```bash
python -m pytest tests/ -v
```
