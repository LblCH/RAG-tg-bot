import os
import time
import requests
from typing import Optional
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# Переменные можно загрузить из .env
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")  # строка вида: Basic <base64(client_id:secret)>
assert GIGACHAT_AUTH_KEY, "Не задан GIGACHAT_AUTH_KEY"

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Кэш токена
access_token = None
token_expiry = 0  # unixtime

def get_access_token() -> str:
    global access_token, token_expiry

    # Проверка: если токен ещё жив, возвращаем
    if access_token and time.time() < token_expiry - 30:
        return access_token

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": 'cb4becfd-9369-42eb-9f2d-0e9c46a01f5f',
        "Authorization": GIGACHAT_AUTH_KEY
    }
    data = {"scope": "GIGACHAT_API_PERS"}

    try:
        response = requests.request("POST", OAUTH_URL, headers=headers, data=data, verify=False)
        response.raise_for_status()
        resp_json = response.json()

        access_token = resp_json["access_token"]
        expires_in = int(resp_json.get("expires_in", 1800))  # обычно 1800 сек
        token_expiry = time.time() + expires_in

        return access_token
    except Exception as e:
        print(f"[!] Ошибка получения токена: {e}")
        return None

def generate_answer_with_gigachat(query: str, context: str) -> str:
    token = get_access_token()
    if not token:
        return "Ошибка авторизации в GigaChat."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": 'Ты сотрудник ООО "СФН", помощник по инвестициям.'
                                      'Отвечай достаточно подробно, точно, немного формально, по делу, не забывая упоминать о преимуществах твоей компании.'},
        {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {query}"}
    ]

    payload = {
        "model": "GigaChat:latest",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1000
    }

    try:
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[!] Ошибка запроса к GigaChat: {e}")
        return "Ошибка генерации ответа от модели."

