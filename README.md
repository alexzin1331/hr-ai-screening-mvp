1. Установить зависимости
pip install -r requirements.txt
2. Создать файл .env

В корне проекта создать файл .env:

TELEGRAM_BOT_TOKEN=your_bot_token

OPENAI_API_KEY=your_api_key

3. Создать Telegram бота

Открыть бота @BotFather в Telegram

Выполнить команду:

/newbot

Скопировать токен и вставить в .env.

после этого
https://console.groq.com

Скопируйте ключ и вставьте в:

GROQ_API_KEY

4. Запустить backend
uvicorn backend:app --reload

Сервер запустится на:

http://localhost:8000
5. Открыть dashboard

В браузере открыть:

http://localhost:8000
