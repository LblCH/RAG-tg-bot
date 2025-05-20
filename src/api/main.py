from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag_pipeline import answer_query
from utils.logger import log_interaction
from utils.filters import is_valid_query

app = FastAPI(title="SFN RAG Chatbot API", version="1.0")

# Разрешим CORS для локальной отладки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде — ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Source(BaseModel):
    url: str
    timestamp: str

class AnswerResponse(BaseModel):
    answer: str
    sources: List[Source]

@app.get("/ask", response_model=AnswerResponse)
async def ask(query: str = Query(..., description="Вопрос пользователя")):
    if not is_valid_query(query):
        return AnswerResponse(answer="Пожалуйста, задайте осмысленный вопрос.", sources=[])

    result = answer_query(query)

    log_interaction(
        query=query,
        answer=result["answer"],
        sources=[s["url"] for s in result["sources"]],
        source="api"
    )

    return result
