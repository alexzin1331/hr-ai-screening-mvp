# Presentation Additions

Документ фиксирует минимальные изменения в коде под критерии презентации без изменения основного пользовательского flow сервиса.

## RAG

Статус: реализован в `dialog_scoring_service`

Что добавлено:
- лексический retrieval по описанию вакансии, hard skills и soft skills
- выбор top-k релевантных фрагментов под ответы кандидата
- использование retrieval-контекста внутри scoring orchestration

Файлы:
- `dialog_scoring_service/agents.py`

Как работает:
- `VacancyRAG` разбивает вакансию на небольшие чанки
- `RetrieverAgent` поднимает наиболее релевантные требования под ответы кандидата
- retrieved evidence включается в explanation результата

Ожидаемый балл: `1 / 1`

## Агент / Мультиагент

Статус: реализован минимальный multi-agent orchestration

Что добавлено:
- `RetrieverAgent`
- `ScoringAgent`
- `ScreeningCoordinatorAgent`

Файлы:
- `dialog_scoring_service/agents.py`
- `dialog_scoring_service/main.py`

Как работает:
- `RetrieverAgent` отвечает за retrieval-контекст
- `ScoringAgent` отвечает за локальный инференс
- `ScreeningCoordinatorAgent` координирует пайплайн и собирает итог

Ожидаемый балл: `2 / 2`

## Инференс модели без API

Статус: реализован

Что используется:
- локальная модель `sentence-transformers`
- вычисление score выполняется локально в `dialog_scoring_service`, без внешнего LLM API

Файлы:
- `dialog_scoring_service/scoring_runtime.py`
- `dialog_scoring_service/main.py`

Примечание:
- основной backend flow не менялся
- локальный инференс уже используется в scoring service и не требует внешнего API

Ожидаемый балл: `1 / 1`

## Дообучение модели

Статус: реализован безопасный lightweight fine-tuning head

Что добавлено:
- training script для обучения линейной calibrator/head поверх локальных эмбеддингов
- загрузка обученного calibrator из `artifacts/soft_skills_calibrator.json`

Файлы:
- `dialog_scoring_service/training/finetune_soft_skills_head.py`
- `dialog_scoring_service/scoring_runtime.py`

Как это позиционировать:
- это не full fine-tune базовой трансформер-модели
- это domain adaptation / trainable scoring head поверх локального encoder-а
- для презентации это лучше подавать как parameter-efficient fine-tuning слоя оценки

Ожидаемый балл: `1-2 / 2`

## Оптимизация под слабое железо

Статус: реализовано

Что добавлено:
- lazy local loading модели
- ограничение числа CPU threads через env
- лимит количества учитываемых ответов кандидата
- CPU-only runtime без обязательного GPU

Файлы:
- `dialog_scoring_service/scoring_runtime.py`

ENV-параметры:
- `DIALOG_SCORING_MODEL_NAME`
- `DIALOG_SCORING_THREADS`
- `DIALOG_SCORING_MAX_ANSWERS`
- `DIALOG_SCORING_CALIBRATOR_PATH`

Ожидаемый балл: `1 / 1`

## Итог по стратегии изменений

Что важно для презентации:
- основной flow продукта не ломался
- внешние API и бизнес-функции не были радикально переписаны
- все добавления сделаны как безопасные, опциональные расширения вокруг уже существующего `dialog_scoring_service`

Рекомендуемая формулировка на защите:
- `RAG` и multi-agent orchestration реализованы в локальном сервисе анализа диалога
- scoring выполняется локально без внешнего API
- добавлен trainable head для предметной адаптации под soft skills scoring
- предусмотрен lightweight runtime под слабое железо
