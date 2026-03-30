import os
import random
import logging
import httpx
from datetime import time
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, JobQueue
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Токены (задаются через переменные окружения) ───────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── 50 МАК карт ────────────────────────────────────────────────────────
MAK_CARDS = [
    {"name": "Одинокое дерево", "emoji": "🌳", "theme": "одиночество и сила"},
    {"name": "Бушующее море", "emoji": "🌊", "theme": "эмоции и хаос"},
    {"name": "Закрытая дверь", "emoji": "🚪", "theme": "границы и возможности"},
    {"name": "Горящая свеча", "emoji": "🕯️", "theme": "надежда и свет"},
    {"name": "Разорванная нить", "emoji": "🧵", "theme": "связи и потери"},
    {"name": "Цветок в трещине", "emoji": "🌸", "theme": "стойкость и рост"},
    {"name": "Туманный лес", "emoji": "🌫️", "theme": "неизвестность и страх"},
    {"name": "Пустая клетка", "emoji": "🪤", "theme": "свобода и ограничения"},
    {"name": "Два зеркала", "emoji": "🪞", "theme": "отражение и самопознание"},
    {"name": "Мост над пропастью", "emoji": "🌉", "theme": "переход и решения"},
    {"name": "Засохший росток", "emoji": "🌱", "theme": "усилия и результат"},
    {"name": "Полная луна", "emoji": "🌕", "theme": "цикличность и завершённость"},
    {"name": "Разбитое зеркало", "emoji": "💔", "theme": "боль и трансформация"},
    {"name": "Тихая гавань", "emoji": "⚓", "theme": "безопасность и покой"},
    {"name": "Переплетённые корни", "emoji": "🌿", "theme": "семья и связь"},
    {"name": "Падающий лист", "emoji": "🍂", "theme": "отпускание и принятие"},
    {"name": "Звёздное небо", "emoji": "✨", "theme": "мечты и ориентиры"},
    {"name": "Лабиринт", "emoji": "🌀", "theme": "поиск пути и замешательство"},
    {"name": "Распускающийся бутон", "emoji": "🌺", "theme": "развитие и потенциал"},
    {"name": "Сломанный мост", "emoji": "🪵", "theme": "разрыв и восстановление"},
    {"name": "Маска", "emoji": "🎭", "theme": "роли и подлинность"},
    {"name": "Тихая вода", "emoji": "💧", "theme": "спокойствие и глубина"},
    {"name": "Горная вершина", "emoji": "⛰️", "theme": "цели и достижения"},
    {"name": "Пустая колыбель", "emoji": "🌙", "theme": "потери и желания"},
    {"name": "Два пути", "emoji": "🛤️", "theme": "выбор и сомнения"},
    {"name": "Солнечный луч", "emoji": "☀️", "theme": "радость и тепло"},
    {"name": "Тёмная нора", "emoji": "🕳️", "theme": "страхи и укрытие"},
    {"name": "Танцующая фигура", "emoji": "💃", "theme": "свобода и выражение"},
    {"name": "Раскрытые ладони", "emoji": "🤲", "theme": "доверие и принятие"},
    {"name": "Буря на горизонте", "emoji": "⛈️", "theme": "тревога и предчувствие"},
    {"name": "Домик в горах", "emoji": "🏡", "theme": "уют и одиночество"},
    {"name": "Сжатый кулак", "emoji": "✊", "theme": "контроль и сила"},
    {"name": "Плывущая лодка", "emoji": "🚣", "theme": "движение и независимость"},
    {"name": "Спящий ребёнок", "emoji": "👶", "theme": "уязвимость и невинность"},
    {"name": "Огонь", "emoji": "🔥", "theme": "страсть и разрушение"},
    {"name": "Осколки стекла", "emoji": "🔮", "theme": "хрупкость и красота"},
    {"name": "Объятия", "emoji": "🤗", "theme": "близость и поддержка"},
    {"name": "Пустая дорога", "emoji": "🛣️", "theme": "одиночество и свобода"},
    {"name": "Переполненный стакан", "emoji": "🥂", "theme": "предел и наполненность"},
    {"name": "Зимний лес", "emoji": "❄️", "theme": "оцепенение и тишина"},
    {"name": "Прыжок в воду", "emoji": "🏊", "theme": "риск и решительность"},
    {"name": "Птица в полёте", "emoji": "🕊️", "theme": "свобода и уход"},
    {"name": "Якорь на дне", "emoji": "⚓", "theme": "привязанность и стабильность"},
    {"name": "Расцветающий сад", "emoji": "🌻", "theme": "забота и рост"},
    {"name": "Пустой стул", "emoji": "🪑", "theme": "отсутствие и ожидание"},
    {"name": "Волчья стая", "emoji": "🐺", "theme": "принадлежность и инстинкты"},
    {"name": "Раскрытая книга", "emoji": "📖", "theme": "знание и история"},
    {"name": "Упавшая корона", "emoji": "👑", "theme": "власть и потеря статуса"},
    {"name": "Гнездо без птиц", "emoji": "🪺", "theme": "пустое место и уход"},
    {"name": "Переплетённые руки", "emoji": "🤝", "theme": "союз и взаимозависимость"},
]

# ─── Генерация послания через Claude API ────────────────────────────────
async def generate_message(card: dict) -> str:
    prompt = f"""Ты — мудрый психолог и проводник. Клиент вытянул МАК карту.

Карта: «{card['name']}» {card['emoji']}
Тема карты: {card['theme']}

Напиши короткое психологическое послание для клиента (3-4 предложения):
- Начни с наблюдения об образе карты
- Дай мягкий вопрос для размышления
- Заверши тёплым посланием-поддержкой
- Пиши на «ты», тепло и без психологического жаргона
- Не упоминай название карты в тексте"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = response.json()
            return data["content"][0]["text"]
    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return "Сегодня эта карта говорит тебе: остановись и прислушайся к себе. Что ты чувствуешь прямо сейчас?"


# ─── Отправка карты ──────────────────────────────────────────────────────
async def send_card(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    card = random.choice(MAK_CARDS)
    message_text = await generate_message(card)

    text = (
        f"🎴 *Карта дня*\n\n"
        f"*«{card['name']}»* {card['emoji']}\n\n"
        f"{message_text}\n\n"
        f"─────────────────\n"
        f"_Напиши /card чтобы вытянуть новую карту_"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown"
    )


# ─── Обработчики команд ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌸 *Добро пожаловать в МАК-бот Ольги Сазыкиной*\n\n"
        "Здесь ты можешь вытянуть карту дня и получить послание от своего подсознания.\n\n"
        "Команды:\n"
        "🎴 /card — вытянуть карту прямо сейчас\n"
        "🔔 /subscribe — получать карту каждое утро в 9:00\n"
        "🔕 /unsubscribe — отписаться от рассылки\n\n"
        "_Просто нажми /card и доверься выбору_ ✨"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔮 Тяну карту для тебя...")
    await send_card(update.effective_chat.id, context)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if jobs:
        await update.message.reply_text("🔔 Ты уже подписан на карту дня!")
        return

    context.job_queue.run_daily(
        callback=lambda ctx: send_card(chat_id, ctx),
        time=time(hour=9, minute=0),
        name=str(chat_id),
        chat_id=chat_id,
    )
    await update.message.reply_text(
        "✅ Отлично! Каждое утро в *9:00* ты будешь получать карту дня 🌸",
        parse_mode="Markdown"
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if not jobs:
        await update.message.reply_text("Ты не подписан на рассылку.")
        return
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("🔕 Рассылка отключена. Ты всегда можешь вернуться 💛")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card", card_command))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    logger.info("Бот запущен ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
