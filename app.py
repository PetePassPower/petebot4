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
