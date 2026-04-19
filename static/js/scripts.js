const appConfig = window.APP_CONFIG || {};

const state = {
    currentPhrase: null,
    nextPhrase: null,
    studySuggestions: [],
};

const elements = {
    language: document.getElementById("language"),
    level: document.getElementById("level"),
    context: document.getElementById("context"),
    characterImage: document.getElementById("character-image"),
    phraseBubble: document.getElementById("phrase-bubble"),
    answerBubble: document.getElementById("answer-bubble"),
    sourcePhrase: document.getElementById("source-phrase"),
    correctTranslation: document.getElementById("correct-translation"),
    userTranslation: document.getElementById("user-translation"),
    feedbackContainer: document.getElementById("feedback-container"),
    feedback: document.getElementById("feedback"),
    studySuggestions: document.getElementById("study-suggestions"),
    studySuggestionsList: document.getElementById("study-suggestions-list"),
    phraseLoader: document.getElementById("phrase-loader"),
    answerLoader: document.getElementById("answer-loader"),
};

const characterImages = appConfig.characterImages || {};

document.addEventListener("DOMContentLoaded", async () => {
    hideSpinner();
    elements.userTranslation.addEventListener("input", autoResizeTextarea);
    elements.userTranslation.addEventListener("keydown", handleTextareaKeydown);
    elements.studySuggestionsList.addEventListener("click", handleStudySuggestionClick);
    elements.studySuggestionsList.addEventListener("mousedown", handleStudySuggestionMouseDown);
    document.addEventListener("keydown", handleDocumentKeydown);

    ["level", "language", "context"].forEach((id) => {
        document.getElementById(id).addEventListener("change", handleControlsChange);
    });

    autoResizeTextarea();
    await displayPhrase();
});

function autoResizeTextarea() {
    elements.userTranslation.style.height = "auto";
    elements.userTranslation.style.height = `${elements.userTranslation.scrollHeight}px`;
}

function showSpinner(target) {
    hideSpinner();

    if (target === "phrase") {
        elements.phraseBubble.classList.add("is-loading");
        elements.phraseLoader.hidden = false;
        return;
    }

    if (target === "answer") {
        elements.answerBubble.classList.add("is-loading");
        elements.answerLoader.hidden = false;
    }
}

function hideSpinner() {
    elements.phraseBubble.classList.remove("is-loading");
    elements.answerBubble.classList.remove("is-loading");
    elements.phraseLoader.hidden = true;
    elements.answerLoader.hidden = true;
}

function getPhraseRequestParams() {
    const params = new URLSearchParams({
        level: elements.level.value,
        language: elements.language.value,
        context: elements.context.value,
    });

    return params.toString();
}

function resetPhraseBubble() {
    elements.sourcePhrase.innerHTML = "";
    elements.correctTranslation.textContent = "";
    elements.correctTranslation.style.visibility = "hidden";
}

function resetAnswerArea() {
    elements.userTranslation.value = "";
    elements.userTranslation.disabled = false;
    elements.feedbackContainer.hidden = true;
    elements.feedback.innerHTML = "";
    dismissStudySuggestions();
    autoResizeTextarea();
}

function setCharacterMood(mood) {
    elements.characterImage.src = characterImages[mood] || characterImages.idle;
}

function showStudySuggestions(studySuggestions) {
    state.studySuggestions = studySuggestions.slice();
    elements.studySuggestionsList.innerHTML = "";

    studySuggestions.forEach((studySuggestion, index) => {
        const card = document.createElement("div");
        card.className = "study-card";

        const label = document.createElement("div");
        label.className = "study-card-label";
        label.textContent = studySuggestion.label || "";

        const button = document.createElement("button");
        button.type = "button";
        button.className = studySuggestion.action === "remove" ? "study-card-action remove" : "study-card-action add";
        button.dataset.index = String(index);
        button.setAttribute("aria-label", studySuggestion.action === "remove" ? "Удалить из изучения" : "Добавить в изучение");

        const symbol = document.createElement("span");
        symbol.className = "study-card-action-symbol";
        symbol.textContent = studySuggestion.action === "remove" ? "-" : "+";

        button.appendChild(symbol);

        card.appendChild(label);
        card.appendChild(button);
        elements.studySuggestionsList.appendChild(card);
    });

    elements.studySuggestions.hidden = studySuggestions.length === 0;
}

function dismissStudySuggestions() {
    state.studySuggestions = [];
    elements.studySuggestions.hidden = true;
    elements.studySuggestionsList.innerHTML = "";
}

async function fetchGeneratedPhrase() {
    const response = await fetch(`${appConfig.generatePhraseUrl}?${getPhraseRequestParams()}`);

    if (!response.ok) {
        throw new Error("Phrase generation request failed");
    }

    const data = await response.json();
    return {
        phrase: data.phrase || "",
        phraseId: data.phrase_id || "",
    };
}

async function preloadNextPhrase() {
    try {
        state.nextPhrase = await fetchGeneratedPhrase();
    } catch (error) {
        console.error("Error while preloading phrase:", error);
        state.nextPhrase = null;
    }
}

async function displayPhrase() {
    resetPhraseBubble();
    resetAnswerArea();
    setCharacterMood("idle");

    if (state.nextPhrase) {
        state.currentPhrase = state.nextPhrase;
        elements.sourcePhrase.innerText = state.currentPhrase.phrase;
        state.nextPhrase = null;
        preloadNextPhrase();
        return;
    }

    await generatePhrase();
}

async function generatePhrase() {
    showSpinner("phrase");

    try {
        state.currentPhrase = await fetchGeneratedPhrase();
        elements.sourcePhrase.innerText = state.currentPhrase.phrase;
        preloadNextPhrase();
    } catch (error) {
        console.error("Error while loading phrase:", error);
    } finally {
        hideSpinner();
    }
}

function renderWordFeedback(wordFeedback) {
    const wordSpan = document.createElement("span");
    wordSpan.innerText = `${wordFeedback.word} `;

    if (wordFeedback.correctness === "correct") {
        wordSpan.classList.add("correct");
    } else if (wordFeedback.correctness === "incorrect") {
        wordSpan.classList.add("incorrect");
    } else if (wordFeedback.correctness === "partially_correct") {
        wordSpan.classList.add("partially-correct");
    }

    return wordSpan;
}

function renderSourcePhraseFeedback(wordFeedbackList) {
    elements.sourcePhrase.innerHTML = "";
    wordFeedbackList.forEach((wordFeedback) => {
        elements.sourcePhrase.appendChild(renderWordFeedback(wordFeedback));
    });
}

function updateCharacterByScore(score) {
    if (score === 5) {
        setCharacterMood("happy");
    } else if (score === 4) {
        setCharacterMood("neutral");
    } else if (score === 2 || score === 3) {
        setCharacterMood("sad");
    } else if (score === 1) {
        setCharacterMood("disappointed");
    }
}

async function checkTranslation() {
    const sourcePhrase = elements.sourcePhrase.innerText.trim();
    const userTranslation = elements.userTranslation.value.trim();

    if (!sourcePhrase || !userTranslation) {
        return;
    }

    showSpinner("answer");
    elements.userTranslation.disabled = true;

    try {
        const response = await fetch(appConfig.checkTranslationUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                source_phrase: sourcePhrase,
                user_translation: userTranslation,
                language: elements.language.value,
                phrase_id: state.currentPhrase?.phraseId || "",
            }),
        });

        if (!response.ok) {
            throw new Error("Translation check request failed");
        }

        const data = await response.json();
        elements.correctTranslation.innerText = data.correct_translation || "";
        elements.correctTranslation.style.visibility = "visible";
        elements.feedback.innerHTML = data.feedback || "";
        elements.feedbackContainer.hidden = false;

        if (data.study_suggestions && data.study_suggestions.length > 0) {
            showStudySuggestions(data.study_suggestions);
        } else {
            dismissStudySuggestions();
        }

        renderSourcePhraseFeedback(data.word_feedback || []);
        updateCharacterByScore(data.score);
    } catch (error) {
        console.error("Error while checking translation:", error);
    } finally {
        hideSpinner();
        elements.userTranslation.disabled = false;
        elements.userTranslation.focus();
        autoResizeTextarea();
    }
}

async function handleControlsChange() {
    state.currentPhrase = null;
    state.nextPhrase = null;
    await displayPhrase();
}

async function handleStudySuggestionClick(event) {
    const button = event.target.closest("button[data-index]");
    if (!button) {
        return;
    }

    const index = Number(button.dataset.index);
    const studySuggestion = state.studySuggestions[index];
    if (!studySuggestion) {
        return;
    }

    const action = studySuggestion.action;
    const item = studySuggestion.item || {};
    const payload = { action };

    if (action === "add") {
        payload.language = item.language || elements.language.value;
        payload.item_type = item.item_type;
        payload.source_text = item.source_text;
        payload.explanation = item.explanation || item.source_text;
    }

    if (action === "remove") {
        payload.item_id = item.id;
    }

    try {
        const response = await fetch(appConfig.studyItemsUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error("Study item request failed");
        }

        state.studySuggestions.splice(index, 1);

        if (state.studySuggestions.length > 0) {
            showStudySuggestions(state.studySuggestions);
        } else {
            dismissStudySuggestions();
        }
    } catch (error) {
        console.error("Error while updating study items:", error);
    } finally {
        elements.userTranslation.focus();
    }
}

function handleStudySuggestionMouseDown(event) {
    const button = event.target.closest("button[data-index]");
    if (!button) {
        return;
    }

    event.preventDefault();
}

function handleTextareaKeydown(event) {
    if (event.key !== "Enter" || event.shiftKey) {
        return;
    }

    event.preventDefault();

    if (!elements.feedbackContainer.hidden || !elements.studySuggestions.hidden || elements.userTranslation.disabled) {
        displayPhrase();
        return;
    }

    if (elements.userTranslation.value.trim() !== "") {
        checkTranslation();
    }
}

function handleDocumentKeydown(event) {
    if (event.key !== "Enter" || event.shiftKey) {
        return;
    }

    if (document.activeElement === elements.userTranslation) {
        return;
    }

    if (elements.userTranslation.disabled) {
        event.preventDefault();
        return;
    }

    if (!elements.feedbackContainer.hidden || !elements.studySuggestions.hidden) {
        event.preventDefault();
        displayPhrase();
    }
}
