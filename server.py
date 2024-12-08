from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import List
import markdown

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

# Загружаем переменные окружения из .env файла
load_dotenv()
client = OpenAI()
client.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__, static_folder='static')

# Хранение истории диалога для генерации разнообразных фраз
dialog_history = [
    {"role": "system", "content": "Ты создаешь фразы на немецком языке для учебных целей. Фразы должны быть разнообразными и охватывать разные темы."}
]

# Маршрут для главной страницы (index.html)
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Генерация случайной немецкой фразы с использованием контекста
@app.route('/generate_phrase', methods=['GET'])
def generate_phrase():
    prompt = "Сгенерируй новую фразу на немецком языке, избегай повторов предыдущих фраз."

    # Добавляем пользовательский запрос в историю диалога
    dialog_history.append({"role": "user", "content": prompt})

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=dialog_history,
        max_tokens=100,
        response_format=OriginalPhrase
    )

    # Извлекаем и сохраняем сгенерированную фразу в истории
    phrase = response.choices[0].message.parsed
    dialog_history.append({"role": "assistant", "content": phrase.phrase})

    return jsonify({'phrase': phrase.phrase.rstrip('.')})

# Проверка перевода пользователя
@app.route('/check_translation', methods=['POST'])
def check_translation():
    data = request.get_json()
    german_phrase = data.get('german_phrase')
    user_translation = data.get('user_translation')

    prompt = (
        f"Вот фраза на немецком языке: \"{german_phrase}\". "
        f"Пользовательский перевод: \"{user_translation}\". "
        f"Предоставь правильный перевод, выставь оценку от 1 до 5, укажи на ошибки в переводе, и дай обратную связь по каждому слову исходной фразы, правильно ли оно переведено. "
        f"Будь менее придирчив к мелким неточностям, таким как артикли и числительные, и учитывай смысловую схожесть слов. "
        f"Считай перевод верным, если переданная информация передана верно, даже если структура фразы немного отличается. "
        f"Слова, в которых есть грамматическая ошибка или заметное смысловое отличие, помечай как 'partially_correct'. "
        f"Для каждого слова укажи одно из значений: 'correct', 'incorrect', 'partially_correct'."
        f"Фидбек должен быть достаточно кратким, разбирать только ошибки и неточности. Это должна быть не одна длинная фраза, в нем должна быть структура, можно использовать Markdown для красивого форматирования."
    )
    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты — полезный ассистент, помогающий изучать язык. Будь менее строг в оценке точности перевода, делай акцент на смысловой передаче информации."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=400,
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