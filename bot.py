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

# ─── 50 МАК карт "УМ В ГАРМОНИИ" ───────────────────────────────────────
# Авторская колода Ольги Сазыкиной
# Структура: id, name_ru, name_en, emoji, theme, ai_prompt, color, image_path
MAK_CARDS = [
    # БЛОК 1: ФУНДАМЕНТ И ЦЕНТР (Карты 1-10)
    {"id": 1, "name": "ЦЕНТР", "name_en": "The Center", "emoji": "🎴", "theme": "Найти свой центр, стабильность, внутренний стержень", "prompt": "A meditative figure standing in the center of concentric circles, geometric patterns radiating outward, golden and indigo color palette --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 2, "name": "ВОСХОЖДЕНИЕ", "name_en": "The Ascent", "emoji": "⛰️", "theme": "Духовный и личностный рост, развитие, преодоление", "prompt": "Silhouettes climbing upward through golden light and mountains, rays of sunrise breaking through mist --ar 1:1.4 --quality 2", "color": "#CD7F32", "image": None},
    {"id": 3, "name": "КОРНИ И ВЕТВИ", "name_en": "Roots and Branches", "emoji": "🌳", "theme": "Связь с прошлым и будущим, баланс глубины и роста", "prompt": "Majestic tree with visible roots deep in earth and branches reaching to sky, vertical unity --ar 1:1.4 --quality 2", "color": "#7C8F8F", "image": None},
    {"id": 4, "name": "ЗЕРКАЛО ВОДЫ", "name_en": "Water Mirror", "emoji": "💧", "theme": "Самопознание, отражение, честность перед собой", "prompt": "Mirror-like water surface reflecting sky and clouds, silhouette of person looking down --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 5, "name": "МОСТ", "name_en": "The Bridge", "emoji": "🌉", "theme": "Переход между состояниями, преодоление пропастей, соединение полюсов", "prompt": "Elegant bridge crossing over misty chasm, transitional moment, promise of passage --ar 1:1.4 --quality 2", "color": "#A66D6D", "image": None},
    {"id": 6, "name": "СВЕТ ВНУТРИ", "name_en": "Inner Light", "emoji": "💡", "theme": "Внутренний ресурс, духовное пробуждение, собственная сила", "prompt": "Silhouette with bright glowing light emanating from heart, inner fire and spiritual awakening --ar 1:1.4 --quality 2", "color": "#E65100", "image": None},
    {"id": 7, "name": "РАЗВЁРТЫВАНИЕ", "name_en": "Unfolding", "emoji": "🌺", "theme": "Раскрытие потенциала, раскрытие крыльев, становление собой", "prompt": "Unfolding flower petals or butterfly wings opening gracefully in motion --ar 1:1.4 --quality 2", "color": "#AD1457", "image": None},
    {"id": 8, "name": "КОЛОДЕЦ", "name_en": "The Well", "emoji": "🕳️", "theme": "Глубинные ресурсы, скрытая мудрость, колодец вдохновения", "prompt": "Ancient stone well with deep darkness and glimmer of water at bottom --ar 1:1.4 --quality 2", "color": "#37474F", "image": None},
    {"id": 9, "name": "ДВА ПОЛЮСА", "name_en": "The Two Poles", "emoji": "☯️", "theme": "Инь-ян, баланс противоположностей, дуальность", "prompt": "Yin-yang symbol using indigo and gold colors, balance of opposites --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 10, "name": "ПРОБУЖДЕНИЕ", "name_en": "Awakening", "emoji": "🌅", "theme": "Просветление, новое видение, начало осознания", "prompt": "Window with first rays of sunrise, figure waking to light, dawn scene --ar 1:1.4 --quality 2", "color": "#F9A825", "image": None},

    # БЛОК 2: ТРАНСФОРМАЦИЯ И ДВИЖЕНИЕ (Карты 11-25)
    {"id": 11, "name": "СПИРАЛЬ", "name_en": "The Spiral", "emoji": "🌀", "theme": "Спиралевидное развитие, циклы и прогресс", "prompt": "Spiral ascending from center, color transition from indigo to golden light --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 12, "name": "КРИСТАЛЛ", "name_en": "The Crystal", "emoji": "💎", "theme": "Ясность, просветлённость, кристаллизация идей", "prompt": "Geometric crystal with multiple facets, light refracting, luminosity --ar 1:1.4 --quality 2", "color": "#7C8F8F", "image": None},
    {"id": 13, "name": "ОБНИМАЮЩИЕ РУКИ", "name_en": "Embracing Hands", "emoji": "🤝", "theme": "Поддержка, единство, принятие, дарование и получение", "prompt": "Two hands embracing or cupping light, warmth and support --ar 1:1.4 --quality 2", "color": "#A66D6D", "image": None},
    {"id": 14, "name": "МЕДИТАЦИЯ", "name_en": "Meditation", "emoji": "🧘", "theme": "Внутренний покой, йога, спокойствие ума, присутствие", "prompt": "Sitting figure in meditation pose in nature, soft golden light --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 15, "name": "ТРАНСФОРМАЦИЯ", "name_en": "Transformation", "emoji": "🦋", "theme": "Глубокое изменение, метаморфоза, смерть и рождение", "prompt": "Metamorphosis from caterpillar to butterfly, magical transition --ar 1:1.4 --quality 2", "color": "#CD7F32", "image": None},
    {"id": 16, "name": "ХРАМ ВНУТРИ", "name_en": "Inner Temple", "emoji": "⛩️", "theme": "Священное пространство внутри, святилище, убежище", "prompt": "Temple architecture inside human figure, golden light, holy space --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 17, "name": "ПЛЕТЕНИЕ", "name_en": "Weaving", "emoji": "🧵", "theme": "Переплетение жизненных нитей, ткань судьбы", "prompt": "Interwoven threads of different colors creating pattern, hands weaving --ar 1:1.4 --quality 2", "color": "#A66D6D", "image": None},
    {"id": 18, "name": "ВОСТОЧНЫЕ ВОРОТА", "name_en": "The Eastern Gate", "emoji": "🚪", "theme": "Портал, возможность, восток и новое начало", "prompt": "Eastern-style ornate gates opening onto new landscape with light --ar 1:1.4 --quality 2", "color": "#CD7F32", "image": None},
    {"id": 19, "name": "ДУШЕВНОЕ ОЗЕРО", "name_en": "Soul's Lake", "emoji": "🌌", "theme": "Глубина чувства, отражение ночного неба в воде", "prompt": "Night lake reflecting stars and moon, perfectly still surface --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 20, "name": "ЛАБИРИНТ РЕШЕНИЙ", "name_en": "The Labyrinth", "emoji": "🌀", "theme": "Путь выбора, лабиринт как медитативный путь", "prompt": "Beautiful labyrinth with light glowing at center or wise figure --ar 1:1.4 --quality 2", "color": "#7C8F8F", "image": None},
    {"id": 21, "name": "ЗВЕЗДНАЯ КАРТА", "name_en": "Celestial Map", "emoji": "⭐", "theme": "Космическая связь, судьба, ориентирование по звёздам", "prompt": "Night sky with constellations forming into a celestial map --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 22, "name": "СЕМЕНА", "name_en": "Seeds", "emoji": "🌱", "theme": "Потенциал, рост, плодородие, начало", "prompt": "Seeds falling into fertile earth or sprouting, potential growth --ar 1:1.4 --quality 2", "color": "#33691E", "image": None},
    {"id": 23, "name": "ЭКРАН ЧУВСТВ", "name_en": "The Emotive Screen", "emoji": "😌", "theme": "Эмоции на лице, выражение чувств, маска и подлинность", "prompt": "Portrait with multiple layers of emotions, light and shadow --ar 1:1.4 --quality 2", "color": "#A66D6D", "image": None},
    {"id": 24, "name": "ГАРМОНИЧНЫЙ САД", "name_en": "The Harmonious Garden", "emoji": "🌻", "theme": "Многоуровневая красота, порядок в природе, культивация жизни", "prompt": "Multi-layered garden in balance and harmony, diverse flowers --ar 1:1.4 --quality 2", "color": "#558B2F", "image": None},
    {"id": 25, "name": "ПОЛЁТ", "name_en": "Flight", "emoji": "🕊️", "theme": "Свобода, взлёт, выход за границы, парение", "prompt": "Human or bird in flight above clouds, freedom and liberation --ar 1:1.4 --quality 2", "color": "#0277BD", "image": None},

    # БЛОК 3: БАЛАНС И ПРОТИВОПОЛОЖНОСТИ (Карты 26-40)
    {"id": 26, "name": "ВОЛНЫ И КАТАМАРАН", "name_en": "Waves and Catamaran", "emoji": "🌊", "theme": "Движение через нестабильность, баланс на волнах жизни", "prompt": "Small catamaran balanced on waves, stability amidst chaos --ar 1:1.4 --quality 2", "color": "#0277BD", "image": None},
    {"id": 27, "name": "МАЯТНИК", "name_en": "The Pendulum", "emoji": "⏳", "theme": "Балансирование между полюсами, ритм жизни", "prompt": "Swinging pendulum between two points, balanced motion --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 28, "name": "ТЕАТРАЛЬНАЯ МАСКА", "name_en": "The Theatrical Mask", "emoji": "🎭", "theme": "Роли и их трансформация, маска и подлинность", "prompt": "Theater masks morphing or layered, roles and transformation --ar 1:1.4 --quality 2", "color": "#C62828", "image": None},
    {"id": 29, "name": "СПЯЩИЙ БУДДА", "name_en": "Sleeping Buddha", "emoji": "🙏", "theme": "Умиротворение, отпускание, спокойный ум", "prompt": "Reclining Buddha figure smiling peacefully, surrounded by soft light --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 30, "name": "ОГОНЬ И ЛЁД", "name_en": "Fire and Ice", "emoji": "🔥❄️", "theme": "Интеграция противоположностей, страсть и спокойствие", "prompt": "Fire and ice elements meeting, creating dynamic interaction --ar 1:1.4 --quality 2", "color": "#D84315", "image": None},
    {"id": 31, "name": "ЛЕСТНИЦА ЗВЁЗД", "name_en": "Stairway of Stars", "emoji": "🪜", "theme": "Восхождение пошаговое, путь развития", "prompt": "Staircase ascending into stars, each step glowing --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 32, "name": "КОЛЫБЕЛЬ", "name_en": "The Cradle", "emoji": "👶", "theme": "Безопасность, детскость, нежность, материнское тепло", "prompt": "Antique cradle swaying gently, warm soft light inside --ar 1:1.4 --quality 2", "color": "#AD1457", "image": None},
    {"id": 33, "name": "УРАГАН И ГЛА УРАГАНА", "name_en": "Hurricane and Its Eye", "emoji": "🌪️", "theme": "Спокойствие в центре хаоса, медитативный центр в бури", "prompt": "Hurricane with swirling clouds, peaceful eye at center --ar 1:1.4 --quality 2", "color": "#546E7A", "image": None},
    {"id": 34, "name": "ДВОЙНОЕ ЗЕРКАЛО", "name_en": "Dual Mirror", "emoji": "🪞", "theme": "Рефлексия и метарефлексия, глубокое самопознание", "prompt": "Two mirrors reflecting each other creating infinite reflection --ar 1:1.4 --quality 2", "color": "#4B0082", "image": None},
    {"id": 35, "name": "ГЕОМЕТРИЧЕСКИЙ САД", "name_en": "The Geometric Garden", "emoji": "🔷", "theme": "Структурированная гармония, порядок как красота", "prompt": "Geometric shapes creating garden, sacred geometry --ar 1:1.4 --quality 2", "color": "#7C8F8F", "image": None},
    {"id": 36, "name": "ПРОЩАНИЕ И ВСТРЕЧА", "name_en": "Farewell and Meeting", "emoji": "👋", "theme": "Циклы, заканчивание и начинание, встреча старого и нового", "prompt": "Two figures on horizon, sunset and sunrise simultaneously --ar 1:1.4 --quality 2", "color": "#F9A825", "image": None},
    {"id": 37, "name": "КНИГА ЖИЗНИ", "name_en": "The Book of Life", "emoji": "📖", "theme": "История жизни, автор собственной жизни", "prompt": "Open ancient book with pages flowing into infinity --ar 1:1.4 --quality 2", "color": "#4E342E", "image": None},
    {"id": 38, "name": "МАЯТНИК ВРЕМЕНИ", "name_en": "The Time Pendulum", "emoji": "⏰", "theme": "Цикличность времени, момент сейчас, вечное движение", "prompt": "Pendulum with clock faces and flowing watercolor colors --ar 1:1.4 --quality 2", "color": "#546E7A", "image": None},
    {"id": 39, "name": "УТЮЖОК (СТИРАНИЕ)", "name_en": "The Iron", "emoji": "🧥", "theme": "Очищение, разглаживание морщин прошлого", "prompt": "Iron smoothing wrinkled fabric into pristine surface --ar 1:1.4 --quality 2", "color": "#3E2723", "image": None},
    {"id": 40, "name": "СОБИРАНИЕ СИЛЫ", "name_en": "Gathering Strength", "emoji": "✨", "theme": "Аккумуляция ресурсов, мобилизация, готовность к действию", "prompt": "Figure collecting stars or light drops in hands --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},

    # БЛОК 4: ИНТЕГРАЦИЯ И ЦЕЛОСТНОСТЬ (Карты 41-50)
    {"id": 41, "name": "НИТЬ АРИАДНЫ", "name_en": "Ariadne's Thread", "emoji": "🧵", "theme": "Путь через лабиринт, спасающая нить, помощь в пути", "prompt": "Thread leading out of labyrinth into light, golden thread --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 42, "name": "ХРУСТАЛЬНЫЙ ДВОРЕЦ", "name_en": "The Crystal Palace", "emoji": "👑", "theme": "Величественная внутренняя красота, дворец как внутреннее величие", "prompt": "Magnificent transparent crystal palace with golden columns --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 43, "name": "МОЛЧАНИЕ МЕЖДУ ЗВУКАМИ", "name_en": "Silence Between Sounds", "emoji": "🤐", "theme": "Пауза, пустота как ресурс, молчание", "prompt": "Abstract composition with sound waves and large spaces of silence --ar 1:1.4 --quality 2", "color": "#37474F", "image": None},
    {"id": 44, "name": "ДВА КРЫЛА", "name_en": "Two Wings", "emoji": "🪶", "theme": "Симметрия, парные качества, баланс половин", "prompt": "Two large beautiful symmetrical wings, luminous and ready --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 45, "name": "КОРОНА ВНУТРИ", "name_en": "The Inner Crown", "emoji": "✨", "theme": "Собственное величие, принятие своей царственности", "prompt": "Glowing crown above human figure or born from inner light --ar 1:1.4 --quality 2", "color": "#F9A825", "image": None},
    {"id": 46, "name": "СЛИЯНИЕ РЕК", "name_en": "Confluence of Rivers", "emoji": "🌊", "theme": "Встреча путей, слияние разных потоков в одно целое", "prompt": "Rivers meeting and merging into one powerful stream --ar 1:1.4 --quality 2", "color": "#0277BD", "image": None},
    {"id": 47, "name": "ГЛАЗ ТИГРА", "name_en": "Tiger's Eye", "emoji": "👁️", "theme": "Сила и мудрость, зоркость, готовность, грация в силе", "prompt": "Intense gaze of tiger eye, profile or direct, mixing gold and black --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
    {"id": 48, "name": "СВЕТЛЫЙ КОРИДОР", "name_en": "Bright Corridor", "emoji": "🚪", "theme": "Выход из темноты, направленность к свету", "prompt": "Long corridor leading toward bright light at the end --ar 1:1.4 --quality 2", "color": "#E65100", "image": None},
    {"id": 49, "name": "ДОЖДЬ И РАДУГА", "name_en": "Rain and Rainbow", "emoji": "🌈", "theme": "Очищение и обновление, надежда после слёз", "prompt": "Rain falling with rainbow appearing simultaneously in sky --ar 1:1.4 --quality 2", "color": "#0277BD", "image": None},
    {"id": 50, "name": "СПИРАЛЬ СВЕТА", "name_en": "Spiral of Light", "emoji": "✨", "theme": "Восхождение к просветлению, интеграция всех уровней", "prompt": "Spiral ascending upward where each turn becomes brighter, star at top --ar 1:1.4 --quality 2", "color": "#D4AF37", "image": None},
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

    # Номер и название карты
    card_num = card.get("id", 1)
    card_name = f"№{card_num} {card['name']}"
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
    """Генерирует психологическое послание через Claude API."""
    prompt = f"""Ты — мудрый психолог и проводник. Клиент вытянул МАК карту авторской колоды "УМ В ГАРМОНИИ".

Карта: «{card['name']}» ({card.get('name_en', '')}) {card.get('emoji', '🎴')}
Психологическая тема: {card['theme']}

Напиши короткое психологическое послание для клиента (3-4 предложения):
- Начни с наблюдения об образе и теме карты
- Дай мягкий, глубокий вопрос для размышления
- Заверши тёплым посланием-поддержкой
- Пиши на «ты», тепло, без психологического жаргона
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
        logger.error(f"Ошибка API Claude: {e}")
        return f"Эта карта говорит тебе: {card['theme']}. Прислушайся к себе — что ты чувствуешь прямо сейчас?"


# ─── Отправка карты ──────────────────────────────────────────────────────
async def send_card(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет случайную МАК карту с психологическим посланием."""
    card = random.choice(MAK_CARDS)
    message_text = await generate_message(card)

    # Проверяем, есть ли реальное изображение карты
    image_bytes = None
    if card.get("image") and Path(card["image"]).exists():
        # Используем реальное изображение
        with open(card["image"], "rb") as f:
            image_bytes = f.read()
        logger.info(f"📸 Использую реальное изображение: {card['image']}")
    else:
        # Генерируем изображение программно
        image_bytes = generate_card_image(card)
        logger.info(f"🎨 Генерирую изображение для карты #{card['id']}: {card['name']}")

    caption = (
        f"🎴 *Карта дня*\n\n"
        f"*№{card['id']} {card['name']}*\n"
        f"_{card.get('name_en', '')}_ {card['emoji']}\n\n"
        f"_{card['theme']}_\n\n"
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
