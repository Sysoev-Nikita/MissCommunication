from flask import Flask, request, jsonify, render_template, session
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import List
import markdown
import uuid

# Модели данных для структурированного ответа
class OriginalPhrase(BaseModel):
    phrase: str

class WordFeedback(BaseModel):
    word: str
    correctness: str  # значения: 'correct', 'incorrect', 'partially_correct'

class CorrectionResponse(BaseModel):
    correct_translation: str
    feedback: str
    score: int  # оценка от 1 до 5
    word_feedback: List[WordFeedback]

# Загрузка переменных окружения
load_dotenv()
client = OpenAI()
client.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)  # Ключ для сессий

# Базовое сообщение с инструкцией
BASE_INSTRUCTION = {
    "role": "system",
    "content": "Ты создаешь фразы для учебных целей. Фразы должны быть разнообразными, охватывать разные темы и соответствовать уровню пользователя."
}

# Хранилище истории для пользователей
user_histories = {}

# Максимальная длина истории
MAX_HISTORY_LENGTH = 100

# Получение или создание истории для пользователя
def get_user_history():
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())  # Генерация нового уникального ID
        session['user_id'] = user_id
    if user_id not in user_histories:
        user_histories[user_id] = [BASE_INSTRUCTION]  # Инициализация истории
    return user_histories[user_id]

# Добавление сообщения в историю
def add_to_user_history(history, role, content):
    history.append({"role": role, "content": content})
    # Удаление старых сообщений, кроме инструкции
    while len(history) > MAX_HISTORY_LENGTH + 1:  # +1 для сохранения инструкции
        history.pop(1)

# Маршрут для главной страницы (index.html)
@app.route('/')
def serve_index():
    return render_template('index.html')

# Генерация фразы
@app.route('/generate_phrase', methods=['GET'])
def generate_phrase():
    level = request.args.get('level', 'A1')  # По умолчанию A1
    language = request.args.get('language', 'german')  # По умолчанию German
    context = request.args.get('context', '').strip()

    history = get_user_history()

    # Создаём подсказку для модели
    prompt = f"Сгенерируй простую фразу на языке {language} для уровня {level}."
    if context:
        prompt += f" Контекст: {context}."

    add_to_user_history(history, "user", prompt)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=history,
        max_tokens=100,
        response_format=OriginalPhrase
    )

    phrase = response.choices[0].message.parsed
    add_to_user_history(history, "assistant", phrase.phrase)

    return jsonify({'phrase': phrase.phrase.rstrip('.')})

# Проверка перевода пользователя
@app.route('/check_translation', methods=['POST'])
def check_translation():
    data = request.get_json()
    german_phrase = data.get('german_phrase')
    user_translation = data.get('user_translation')

    if not german_phrase or not user_translation:
        return jsonify({'error': 'Invalid input data'}), 400

    # Формируем запрос для проверки перевода
    prompt = (
        f"Вот оригинальная фраза: \"{german_phrase}\". "
        f"Пользовательский перевод: \"{user_translation}\". "
        f"Предоставь правильный перевод, выставь оценку от 1 до 5, укажи на ошибки в переводе, и дай обратную связь по каждому слову исходной фразы, правильно ли оно переведено. "
        f"Для каждого слова укажи одно из значений: 'correct', 'incorrect', 'partially_correct'."
        f"Слова, смысл которых был передан в пользовательском переводе верно, помечай как 'correct'. "
        f"Слова, в которых есть грамматическая ошибка или заметное смысловое отличие, помечай как 'partially_correct'. "
        f"Слова, смысл которых не передан в пользовательском переводе, помечай как 'incorrect'. "
        f"Будь менее придирчив к мелким неточностям, таким как артикли и числительные, и учитывай смысловую схожесть слов. "
        f"Фидбек должен быть структурированным, конкретным и полезным и использовать Markdown для удобного форматирования."
    )

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты — полезный ассистент, помогающий изучать язык. Будь менее строг в оценке точности перевода, делай акцент на смысловой передаче информации."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        response_format=CorrectionResponse
    )

    parsed_response = response.choices[0].message.parsed

    feedback_html = markdown.markdown(parsed_response.feedback)

    return jsonify({
        'correct_translation': parsed_response.correct_translation.rstrip('.'),
        'feedback': feedback_html,
        'score': parsed_response.score,
        'word_feedback': [
            {
                'word': word_feedback.word,
                'correctness': word_feedback.correctness
            } for word_feedback in parsed_response.word_feedback
        ]
    })

if __name__ == '__main__':
    app.run(debug=True)
