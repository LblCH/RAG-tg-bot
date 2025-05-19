from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import faiss
import json
import numpy as np
import logging
from typing import List

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === Конфигурация ===
INDEX_PATH = "faiss_index/index.faiss"
METADATA_PATH = "faiss_index/metadata.json"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

# === Инициализация приложения ===
app = FastAPI(
    title="FAISS Search API",
    description="Сервис поиска по эмбеддингам с использованием FAISS и SentenceTransformer",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# === Загрузка модели, индекса и метаданных ===
try:
    logger.info("Загрузка модели эмбеддингов и индекса FAISS")
    model = SentenceTransformer(MODEL_NAME)
    index = faiss.read_index(INDEX_PATH)

    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    chunks = [m.get("text", "") for m in metadata]

except Exception as e:
    logger.error(f"Ошибка инициализации системы: {str(e)}")
    raise

# === Модели запросов и ответов ===
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Поисковый запрос")
    top_k: int = Field(default=TOP_K, ge=1, le=20, description="Количество релевантных результатов")

class SearchResult(BaseModel):
    text: str
    url: str
    score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

class ErrorResponse(BaseModel):
    error: str
    code: int

# === Основной эндпоинт поиска ===
@app.post("/search", response_model=SearchResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
def search(req: SearchRequest):
    try:
        logger.info(f"Выполняется поиск для запроса: {req.query}")
        query_embedding = model.encode([req.query], normalize_embeddings=True).astype(np.float32)
        distances, indices = index.search(query_embedding, k=req.top_k)

        results = []
        for rank, idx in enumerate(indices[0]):
            results.append(SearchResult(
                text=chunks[idx][:1000],
                url=metadata[idx].get("url", "-"),
                score=float(distances[0][rank])
            ))

        return SearchResponse(query=req.query, results=results)

    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

# === Главная страница ===
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# === Глобальная обработка ошибок ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.status_code},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Внутренняя ошибка сервера", "code": 500},
    )

# === Запуск локального сервера ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
