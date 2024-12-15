from flask import Flask, request, jsonify, render_template
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
    {"role": "system", "content": "Ты создаешь фразы для учебных целей. Фразы должны быть разнообразными, охватывать разные темы и соответствовать уровню пользователя."}
]

# Маршрут для главной страницы (index.html)
@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/generate_phrase', methods=['GET'])
def generate_phrase():
    level = request.args.get('level', 'A1')  # По умолчанию A1
    language = request.args.get('language', 'german')  # По умолчанию German
    context = request.args.get('context', '').strip()

    # Создаем подсказку для модели
    prompt = f"Сгенерируй простую фразу на языке {language} для уровня {level}."
    if context:
        prompt += f" Контекст: {context}."

    dialog_history.append({"role": "user", "content": prompt})

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=dialog_history,
        max_tokens=100,
        response_format=OriginalPhrase
    )

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
