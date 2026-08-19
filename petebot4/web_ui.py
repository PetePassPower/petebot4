import json

CHAT_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>petebot4</title>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    max-width: 720px;
    margin: 40px auto;
    padding: 0 16px;
    color: #1a1a2e;
  }
  h1 { font-size: 1.75rem; margin-bottom: 24px; }
  #messages { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
  .bubble { padding: 12px 16px; border-radius: 12px; max-width: 80%; white-space: pre-wrap; }
  .user { align-self: flex-end; background: #e94560; color: #fff; }
  .assistant { align-self: flex-start; background: #f2f2f7; }
  .error { align-self: flex-start; background: #fdecea; color: #b3261e; }
  .model-caption { font-size: 0.75rem; color: #888; margin-top: 4px; align-self: flex-start; }
  #input-row { display: flex; gap: 8px; }
  #message-input {
    flex: 1;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid #ddd;
    font-size: 1rem;
  }
  #send-button {
    padding: 12px 20px;
    border-radius: 8px;
    border: none;
    background: #e94560;
    color: #fff;
    font-size: 1rem;
    cursor: pointer;
  }
  #send-button:disabled { opacity: 0.5; cursor: default; }
</style>
</head>
<body>
<h1>petebot4</h1>
<div id="messages"></div>
<div id="input-row">
  <input id="message-input" type="text" placeholder="메시지를 입력하세요" autocomplete="off">
  <button id="send-button">보내기</button>
</div>
<script>
const API_KEY = __API_KEY_JSON__;
const MAX_HISTORY_TURNS = 3;
const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("message-input");
const buttonEl = document.getElementById("send-button");
let conversationHistory = [];

function addBubble(role, text) {
  const bubble = document.createElement("div");
  bubble.className = "bubble " + role;
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  return bubble;
}

function addCaption(text) {
  const caption = document.createElement("div");
  caption.className = "model-caption";
  caption.textContent = text;
  messagesEl.appendChild(caption);
}

async function sendMessage() {
  const message = inputEl.value.trim();
  if (!message) return;

  addBubble("user", message);
  inputEl.value = "";
  inputEl.disabled = true;
  buttonEl.disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({ message: message, history: conversationHistory }),
    });

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      data = null;
    }

    if (!response.ok) {
      const detail = data && data.error ? data.error : "요청에 실패했습니다.";
      addBubble("error", "오류가 발생했습니다: " + detail);
    } else {
      addBubble("assistant", data.reply);
      if (data.model) addCaption(data.model);
      conversationHistory.push({ role: "user", content: message });
      conversationHistory.push({ role: "assistant", content: data.reply });
      conversationHistory = conversationHistory.slice(-MAX_HISTORY_TURNS * 2);
    }
  } catch (networkError) {
    addBubble("error", "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.");
  } finally {
    inputEl.disabled = false;
    buttonEl.disabled = false;
    inputEl.focus();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

buttonEl.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", function (event) {
  if (event.key === "Enter") sendMessage();
});
</script>
</body>
</html>
"""


def render_chat_page(api_key: str) -> str:
    return CHAT_PAGE_TEMPLATE.replace("__API_KEY_JSON__", json.dumps(api_key))
