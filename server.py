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
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
    prompt = "Сгенерируй новую простую фразу на немецком языке для начального уровня изучения, избегай повторов предыдущих фраз."

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

    return jsonify({'phrase': phrase.phrase})

# Проверка перевода пользователя
@app.route('/check_translation', methods=['POST'])
def check_translation():
    data = request.get_json()
    german_phrase = data.get('german_phrase')
    user_translation = data.get('user_translation')

    prompt = (
        f"Вот фраза на немецком языке: \"{german_phrase}\". "
        f"Пользовательский перевод: \"{user_translation}\". "
        f"Предоставь правильный перевод и укажи на ошибки в переводе."
    )
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты — полезный ассистент, помогающий изучать язык."},
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
