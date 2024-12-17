let nextPhrase = null;  // Буфер для хранения предзагруженной фразы

document.addEventListener("DOMContentLoaded", function() {
    preloadNextPhrase();  // Предзагружаем первую фразу
    displayPhrase();      // Отображаем фразу из буфера
});

// Предзагрузка следующей фразы
async function preloadNextPhrase() {
    const level = document.getElementById("level").value;
    const language = document.getElementById("language").value;
    const context = document.getElementById("context").value;

    try {
        const response = await fetch(`/generate_phrase?level=${level}&language=${language}&context=${context}`);
        const data = await response.json();
        nextPhrase = data.phrase;  // Сохраняем фразу в буфере
    } catch (error) {
        console.error("Ошибка при предзагрузке фразы:", error);
        nextPhrase = null;
    }
}

// Отображение новой фразы
function displayPhrase() {
    const phraseContainer = document.getElementById('german-phrase');

    if (nextPhrase) {
        phraseContainer.innerText = nextPhrase;  // Берём из буфера
        nextPhrase = null;                       // Очищаем буфер
        preloadNextPhrase();                     // Загружаем следующую фразу
    } else {
        generatePhrase();  // Если буфер пуст, отправляем запрос на сервер
    }

    // Сбрасываем интерфейс
    document.getElementById('correct-translation').style.visibility = 'hidden';
    document.getElementById('user-translation').value = '';
    document.getElementById('feedback-container').style.display = 'none';
    document.getElementById('character-image').src = 'static/images/neutral_positive.webp';
}

async function generatePhrase() {
    const level = document.getElementById("level").value;
    const language = document.getElementById("language").value;
    const context = document.getElementById("context").value;

    document.getElementById("processing").style.display = "block";

    const response = await fetch(`/generate_phrase?level=${level}&language=${language}&context=${context}`);
    const data = await response.json();

    document.getElementById("processing").style.display = "none";
    document.getElementById('german-phrase').innerText = data.phrase;
    preloadNextPhrase();  // Сразу предзагружаем следующую фразу
}

async function checkTranslation() {
    const germanPhrase = document.getElementById('german-phrase').innerText;
    const userTranslation = document.getElementById('user-translation').value;

    document.getElementById("processing").style.display = "block";
    document.getElementById("user-translation").disabled = true;

    const response = await fetch('/check_translation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            german_phrase: germanPhrase,
            user_translation: userTranslation
        })
    });

    const data = await response.json();

    document.getElementById("processing").style.display = "none";
    document.getElementById("user-translation").disabled = false;
    document.getElementById("user-translation").focus();

    document.getElementById('correct-translation').innerText = data.correct_translation;
    document.getElementById('correct-translation').style.visibility = 'visible';
    document.getElementById('feedback').innerHTML = data.feedback;

    const germanPhraseElement = document.getElementById('german-phrase');
    germanPhraseElement.innerHTML = '';

    data.word_feedback.forEach(wordFeedback => {
        const wordSpan = document.createElement('span');
        wordSpan.innerText = wordFeedback.word + ' ';
        if (wordFeedback.correctness === 'correct') {
            wordSpan.classList.add('correct');
        } else if (wordFeedback.correctness === 'incorrect') {
            wordSpan.classList.add('incorrect');
        } else if (wordFeedback.correctness === 'partially_correct') {
            wordSpan.classList.add('partially-correct');
        }
        germanPhraseElement.appendChild(wordSpan);
    });

    document.getElementById('feedback-container').style.display = 'block';

    const characterImage = document.getElementById('character-image');
    switch (data.score) {
        case 5:
            characterImage.src = 'static/images/happy.webp';
            break;
        case 4:
            characterImage.src = 'static/images/neutral_positive.webp';
            break;
        case 2:
        case 3:
            characterImage.src = 'static/images/sad.webp';
            break;
        case 1:
            characterImage.src = 'static/images/disappointed.webp';
            break;
    }
}

// Обработка нажатия Enter на уровне всего документа
document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const userTranslationField = document.getElementById('user-translation');

        // Если уже есть фидбек или поле заблокировано, показываем новую фразу
        if (document.getElementById('feedback-container').style.display === 'block' || userTranslationField.disabled) {
            displayPhrase();
        } 
        // Проверка перевода, если фидбек ещё не отображён
        else if (userTranslationField.value.trim() !== '') {
            checkTranslation();
        }
    }
});

// Сброс буфера при изменении параметров уровня, языка или контекста
['level', 'language', 'context'].forEach(id => {
    document.getElementById(id).addEventListener('change', function() {
        nextPhrase = null;  // Очищаем буфер
        preloadNextPhrase();  // Предзагружаем новую фразу с учётом изменений
    });
});
