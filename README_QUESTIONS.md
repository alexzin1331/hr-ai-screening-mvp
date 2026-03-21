# README_QUESTIONS

## Основные вопросы по ML и AI

### 1. Как происходит оценка резюме?

Сначала файл резюме парсится в текст, потом из текста извлекается структурированный профиль кандидата, после этого профиль сравнивается с вакансией и считается `resume score`.  
Для extraction используется LLM-клиент, а для scoring сейчас используется LLM + эвристический matching по навыкам и опыту.  
Сравниваются: `hard_skills`, `soft_skills`, опыт, seniority, позиция и summary кандидата.

Где в коде:
- [pipeline.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/pipeline.py)
- функция: `ResumeProcessingPipeline._process_single_file()`
- [candidate_extractor.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/candidate_extractor.py)
- функция: `CandidateExtractorService.extract()`
- [scoring.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/scoring.py)
- функция: `ScoringService.score()`

### 2. Это поиск по ключевым словам или по смыслу?

Для soft skills это не просто keyword matching: там используется semantic matching через embeddings.  
Для резюме в backend есть смешанный подход: LLM-оценка + явное совпадение навыков и опыта.  
Отличие от keyword matching в том, что embedding-модель сравнивает смысл фраз, а не только точное совпадение слов.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- функция: `LocalEmbeddingScorer.score()`
- [scoring.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/scoring.py)
- функции: `_skill_overlap()`, `_heuristic_score()`

### 3. Как считается итоговый score?

Сначала считается `score_resume`, потом после Telegram screening считается `score_dialog` для soft skills.  
Итоговый `total_score` агрегируется как среднее между `score_resume` и `score_dialog`; если dialog score ещё нет, используется только `score_resume`.  
Оба score нормализуются в диапазон `0..100`.

Где в коде:
- [scoring.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/scoring.py)
- функция: `ScoringService.score()`
- [screening.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/screening.py)
- функции: `_finalize_dialog_scoring()`, `_normalize_dialog_score()`

### 4. Как оцениваются soft skills?

После ответов кандидата в Telegram используется `sentence-transformers` модель `intfloat/multilingual-e5-small`.  
Считаются embeddings требований вакансии и ответов кандидата, затем берётся `cosine similarity`.  
Поверх similarity добавлены lexical overlap, diversity, richness ответов и optional calibrator.  
Если calibrator сохранён, он донастраивает итоговую оценку без полного fine-tuning модели.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- функция: `LocalEmbeddingScorer.score()`
- [main.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/main.py)
- endpoint: `/evaluate`

### 5. Что такое RAG в вашем проекте?

У нас RAG используется в `dialog_scoring_service` как retrieval по тексту вакансии.  
Контекст берётся из `vacancy_description`, `hard_skills` и `soft_skills`, разбивается на маленькие чанки и затем выбираются наиболее релевантные под ответы кандидата.  
Это нужно, чтобы scoring опирался не на весь текст сразу, а на наиболее важные требования вакансии.

Где в коде:
- [agents.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/agents.py)
- классы: `VacancyRAG`, `RetrieverAgent`
- функции: `build_chunks()`, `retrieve()`, `run()`

### 6. Что значит multi-agent в вашей системе?

Multi-agent здесь значит разделение pipeline на несколько простых ролей, а не один большой модуль.  
`RetrieverAgent` поднимает релевантный контекст, `ScoringAgent` считает score, `ScreeningCoordinatorAgent` связывает всё вместе.  
Это упрощает объяснение логики и позволяет отдельно улучшать retrieval и scoring.

Где в коде:
- [agents.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/agents.py)
- классы: `RetrieverAgent`, `ScoringAgent`, `ScreeningCoordinatorAgent`

### 7. Почему используется embedding-модель, а не LLM?

Для задачи similarity embedding-модель быстрее, дешевле и стабильнее.  
Нам нужно не генерировать длинный текст, а сравнить, насколько ответы кандидата близки к требованиям вакансии по смыслу.  
Поэтому локальный embedding inference здесь практичнее, чем большой генеративный LLM.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- функция: `get_model()`
- класс: `LocalEmbeddingScorer`

### 8. Что такое cosine similarity и где она используется?

Cosine similarity показывает, насколько два вектора смотрят в одном направлении.  
Простыми словами: чем ближе embedding вакансии и embedding ответов кандидата, тем выше смысловое совпадение.  
У нас она используется как базовая метрика soft skills matching.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- функция: `LocalEmbeddingScorer.score()`
- строка с методом: `np.dot(job_emb, avg_answer_emb)` при `normalize_embeddings=True`

### 9. Что будет, если LLM или ML-сервис не работает?

Если недоступен `dialog_scoring_service`, основной backend остаётся рабочим: загрузка резюме, dashboard, Telegram flow и email не ломаются.  
Если падает extraction/scoring в backend, ошибки ловятся, резюме помечается как `parse_failed`, а pipeline не падает целиком.  
То есть система деградирует частично, а не полностью.

Где в коде:
- [pipeline.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/pipeline.py)
- функция: `_process_single_file()`
- [screening.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/screening.py)
- функция: `_finalize_dialog_scoring()`
- [error_handlers.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/core/error_handlers.py)

### 10. Почему вы не дообучали всю модель?

Полный fine-tuning трансформера дороже по данным, времени и вычислениям, а для MVP это избыточно.  
Поэтому выбран lightweight подход: базовая embedding-модель + calibrator/head поверх уже готовых признаков.  
Так мы получаем адаптацию под задачу без риска сломать inference и без тяжёлого обучения.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- класс: `LinearCalibrator`
- [finetune_soft_skills_head.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/training/finetune_soft_skills_head.py)

## Дополнительные вопросы

### Как система работает с разными языками?

Для soft skills используется multilingual embedding-модель `intfloat/multilingual-e5-small`, поэтому русский и английский поддерживаются лучше, чем у monolingual модели.  
Для extraction текст резюме передаётся как есть, а JSON-схема задаёт структуру результата.

Где в коде:
- [scoring_runtime.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/scoring_runtime.py)
- [candidate_extractor.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/candidate_extractor.py)

### Как учитывается опыт кандидата?

Опыт учитывается в `resume score` через `total_years_experience` и ожидаемый уровень `seniority`.  
Например, для `Senior` ожидается больше лет опыта, чем для `Junior`, и это влияет на итоговую эвристику.

Где в коде:
- [scoring.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/scoring.py)
- функция: `_experience_score()`

### Как нормализуются навыки?

Навыки переводятся в упрощённый текстовый вид: lower-case и токены без лишних символов.  
После этого считается overlap между требованиями вакансии и данными кандидата из extraction.

Где в коде:
- [scoring.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/hr-ai-screening-mvp/app/services/scoring.py)
- функции: `_normalize_text()`, `_skill_overlap()`

### Как можно улучшить модель?

Лучшее направление — собрать размеченный датасет ответов кандидатов и обучить calibrator на реальных HR-оценках.  
Дальше можно добавить более качественный retrieval, доменную нормализацию навыков и отдельную модель под resume matching.

Где в коде:
- [finetune_soft_skills_head.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/training/finetune_soft_skills_head.py)
- [agents.py](/Users/v/PycharmProjects/hr-ai-screening-mvp_1/dialog_scoring_service/agents.py)
