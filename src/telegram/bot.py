import os
import sys
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from telegram.helpers import escape_markdown
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.logger import log_interaction
from utils.filters import is_valid_query

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://localhost:8000/ask")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "*Добро пожаловать в SFN Chatbot!*\n\n"
        "Я ИИ-бот, который помогает найти ответы на вопросы об инвестициях, паевых фондах и работе компании *ООО «СФН»*.\n\n"
        "Просто отправьте мне ваш вопрос, например:\n"
        "— Что такое инвестиционный пай?\n"
        "— Как вернуть средства из ЗПИФ?\n"
        "— Нужно ли проходить тест перед покупкой паёв?\n\n"
        "Я найду информацию в базе знаний и постараюсь ответить максимально точно.\n"
        "Если возникнут проблемы — напишите разработчику. Удачи!"
    )
    safe_welcome_text = escape_markdown(welcome_text, version=2)
    await update.message.reply_markdown_v2(safe_welcome_text)

# === Обработка запроса ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Пожалуйста, отправьте текст вопроса.")
        return

    if not is_valid_query(query):
        await update.message.reply_text("Пожалуйста, сформулируйте более конкретный вопрос.")
        return

    try:
        response = requests.get(API_ENDPOINT, params={"query": query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        answer = data.get("answer", "Нет ответа.")
        sources = data.get("sources", [])
        escaped_answer = escape_markdown(answer, version=2)
        escaped_sources = [escape_markdown(s["url"], version=2) for s in sources]
        source_text = "\n".join([f"🔗 {s}" for s in escaped_sources]) if sources else ""

        reply = f"*Ответ:*\n{escaped_answer}\n\n*Источники:*\n{source_text}"
        log_interaction(
            query=query,
            answer=answer,
            sources=[s["url"] for s in sources],
            source="telegram",
            user_id=update.effective_user.id
        )
        await update.message.reply_markdown_v2(reply)
    except Exception as e:
        logger.exception("Ошибка при обработке запроса")
        await update.message.reply_text("Произошла ошибка при получении ответа. Попробуйте позже.")

# === Запуск бота ===
if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN в .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram-бот запущен")
    app.add_handler(CommandHandler("start", start_command))
    app.run_polling()
