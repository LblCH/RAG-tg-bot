import json
import sys
from pathlib import Path
from datetime import datetime
import faiss
from sentence_transformers import SentenceTransformer
import nltk
from nltk.tokenize import sent_tokenize
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# === CONFIG ===
TEXT_DIR = Path("data/clean")
OUTPUT_DIR = Path("data/index")
METADATA_FILE = OUTPUT_DIR / "metadata.jsonl"
FAISS_INDEX_FILE = OUTPUT_DIR / "faiss.index"

CHUNK_SIZE = 5  # предложений на чанк
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# === БЕЗОПАСНОСТЬ: Валидация путей ===
def validate_path(path: Path, base_dir: Path) -> bool:
    """Проверяет, что путь находится внутри базовой директории (защита от path traversal)"""
    try:
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        return str(resolved_path).startswith(str(resolved_base))
    except Exception:
        return False

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

def process_file(filepath: Path):
    """Обрабатывает файл с валидацией пути и обработкой ошибок"""
    # БЕЗОПАСНОСТЬ: проверка пути
    if not validate_path(filepath, TEXT_DIR):
        logger.error(f"Попытка доступа к файлу вне базовой директории: {filepath}")
        return
    
    print(f"Обработка: {filepath.name}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        logger.error(f"Файл не найден: {filepath}")
        return
    except PermissionError:
        logger.error(f"Нет прав на чтение файла: {filepath}")
        return
    except UnicodeDecodeError as e:
        logger.error(f"Ошибка кодировки файла {filepath}: {e}")
        return
    except Exception as e:
        logger.error(f"Ошибка чтения файла {filepath}: {e}")
        return
    
    if not lines:
        logger.warning(f"Пустой файл: {filepath}")
        return
        
    url_line = lines[0].strip() if lines and lines[0].startswith("[URL]") else ""
    source_url = url_line.replace("[URL] ", "") if url_line else "unknown"
    text = "".join(lines[1:] if url_line else lines)

    chunks = chunk_text_semantic(text)
    
    if not chunks:
        logger.warning(f"Не удалось создать чанки из файла: {filepath}")
        return

    embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)

    global index, dim
    if index is None:
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)

    index.add(embeddings)

    # Формируем метаданные
    meta_path = filepath.with_suffix(".meta.json")
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            source_url = meta.get("url", "unknown")
            timestamp = meta.get("timestamp", datetime.now().isoformat())
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Ошибка чтения метаданных {meta_path}: {e}")
            timestamp = datetime.now().isoformat()
    else:
        timestamp = datetime.now().isoformat()
    
    # БЕЗОПАСНОСТЬ: валидация пути к документу
    full_doc_link = f"/data/raw/{filepath.stem}"

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
    
    # БЕЗОПАСНОСТЬ: создание директорий с проверкой
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Ошибка создания директории {OUTPUT_DIR}: {e}")
        sys.exit(1)

    all_txt_files = sorted(TEXT_DIR.glob("*.txt"))
    
    if not all_txt_files:
        logger.warning(f"Не найдено файлов для обработки в {TEXT_DIR}")
    
    for path in all_txt_files:
        process_file(path)

    if index is None or index.ntotal == 0:
        logger.error("Индекс пуст. Невозможно сохранить.")
        sys.exit(1)

    print("Сохраняем FAISS-индекс и метаданные...")
    
    try:
        faiss.write_index(index, str(FAISS_INDEX_FILE))
    except Exception as e:
        logger.error(f"Ошибка сохранения индекса: {e}")
        sys.exit(1)

    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            for item in metadata:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except IOError as e:
        logger.error(f"Ошибка сохранения метаданных: {e}")
        sys.exit(1)

    print(f"Завершено. Индекс: {FAISS_INDEX_FILE}, метаданные: {METADATA_FILE}")
