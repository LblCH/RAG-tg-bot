# SFN RAG Chatbot

ИИ-чат-бот на базе Retrieval-Augmented Generation (RAG), обученный на базе знаний с сайта.
Отвечает на вопросы пользователей на основе информации, представленной на сайте.

## Функционал

- Парсинг информации с сайта SFN
- Индексация базы знаний с помощью FAISS
- Генерация ответов на естественном языке с помощью LLM (GigaChat или BART)
- API-интерфейс через FastAPI
- (опционально) Telegram-бот
- Обработка ошибок и fallback'ов
- Архитектура и рекомендации по масштабированию

---

## Установка

```bash
git clone https://github.com/LblCH/sfn-rag-chatbot.git
cd sfn-rag-chatbot
python -m venv venv
source venv/bin/activate   # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```
## Настройка переменных окружения
Создайте .env в корне проекта:

```env
GIGACHAT_AUTH_KEY=Basic ваш_ключ
```

## Использование

🔹 1. Подготовка базы знаний
```bash
python src/data_pipeline/build_knowledge_base.py
python src/data_pipeline/build_faiss_index.py
```
Скрипт:
- парсит сайт
- очищает текст
- разбивает его на чанки
- сохраняет эмбеддинги в FAISS-индексе

🔹 2. Запуск FastAPI
```bash
uvicorn src.api.main:app --reload
```
API будет доступно по адресу:
```bash
http://localhost:8000/ask?query=Что такое инвестиционный пай?
```
либо
```bash
http://localhost:8000/docs - SwaggerUI
```
🔹 3. Пример запроса
```bash
curl "http://localhost:8000/ask?query=Как вернуть средства из ЗПИФ?"
```
Ответ:

```json
{
"answer": "Паи розничных фондов ООО «СФН» можно реализовать на вторичном рынке...",
"sources": [
   {
      "url": "https://sfn-am.ru/company_faq",
      "timestamp": "2025-05-20T03:20:49.409428"
   },
   {
      "url": "https://sfn-am.ru/company_faq_query=выплата",
      "timestamp": "2025-05-20T03:20:52.374407"
   },
   {
      "url": "https://sfn-am.ru/company_faq_query=доход",
      "timestamp": "2025-05-20T03:20:55.349514"
   }
   ]
}
```

🔹 4. (Опционально) Запуск Telegram-бота
Создать бота через BotFather, сохранить токен и добавь его в .env:

```env
TELEGRAM_TOKEN=...
```
```bash
python src/telegram/bot.py
```

## Архитектура
Визуальная схема: docs/architecture.png
### Основные компоненты:
- FAISS: быстрый поиск релевантных фрагментов
- LLM: генерация ответа на основе вопроса + контекста
- FastAPI: простой REST-интерфейс
- Telegram (опционально): диалоговый интерфейс

## TO DO:
- Использовать Qdrant или Weaviate вместо FAISS при росте базы
- ~~Добавить обработку pdf и docx~~
- Добавить query-классификатор (напр. "дивиденды", "покупка паёв")
- Подключить логирование и сбор метрик (например, Prometheus + Grafana)
- Кэшировать часто задаваемые вопросы
- Поддержка мультиязычности (RU/EN)

## Примеры запросов
1. Что такое инвестиционный пай?
   → Инвестиционный пай — это ценная бумага...
2. Как вернуть средства из ЗПИФ?
   → Паи розничных фондов ООО «СФН» можно реализовать...
3. Нужно ли проходить тест перед покупкой паёв?
   → Тест из семи вопросов доступен в Сбербанк Онлайн...
