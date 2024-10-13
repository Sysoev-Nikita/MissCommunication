from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Модели данных для структурированного ответа
class OriginalPhrase(BaseModel):
    phrase: str

class CorrectionResponse(BaseModel):
    correct_translation: str
    feedback: str

# Загружаем переменные окружения из .env файла
load_dotenv()
client = OpenAI()
client.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__, static_folder='static')

# Маршрут для главной страницы (index.html)
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Генерация случайной немецкой фразы
@app.route('/generate_phrase', methods=['GET'])
def generate_phrase():
    prompt = "Generate a simple German phrase for a beginner learning level."
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You generate phrases in German for studying purposes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        response_format=OriginalPhrase
    )
    phrase = response.choices[0].message.parsed
    return jsonify({'phrase': phrase.phrase})

# Проверка перевода пользователя
@app.route('/check_translation', methods=['POST'])
def check_translation():
    data = request.get_json()
    german_phrase = data.get('german_phrase')
    user_translation = data.get('user_translation')

    prompt = (
        f"Here is a German phrase: \"{german_phrase}\". "
        f"The user's translation is: \"{user_translation}\". "
        f"Provide the correct translation and highlight mistakes."
    )
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=400,
        response_format=CorrectionResponse
    )
    parsed_response = response.choices[0].message.parsed
    return jsonify({
        'correct_translation': parsed_response.correct_translation,
        'feedback': parsed_response.feedback
    })

if __name__ == '__main__':
    app.run(debug=True)
