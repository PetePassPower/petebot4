import os

from openai import OpenAI

from petebot4.system_prompt import SYSTEM_PROMPT

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b:free"
DISPLAY_MODEL = "openai/gpt-oss-20b"


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=30.0, max_retries=1)


def chat_completion(client, system_prompt: str, user_input: str, model: str = DEFAULT_MODEL) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content
    if not content:
        raise ValueError("model returned empty content")
    return content


def get_reply(user_message: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    client = get_client(api_key)
    return chat_completion(client, SYSTEM_PROMPT, user_message)
