# HR AI Screening MVP

Проект состоит из двух сервисов:

- `hr-ai-screening-mvp` - основной FastAPI backend, загрузка резюме, вакансии, email/Telegram flow, dashboard
- `dialog_scoring_service` - отдельный FastAPI сервис для оценки ответов кандидата по эмбеддингам и расчёта `SCORE SOFT SKILLS`

## Быстрый запуск

### 1. Backend

```bash
cd hr-ai-screening-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
docker compose up -d db
alembic upgrade head
uvicorn backend:app --reload
```

Backend будет доступен на `http://127.0.0.1:8000`.

Обязательный минимум в `.env` для локального старта:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:6432/hr_ai_screening
LLM_PROVIDER=mock
EMAIL_PROVIDER=mock
TELEGRAM_POLLING_ENABLED=false
```

Если нужен Telegram onboarding:

```env
TELEGRAM_BOT_TOKEN=...
BOT_USERNAME=...
TELEGRAM_POLLING_ENABLED=true
```

Если нужен полный scoring после ответов кандидата в Telegram:

```env
DIALOG_SCORING_API_URL=http://127.0.0.1:8001
```

Если нужен email через Resend:

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=...
RESEND_EMAIL_FROM=HR AI Screening <onboarding@resend.dev>
```

### 2. Dialog Scoring Service

Нужен только если хотите включить оценку диалога после Telegram screening.

```bash
cd dialog_scoring_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001
```

После этого в `hr-ai-screening-mvp/.env` добавьте:

```env
DIALOG_SCORING_API_URL=http://127.0.0.1:8001
```

Backend принимает и базовый URL сервиса, и полный endpoint. Если указан только хост, путь `/evaluate` добавляется автоматически.

## Проверка

```bash
cd hr-ai-screening-mvp
pytest -q
```

## Требования к компьютеру

Минимум для backend без ML-сервиса:

- CPU: 2 ядра
- RAM: 4 GB
- Диск: 2-3 GB свободно
- Docker Desktop или локальный PostgreSQL 16
- Python 3.12

Рекомендуемо для запуска вместе с `dialog_scoring_service`:

- CPU: 4 ядра
- RAM: 8-16 GB
- Диск: 8-12 GB свободно
- Стабильный интернет при первом запуске ML-модели, потому что `sentence-transformers` скачает модель

## Что проверить перед использованием

- `pytest -q` должен проходить в `hr-ai-screening-mvp`
- PostgreSQL должен отвечать на порту `6432`
- для Telegram нужен валидный `TELEGRAM_BOT_TOKEN`
- для Resend нужен валидный `RESEND_API_KEY`
- для soft skills scoring должен быть поднят `dialog_scoring_service`
- `dialog_scoring_service` не стартует только по корневому `requirements.txt`, ему нужны отдельные ML-зависимости
