import asyncio
import aiosqlite
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from calendar import monthcalendar, month_name

# ============ НАСТРОЙКИ ============
API_TOKEN = '8278829733:AAFJGwqcurBtrGLqq3szbFcFd9i09LHgHag'
ADMINS = [434755668, 819582279]  # Замени на ваши user_id

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ============ ИНИЦИАЛИЗАЦИЯ БД ============
async def init_db():
    async with aiosqlite.connect('household.db') as db:
        # Основные таблицы
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                score INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_level_up TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                points INTEGER,
                is_team BOOLEAN DEFAULT 0,
                category TEXT DEFAULT "Без категории"
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS completed_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                completed_at TEXT,
                is_team BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                icon TEXT,
                points INTEGER DEFAULT 0,
                title TEXT,
                type TEXT,
                is_hidden BOOLEAN DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id INTEGER,
                unlocked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(achievement_id) REFERENCES achievements(id),
                UNIQUE(user_id, achievement_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_titles (
                user_id INTEGER PRIMARY KEY,
                title TEXT DEFAULT "Новичок Быта",
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                start_date TEXT,
                end_date TEXT,
                is_active BOOLEAN DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_season_archive (
                user_id INTEGER,
                season_id INTEGER,
                final_score INTEGER,
                final_level INTEGER,
                rank_in_season INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(season_id) REFERENCES seasons(id),
                UNIQUE(user_id, season_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS completed_tasks_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_name TEXT,
                points INTEGER,
                completed_at TEXT,
                season_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(season_id) REFERENCES seasons(id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS daily_actions (
                user_id INTEGER,
                date TEXT,
                dishwasher_used BOOLEAN DEFAULT 0,
                trash_taken_out BOOLEAN DEFAULT 0,
                dishes_washed BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_id, date),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                task_keyword TEXT,
                bonus_points INTEGER,
                is_active BOOLEAN DEFAULT 0,
                assigned_to INTEGER,
                assigned_at TEXT,
                completed_at TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS weekly_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                target_count INTEGER,
                created_at TEXT,
                achieved_at TEXT DEFAULT NULL
            )
        ''')

        # ============ ДОБАВЛЯЕМ ВСЕ ЗАДАНИЯ ============
        your_tasks = [
            # 🍽 КУХНЯ
            ("Помыть посуду после ужина", 3, 0, "🍽 КУХНЯ"),
            ("Помыть посуду после обеда или завтрака", 2, 0, "🍽 КУХНЯ"),
            ("Приготовить ужин на двоих (с сервировкой и уборкой)", 5, 1, "🍽 КУХНЯ"),
            ("Приготовить завтрак (горячий, на двоих)", 3, 1, "🍽 КУХНЯ"),
            ("Приготовить обед с собой на работу", 3, 0, "🍽 КУХНЯ"),
            ("Сходить за продуктами (по списку, 10+ позиций)", 4, 1, "🍽 КУХНЯ"),
            ("Разгрузить/загрузить посудомоечную машину полностью", 2, 0, "🍽 КУХНЯ"),
            ("Вынести мусор + заменить мешки", 2, 0, "🍽 КУХНЯ"),
            ("Протереть кухонные поверхности (стол, плита, фартук)", 2, 0, "🍽 КУХНЯ"),
            ("Очистить холодильник внутри (мытьё полок, проверка сроков)", 5, 1, "🍽 КУХНЯ"),
            ("Разморозить и помыть морозильную камеру", 8, 1, "🍽 КУХНЯ"),
            ("Составить меню на неделю + список покупок", 3, 1, "🍽 КУХНЯ"),
            ("Замариновать/заготовить еду впрок (на 2+ дня)", 4, 1, "🍽 КУХНЯ"),
            ("Помыть духовку/микроволновку внутри", 6, 1, "🍽 КУХНЯ"),
            ("Убрать кладовку/шкаф с продуктами (просроченное, порядок)", 5, 1, "🍽 КУХНЯ"),

            # 🧹 УБОРКА В КВАРТИРЕ
            ("Пропылесосить всю квартиру (включая под мебелью и углы)", 4, 0, "🧹 УБОРКА"),
            ("Помыть полы во всех комнатах", 5, 1, "🧹 УБОРКА"),
            ("Протереть пыль по всей квартире (включая технику, картины, полки)", 4, 1, "🧹 УБОРКА"),
            ("Помыть ванную комнату (ванна, раковина, зеркало, пол, мусорка)", 5, 1, "🧹 УБОРКА"),
            ("Помыть туалет (унитаз, пол, бачок, держатель бумаги)", 3, 0, "🧹 УБОРКА"),
            ("Помыть зеркала в доме (без разводов)", 3, 0, "🧹 УБОРКА"),
            ("Почистить ковры/коврики (пылесос + пятновыводитель при необходимости)", 4, 1, "🧹 УБОРКА"),
            ("Помыть окна (1 окно стандартного размера)", 4, 1, "🧹 УБОРКА"),
            ("Помыть батареи/радиаторы от пыли", 3, 0, "🧹 УБОРКА"),
            ("Убрать детскую/кабинет/кладовку (полный порядок, сортировка вещей)", 6, 1, "🧹 УБОРКА"),
            ("Вынести крупный/строительный мусор (вызвать службу или отвезти)", 6, 1, "🧹 УБОРКА"),
            ("Помыть входную дверь и дверные ручки по всей квартире", 3, 0, "🧹 УБОРКА"),
            ("Почистить вентиляционные решётки/кондиционер (внешняя очистка)", 4, 0, "🧹 УБОРКА"),
            ("Помыть плинтуса по всей квартире", 4, 1, "🧹 УБОРКА"),
            ("Сменить постельное бельё на всех кроватях", 4, 1, "🧹 УБОРКА"),

            # 🧺 СТИРКА, ГЛАЖКА, ШКАФЫ
            ("Загрузить стиральную машину (полная загрузка, с сортировкой)", 2, 0, "🧺 СТИРКА"),
            ("Развесить/разложить посушенное бельё аккуратно", 3, 0, "🧺 СТИРКА"),
            ("Погладить 10+ вещей", 4, 0, "🧺 СТИРКА"),
            ("Перебрать шкаф (сезонная ротация, убрать ненужное)", 8, 1, "🧺 СТИРКА"),
            ("Зашить дырку/пришить пуговицу качественно", 3, 0, "🧺 СТИРКА"),
            ("Организовать хранение вещей (ящики, коробки, подписи)", 6, 1, "🧺 СТИРКА"),
            ("Почистить обувь (5+ пар, включая внутреннюю обработку)", 4, 1, "🧺 СТИРКА"),
            ("Отнести/забрать вещи в химчистку", 3, 0, "🧺 СТИРКА"),
            ("Собрать и отвезти/отправить посылку (одежду, книги и т.п.)", 4, 1, "🧺 СТИРКА"),

            # 🛒 АДМИНИСТРАЦИЯ, ПЛАНИРОВАНИЕ, БЫТ
            ("Оплатить все коммунальные услуги в срок", 3, 0, "🛒 БЫТ"),
            ("Записаться и сходить на приём (врач, парикмахер, автосервис и т.п.)", 2, 0, "🛒 БЫТ"),
            ("Организовать приход гостей (уборка, еда, напитки, атмосфера)", 6, 1, "🛒 БЫТ"),
            ("Спланировать отпуск/выходные (маршрут, бронь, список вещей)", 7, 1, "🛒 БЫТ"),
            ("Купить, упаковать и подписать подарок (к ДР, празднику)", 5, 1, "🛒 БЫТ"),
            ("Организовать семейный вечер (фильм, настолка, тематический ужин)", 5, 1, "🛒 БЫТ"),
            ("Составить/обновить список дел по дому на неделю", 3, 1, "🛒 БЫТ"),
            ("Разобрать почту/бумаги/документы (подписки, счета, архив)", 5, 0, "🛒 БЫТ"),
            ("Обновить аптечку (проверить сроки, докупить, подписать)", 4, 1, "🛒 БЫТ"),
            ("Организовать техобслуживание техники (стиралка, пылесос, кондиционер)", 5, 1, "🛒 БЫТ"),
            ("Сделать фото/видео семейного момента + сохранить в архив", 3, 1, "🛒 БЫТ"),

            # 🐶 ПИТОМЦЫ
            ("Выгулять собаку (30+ минут, активная прогулка)", 3, 0, "🐶 ПИТОМЦЫ"),
            ("Накормить питомца + помыть миски + убрать лоток/клетку", 2, 0, "🐶 ПИТОМЦЫ"),
            ("Почистить аквариум/клетку/террариум", 5, 0, "🐶 ПИТОМЦЫ"),
            ("Сходить с питомцем к ветеринару", 5, 1, "🐶 ПИТОМЦЫ"),
            ("Купить корм/наполнитель/игрушки для питомца", 3, 0, "🐶 ПИТОМЦЫ"),
            ("Постричь когти/почесать/почистить шерсть питомцу", 4, 0, "🐶 ПИТОМЦЫ"),
            ("Обучить питомца новой команде/трюку", 6, 1, "🐶 ПИТОМЦЫ"),
            ("Организовать фотосессию с питомцем", 4, 1, "🐶 ПИТОМЦЫ"),
            ("Сделать уборку в зоне питомца (лежанка, игрушки, уголок)", 3, 0, "🐶 ПИТОМЦЫ"),
            ("Придумать и сделать игрушку для питомца своими руками", 5, 1, "🐶 ПИТОМЦЫ"),
        ]

        for name, points, is_team, category in your_tasks:
            await db.execute('INSERT OR IGNORE INTO tasks (name, points, is_team, category) VALUES (?, ?, ?, ?)', (name, points, is_team, category))

        # ============ ДОБАВЛЯЕМ ВСЕ АЧИВКИ ============
        achievements_data = [
            # 🦸‍♂️ ГЕРОИЧЕСКИЕ
            ("Мастер Посудомойки", "Загрузил/разгрузил посудомойку 7 дней подряд", "🦸‍♂️", 5, "Рыцарь Чистых Тарелок", "heroic", 0),
            ("Тень Уборки", "Убрал всю квартиру, пока партнёр спал", "🥷", 8, "Ниндзя Чистоты", "heroic", 0),
            ("Гладильный Дракон", "Погладил 20 вещей за один присест", "🐉", 7, "Повелитель Утюга", "heroic", 0),
            ("Шеф-невидимка", "Приготовил ужин, накрыл, угостил, и убрал всё, пока партнёр смотрел сериал", "👻", 10, "Кулинарный Призрак", "heroic", 0),
            ("Мусорный Магнат", "Вынес мусор 5 раз подряд без напоминаний", "🗑️", 5, "Король Контейнеров", "heroic", 0),
            ("Мастер Переговоров", "Убедил партнёра убрать свою комнату БЕЗ крика", "🗣️", 6, "Дипломат Грязи", "heroic", 0),

            # 🐉 ЛЕГЕНДАРНЫЕ
            ("Очиститель Храма", "Помыл духовку ДО БЛЕСКА", "🔥", 10, "Последний Герой Грязной Кухни", "legendary", 0),
            ("Герой Морозилки", "Разморозил + вымыл + аккуратно вернул всё на место", "❄️", 12, "Покоритель Ледяного Ада", "legendary", 0),
            ("Сантехник Судьбы", "Починил капающий кран САМ", "🔧", 15, "Маг Гаечных Ключей", "legendary", 0),
            ("Хранитель Порядка", "Привёл в порядок шкаф, в котором 'ничего не найти'", "🗄️", 10, "Архивариус Хаоса", "legendary", 0),
            ("Властелин Времени", "Спланировал неделю, и всё прошло по плану", "⏳", 12, "Пророк Расписания", "legendary", 0),
            ("Гуру Бюджета", "Оплатил все счета + нашёл способ сэкономить", "💰", 8, "Финансовый Ниндзя", "legendary", 0),

            # 😈 ПОЗОРНЫЕ
            ("Посол Грязи", "Не мыл посуду 3 дня подряд", "🦠", -5, "Представитель Бактериальной Империи", "shameful", 0),
            ("Мастер Откладывания", "Откладывал одно дело больше недели", "🐌", -3, "Чемпион Прокрастинации", "shameful", 0),
            ("Саботажник Пылесоса", "Видел пыль, но сделал вид, что не заметил", "🙈", -2, "Шпион Хаоса", "shameful", 0),
            ("Гений Забывчивости", "Забыл вынести мусор, и он переполнился", "🤯", -4, "Последний Мусорный Шаман", "shameful", 0),
            ("Король Отговорок", "Придумал 5 причин, почему не может убрать сегодня", "🤥", -5, "Мастер Оправданий", "shameful", 0),
            ("Тролль Уборки", "Специально оставил одну грязную тарелку, чтобы 'не было идеально'", "😈", -3, "Агент Хаоса", "shameful", 0),

            # 💘 РОМАНТИЧЕСКИЕ
            ("Сердцеед Чистоты", "Сделал уборку + оставил записку с комплиментом", "💌", 7, "Романтик с Тряпкой", "romantic", 0),
            ("Ужин при Свечах (и без посуды после)", "Приготовил романтический ужин + убрал всё", "🕯️", 10, "Купидон Кухни", "romantic", 0),
            ("Сюрприз-Атака", "Сделал массаж после тяжёлого дня без просьбы", "💆‍♂️", 8, "Тайный Целитель", "romantic", 0),
            ("Танцпол на Кухне", "Включил музыку и убирался вместе с партнёром танцуя", "🕺", 6, "Диджей Чистоты", "romantic", 0),
            ("Подарочный Ниндзя", "Купил подарок без повода и вручил с интригой", "🎁", 8, "Эльф Сюрпризов", "romantic", 0),

            # 🎲 ВЕСЁЛЫЕ
            ("Случайный Гений", "Случайно придумал гениальный лайфхак по дому", "🧠", 5, "Профессор Быта", "funny", 0),
            ("Мем-Мастер", "Сфоткал смешной момент уборки и сохранил в семейный архив", "📸", 3, "Хранитель Смеха", "funny", 0),
            ("Однорукий Пылесос", "Убирал одной рукой, держа телефон/кошку", "🤹", 4, "Циркач Дома", "funny", 0),
            ("Голосовой Ассистент Реальности", "Отдал команду 'Алиса/Сири, напомни...' и это сработало", "🤖", 2, "Маг Гаджетов", "funny", 0),
            ("Спаситель Посуды", "Успел помыть последнюю тарелку перед визитом гостей", "⏱️", 5, "Герой Последней Минуты", "funny", 0),
            ("Философ Грязи", "Вместо уборки сел и поразмышлял о смысле чистоты", "🤔", -1, "Мыслитель с Тряпкой", "funny", 0),

            # 👑 БОСС-МОДЫ
            ("Неделя Без Напоминаний", "Всю неделю делал дела без единого 'а ты сделал?'", "📅", 15, "Самодостаточный Герой", "boss", 0),
            ("Месяц Идеального Баланса", "Оба партнёра набрали одинаковое количество баллов", "⚖️", 20, "Гармония Быта", "boss", 0),
            ("Тёмная Сторона Лени", "Целый день ничего не делал, но честно признался", "🌚", -10, "Искренний Тролль", "boss", 0),
            ("Режим Бога Дома", "За неделю выполнил 50+ баллов", "⚡", 25, "Божество Быта", "boss", 0),
            ("Суперкомбо Партнёров", "Сделали одно дело ВМЕСТЕ и получили удовольствие", "🤝", 10, "Команда Мечты", "boss", 0),

            # 🕵️‍♂️ СЕКРЕТНЫЕ
            ("Секретный Агент Любви", "Сделал что-то приятное без повода и не сказал об этом", "🕵️‍♂️", 10, "Агент Любви", "secret", 1),
            ("Мастер Подмены", "Сделал дело партнёра, пока тот отдыхал", "🔄", 8, "Тень Заботы", "secret", 1),
            ("Филантроп Хаоса", "Позволил дому быть немного неидеальным, чтобы снять стресс с партнёра", "🧘‍♀️", 5, "Мудрец Баланса", "secret", 1),
        ]

        for name, desc, icon, points, title, ach_type, is_hidden in achievements_data:
            await db.execute('''
                INSERT OR IGNORE INTO achievements (name, description, icon, points, title, type, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, desc, icon, points, title, ach_type, is_hidden))

        # Примеры квестов
        quests = [
            ("Ужин с любовью", "Приготовь ужин для партнёра", "ужин", 5),
            ("Гладильная атака", "Погладь 5+ вещей", "глад", 4),
            ("Тайный помощник", "Сделай дело партнёра, пока он не видит", "тайно", 6),
            ("Музыкальная уборка", "Включи музыку и убери одну комнату", "музык", 3),
            ("Фото момента", "Сделай фото уютного момента и сохрани", "фото", 4),
            ("Забота без слов", "Сделай что-то приятное без просьбы", "приятно", 7),
        ]
        for name, desc, keyword, points in quests:
            await db.execute('''
                INSERT OR IGNORE INTO quests (name, description, task_keyword, bonus_points)
                VALUES (?, ?, ?, ?)
            ''', (name, desc, keyword, points))

        await db.commit()

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def get_main_menu(user_id: int = None):
    buttons = [
        [KeyboardButton(text="📋 Мои дела"), KeyboardButton(text="🏆 Рейтинг")],
        [KeyboardButton(text="📅 Календарь"), KeyboardButton(text="🎯 Цели недели")],
        [KeyboardButton(text="🏅 Мои ачивки"), KeyboardButton(text="🔔 Напоминания")],
    ]
    if user_id and is_admin(user_id):
        buttons.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def update_level(user_id: int):
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT score, level FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            score, current_level = row

        new_level = min(10, score // 100 + 1)

        if new_level > current_level:
            async with db.execute('SELECT name FROM users WHERE user_id = ?', (user_id,)) as cursor:
                name = (await cursor.fetchone())[0]

            HUSBAND_RANKS = [
                "Новичок", "Помощник посудомойки", "Ассистент уборки", "Младший дворецкий",
                "Старший дворецкий", "Менеджер хаоса", "Директор чистоты", "Вице-президент быта",
                "Президент дома", "Император уюта", "Божество домашнего очага"
            ]
            WIFE_RANKS = [
                "Новичок", "Фея чистоты", "Хранительница порядка", "Маг уборки",
                "Гуру быта", "Королева дома", "Императрица уюта", "Архитектор гармонии",
                "Властелинка комфорта", "Богиня домашнего очага", "Легенда семейного гнездышка"
            ]
            NEUTRAL_RANKS = [
                "Новичок", "Уборщик-стажёр", "Ассистент чистоты", "Специалист по порядку",
                "Эксперт быта", "Мастер домашнего фронта", "Гуру уюта", "Легенда чистоты",
                "Мессия порядка", "Божество быта", "Вечный чемпион домашнего очага"
            ]

            if name.endswith(("а", "я")) and name not in ["Илья", "Никита"]:
                rank_list = WIFE_RANKS
            else:
                rank_list = HUSBAND_RANKS

            if new_level <= len(rank_list):
                new_rank = rank_list[new_level - 1]
            else:
                new_rank = NEUTRAL_RANKS[min(new_level - 1, len(NEUTRAL_RANKS) - 1)]

            await db.execute('UPDATE users SET level = ?, last_level_up = ? WHERE user_id = ?', 
                           (new_level, datetime.now().isoformat(), user_id))
            await db.commit()

            await bot.send_message(
                user_id,
                f"🎉 ПОЗДРАВЛЯЕМ! Ты достиг(ла) {new_level} уровня!\n"
                f"Твой новый ранг: *{new_rank}*\n"
                f"Продолжай в том же духе! 🚀",
                parse_mode="Markdown"
            )

async def record_daily_action(user_id: int, action: str):
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect('household.db') as db:
        await db.execute('''
            INSERT OR IGNORE INTO daily_actions (user_id, date, dishwasher_used, trash_taken_out, dishes_washed)
            VALUES (?, ?, 0, 0, 0)
        ''', (user_id, today))

        if action == "dishwasher":
            await db.execute('UPDATE daily_actions SET dishwasher_used = 1 WHERE user_id = ? AND date = ?', (user_id, today))
        elif action == "trash":
            await db.execute('UPDATE daily_actions SET trash_taken_out = 1 WHERE user_id = ? AND date = ?', (user_id, today))
        elif action == "dishes":
            await db.execute('UPDATE daily_actions SET dishes_washed = 1 WHERE user_id = ? AND date = ?', (user_id, today))

        await db.commit()

async def create_new_season():
    now = datetime.now()
    season_name = now.strftime("%B %Y")
    start_date = now.strftime("%Y-%m-01")
    if now.month == 12:
        end_date = f"{now.year + 1}-01-01"
    else:
        end_date = f"{now.year}-{now.month + 1:02d}-01"

    async with aiosqlite.connect('household.db') as db:
        await db.execute('UPDATE seasons SET is_active = 0 WHERE is_active = 1')

        await db.execute('''
            INSERT OR IGNORE INTO seasons (name, start_date, end_date, is_active)
            VALUES (?, ?, ?, 1)
        ''', (season_name, start_date, end_date))

        season_id = None
        async with db.execute('SELECT id FROM seasons WHERE name = ?', (season_name,)) as cursor:
            row = await cursor.fetchone()
            if row:
                season_id = row[0]

        if not season_id:
            return

        async with db.execute('SELECT user_id, score, level FROM users') as cursor:
            users = await cursor.fetchall()

        for user_id, score, level in users:
            await db.execute('''
                INSERT OR IGNORE INTO user_season_archive (user_id, season_id, final_score, final_level)
                VALUES (?, ?, ?, ?)
            ''', (user_id, season_id, score, level))

        async with db.execute('''
            SELECT ct.user_id, t.name, t.points, ct.completed_at
            FROM completed_tasks ct
            JOIN tasks t ON ct.task_id = t.id
            WHERE date(ct.completed_at) >= ?
        ''', (start_date,)) as cursor:
            tasks = await cursor.fetchall()

        for user_id, task_name, points, completed_at in tasks:
            await db.execute('''
                INSERT INTO completed_tasks_archive (user_id, task_name, points, completed_at, season_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, task_name, points, completed_at, season_id))

        await db.execute('UPDATE users SET score = 0, level = 1')
        await db.commit()

        async with db.execute('SELECT user_id FROM users') as cursor:
            users = await cursor.fetchall()

        for (user_id,) in users:
            try:
                await bot.send_message(
                    user_id,
                    f"🎉 *Новый сезон: {season_name}!*\n\n"
                    "Все баллы и уровни сброшены!\n"
                    "Но не переживай — твоя история сохранена.\n"
                    "Стань чемпионом этого месяца! 🏆",
                    parse_mode="Markdown"
                )
            except:
                pass

# ============ ИИ-СОВЕТНИК ============
ADVICE_TEMPLATES = [
    "Ты {days} дней не {task} — может, пора? 😉",
    "Ты часто делаешь {category} — попробуй ‘{suggestion}’, это даст +{points} баллов!",
    "{partner} вчера сделал(а) ‘{task}’ за тебя — может, отблагодаришь {reward}?",
    "Сегодня отличный день для ‘{task}’ — сделай и получи +{points} баллов!",
    "Ты в {steps} делах от ачивки ‘{achievement}’ — самое время!",
    "Редкое, но щедрое дело: ‘{task}’ — целых +{points} баллов!",
    "Почему бы не устроить ‘{fun_task}’? Это поднимет настроение вам обоим 😊",
]

async def generate_ai_advice(user_id: int):
    advice = "Совет дня не сформирован 😅"
    partner_name = "твой партнёр"

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT name FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return advice
            user_name = row[0]

        partner_id = ADMINS[0] if user_id != ADMINS[0] else ADMINS[1] if len(ADMINS) > 1 else None
        if partner_id:
            async with db.execute('SELECT name FROM users WHERE user_id = ?', (partner_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    partner_name = row[0]

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        async with db.execute('''
            SELECT t.name FROM tasks t
            WHERE t.id NOT IN (
                SELECT task_id FROM completed_tasks 
                WHERE user_id = ? AND date(completed_at) > ?
            )
            ORDER BY RANDOM() LIMIT 1
        ''', (user_id, three_days_ago)) as cursor:
            row = await cursor.fetchone()
            if row:
                task_name = row[0]
                return ADVICE_TEMPLATES[0].format(days="3", task=task_name.lower())

        async with db.execute('''
            SELECT t.category, COUNT(*) as cnt
            FROM completed_tasks ct
            JOIN tasks t ON ct.task_id = t.id
            WHERE ct.user_id = ?
            GROUP BY t.category
            ORDER BY cnt DESC LIMIT 1
        ''', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                top_category, _ = row
                async with db.execute('''
                    SELECT name, points FROM tasks 
                    WHERE category = ? AND id NOT IN (
                        SELECT task_id FROM completed_tasks WHERE user_id = ?
                    )
                    ORDER BY RANDOM() LIMIT 1
                ''', (top_category, user_id)) as cursor:
                    row2 = await cursor.fetchone()
                    if row2:
                        suggestion, points = row2
                        return ADVICE_TEMPLATES[1].format(category=top_category, suggestion=suggestion, points=points)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if partner_id:
            async with db.execute('''
                SELECT t.name FROM completed_tasks ct
                JOIN tasks t ON ct.task_id = t.id
                WHERE ct.user_id = ? AND date(ct.completed_at) = ?
                ORDER BY RANDOM() LIMIT 1
            ''', (partner_id, yesterday)) as cursor:
                row = await cursor.fetchone()
                if row:
                    task_done = row[0]
                    rewards = ["массаж", "чашку чая", "комплимент", "сюрприз"]
                    reward = random.choice(rewards)
                    return ADVICE_TEMPLATES[2].format(partner=partner_name, task=task_done, reward=reward)

        # Проверка ближайшей ачивки
        async with db.execute('''
            SELECT a.name FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
            WHERE ua.id IS NULL
            ORDER BY RANDOM() LIMIT 1
        ''', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                ach_name = row[0]
                return ADVICE_TEMPLATES[4].format(steps="2-3", achievement=ach_name)

    return random.choice(ADVICE_TEMPLATES).format(
        days="несколько",
        task="что-нибудь полезное",
        category="быт",
        suggestion="любое новое дело",
        points="5-10",
        partner=partner_name,
        reward="что-то приятное",
        achievement="следующую ачивку",
        fun_task="танцевальную уборку"
    )

async def send_daily_advice():
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            users = await cursor.fetchall()

    for (user_id,) in users:
        advice = await generate_ai_advice(user_id)
        try:
            await bot.send_message(
                user_id,
                f"🧠 *ИИ-советник говорит:*\n\n{advice}\n\nЭто просто совет — ты молодец в любом случае! ❤️",
                parse_mode="Markdown"
            )
        except:
            pass

# ============ КАЛЕНДАРЬ ============
@dp.message(lambda message: message.text == "📅 Календарь" or message.text.startswith("/calendar"))
async def show_calendar(message: types.Message):
    parts = message.text.split()
    now = datetime.now()
    year, month = now.year, now.month

    if len(parts) > 1:
        try:
            date_str = parts[1]
            year, month = map(int, date_str.split('-'))
        except:
            pass

    month_name_str = month_name[month]
    async with aiosqlite.connect('household.db') as db:
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        async with db.execute('''
            SELECT strftime('%d', completed_at) as day, t.name, t.points, t.category
            FROM completed_tasks ct
            JOIN tasks t ON ct.task_id = t.id
            WHERE ct.user_id = ? AND completed_at >= ? AND completed_at < ?
            ORDER BY completed_at
        ''', (message.from_user.id, start_date, end_date)) as cursor:
            tasks = await cursor.fetchall()

    days = {}
    for day, name, points, category in tasks:
        if day not in days:
            days[day] = []
        days[day].append((name, points, category))

    cal = monthcalendar(year, month)
    lines = []
    lines.append(f"📆 *Календарь: {month_name_str} {year}*")
    lines.append("Пн Вт Ср Чт Пт Сб Вс")

    category_icons = {
        "🍽 КУХНЯ": "🍽",
        "🧹 УБОРКА": "🧹",
        "🧺 СТИРКА": "🧺",
        "🛒 БЫТ": "🛒",
        "🐶 ПИТОМЦЫ": "🐶",
        "💡 ОСОБЫЕ": "💡",
        "Без категории": "📌",
    }

    for week in cal:
        week_str = ""
        icons_str = ""
        for day in week:
            if day == 0:
                week_str += "   "
                icons_str += "  "
            else:
                day_str = f"{day:2d}"
                week_str += day_str + " "
                d_str = str(day)
                if d_str in days:
                    icons = set()
                    for _, _, cat in days[d_str]:
                        icon = category_icons.get(cat, "📌")
                        icons.add(icon)
                    icons_str += "".join(list(icons)[:2])
                else:
                    icons_str += "  "
        lines.append(week_str.rstrip())
        if icons_str.strip():
            lines.append(icons_str)

    lines.append("\n*🍽=кухня 🧹=уборка 🧺=стирка 🛒=быт 👶=дети 💡=особые*")
    lines.append("\nДля подробного просмотра дня — напиши `/day 15`")

    await message.answer("\n".join(lines), parse_mode="Markdown")

@dp.message(lambda message: message.text.startswith("/day"))
async def show_day_details(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Используй: /day <число>")
        return

    try:
        day = int(parts[1])
        now = datetime.now()
        date_str = f"{now.year}-{now.month:02d}-{day:02d}"
    except:
        await message.answer("Неверный формат даты.")
        return

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('''
            SELECT t.name, t.points, t.category
            FROM completed_tasks ct
            JOIN tasks t ON ct.task_id = t.id
            WHERE ct.user_id = ? AND date(ct.completed_at) = ?
            ORDER BY ct.completed_at
        ''', (message.from_user.id, date_str)) as cursor:
            tasks = await cursor.fetchall()

    if not tasks:
        await message.answer(f"📅 В этот день ты ничего не делал(а). Отдыхал(а) — это тоже важно! 😊")
        return

    lines = [f"📅 *{date_str}*", ""]
    total = 0
    for name, points, category in tasks:
        lines.append(f"✅ {name} (+{points} баллов) — {category}")
        total += points

    lines.append(f"\n**Итого: {total} баллов**")
    await message.answer("\n".join(lines), parse_mode="Markdown")

# ============ КВЕСТЫ ============
async def assign_random_quest():
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            users = await cursor.fetchall()

        for (user_id,) in users:
            async with db.execute('SELECT 1 FROM quests WHERE assigned_to = ? AND completed_at IS NULL', (user_id,)) as cursor:
                if await cursor.fetchone():
                    continue

            async with db.execute('SELECT id, name, description, bonus_points FROM quests WHERE assigned_to IS NULL OR completed_at IS NOT NULL ORDER BY RANDOM() LIMIT 1') as cursor:
                row = await cursor.fetchone()
                if not row:
                    continue

                quest_id, name, desc, points = row

                await db.execute('''
                    UPDATE quests
                    SET is_active = 1, assigned_to = ?, assigned_at = ?, completed_at = NULL
                    WHERE id = ?
                ''', (user_id, datetime.now().isoformat(), quest_id))
                await db.commit()

                try:
                    await bot.send_message(
                        user_id,
                        f"✨ *Секретный квест от бота!*\n\n"
                        f"«{name}»\n{desc}\n\n"
                        f"🎯 Бонус: +{points} баллов\n"
                        f"Не обязательно — но будет приятно 😉",
                        parse_mode="Markdown"
                    )
                except:
                    pass

# ============ АЧИВКИ ============
async def check_and_award_achievements(user_id: int, trigger: str = None, data: dict = None, task_name: str = None, category: str = None):
    unlocked = []

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('''
            SELECT a.name FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ?
        ''', (user_id,)) as cursor:
            current = await cursor.fetchall()
        current_names = {row[0] for row in current}

        # ============ ПРОВЕРКА УСЛОВИЙ ============
        # 🦸‍♂️ Героические
        if "Мастер Посудомойки" not in current_names and trigger == "dishwasher_streak" and data.get("days", 0) >= 7:
            unlocked.append("Мастер Посудомойки")

        if "Тень Уборки" not in current_names and trigger == "clean_while_sleep":
            unlocked.append("Тень Уборки")

        if "Гладильный Дракон" not in current_names and trigger == "ironing_session" and data.get("items", 0) >= 20:
            unlocked.append("Гладильный Дракон")

        if "Шеф-невидимка" not in current_names and trigger == "stealth_dinner":
            unlocked.append("Шеф-невидимка")

        if "Мусорный Магнат" not in current_names and trigger == "trash_streak" and data.get("days", 0) >= 5:
            unlocked.append("Мусорный Магнат")

        if "Мастер Переговоров" not in current_names and trigger == "clean_negotiation":
            unlocked.append("Мастер Переговоров")

        # 🐉 Легендарные
        if "Очиститель Храма" not in current_names and trigger == "clean_oven":
            unlocked.append("Очиститель Храма")

        if "Герой Морозилки" not in current_names and trigger == "defrost_freezer":
            unlocked.append("Герой Морозилки")

        if "Сантехник Судьбы" not in current_names and trigger == "fix_faucet":
            unlocked.append("Сантехник Судьбы")

        if "Хранитель Порядка" not in current_names and trigger == "organize_closet":
            unlocked.append("Хранитель Порядка")

        if "Властелин Времени" not in current_names and trigger == "perfect_week":
            unlocked.append("Властелин Времени")

        if "Гуру Бюджета" not in current_names and trigger == "save_money":
            unlocked.append("Гуру Бюджета")

        # 😈 Позорные
        if "Посол Грязи" not in current_names and trigger == "no_dishes" and data.get("days", 0) >= 3:
            unlocked.append("Посол Грязи")

        if "Мастер Откладывания" not in current_names and trigger == "procrastination" and data.get("days", 0) > 7:
            unlocked.append("Мастер Откладывания")

        if "Саботажник Пылесоса" not in current_names and trigger == "ignore_dust":
            unlocked.append("Саботажник Пылесоса")

        if "Гений Забывчивости" not in current_names and trigger == "forgot_trash":
            unlocked.append("Гений Забывчивости")

        if "Король Отговорок" not in current_names and trigger == "excuses" and data.get("count", 0) >= 5:
            unlocked.append("Король Отговорок")

        if "Тролль Уборки" not in current_names and trigger == "leave_dirty_plate":
            unlocked.append("Тролль Уборки")

        # 💘 Романтические
        if "Сердцеед Чистоты" not in current_names and trigger == "clean_with_note":
            unlocked.append("Сердцеед Чистоты")

        if "Ужин при Свечах (и без посуды после)" not in current_names and trigger == "romantic_dinner":
            unlocked.append("Ужин при Свечах (и без посуды после)")

        if "Сюрприз-Атака" not in current_names and trigger == "surprise_massage":
            unlocked.append("Сюрприз-Атака")

        if "Танцпол на Кухне" not in current_names and trigger == "dance_cleaning":
            unlocked.append("Танцпол на Кухне")

        if "Подарочный Ниндзя" not in current_names and trigger == "secret_gift":
            unlocked.append("Подарочный Ниндзя")

        # 🎲 Весёлые
        if "Случайный Гений" not in current_names and trigger == "lifehack":
            unlocked.append("Случайный Гений")

        if "Мем-Мастер" not in current_names and trigger == "funny_photo":
            unlocked.append("Мем-Мастер")

        if "Однорукий Пылесос" not in current_names and trigger == "one_hand_clean":
            unlocked.append("Однорукий Пылесос")

        if "Голосовой Ассистент Реальности" not in current_names and trigger == "voice_assistant":
            unlocked.append("Голосовой Ассистент Реальности")

        if "Спаситель Посуды" not in current_names and trigger == "last_minute_clean":
            unlocked.append("Спаситель Посуды")

        if "Философ Грязи" not in current_names and trigger == "philosophize":
            unlocked.append("Философ Грязи")

        # 👑 Босс-моды
        if "Неделя Без Напоминаний" not in current_names and trigger == "no_reminders_week":
            unlocked.append("Неделя Без Напоминаний")

        if "Месяц Идеального Баланса" not in current_names and trigger == "perfect_balance_month":
            unlocked.append("Месяц Идеального Баланса")

        if "Тёмная Сторона Лени" not in current_names and trigger == "honest_lazy_day":
            unlocked.append("Тёмная Сторона Лени")

        if "Режим Бога Дома" not in current_names and trigger == "god_mode_week" and data.get("points", 0) >= 50:
            unlocked.append("Режим Бога Дома")

        if "Суперкомбо Партнёров" not in current_names and trigger == "team_fun":
            unlocked.append("Суперкомбо Партнёров")

        # 🕵️‍♂️ Секретные — можно выдавать вручную

        # ============ ВЫДАЧА АЧИВОК ============
        for ach_name in unlocked:
            async with db.execute('SELECT id, points, title, icon, description FROM achievements WHERE name = ?', (ach_name,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    ach_id, points, title, icon, desc = row

                    await db.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))

                    if title:
                        await db.execute('''
                            INSERT OR REPLACE INTO user_titles (user_id, title)
                            VALUES (?, ?)
                        ''', (user_id, title))

                    await db.execute('''
                        INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at)
                        VALUES (?, ?, ?)
                    ''', (user_id, ach_id, datetime.now().isoformat()))
                    await db.commit()

                    await bot.send_message(
                        user_id,
                        f"🎉 {icon} *{ach_name}*\n{desc}\n{'+' if points >= 0 else ''}{points} баллов\nТитул: *{title}*",
                        parse_mode="Markdown"
                    )

# ============ ХЕНДЛЕРЫ ============
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    async with aiosqlite.connect('household.db') as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)', (user_id, name))
        await db.commit()

    await message.answer(
        f"Привет, {name}! 👋\nДобро пожаловать в FamilyScoreBot 🏆\nВыбери действие в меню ниже 👇",
        reply_markup=get_main_menu(user_id)
    )

@dp.message(Command("myid"))
async def show_my_id(message: types.Message):
    await message.answer(f"Твой user_id: `{message.from_user.id}`", parse_mode="Markdown")

@dp.message(lambda message: message.text == "📋 Мои дела")
async def handle_my_tasks(message: types.Message):
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT id, name, points, is_team, category FROM tasks ORDER BY category, name') as cursor:
            tasks = await cursor.fetchall()

    if not tasks:
        await message.answer("Нет доступных дел. Админ может добавить через /addtask")
        return

    current_category = ""
    for task_id, name, points, is_team, category in tasks:
        if category != current_category:
            current_category = category
            await message.answer(f"*{category}*", parse_mode="Markdown")

        suffix = " (командное)" if is_team else ""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task_id}"))
        await message.answer(f"🔹 {name} — {points} баллов{suffix}", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith('done_'))
async def handle_task_done(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    name = callback_query.from_user.first_name

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT name, points, is_team, category FROM tasks WHERE id = ?', (task_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await callback_query.answer("Задача не найдена!")
                return
            task_name, points, is_team, category = row

        today = datetime.now().strftime("%Y-%m-%d")
        async with db.execute('''
            SELECT 1 FROM completed_tasks 
            WHERE user_id = ? AND task_id = ? AND date(completed_at) = ?
        ''', (user_id, task_id, today)) as cursor:
            if await cursor.fetchone():
                await callback_query.answer("Ты уже сделал(а) это сегодня! 😊", show_alert=True)
                return

        if is_team:
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="Один", callback_data=f"single_{task_id}"))
            kb.add(InlineKeyboardButton(text="Вместе", callback_data=f"team_{task_id}"))
            await bot.send_message(
                callback_query.message.chat.id,
                "Ты сделал(а) это дело один или вместе с партнёром?",
                reply_markup=kb.as_markup()
            )
            return

        await db.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))
        await db.execute('INSERT INTO completed_tasks (user_id, task_id, completed_at, is_team) VALUES (?, ?, ?, ?)',
                         (user_id, task_id, datetime.now().isoformat(), 0))
        await db.commit()

        if "посудомоечн" in task_name.lower():
            await record_daily_action(user_id, "dishwasher")
            await check_and_award_achievements(user_id, trigger="dishwasher_streak", data={"days": 1})
        if "вынести мусор" in task_name.lower():
            await record_daily_action(user_id, "trash")
            await check_and_award_achievements(user_id, trigger="trash_streak", data={"days": 1})
        if "помыть посуду" in task_name.lower():
            await record_daily_action(user_id, "dishes")
            await check_and_award_achievements(user_id, trigger="no_dishes", data={"days": 1})

        await update_level(user_id)
        await callback_query.answer(f"Отлично! +{points} баллов 🎉")
        await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
        await bot.send_message(callback_query.message.chat.id, f"✅ {name} выполнил(а) задачу и получил(а) {points} баллов!")

@dp.callback_query(lambda c: c.data.startswith('single_') or c.data.startswith('team_'))
async def handle_team_choice(callback_query: types.CallbackQuery):
    prefix, task_id_str = callback_query.data.split('_', 1)
    task_id = int(task_id_str)
    user_id = callback_query.from_user.id
    name = callback_query.from_user.first_name

    is_team = prefix == "team"

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT name, points, category FROM tasks WHERE id = ?', (task_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            task_name, points, category = row

        await db.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, user_id))
        await db.execute('INSERT INTO completed_tasks (user_id, task_id, completed_at, is_team) VALUES (?, ?, ?, ?)',
                         (user_id, task_id, datetime.now().isoformat(), int(is_team)))
        await db.commit()

        if "посудомоечн" in task_name.lower():
            await record_daily_action(user_id, "dishwasher")
        if "вынести мусор" in task_name.lower():
            await record_daily_action(user_id, "trash")
        if "помыть посуду" in task_name.lower():
            await record_daily_action(user_id, "dishes")

        if is_team:
            partner_id = ADMINS[0] if user_id != ADMINS[0] else ADMINS[1] if len(ADMINS) > 1 else None
            if partner_id:
                await db.execute('UPDATE users SET score = score + ? WHERE user_id = ?', (points, partner_id))
                await db.execute('INSERT INTO completed_tasks (user_id, task_id, completed_at, is_team) VALUES (?, ?, ?, ?)',
                                 (partner_id, task_id, datetime.now().isoformat(), 1))
                await db.commit()
                try:
                    await bot.send_message(partner_id, f"🎉 {name} отметил(а), что вы вместе выполнили '{task_name}'! Тебе тоже +{points} баллов!")
                except:
                    pass

        await update_level(user_id)
        if is_team and partner_id:
            await update_level(partner_id)

        await callback_query.answer(f"{'Вместе' if is_team else 'Один'} — +{points} баллов!")
        await bot.send_message(callback_query.message.chat.id, f"✅ {name} {'вместе с партнёром ' if is_team else ''}выполнил(а) '{task_name}'!")

@dp.message(lambda message: message.text == "🏆 Рейтинг")
async def show_score(message: types.Message):
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('''
            SELECT u.name, u.score, u.level, COALESCE(ut.title, "Новичок Быта") as title
            FROM users u
            LEFT JOIN user_titles ut ON u.user_id = ut.user_id
            ORDER BY u.score DESC
        ''') as cursor:
            users = await cursor.fetchall()

    text = "🏆 *Рейтинг семейной команды:*\n\n"
    for i, (name, score, level, title) in enumerate(users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        text += f"{medal} {name}\n— Уровень {level} | *{title}*\n— {score} баллов\n\n"

    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda message: message.text == "🏅 Мои ачивки")
async def show_achievements(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('''
            SELECT a.icon, a.name, a.description
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
        ''', (user_id,)) as cursor:
            achievements = await cursor.fetchall()

    if not achievements:
        await message.answer("Ты пока не получил(а) ни одной ачивки 😅\nВыполняй дела — и они появятся!")
        return

    text = "🏅 *Твои ачивки:*\n\n"
    for icon, name, desc in achievements:
        text += f"{icon} *{name}*\n— {desc}\n\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT name FROM seasons WHERE is_active = 1') as cursor:
            row = await cursor.fetchone()
            current_season = row[0] if row else "Неизвестно"

        async with db.execute('SELECT score, level FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            current_score, current_level = row if row else (0, 1)

        async with db.execute('''
            SELECT SUM(final_score) FROM user_season_archive WHERE user_id = ?
        ''', (user_id,)) as cursor:
            total_score = (await cursor.fetchone())[0] or 0
        total_score += current_score

        year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        async with db.execute('''
            SELECT SUM(points) FROM completed_tasks_archive 
            WHERE user_id = ? AND completed_at >= ?
        ''', (user_id, year_ago)) as cursor:
            year_score = (await cursor.fetchone())[0] or 0

        async with db.execute('SELECT title FROM user_titles WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            current_title = row[0] if row else "Новичок Быта"

    text = f"📊 *Твоя статистика*\n\n"
    text += f"📅 Текущий сезон: *{current_season}*\n"
    text += f"🏆 Текущий уровень: {current_level}\n"
    text += f"🎖️ Титул: *{current_title}*\n"
    text += f"📈 Баллов в сезоне: {current_score}\n\n"
    text += f"📆 За год: {year_score} баллов\n"
    text += f"🏅 За всё время: {total_score} баллов"

    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("champions"))
async def show_champions(message: types.Message):
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT id, name FROM seasons ORDER BY id DESC') as cursor:
            seasons = await cursor.fetchall()

        if not seasons:
            await message.answer("Нет завершённых сезонов.")
            return

        text = "🏆 *Чемпионы сезонов:*\n\n"

        for season_id, season_name in seasons:
            async with db.execute('''
                SELECT u.name, usa.final_score
                FROM user_season_archive usa
                JOIN users u ON usa.user_id = u.user_id
                WHERE usa.season_id = ?
                ORDER BY usa.final_score DESC
                LIMIT 1
            ''', (season_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    champion, score = row
                    text += f"🏅 {season_name}: *{champion}* ({score} баллов)\n"

        await message.answer(text, parse_mode="Markdown")

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(lambda message: message.text == "🛠 Админ-панель")
async def handle_admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет доступа.")
        return
    await message.answer(
        "🛠 *Админ-панель*\n\n"
        "*Управление делами:*\n"
        "`/addtask \"название\" баллы [team] [\"категория\"]`\n"
        "`/edittask ID \"название\" баллы [team] [\"категория\"]`\n"
        "`/deletetask ID`\n\n"
        "*Управление ачивками:*\n"
        "`/addachiv \"название\" \"описание\" \"эмодзи\" баллы \"титул\" \"тип\" [скрытая]`\n"
        "`/deleteachiv ID`\n"
        "`/listachiv`\n\n"
        "*Цели:*\n"
        "`/setgoal \"Описание\" количество`\n\n"
        "*Призы:*\n"
        "`/prize @username описание`",
        parse_mode="Markdown"
    )

# --- Управление делами ---
@dp.message(Command("addtask"))
async def add_task(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    text = message.text[9:].strip()
    args = []
    current = ""
    in_quotes = False
    for char in text:
        if char == '"' and (not current or current[-1] != '\\'):
            in_quotes = not in_quotes
        elif char == ' ' and not in_quotes:
            if current:
                args.append(current)
                current = ""
        else:
            current += char
    if current:
        args.append(current)

    if len(args) < 2:
        await message.answer('Используй: /addtask "название" баллы [team] ["категория"]')
        return

    name = args[0].strip('"')
    try:
        points = int(args[1])
    except:
        await message.answer("Баллы должны быть числом!")
        return

    is_team = len(args) > 2 and args[2].lower() == "team"
    category = args[3].strip('"') if len(args) > 3 else "Без категории"

    async with aiosqlite.connect('household.db') as db:
        try:
            await db.execute('INSERT INTO tasks (name, points, is_team, category) VALUES (?, ?, ?, ?)', (name, points, int(is_team), category))
            await db.commit()
            await message.answer(f"✅ Добавлено {'командное' if is_team else 'личное'} дело: '{name}' за {points} баллов ({category})")
        except aiosqlite.IntegrityError:
            await message.answer("❌ Дело с таким названием уже существует!")

@dp.message(Command("edittask"))
async def edit_task(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    text = message.text[10:].strip()
    args = []
    current = ""
    in_quotes = False
    for char in text:
        if char == '"' and (not current or current[-1] != '\\'):
            in_quotes = not in_quotes
        elif char == ' ' and not in_quotes:
            if current:
                args.append(current)
                current = ""
        else:
            current += char
    if current:
        args.append(current)

    if len(args) < 3:
        await message.answer('Используй: /edittask ID "название" баллы [team] ["категория"]')
        return

    try:
        task_id = int(args[0])
        name = args[1].strip('"')
        points = int(args[2])
    except:
        await message.answer("ID и баллы должны быть числами!")
        return

    is_team = len(args) > 3 and args[3].lower() == "team"
    category = args[4].strip('"') if len(args) > 4 else "Без категории"

    async with aiosqlite.connect('household.db') as db:
        await db.execute('UPDATE tasks SET name = ?, points = ?, is_team = ?, category = ? WHERE id = ?', (name, points, int(is_team), category, task_id))
        if db.total_changes == 0:
            await message.answer("❌ Дело с таким ID не найдено.")
        else:
            await db.commit()
            await message.answer(f"✅ Дело ID {task_id} обновлено!")

@dp.message(Command("deletetask"))
async def delete_task(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используй: /deletetask <ID>")
        return

    try:
        task_id = int(args[1])
    except:
        await message.answer("ID должен быть числом!")
        return

    async with aiosqlite.connect('household.db') as db:
        await db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        await db.commit()
        await message.answer(f"🗑️ Дело ID {task_id} удалено!")

# --- Управление ачивками ---
@dp.message(Command("addachiv"))
async def add_achievement(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    text = message.text[10:].strip()
    args = []
    current = ""
    in_quotes = False
    for char in text:
        if char == '"' and (not current or current[-1] != '\\'):
            in_quotes = not in_quotes
        elif char == ' ' and not in_quotes:
            if current:
                args.append(current)
                current = ""
        else:
            current += char
    if current:
        args.append(current)

    if len(args) < 6:
        await message.answer('Используй: /addachiv "название" "описание" "эмодзи" баллы "титул" "тип" [скрытая]')
        return

    name = args[0].strip('"')
    desc = args[1].strip('"')
    icon = args[2].strip('"')
    try:
        points = int(args[3])
    except:
        await message.answer("Баллы должны быть числом!")
        return
    title = args[4].strip('"')
    ach_type = args[5].strip('"')
    is_hidden = len(args) > 6 and args[6].lower() == "true"

    async with aiosqlite.connect('household.db') as db:
        try:
            await db.execute('''
                INSERT INTO achievements (name, description, icon, points, title, type, is_hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, desc, icon, points, title, ach_type, int(is_hidden)))
            await db.commit()
            await message.answer(f"✅ Добавлена ачивка: '{name}' ({ach_type})")
        except aiosqlite.IntegrityError:
            await message.answer("❌ Ачивка с таким названием уже существует!")

@dp.message(Command("deleteachiv"))
async def delete_achievement(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Используй: /deleteachiv <ID>")
        return

    try:
        ach_id = int(args[1])
    except:
        await message.answer("ID должен быть числом!")
        return

    async with aiosqlite.connect('household.db') as db:
        await db.execute('DELETE FROM achievements WHERE id = ?', (ach_id,))
        await db.commit()
        await message.answer(f"🗑️ Ачивка ID {ach_id} удалена!")

@dp.message(Command("listachiv"))
async def list_achievements(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У тебя нет прав.")
        return

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT id, name, type, points FROM achievements ORDER BY type, name') as cursor:
            achievements = await cursor.fetchall()

    if not achievements:
        await message.answer("Нет ачивок.")
        return

    categories = {
        "heroic": "🦸‍♂️ ГЕРОИЧЕСКИЕ",
        "legendary": "🌟 ЛЕГЕНДАРНЫЕ",
        "romantic": "💘 РОМАНТИЧЕСКИЕ",
        "funny": "🎲 ВЕСЁЛЫЕ",
        "boss": "👑 БОСС-МОДЫ",
        "shameful": "🤡 ПОЗОРНЫЕ",
        "secret": "🕵️‍♂️ СЕКРЕТНЫЕ",
    }

    text = "📋 *Все ачивки:*\n\n"
    current_type = ""

    for ach_id, name, ach_type, points in achievements:
        if ach_type != current_type:
            current_type = ach_type
            text += f"\n*{categories.get(ach_type, ach_type.upper())}*\n"
        sign = "+" if points >= 0 else ""
        text += f"ID {ach_id}: {name} ({sign}{points} баллов)\n"

    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("setgoal"))
async def set_weekly_goal(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только админ может задавать цели.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer('Используй: /setgoal "Описание цели" количество')
        return

    desc = args[1].strip('"')
    try:
        target = int(args[2])
    except:
        await message.answer("Количество должно быть числом!")
        return

    async with aiosqlite.connect('household.db') as db:
        await db.execute('INSERT INTO weekly_goals (description, target_count, created_at) VALUES (?, ?, ?)',
                         (desc, target, datetime.now().isoformat()))
        await db.commit()

    await message.answer(f"🎯 Установлена новая цель на неделю:\n«{desc}» — нужно сделать {target} дел вместе!")

@dp.message(Command("prize"))
async def award_prize(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только админы могут выдавать призы.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Используй: /prize @username описание_приза")
        return

    _, username, prize_desc = args
    target_username = username.lstrip('@')

    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT user_id FROM users WHERE name = ?', (target_username,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("Пользователь не найден. Убедись, что он запускал бота.")
                return
            target_id = row[0]

    try:
        await bot.send_message(
            target_id,
            f"🏆 *Ты получил приз!*\n\n"
            f"Администратор наградил тебя за отличную работу:\n"
            f"🎁 *{prize_desc}*\n\n"
            f"Поздравляем! Продолжай в том же духе!",
            parse_mode="Markdown"
        )
        await message.answer(f"✅ Приз успешно отправлен пользователю @{target_username}!")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить приз: {e}")

# ============ НАПОМИНАНИЯ ============
async def send_daily_reminders():
    async with aiosqlite.connect('household.db') as db:
        async with db.execute('SELECT user_id, name FROM users') as cursor:
            users = await cursor.fetchall()
        async with db.execute('SELECT name, points, category FROM tasks ORDER BY category, name') as cursor:
            tasks = await cursor.fetchall()

    if not users or not tasks:
        return

    categories = {}
    for name, points, category in tasks:
        if category not in categories:
            categories[category] = []
        categories[category].append(f"• {name} (+{points} баллов)")

    for user_id, name in users:
        try:
            text = f"👋 Привет, {name}!\n\n*Не забудь сегодня выполнить дела:*\n\n"
            for cat, items in categories.items():
                text += f"*{cat}*\n" + "\n".join(items) + "\n\n"
            text += "Жми '📋 Мои дела', чтобы отметить выполненные!"
            await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=get_main_menu(user_id))
        except Exception as e:
            print(f"Ошибка отправки напоминания: {e}")

async def send_weekly_report():
    report_chat_id = ADMINS[0]

    async with aiosqlite.connect('household.db') as db:
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        async with db.execute('''
            SELECT u.name, COUNT(ct.id), SUM(t.points)
            FROM completed_tasks ct
            JOIN users u ON ct.user_id = u.user_id
            JOIN tasks t ON ct.task_id = t.id
            WHERE ct.completed_at > ?
            GROUP BY u.user_id
            ORDER BY SUM(t.points) DESC
        ''', (week_ago,)) as cursor:
            weekly_stats = await cursor.fetchall()

        async with db.execute('''
            SELECT description, target_count, created_at, achieved_at
            FROM weekly_goals
            ORDER BY id DESC LIMIT 1
        ''') as cursor:
            goal_row = await cursor.fetchone()

    text = "📊 *Еженедельный отчёт FamilyScoreBot*\n"
    text += f"🗓️ {datetime.now().strftime('%d.%m.%Y')}\n\n"

    if weekly_stats:
        text += "🎖️ *Рейтинг недели:*\n"
        for i, (name, count, points) in enumerate(weekly_stats, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} {name} — {count} дел, {points} баллов\n"

    if goal_row:
        desc, target, created, achieved = goal_row
        async with aiosqlite.connect('household.db') as db:
            async with db.execute('''
                SELECT COUNT(*) FROM completed_tasks WHERE completed_at > ?
            ''', (week_ago,)) as cursor:
                total_done = (await cursor.fetchone())[0]

        if not achieved and total_done >= target:
            text += f"\n🎯 *ЦЕЛЬ ДОСТИГНУТА!* {desc}\n🎉 Поздравляем семью!"
            async with aiosqlite.connect('household.db') as db:
                await db.execute('UPDATE weekly_goals SET achieved_at = ? WHERE description = ?', (datetime.now().isoformat(), desc))
                await db.commit()
        else:
            text += f"\n🎯 *Цель недели:* {desc}\n📈 Прогресс: {total_done}/{target}"

    text += "\n\nОтдыхайте и готовьтесь к новой неделе! 💪"

    try:
        await bot.send_message(report_chat_id, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки отчёта: {e}")

# ============ ЗАПУСК ============
async def main():
    await init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_reminders, CronTrigger(hour=19, minute=0))
    scheduler.add_job(send_weekly_report, CronTrigger(day_of_week='sun', hour=20, minute=0))
    scheduler.add_job(create_new_season, CronTrigger(day=1, hour=0, minute=0))
    scheduler.add_job(assign_random_quest, CronTrigger(day_of_week='mon,wed,fri', hour=10, minute=0))
    scheduler.add_job(send_daily_advice, CronTrigger(hour=12, minute=0))
    scheduler.start()

    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
