import os
import re
import requests
import time
import fitz  # PyMuPDF
import docx
import json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

BASE_URL = "https://sfn-am.ru"
SAVE_DIR_RAW = "data/raw"
SAVE_DIR_CLEAN = "data/clean"

# Страницы, которые стоит скачать
TARGET_PATHS = [
    "/",                            # Главная
    "/company/faq",                 # FAQ
    "/funds",                       # ЗПИФ
    "/articles",                    # Статьи
    "/company",                     # О компании
    "/company/news",                # Новости
    "/disclosure",                  # Документы
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
    "Referer": "https://google.com",
}

os.makedirs(SAVE_DIR_RAW, exist_ok=True)
os.makedirs(SAVE_DIR_CLEAN, exist_ok=True)

def extract_text_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        text = "\n".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        print(f"[!] Ошибка при чтении PDF {filepath}: {e}")
        return ""

def extract_text_from_docx(filepath):
    try:
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        print(f"[!] Ошибка при чтении DOCX {filepath}: {e}")
        return ""

def sanitize_filename(path: str) -> str:
    """Преобразует URL-путь в безопасное имя файла"""
    # Заменяем / -> _
    filename = path.strip("/").replace("/", "_") or "home"
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # Удаляем нежелательные блоки
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "button", "a"]):
        tag.decompose()

    # Удаляем скрытые (например, aria-hidden)
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        tag.decompose()

    # Оставим заголовки и абзацы
    lines = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(strip=True)
        if text:
            lines.append(text)

    return "\n".join(lines)

def get_internal_links(html, base_path):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        # Только внутренние и внутри текущего раздела
        if href.startswith("/") and href.startswith(base_path):
            links.add(href)
    return links

def crawl_section(section_path):
    visited = set()

    def crawl(path):
        if path in visited:
            return
        visited.add(path)

        full_url = urljoin(BASE_URL, path)
        print(f"Fetching: {full_url}")

        try:
            session = requests.Session()
            session.headers.update(HEADERS)

            response = session.get(full_url)
            # response = requests.get(full_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[!] Failed to fetch {full_url}: {e}")
            return

        content_type = response.headers.get("Content-Type", "")
        page_name = sanitize_filename(path)

        # Если PDF
        if "application/pdf" in content_type or path.endswith(".pdf"):
            filepath = f"{SAVE_DIR_RAW}/{page_name}.pdf"
            if not os.path.exists(filepath):
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"Saved PDF: {filepath}")
            text = extract_text_from_pdf(filepath)
            if text:
                with open(f"{SAVE_DIR_CLEAN}/{page_name}.txt", "w", encoding="utf-8") as f:
                    f.write(text)
            time.sleep(5)
            return

        # Если DOCX
        if "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in content_type or path.endswith(".docx"):
            filepath = f"{SAVE_DIR_RAW}/{page_name}.docx"
            if not os.path.exists(filepath):
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"Saved DOCX: {filepath}")
            text = extract_text_from_docx(filepath)
            if text:
                with open(f"{SAVE_DIR_CLEAN}/{page_name}.txt", "w", encoding="utf-8") as f:
                    f.write(text)
            time.sleep(5)
            return

        # Сохраняем HTML
        filepath_html = f"{SAVE_DIR_RAW}/{page_name}.html"
        with open(filepath_html, "w", encoding="utf-8") as f:
            f.write(response.text)

        # Сохраняем очищенный текст
        text = clean_text(response.text)
        with open(f"{SAVE_DIR_CLEAN}/{page_name}.txt", "w", encoding="utf-8") as f:
            f.write(text)

        # сохраняем метаинформацию
        meta = {
            "url": full_url,
            "path": filepath_html,
            "timestamp": datetime.now().isoformat()
        }

        with open(f"{SAVE_DIR_CLEAN}/{page_name}.meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Находим вложенные ссылки
        sublinks = get_internal_links(response.text, section_path)
        for link in sublinks:
            crawl(link)

    crawl(section_path)

if __name__ == "__main__":
    print("Start parsing SFN site...")
    for path in tqdm(TARGET_PATHS):
        crawl_section(path)
    print("Parsing complete.")
