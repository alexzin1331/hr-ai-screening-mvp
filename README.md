# HR AI Screening MVP

Production-like MVP для локального запуска HR screening системы: вакансии, загрузка PDF/DOCX/ZIP, LLM extraction, scoring, email invitation, Telegram onboarding через deep link `/start`, MVP screening-диалог, dashboard, экспорт и подробные логи.

## 1. Аудит текущей схемы контакта

Почему схема с `@username` неверна:

- Telegram Bot API не гарантирует возможность написать пользователю первым по `@username`;
- для личных сообщений боту нужен реальный `telegram_chat_id`;
- `username` может отсутствовать, меняться и не является надёжным delivery key;
- попытка первичного outreach напрямую в Telegram даёт `400 Bad Request` и ломает expected flow.

Почему схема `email -> deep link -> /start -> chat_id` правильнее:

- email подходит как первичный внешний канал контакта;
- deep link `https://t.me/<BOT_USERNAME>?start=<invite_token>` безопасно переносит invite context;
- после `/start` бот получает `chat_id`, и дальше Telegram становится штатным двусторонним каналом;
- статусная модель прозрачна: `email_invite_sent`, `awaiting_candidate_start`, `telegram_connected`, `screening_in_progress`, `screening_completed`.

Минимальные изменения для быстрого MVP:

- расширить модель `Candidate` полями email-invite и Telegram binding;
- перевести outreach с Telegram username на email invite;
- добавить webhook `POST /telegram/webhook` для `/start <invite_token>`;
- сохранить screening-диалог в `screening_sessions.messages_json`;
- использовать `telegram_chat_id` как единственный идентификатор доставки в Telegram.

## 2. Новая архитектура

```text
app/
  api/routes/
  core/
  db/
  integrations/email/
  integrations/llm/
  models/
  repositories/
  schemas/
  services/
dashboard/
alembic/
tests/
```

Ключевые файлы:

- приложение: [app/main.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/main.py)
- candidate model: [app/models/candidate.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/models/candidate.py)
- email service: [app/services/email_service.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/email_service.py)
- invite token generator: [app/utils/tokens.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/utils/tokens.py)
- screening / telegram onboarding: [app/services/screening.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/screening.py)
- telegram sender: [app/services/telegram_service.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/telegram_service.py)
- миграции: [alembic/versions/20260311_0001_initial.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/alembic/versions/20260311_0001_initial.py), [alembic/versions/20260311_0002_email_invite_onboarding.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/alembic/versions/20260311_0002_email_invite_onboarding.py)
- dashboard: [dashboard/index.html](/Users/v/PycharmProjects/hr-ai-screening-mvp/dashboard/index.html), [dashboard/app.js](/Users/v/PycharmProjects/hr-ai-screening-mvp/dashboard/app.js)

## 3. Что реализовано

- FastAPI backend с новым API под `/api`
- PostgreSQL-ready модель кандидата с `telegram_chat_id`, `invite_token`, `contact_status`, `email_invite_status`
- email-first outreach через Resend Email API
- официальный Python SDK `resend`
- deep link generation для Telegram bot onboarding
- webhook для `/start <invite_token>`
- polling-режим для локальной разработки без публичного webhook
- MVP screening flow после подключения кандидата
- хранение screening сообщений в БД
- экспорт кандидатов с новыми полями контакта
- dashboard под email invite flow
- Alembic migration для новой модели контакта

## 4. Переменные окружения

См. шаблон: [.env.example](/Users/v/PycharmProjects/hr-ai-screening-mvp/.env.example)

Минимальный локальный `.env`:

```env
APP_ENV=development
DEBUG=true
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:6432/hr_ai_screening
LLM_PROVIDER=mock
EMAIL_PROVIDER=resend
RESEND_API_KEY=your_resend_api_key
RESEND_EMAIL_FROM=HR AI Screening <onboarding@resend.dev>
TELEGRAM_BOT_TOKEN=
BOT_USERNAME=your_bot_username
TELEGRAM_POLLING_ENABLED=true
INVITE_TOKEN_TTL_HOURS=168
```

## 5. EMAIL INVITATIONS (Resend)

1. Создайте аккаунт на `https://resend.com`
2. Получите `RESEND_API_KEY`
3. Добавьте ключ и sender в `.env`
4. Установите зависимости: `pip install -r requirements.txt`

Минимальная конфигурация:

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxx
RESEND_EMAIL_FROM=HR AI Screening <onboarding@resend.dev>
BOT_USERNAME=your_telegram_bot_username
```

Сервис отправки реализован в [app/services/email_service.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/email_service.py) и использует официальный SDK `resend`.

## 6. TELEGRAM POLLING ДЛЯ ЛОКАЛЬНОЙ РАЗРАБОТКИ

Если backend запущен локально и у него нет публичного `https` URL, webhook от Telegram работать не будет. Для этого добавлен polling worker в [app/services/telegram_polling.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/telegram_polling.py).

Минимальная настройка:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
BOT_USERNAME=your_bot_username
TELEGRAM_POLLING_ENABLED=true
TELEGRAM_POLLING_TIMEOUT_SECONDS=25
TELEGRAM_POLLING_RETRY_DELAY_SECONDS=3
```

Что делает polling mode:

- при старте приложения вызывает `deleteWebhook`
- затем циклически читает `getUpdates`
- передаёт `/start TOKEN` и обычные сообщения в существующий screening flow
- не требует `ngrok` или публичного домена для локального MVP

## 7. Запуск

Через Docker только БД:

```bash
docker compose up -d db
```

Локально backend:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn backend:app --reload
```

Если PostgreSQL проброшен как `6432:5432`, то в `.env` должно быть:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:6432/hr_ai_screening
```

## 8. Основные API endpoints

- `POST /api/vacancies`
- `POST /api/vacancies/{vacancy_id}/resumes/upload`
- `GET /api/vacancies/{vacancy_id}/candidates`
- `POST /api/vacancies/{vacancy_id}/send-invites`
- `POST /api/telegram/webhook`
- `GET /api/candidates/{candidate_id}`
- `GET /health/live`
- `GET /health/ready`

Legacy compatibility сохранена для старых эндпоинтов, но primary flow теперь email-first.

## 9. Примеры API-запросов

Создать вакансию:

```bash
curl -X POST http://localhost:8000/api/vacancies \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Backend Engineer",
    "description": "Нужен инженер с FastAPI и PostgreSQL",
    "hard_skills": ["Python", "FastAPI", "PostgreSQL"],
    "soft_skills": ["Communication"],
    "seniority": "Middle",
    "status": "active"
  }'
```

Загрузить резюме:

```bash
curl -X POST http://localhost:8000/api/vacancies/1/resumes/upload \
  -F "file=@./resumes.zip" \
  -F "consent_to_personal_data_processing=true"
```

Запустить отправку invite-писем:

```bash
curl -X POST http://localhost:8000/api/vacancies/1/send-invites \
  -H "Content-Type: application/json" \
  -d '{"top_n": 5, "refresh_invite_token": false}'
```

Webhook `/start` от Telegram:

```bash
curl -X POST http://localhost:8000/api/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "text": "/start INVITE_TOKEN",
      "chat": {"id": 777001},
      "from": {"username": "candidate_username"}
    }
  }'
```

Получить кандидата:

```bash
curl http://localhost:8000/api/candidates/1
```

## 10. Как читать логи

Логи пишутся в `stdout`.

Ищи в логах:

- `request_id` для запроса;
- `vacancy_id`, `candidate_id` для пайплайна;
- частично маскированный `invite_token`;
- этапы: `email_extracted`, `invite_token_generated`, `email_send_attempt`, `email_send_success`, `email_send_error`, `candidate_started_telegram`, `telegram_chat_linked`.

Основные файлы логики:

- logging middleware: [app/core/logging.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/core/logging.py)
- pipeline: [app/services/pipeline.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/pipeline.py)
- email flow: [app/services/email_service.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/email_service.py)
- telegram onboarding: [app/services/screening.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/screening.py)
- telegram polling: [app/services/telegram_polling.py](/Users/v/PycharmProjects/hr-ai-screening-mvp/app/services/telegram_polling.py)

Типовые контактные статусы:

- `email_missing`
- `email_invite_pending`
- `email_invite_sent`
- `awaiting_candidate_start`
- `telegram_connected`
- `screening_in_progress`
- `screening_completed`
- `contact_failed`

## 11. Тесты

Запуск:

```bash
pytest
```

Покрыто:

- create vacancy
- upload resumes
- email outreach
- telegram `/start`
- resend email service unit test
- broken zip
- unsupported file
- empty resume
- invalid LLM response

Полный рабочий код разложен по файлам в репозитории. После `pip install -r requirements.txt`, настройки `.env` и `alembic upgrade head` проект готов к локальному запуску.
