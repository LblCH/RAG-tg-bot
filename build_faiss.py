import json
import numpy as np
import faiss
import re
import hashlib
from pathlib import Path
from typing import List, Tuple, Set
from sentence_transformers import SentenceTransformer
import pandas as pd
from tqdm import tqdm
import logging
import nltk

nltk.download('punkt')
from nltk.tokenize import sent_tokenize

# === Конфигурация логирования ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === Настройки ===
DATA_FILE = "webcrawler/output.json"
MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500  # Максимальная длина чанка в символах
MIN_CHUNK_LENGTH = 50
FAISS_DIR = Path("faiss_index")

# === Функции ===
def split_text_semantically(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Разбивает текст на семантически цельные чанки по предложениям"""
    sentences = sent_tokenize(text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current += sentence + " "
        else:
            if len(current.strip()) >= MIN_CHUNK_LENGTH:
                chunks.append(current.strip())
            current = sentence + " "
    if len(current.strip()) >= MIN_CHUNK_LENGTH:
        chunks.append(current.strip())
    return chunks

def compute_hash(text: str) -> str:
    """Вычисляет SHA256-хеш от текста"""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def load_chunks_from_json(filepath: str) -> Tuple[List[str], List[dict]]:
    """Загружает текст из JSON, делает нарезку на чанки и фильтрует дубликаты"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks, metadata = [], []
    seen_hashes: Set[str] = set()

    for entry in data:
        url = entry.get('url')
        text = entry.get('text', '').strip()
        if not text:
            continue
        for i, chunk in enumerate(split_text_semantically(text)):
            if len(chunk) < MIN_CHUNK_LENGTH:
                continue
            chunk_hash = compute_hash(chunk)
            if chunk_hash in seen_hashes:
                continue
            seen_hashes.add(chunk_hash)
            chunks.append(chunk)
            metadata.append({
                "url": url,
                "chunk_index": i,
                "hash": chunk_hash,
                "text": chunk
            })
    return chunks, metadata

def embed_chunks(chunks: List[str], model: SentenceTransformer) -> np.ndarray:
    """Генерация эмбеддингов"""
    return model.encode(
        chunks,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Создание FAISS индекса"""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index

def save_index(index: faiss.Index, metadata: List[dict], path: Path = FAISS_DIR):
    """Сохраняет индекс и метаданные"""
    path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path / "index.faiss"))
    with open(path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

def main():
    logger.info("Загрузка и обработка данных...")
    chunks, metadata = load_chunks_from_json(DATA_FILE)
    logger.info(f"Получено {len(chunks)} уникальных чанков")

    logger.info("Загрузка модели эмбеддингов...")
    model = SentenceTransformer(MODEL_NAME)

    logger.info("Генерация эмбеддингов...")
    embeddings = embed_chunks(chunks, model)

    logger.info("Построение FAISS индекса...")
    index = build_faiss_index(embeddings)

    logger.info("Сохранение индекса и метаданных...")
    save_index(index, metadata)
    logger.info("Готово.")

if __name__ == "__main__":
    main()