import os
import random
import logging
import httpx
import io
from datetime import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, JobQueue
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Токены (задаются через переменные окружения) ───────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── Шрифт ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = str(BASE_DIR / "fonts" / "DejaVuSans-Bold.ttf")
FONT_REGULAR_PATH = str(BASE_DIR / "fonts" / "DejaVuSans.ttf")

def find_fonts():
    """Проверяет наличие шрифтов."""
    if Path(FONT_PATH).exists():
        logger.info(f"Шрифт найден: {FONT_PATH}")
    else:
        logger.warning(f"Шрифт не найден: {FONT_PATH}")

# ─── 50 МАК карт ────────────────────────────────────────────────────────
MAK_CARDS = [
    {"name": "Одинокое дерево", "emoji": "🌳", "theme": "одиночество и сила", "color": "#2D5016"},
    {"name": "Бушующее море", "emoji": "🌊", "theme": "эмоции и хаос", "color": "#0D47A1"},
    {"name": "Закрытая дверь", "emoji": "🚪", "theme": "границы и возможности", "color": "#5D4037"},
    {"name": "Горящая свеча", "emoji": "🕯️", "theme": "надежда и свет", "color": "#E65100"},
    {"name": "Разорванная нить", "emoji": "🧵", "theme": "связи и потери", "color": "#6A1B9A"},
    {"name": "Цветок в трещине", "emoji": "🌸", "theme": "стойкость и рост", "color": "#AD1457"},
    {"name": "Туманный лес", "emoji": "🌫️", "theme": "неизвестность и страх", "color": "#37474F"},
    {"name": "Пустая клетка", "emoji": "🪤", "theme": "свобода и ограничения", "color": "#4E342E"},
    {"name": "Два зеркала", "emoji": "🪞", "theme": "отражение и самопознание", "color": "#283593"},
    {"name": "Мост над пропастью", "emoji": "🌉", "theme": "переход и решения", "color": "#1565C0"},
    {"name": "Засохший росток", "emoji": "🌱", "theme": "усилия и результат", "color": "#33691E"},
    {"name": "Полная луна", "emoji": "🌕", "theme": "цикличность и завершённость", "color": "#1A237E"},
    {"name": "Разбитое зеркало", "emoji": "💔", "theme": "боль и трансформация", "color": "#B71C1C"},
    {"name": "Тихая гавань", "emoji": "⚓", "theme": "безопасность и покой", "color": "#006064"},
    {"name": "Переплетённые корни", "emoji": "🌿", "theme": "семья и связь", "color": "#1B5E20"},
    {"name": "Падающий лист", "emoji": "🍂", "theme": "отпускание и принятие", "color": "#BF360C"},
    {"name": "Звёздное небо", "emoji": "✨", "theme": "мечты и ориентиры", "color": "#0D47A1"},
    {"name": "Лабиринт", "emoji": "🌀", "theme": "поиск пути и замешательство", "color": "#4A148C"},
    {"name": "Распускающийся бутон", "emoji": "🌺", "theme": "развитие и потенциал", "color": "#880E4F"},
    {"name": "Сломанный мост", "emoji": "🪵", "theme": "разрыв и восстановление", "color": "#3E2723"},
    {"name": "Маска", "emoji": "🎭", "theme": "роли и подлинность", "color": "#311B92"},
    {"name": "Тихая вода", "emoji": "💧", "theme": "спокойствие и глубина", "color": "#01579B"},
    {"name": "Горная вершина", "emoji": "⛰️", "theme": "цели и достижения", "color": "#455A64"},
    {"name": "Пустая колыбель", "emoji": "🌙", "theme": "потери и желания", "color": "#1A237E"},
    {"name": "Два пути", "emoji": "🛤️", "theme": "выбор и сомнения", "color": "#4E342E"},
    {"name": "Солнечный луч", "emoji": "☀️", "theme": "радость и тепло", "color": "#E65100"},
    {"name": "Тёмная нора", "emoji": "🕳️", "theme": "страхи и укрытие", "color": "#212121"},
    {"name": "Танцующая фигура", "emoji": "💃", "theme": "свобода и выражение", "color": "#C62828"},
    {"name": "Раскрытые ладони", "emoji": "🤲", "theme": "доверие и принятие", "color": "#00695C"},
    {"name": "Буря на горизонте", "emoji": "⛈️", "theme": "тревога и предчувствие", "color": "#263238"},
    {"name": "Домик в горах", "emoji": "🏡", "theme": "уют и одиночество", "color": "#33691E"},
    {"name": "Сжатый кулак", "emoji": "✊", "theme": "контроль и сила", "color": "#B71C1C"},
    {"name": "Плывущая лодка", "emoji": "🚣", "theme": "движение и независимость", "color": "#0277BD"},
    {"name": "Спящий ребёнок", "emoji": "👶", "theme": "уязвимость и невинность", "color": "#6A1B9A"},
    {"name": "Огонь", "emoji": "🔥", "theme": "страсть и разрушение", "color": "#D84315"},
    {"name": "Осколки стекла", "emoji": "🔮", "theme": "хрупкость и красота", "color": "#4527A0"},
    {"name": "Объятия", "emoji": "🤗", "theme": "близость и поддержка", "color": "#AD1457"},
    {"name": "Пустая дорога", "emoji": "🛣️", "theme": "одиночество и свобода", "color": "#37474F"},
    {"name": "Переполненный стакан", "emoji": "🥂", "theme": "предел и наполненность", "color": "#827717"},
    {"name": "Зимний лес", "emoji": "❄️", "theme": "оцепенение и тишина", "color": "#546E7A"},
    {"name": "Прыжок в воду", "emoji": "🏊", "theme": "риск и решительность", "color": "#00838F"},
    {"name": "Птица в полёте", "emoji": "🕊️", "theme": "свобода и уход", "color": "#1565C0"},
    {"name": "Якорь на дне", "emoji": "⚓", "theme": "привязанность и стабильность", "color": "#004D40"},
    {"name": "Расцветающий сад", "emoji": "🌻", "theme": "забота и рост", "color": "#558B2F"},
    {"name": "Пустой стул", "emoji": "🪑", "theme": "отсутствие и ожидание", "color": "#3E2723"},
    {"name": "Волчья стая", "emoji": "🐺", "theme": "принадлежность и инстинкты", "color": "#424242"},
    {"name": "Раскрытая книга", "emoji": "📖", "theme": "знание и история", "color": "#4E342E"},
    {"name": "Упавшая корона", "emoji": "👑", "theme": "власть и потеря статуса", "color": "#F9A825"},
    {"name": "Гнездо без птиц", "emoji": "🪺", "theme": "пустое место и уход", "color": "#5D4037"},
    {"name": "Переплетённые руки", "emoji": "🤝", "theme": "союз и взаимозависимость", "color": "#00695C"},
]

# ─── Генерация изображения карты ─────────────────────────────────────────
def generate_card_image(card: dict) -> bytes:
    """Создаёт красивое изображение МАК-карты."""
    W, H = 480, 640
    bg_color = card.get("color", "#1a1a2e")

    # Парсим цвет
    r = int(bg_color[1:3], 16)
    g = int(bg_color[3:5], 16)
    b = int(bg_color[5:7], 16)

    img = Image.new("RGB", (W, H), (r, g, b))
    draw = ImageDraw.Draw(img)

    # Градиент затемнение снизу
    for y in range(H // 2, H):
        alpha = (y - H // 2) / (H // 2)
        dark = int(alpha * 80)
        draw.line([(0, y), (W, y)], fill=(max(0, r - dark), max(0, g - dark), max(0, b - dark)))

    # Рамка
    border_color = (255, 215, 100)
    draw.rectangle([12, 12, W - 12, H - 12], outline=border_color, width=2)
    draw.rectangle([20, 20, W - 20, H - 20], outline=border_color, width=1)

    # Декоративные уголки
    corner_len = 30
    for cx, cy, dx, dy in [(24, 24, 1, 1), (W-24, 24, -1, 1), (24, H-24, 1, -1), (W-24, H-24, -1, -1)]:
        draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=border_color, width=2)
        draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=border_color, width=2)

    # Шрифты
    try:
        bold = FONT_PATH or FONT_REGULAR_PATH
        regular = FONT_REGULAR_PATH or FONT_PATH
        font_big = ImageFont.truetype(bold, 36)
        font_medium = ImageFont.truetype(bold, 24)
        font_small = ImageFont.truetype(regular, 18)
        font_emoji = ImageFont.truetype(bold, 80)
    except Exception:
        font_big = ImageFont.load_default()
        font_medium = font_big
        font_small = font_big
        font_emoji = font_big

    # Верхний текст "МАК КАРТА"
    header = "МАК КАРТА"
    bbox = draw.textbbox((0, 0), header, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 40), header, font=font_small, fill=(255, 215, 100))

    # Разделитель
    line_y = 72
    draw.line([(60, line_y), (W - 60, line_y)], fill=(255, 215, 100, 128), width=1)

    # Эмодзи (большой символ в центре)
    emoji_text = card["emoji"]
    try:
        bbox = draw.textbbox((0, 0), emoji_text, font=font_emoji)
        ew = bbox[2] - bbox[0]
        eh = bbox[3] - bbox[1]
        draw.text(((W - ew) // 2, 160), emoji_text, font=font_emoji, fill="white")
    except Exception:
        # Если эмодзи не рендерится, рисуем декоративный круг
        draw.ellipse([(W//2-50, 180), (W//2+50, 280)], outline=border_color, width=2)

    # Декоративные звёздочки
    star_color = (255, 255, 255, 60)
    for _ in range(20):
        sx = random.randint(30, W - 30)
        sy = random.randint(90, 350)
        size = random.randint(1, 3)
        draw.ellipse([(sx, sy), (sx + size, sy + size)], fill=(255, 255, 255))

    # Название карты
    card_name = f"«{card['name']}»"
    bbox = draw.textbbox((0, 0), card_name, font=font_big)
    tw = bbox[2] - bbox[0]
    name_y = 360
    # Если название длинное — разбиваем на строки
    if tw > W - 60:
        words = card_name.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        for i, line in enumerate([line1, line2]):
            bbox = draw.textbbox((0, 0), line, font=font_big)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, name_y + i * 44), line, font=font_big, fill="white")
        theme_y = name_y + 100
    else:
        draw.text(((W - tw) // 2, name_y), card_name, font=font_big, fill="white")
        theme_y = name_y + 56

    # Тема
    theme_text = card["theme"]
    bbox = draw.textbbox((0, 0), theme_text, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, theme_y), theme_text, font=font_medium, fill=(255, 215, 100))

    # Нижний разделитель
    draw.line([(60, H - 72), (W - 60, H - 72)], fill=(255, 215, 100), width=1)

    # Подпись
    footer = "Ум в гармонии"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - 55), footer, font=font_small, fill=(200, 200, 200))

    # Сохраняем в bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


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

    # Генерируем изображение карты
    image_bytes = generate_card_image(card)

    caption = (
        f"🎴 *Карта дня*\n\n"
        f"*«{card['name']}»* {card['emoji']}\n\n"
        f"{message_text}\n\n"
        f"─────────────────\n"
        f"_Напиши /card чтобы вытянуть новую карту_"
    )

    # Отправляем фото с подписью
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=image_bytes,
        caption=caption,
        parse_mode="Markdown",
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
        parse_mode="Markdown",
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
    find_fonts()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card", card_command))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    logger.info("Бот запущен ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
