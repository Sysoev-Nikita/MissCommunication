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

## Что важно помнить

- Фраза генерируется с учетом истории пользователя в рамках текущей сессии.
- Все промпты вынесены в файлы, так что менять поведение модели лучше оттуда.
- Фронтенд и backend используют единые имена: `source_phrase`, `user_translation`, `score`, `word_feedback`.
