import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from pathlib import Path
from llm_client_gigachat import generate_answer_with_gigachat

# === CONFIG ===
INDEX_PATH = Path("data/index/faiss.index")
METADATA_PATH = Path("data/index/metadata.jsonl")
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 5

# === ЗАГРУЗКА МОДЕЛИ И ИНДЕКСА ===
model = SentenceTransformer(EMBED_MODEL_NAME)
index = faiss.read_index(str(INDEX_PATH))

with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = [json.loads(line) for line in f]

assert len(metadata) == index.ntotal, "Несовпадение количества чанков и метаданных"

# === ПОИСК ===
def retrieve_relevant_chunks(query: str, top_k: int = TOP_K) -> List[Dict]:
    query_vec = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vec, top_k)

    chunks = []
    for idx in indices[0]:
        if idx < len(metadata):
            chunks.append(metadata[idx])
    return chunks

def build_prompt(query: str, chunks: List[Dict]) -> str:
    context = "\n".join([f"- {ch['chunk_text']}" for ch in chunks])
    return query, context

def answer_query(query: str) -> Dict:
    chunks = retrieve_relevant_chunks(query)
    query, context = build_prompt(query, chunks)
    output = generate_answer_with_gigachat(query, context)

    return {
        "answer": output.strip(),
        "sources": [
            {
                "url": chunk["source_url"],
                "timestamp": chunk["timestamp"]
            } for chunk in chunks
        ]
    }

if __name__ == "__main__":
    q = "Что такое инвестиционный пай?"
    result = answer_query(q)

    print("Ответ:", result["answer"])
    print("Источники:")
    for src in result["sources"]:
        print(f" - {src['url']}")