# Архитектура RAG-чат-бота для СФН

## Цель

RAG-чат-бот создан для ответов на вопросы инвесторов на основе документов и статей с сайта [https://sfn-am.ru](https://sfn-am.ru).

---

## Состав системы

### Парсер сайта (src\data_pipeline\build_knowledge_base.py)

* Парсит HTML, PDF, DOCX из заданных разделов.
* Сохраняет:

    * сырой HTML/файлы в `data/raw/`
    * очищенные `.txt` в `data/clean/`
    * `.meta.json` файл с URL и временем обработки

### 2. FAISS-индексация (src/data_pipeline/build_faiss_index.py)

* Разбивает тексты на чанки (5 предложений)
* Получает эмбеддинги через `sentence-transformers`
* Сохраняет:

    * `faiss.index`
    * `metadata.jsonl` с URL, timestamp, текстом и путём

### 3. RAG-пайплайн (src/rag_pipeline.py)

* Ищет релевантные чанки по FAISS
* Собирает контекст
* Передаёт в GigaChat (OpenAI-style API)
* Выдаёт ответ + список источников

### 4. GigaChat-клиент (src/llm_client_gigachat.py)

* Автоматически получает OAuth2 `access_token`
* Кэширует его до 30 минут
* Посылает ChatCompletion-запрос

### 5. FastAPI (src/api/main.py)

* GET `/ask?query=...`
* Возвращает:

    * `answer`, `sources[]`
* С Swagger UI `/docs`
* Проводит фильтрацию вопросов
* Логгирует в `logs/queries.jsonl`

### 6. Telegram-бот (src/telegram/bot.py)

* Работает через `python-telegram-bot`
* `/start` — приветствие
* Сообщения вызывают API `/ask`
* Экранирует MarkdownV2
* Фильтрует мусор

### 7. Фильтры (src/utils/filters.py)

* Сообщения типа `123`, `....`, `/reset` отклоняются

### 8. Логгирование (src/utils/logger.py)

* `logs/queries.jsonl` для аудита всех запросов

---

## Структура проекта

```
project/
├── data/
│   ├── raw/           # HTML, PDF, DOCX
│   └── clean/         # .txt + .meta.json
├── src/
│   ├── data_pipeline/
│   │   ├── build_knowledge_base.py
│   │   └── build_faiss_index.py
│   ├── rag_pipeline.py
│   ├── llm_client_gigachat.py
│   ├── api/
│   │   └── main.py
│   ├── telegram/
│   │   └── bot.py
│   └── utils/
│       ├── filters.py
│       └── logger.py
├── logs/
│   └── queries.jsonl
├── requirements.txt
├── README.md
└── .env
```

---

## Расширяемость

* Telegram inline / голосовые запросы
* Streamlit/веб-интерфейс
* SQLite/граф документов
* Сессии для Telegram/автодополнение
* Дописать проверку дубликатов с использованием хэш-функций
* Создать docker-compose для разворачивания в инфраструктуре
* Доработать до полноценного пайплайна для тестирования разных подходов
  (разные LLM, эмбеддеры, БД, промты и т.д.)
* Заменить FAISS на Qdrant или Weaviate при росте данных
* Использовать LangChain, LlamaIndex для гибкости
* Добавить user feedback loop (для активного обучения)
* Кэшировать частые запросы
* Логировать ошибки и запросы (Prometheus/Grafana)
* Обучить или дообучить модель эмбеддинга под домен
