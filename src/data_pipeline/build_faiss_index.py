import json
from pathlib import Path
from datetime import datetime
import faiss
from sentence_transformers import SentenceTransformer
import nltk
from nltk.tokenize import sent_tokenize

# === CONFIG ===
TEXT_DIR = Path("data/clean")
OUTPUT_DIR = Path("data/index")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_FILE = OUTPUT_DIR / "metadata.jsonl"
FAISS_INDEX_FILE = OUTPUT_DIR / "faiss.index"

CHUNK_SIZE = 5  # предложений на чанк
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# === LOAD MODEL ===
print("Загрузка модели эмбеддингов...")
model = SentenceTransformer(MODEL_NAME)

# === ЧАНКИНГ ===
def chunk_text_semantic(text, chunk_size=CHUNK_SIZE):
    sentences = sent_tokenize(text, language="russian")
    chunks = []
    for i in range(0, len(sentences), chunk_size):
        chunk = " ".join(sentences[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks

# === ПОДГОТОВКА ===
index = None
metadata = []
dim = None

def process_file(filepath):
    print(f"Обработка: {filepath.name}")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        url_line = lines[0].strip() if lines and lines[0].startswith("[URL]") else ""
        source_url = url_line.replace("[URL] ", "") if url_line else "unknown"
        text = "".join(lines[1:] if url_line else lines)

    chunks = chunk_text_semantic(text)

    embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)

    global index, dim
    if index is None:
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)

    index.add(embeddings)

    # Формируем метаданные
    meta_path = filepath.with_suffix(".meta.json")
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        source_url = meta.get("url", "unknown")
        timestamp = meta.get("timestamp", datetime.now().isoformat())
    else:
        source_url = "unknown"
        timestamp = datetime.now().isoformat()
    full_doc_link = f"/data/raw/{filepath.stem}"  # путь до оригинала

    for chunk_text in chunks:
        metadata.append({
            "chunk_text": chunk_text,
            "source_url": source_url,
            "full_document_path": full_doc_link,
            "timestamp": timestamp
        })

# === MAIN ===
if __name__ == "__main__":
    nltk.download("punkt_tab")

    all_txt_files = sorted(TEXT_DIR.glob("*.txt"))
    for path in all_txt_files:
        process_file(path)

    print("Сохраняем FAISS-индекс и метаданные...")

    faiss.write_index(index, str(FAISS_INDEX_FILE))

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        for item in metadata:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Завершено. Индекс: {FAISS_INDEX_FILE}, метаданные: {METADATA_FILE}")
