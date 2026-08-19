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

## Deploy (Render)

`render.yaml`을 사용해 [Render](https://render.com)의 무료 웹 서비스 티어에
REST API(`api.py`)와 Streamlit UI(`app.py`)를 각각 별도 서비스로 배포할 수
있습니다. FastAPI와 Streamlit은 서로 다른 서버 프로세스라 하나의 URL로
합칠 수는 없지만, `render.yaml` 하나로 두 서비스를 한 번에 관리합니다.

1. 이 저장소를 GitHub에 올립니다.
2. Render 대시보드에서 "New" → "Blueprint"로 이 저장소를 연결하면
   `render.yaml`의 두 서비스(`petebot4`, `petebot4-ui`)를 자동으로 인식합니다.
3. 환경변수 값을 Render 대시보드에서 직접 입력합니다(`render.yaml`에는 값이
   들어있지 않습니다):
   - `petebot4` 서비스: `OPENROUTER_API_KEY`, `API_KEY`
   - `petebot4-ui` 서비스: `API_KEY`(위와 같은 값)
4. 배포가 끝나면:
   - REST API: `https://petebot4.onrender.com/chat`
   - Streamlit UI: `https://petebot4-ui.onrender.com`
   - UI는 `API_BASE_URL`(`render.yaml`에 이미 배포된 API 주소로 설정됨)을
     통해 자동으로 REST API를 호출합니다.

무료 티어는 일정 시간 요청이 없으면 슬립 상태가 되어 첫 요청 응답이
느릴 수 있습니다.

## Tests

```bash
python -m pytest tests/ -v
```
