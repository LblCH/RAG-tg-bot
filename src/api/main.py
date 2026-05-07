from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag_pipeline import answer_query
from utils.logger import log_interaction
from utils.filters import is_valid_query

# Настройка логгера
logger = logging.getLogger(__name__)

app = FastAPI(title="SFN RAG Chatbot API", version="1.0")

# БЕЗОПАСНОСТЬ: Ограниченный CORS для продакшена
# В продакшене замените на конкретные домены
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Ограничено разрешёнными доменами
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Только необходимые методы
    allow_headers=["Content-Type", "Authorization"],  # Только необходимые заголовки
)

class Source(BaseModel):
    url: str = Field(..., description="URL источника", max_length=2048)
    timestamp: str = Field(..., description="Временная метка источника")

class AnswerResponse(BaseModel):
    answer: str = Field(..., description="Ответ на вопрос", max_length=10000)
    sources: List[Source] = Field(default_factory=list, description="Список источников")

@app.get("/ask", response_model=AnswerResponse)
async def ask(query: str = Query(..., description="Вопрос пользователя", min_length=5, max_length=2000)):
    # Валидация запроса на уровне API
    if not query or len(query.strip()) < 5:
        raise HTTPException(status_code=400, detail="Вопрос слишком короткий")
    
    # Проверка на потенциально опасные символы (базовая защита от инъекций)
    if any(char in query for char in ['\x00', '\n', '\r', '\t']):
        raise HTTPException(status_code=400, detail="Вопрос содержит недопустимые символы")
    
    if not is_valid_query(query):
        return AnswerResponse(answer="Пожалуйста, задайте осмысленный вопрос.", sources=[])

    try:
        result = answer_query(query)
    except FileNotFoundError as e:
        logger.error(f"Файл индекса или метаданных не найден: {e}")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен")
    except Exception as e:
        logger.exception(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

    log_interaction(
        query=query,
        answer=result["answer"],
        sources=[s["url"] for s in result["sources"]],
        source="api"
    )

    return result
