let nextPhrase = null;

document.addEventListener("DOMContentLoaded", async function () {
    hideSpinner();
    await displayPhrase();
});

async function preloadNextPhrase() {
    const level = document.getElementById("level").value;
    const language = document.getElementById("language").value;
    const context = document.getElementById("context").value;

    try {
        const response = await fetch(`/generate_phrase?level=${level}&language=${language}&context=${context}`);
        const data = await response.json();
        nextPhrase = data.phrase || null;
        return nextPhrase;
    } catch (error) {
        console.error("Error while preloading phrase:", error);
        nextPhrase = null;
        return null;
    }
}

async function displayPhrase() {
    resetPhraseContainer();

    if (nextPhrase) {
        document.getElementById("german-phrase").innerText = nextPhrase;
        nextPhrase = null;
        preloadNextPhrase();
    } else {
        await generatePhrase();
    }

    document.getElementById("user-translation").value = "";
    document.getElementById("feedback-container").style.display = "none";
    document.getElementById("character-image").src = "static/images/neutral_positive.webp";
}

function resetPhraseContainer() {
    const phraseContainer = document.getElementById("phrase-container");
    const germanPhrase = document.getElementById("german-phrase");
    const correctTranslation = document.getElementById("correct-translation");

    germanPhrase.innerHTML = "";
    correctTranslation.innerHTML = "";
    correctTranslation.style.visibility = "hidden";

    phraseContainer.style.display = "flex";
    phraseContainer.style.alignItems = "center";
    phraseContainer.style.justifyContent = "center";
    phraseContainer.style.height = "";
    phraseContainer.style.minHeight = "140px";
}

function showSpinner() {
    document.getElementById("processing").style.display = "block";
}

function hideSpinner() {
    document.getElementById("processing").style.display = "none";
}

async function generatePhrase() {
    resetPhraseContainer();
    showSpinner();

    const level = document.getElementById("level").value;
    const language = document.getElementById("language").value;
    const context = document.getElementById("context").value;

    try {
        const response = await fetch(`/generate_phrase?level=${level}&language=${language}&context=${context}`);
        const data = await response.json();

        document.getElementById("german-phrase").innerText = data.phrase || "";
        preloadNextPhrase();
        return data.phrase || null;
    } catch (error) {
        console.error("Error while loading phrase:", error);
        return null;
    } finally {
        hideSpinner();
    }
}

async function checkTranslation() {
    const germanPhrase = document.getElementById("german-phrase").innerText;
    const userTranslation = document.getElementById("user-translation").value;

    showSpinner();
    document.getElementById("user-translation").disabled = true;

    const response = await fetch("/check_translation", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            german_phrase: germanPhrase,
            user_translation: userTranslation
        })
    });

    const data = await response.json();

    hideSpinner();
    document.getElementById("user-translation").disabled = false;
    document.getElementById("user-translation").focus();

    document.getElementById("correct-translation").innerText = data.correct_translation;
    document.getElementById("correct-translation").style.visibility = "visible";
    document.getElementById("feedback").innerHTML = data.feedback;

    const germanPhraseElement = document.getElementById("german-phrase");
    germanPhraseElement.innerHTML = "";

    data.word_feedback.forEach(wordFeedback => {
        const wordSpan = document.createElement("span");
        wordSpan.innerText = wordFeedback.word + " ";

        if (wordFeedback.correctness === "correct") {
            wordSpan.classList.add("correct");
        } else if (wordFeedback.correctness === "incorrect") {
            wordSpan.classList.add("incorrect");
        } else if (wordFeedback.correctness === "partially_correct") {
            wordSpan.classList.add("partially-correct");
        }

        germanPhraseElement.appendChild(wordSpan);
    });

    document.getElementById("feedback-container").style.display = "block";

    const characterImage = document.getElementById("character-image");
    switch (data.score) {
        case 5:
            characterImage.src = "static/images/happy.webp";
            break;
        case 4:
            characterImage.src = "static/images/neutral_positive.webp";
            break;
        case 2:
        case 3:
            characterImage.src = "static/images/sad.webp";
            break;
        case 1:
            characterImage.src = "static/images/disappointed.webp";
            break;
    }
}

document.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const userTranslationField = document.getElementById("user-translation");

        if (document.getElementById("feedback-container").style.display === "block" || userTranslationField.disabled) {
            displayPhrase();
        } else if (userTranslationField.value.trim() !== "") {
            checkTranslation();
        }
    }
});

["level", "language", "context"].forEach(id => {
    document.getElementById(id).addEventListener("change", async function () {
        nextPhrase = null;
        await displayPhrase();
    });
});
