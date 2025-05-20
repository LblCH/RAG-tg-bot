import os
import json
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("logs/queries.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_interaction(query: str, answer: str, sources: list, source: str = "api", user_id: str = None):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "answer": answer,
        "sources": sources,
        "source": source,
        "user_id": user_id
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")