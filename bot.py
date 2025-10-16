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
        [KeyboardButton(text="Помощь"), 
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

Я - интеллектуальный помощник STLNbot, основанным @azastln, на модели Gemini 2.0 Flash Experimental.

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

@dp.message()
async def handle_message(message: Message):
    user_text = message.text
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        thinking_msg = await message.answer("Обрабатываю ваш запрос...")
        
        # Улучшенный промпт для более человеческих ответов
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""Ты - умный человек, который дает четкие, структурированные ответы на русском языке для моего развитие. 

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
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,  # Более консервативные ответы
                "topK": 40,
                "topP": 0.8,
                "maxOutputTokens": 2048,
            }
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if "candidates" in data and data["candidates"]:
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
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
            
        else:
            error_msg = "Не удалось получить ответ от AI. Попробуйте переформулировать вопрос."
            await message.answer(error_msg)
            
            user = message.from_user
            save_request(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                user_message=user_text,
                bot_response="ОШИБКА: Не удалось получить ответ от AI"
            )

    except requests.exceptions.Timeout:
        error_msg = "Время ожидания истекло. Попробуйте еще раз."
        await message.answer(error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = "Техническая ошибка. Попробуйте позже."
        await message.answer(error_msg)
        print(f"Network error: {e}")
    
    except Exception as e:
        error_msg = "Произошла непредвиденная ошибка. Попробуйте еще раз."
        await message.answer(error_msg)
        print(f"Unexpected error: {e}")

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
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
