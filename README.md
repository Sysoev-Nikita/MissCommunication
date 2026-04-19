# Miss Communication

Небольшое Flask-приложение для тренировки перевода в формате чата.

## Структура

- `main.py` — точка входа для локального запуска и gunicorn.
- `misscommunication/config.py` — конфигурация приложения, UI-тексты, доступные языки и уровни.
- `misscommunication/service.py` — вся логика работы с OpenAI.
- `misscommunication/history.py` — хранение истории генерации фраз в сессии.
- `misscommunication/models.py` — модели структурированных ответов.
- `misscommunication/prompts.py` — загрузка prompt-файлов.
- `prompts/` — все системные и пользовательские промпты.
- `templates/index.html` — HTML-шаблон.
- `static/js/scripts.js` — клиентская логика.
- `static/css/styles.css` — стили.

## Запуск локально

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Для работы нужен `OPENAI_API_KEY` в `.env`.

Можно скопировать шаблон из `.env.example` и поменять значения под себя.

## Конфиг

Основные параметры теперь настраиваются через `.env`:

- `STUDY_ITEM_REUSE_PROBABILITY` — вероятность того, что новая фраза будет специально включать элемент из списка на изучение.
- `PHRASE_GENERATION_MODEL` — модель для генерации новой фразы.
- `TRANSLATION_CHECK_MODEL` — модель для структурированной проверки перевода.
- `FEEDBACK_MODEL` — модель для текстового фидбека.
- `OPENAI_REASONING_EFFORT` — уровень reasoning для моделей семейства GPT-5 (`none`, `low`, `medium`, `high`, `xhigh`).
- `OPENAI_API_LOGGING_ENABLED` — включить или выключить логирование запросов к OpenAI.
- `OPENAI_API_LOG_FILE` — путь к JSONL-файлу с логами запросов и ответов.

## Логи OpenAI

Если `OPENAI_API_LOGGING_ENABLED=true`, приложение пишет JSONL-логи в `logs/openai_api.jsonl`.

Для каждого обращения к API в лог попадает:

- этап (`phrase_generation`, `translation_check`, `feedback_generation`);
- модель;
- полный список сообщений, которые были отправлены;
- число символов в запросе;
- usage от OpenAI, если он вернулся;
- полный ответ модели;
- извлеченный текст ответа;
- распарсенный payload для structured-ответов.

## Что важно помнить

- Фраза генерируется с учетом истории пользователя в рамках текущей сессии.
- Все промпты вынесены в файлы, так что менять поведение модели лучше оттуда.
- Фронтенд и backend используют единые имена: `source_phrase`, `user_translation`, `score`, `word_feedback`.
