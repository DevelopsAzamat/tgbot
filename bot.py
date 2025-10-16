import os
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import requests
import json
import aiohttp

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("Ошибка: проверь .env файл")
    exit()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Используем экспериментальную модель, которая работает с твоим ключом
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

print(f"Используем модель: gemini-2.0-flash-exp")

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('requests.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_request(user_id, username, first_name, last_name, user_message, bot_response):
    conn = sqlite3.connect('requests.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests (user_id, username, first_name, last_name, user_message, bot_response)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, user_message, bot_response))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('requests.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM requests')
    total_requests = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM requests')
    unique_users = cursor.fetchone()[0]
    cursor.execute('''
        SELECT username, user_message, timestamp 
        FROM requests 
        ORDER BY timestamp DESC 
        LIMIT 5
    ''')
    recent_requests = cursor.fetchall()
    conn.close()
    return {
        'total_requests': total_requests,
        'unique_users': unique_users,
        'recent_requests': recent_requests
    }

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="О боте"), KeyboardButton(text="Примеры запросов")],
        [KeyboardButton(text="Помощь"), ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Напишите ваш вопрос..."
)

@dp.message(CommandStart())
async def start_command(message: Message):
    welcome_text = """
<b>Добро пожаловать в умный чат-бот!</b>

Я помогу вам с:
• Ответами на вопросы
• Решением задач
• Объяснением сложных тем
• Творческими идеями

Просто напишите ваш вопрос или выберите опцию ниже.
    """
    await message.answer(welcome_text, reply_markup=main_keyboard)

@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = """
<b>Справка по использованию бота</b>

Команды:
/start - начать работу
/help - показать справку
/myid - узнать свой ID
/stats - статистика (только для админа)

Примеры запросов:
• "Объясни квантовую физику простыми словами"
• "Напиши план для изучения Python"
• "Помоги решить математическую задачу"
• "Расскажи интересный факт о космосе"
    """
    await message.answer(help_text)

@dp.message(Command("myid"))
async def get_my_id(message: Message):
    user = message.from_user
    user_info = f"""
<b>Ваши данные:</b>

ID: <code>{user.id}</code>
Имя: {user.first_name}
Фамилия: {user.last_name or 'Не указана'}
Username: @{user.username or 'Не указан'}
    """
    await message.answer(user_info)

@dp.message(Command("stats"))
async def stats_command(message: Message):
    YOUR_ADMIN_ID = 6368916881
    
    if message.from_user.id == YOUR_ADMIN_ID:
        stats = get_stats()
        stats_text = f"""
<b>Статистика бота</b>

Модель: gemini-2.0-flash-exp
Всего пользователей: {stats['unique_users']}
Всего запросов: {stats['total_requests']}
"""
        
        if stats['recent_requests']:
            stats_text += "\n<b>Последние запросы:</b>"
            for i, (username, user_message, timestamp) in enumerate(stats['recent_requests'], 1):
                # Исправляем обработку None значений
                safe_username = username or "Нет username"
                safe_message = user_message or "Пустой запрос"
                short_message = safe_message[:50] + "..." if len(safe_message) > 50 else safe_message
                
                stats_text += f"\n{i}. @{safe_username}: {short_message}"
                stats_text += f"\n   Время: {timestamp}"
        else:
            stats_text += "\n\nПока нет запросов."
        
        await message.answer(stats_text)
    else:
        await message.answer("❌ Эта команда доступна только администратору")

@dp.message(F.text == "О боте")
async def about_bot(message: Message):
    about_text = """
<b>О боте</b>

Я - интеллектуальный текстовый, основанный на модели Gemini 2.0 Flash Experimental, разработчиком @azastln.

Мои возможности:
• Отвечать на вопросы любой сложности
• Помогать с учебой и работой
• Объяснять сложные концепции
• Поддерживать беседу на различные темы
    """
    await message.answer(about_text)

@dp.message(F.text == "Примеры запросов")
async def examples(message: Message):
    examples_text = """
<b>Примеры запросов для вдохновения:</b>

Образование:
• "Объясни теорию относительности"
• "Помоги с домашним заданием по математике"
• "Расскажи о Древнем Риме"

Творчество:
• "Напиши короткий рассказ о космосе"
• "Придумай идеи для стартапа"
• "Составь план тренировок"

Помощь:
• "Как научиться программировать?"
• "Давай подготовимся к собеседованию"
• "Объясни эту научную статью"
    """
    await message.answer(examples_text)


@dp.message(F.text == "Помощь")
async def help_button(message: Message):
    await help_command(message)

async def call_gemini_api(user_text: str) -> str:
    """Функция для вызова Gemini API с улучшенной обработкой языков"""
    
    # Определяем язык запроса и создаем соответствующий промпт
    central_asian_keywords = [
        # Казахский
        "сәлем", "салем", "жарайды", "рахмет", "көмек", "сурау",
        # Узбекский
        "салом", "хайр", "рахмат", "ёрдам", "сўров",
        # Кыргызский
        "салам", "жакшы", "рахмат", "жардам", "суроо",
        # Таджикский
        "салом", "хуб", "рахмат", "ёрдам", "пурсиш"
    ]
    
    is_central_asian = any(keyword in user_text.lower() for keyword in central_asian_keywords)
    
    # Специальные ответы для вопросов о создателе
    creator_questions = [
        "кто твой создатель", "кто создал тебя", "who created you", 
        "ким сені жасады", "ким сени жасанды", "сені кім жасады",
        "сени ким жасанды", "ким сенди жаратты", "сенди ким жаратты"
    ]
    
    if any(question in user_text.lower() for question in creator_questions):
        if is_central_asian:
            return "Мені жасаған - Azamatstln (Азаматстлн). Ол боттарды әзірлеумен айналысады және мені жаратты."
        else:
            return "Меня создал Azamatstln. Он занимается разработкой ботов и создал меня."
    
    # Улучшенный промпт для более человеческих ответов с поддержкой языков
    if is_central_asian:
        prompt = f"""Ты - умный помощник, который дает четкие, структурированные ответы. 

Требования к ответу:
1. Если запрос на казахском, узбекском, кыргызском или другом языке Средней Азии - отвечай на том же языке
2. Если запрос смешанный или непонятный - отвечай на русском
3. Будь конкретным и по делу
4. Избегай лишних эмоций и смайликов
5. Структурируй ответ, если тема сложная
6. Используй простой и понятный язык
7. Не добавляй вступление вроде "Привет! Я рад помочь"
8. Давай информацию сразу по существу
9. Если вопрос простой - отвечай кратко
10. Если сложный - разбивай на логические части

Запрос пользователя: {user_text}

Ответ:"""
    else:
        prompt = f"""Ты - умный помощник, который дает четкие, структурированные ответы на русском языке. 

Требования к ответу:
1. Будь конкретным и по делу
2. Избегай лишних эмоций и смайликов
3. Структурируй ответ, если тема сложная
4. Используй простой и понятный язык
5. Не добавляй вступление вроде "Привет! Я рад помочь"
6. Давай информацию сразу по существу
7. Если вопрос простой - отвечай кратко
8. Если сложный - разбивай на логические части

Запрос пользователя: {user_text}

Ответ:"""

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "topK": 40,
            "topP": 0.8,
            "maxOutputTokens": 2048,
        }
    }

    headers = {'Content-Type': 'application/json'}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                
                if "candidates" in data and data["candidates"]:
                    answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return answer
                else:
                    return "Не удалось получить ответ от AI. Попробуйте переформулировать вопрос."
                    
    except Exception as e:
        print(f"API Error: {e}")
        return "Техническая ошибка. Попробуйте позже."

@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        thinking_msg = await message.answer("Обрабатываю ваш запрос...")
        
        answer = await call_gemini_api(user_text)
        
        await bot.delete_message(message.chat.id, thinking_msg.message_id)
        
        # Сохраняем запрос в базу данных
        user = message.from_user
        save_request(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            user_message=user_text,
            bot_response=answer[:500]
        )
        
        # Отправляем чистый ответ без лишнего оформления
        await message.answer(answer)
            
    except Exception as e:
        error_msg = "Произошла непредвиденная ошибка. Попробуйте еще раз."
        await message.answer(error_msg)
        print(f"Unexpected error: {e}")

async def self_test():
    """Функция для самопроверки бота"""
    try:
        # Отправляем тестовый запрос самому себе
        test_message = "Привет! Ответь коротко - ты работаешь?"
        print("Отправляю тестовый запрос...")
        
        answer = await call_gemini_api(test_message)
        print(f"Тестовый ответ: {answer}")
        
        return True
    except Exception as e:
        print(f"Ошибка самопроверки: {e}")
        return False

async def keep_alive():
    """Функция для поддержания активности бота"""
    while True:
        try:
            # Проверяем соединение с ботом
            me = await bot.get_me()
            print(f"Бот активен: {me.username} - {datetime.now()}")
            
            # Выполняем самопроверку каждые 10 минут
            await self_test()
            
        except Exception as e:
            print(f"Ошибка поддержания активности: {e}")
        
        # Ждем 10 минут до следующей проверки
        await asyncio.sleep(600)

def view_database():
    conn = sqlite3.connect('requests.db')
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("ПРОСМОТР БАЗЫ ДАННЫХ ЗАПРОСОВ")
    print("="*50)
    
    cursor.execute('SELECT COUNT(*) FROM requests')
    total = cursor.fetchone()[0]
    print(f"Всего запросов: {total}")
    
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM requests')
    unique_users = cursor.fetchone()[0]
    print(f"Уникальных пользователей: {unique_users}")
    
    print(f"\nПоследние 10 запросов:")
    print("-" * 50)
    
    cursor.execute('''
        SELECT user_id, username, user_message, timestamp 
        FROM requests 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''')
    
    requests = cursor.fetchall()
    for i, (user_id, username, user_message, timestamp) in enumerate(requests, 1):
        # Исправляем обработку None значений
        safe_username = username or "Нет username"
        safe_message = user_message or "Пустой запрос"
        short_msg = safe_message[:60] + "..." if len(safe_message) > 60 else safe_message
        
        print(f"{i}. ID: {user_id} | @{safe_username}")
        print(f"   Запрос: {short_msg}")
        print(f"   Время: {timestamp}")
        print()
    
    conn.close()

async def main():
    init_db()
    print("База данных инициализирована!")
    print("Бот запущен с моделью: gemini-2.0-flash-exp")
    
    view_database()
    
    # Запускаем фоновую задачу для поддержания активности
    asyncio.create_task(keep_alive())
    
    print("Фоновая задача поддержания активности запущена!")
    
    # Запускаем опрос
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Для Render важно обрабатывать корректное завершение
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        # Перезапускаем через некоторое время
        asyncio.run(asyncio.sleep(5))
        asyncio.run(main())
