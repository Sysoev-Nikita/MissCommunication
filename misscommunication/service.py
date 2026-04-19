import markdown
from openai import OpenAI

from .config import AppConfig
from .history import SessionHistoryStore
from .models import PhraseResponse, TranslationAssessment, TranslationFeedbackResult
from .prompts import PromptRepository


class LanguageTutorService:
    def __init__(
        self,
        config: AppConfig,
        client: OpenAI,
        prompts: PromptRepository,
        history_store: SessionHistoryStore,
    ) -> None:
        self.config = config
        self.client = client
        self.prompts = prompts
        self.history_store = history_store

    @classmethod
    def from_config(cls, config: AppConfig) -> "LanguageTutorService":
        prompts = PromptRepository(config.prompts_dir)
        history_store = SessionHistoryStore(
            max_history_length=config.max_history_length,
            base_message={
                "role": "system",
                "content": prompts.load("phrase_generation_system.txt"),
            },
        )

        client = OpenAI(api_key=config.openai_api_key)
        return cls(config=config, client=client, prompts=prompts, history_store=history_store)

    def generate_phrase(self, level: str, language: str, context: str) -> str:
        self._validate_level(level)
        self._validate_language(language)

        history = self.history_store.get_history()
        prompt = self.prompts.load(
            "phrase_generation_user.txt",
            language=language,
            level=level,
            context=f" Контекст: {context}." if context else "",
        )

        self.history_store.append(history, "user", prompt)

        response = self.client.beta.chat.completions.parse(
            model=self.config.phrase_generation_model,
            messages=history,
            max_tokens=100,
            response_format=PhraseResponse,
        )

        phrase = response.choices[0].message.parsed
        self.history_store.append(history, "assistant", phrase.phrase)
        return phrase.phrase.rstrip(".")

    def check_translation(self, source_phrase: str, user_translation: str) -> TranslationFeedbackResult:
        prompt_check = self.prompts.load(
            "translation_check_user.txt",
            source_phrase=source_phrase,
            user_translation=user_translation,
        )

        response_check = self.client.beta.chat.completions.parse(
            model=self.config.translation_check_model,
            messages=[
                {"role": "system", "content": self.prompts.load("translation_check_system.txt")},
                {"role": "user", "content": prompt_check},
            ],
            max_tokens=1000,
            response_format=TranslationAssessment,
        )

        assessment = response_check.choices[0].message.parsed

        response_feedback = self.client.chat.completions.create(
            model=self.config.feedback_model,
            messages=[
                {"role": "system", "content": self.prompts.load("feedback_system.txt")},
                {"role": "user", "content": prompt_check},
                {"role": "assistant", "content": assessment.model_dump_json()},
                {"role": "user", "content": self.prompts.load("feedback_user.txt")},
            ],
            max_tokens=1000,
        )

        feedback_markdown = response_feedback.choices[0].message.content or ""
        feedback_html = markdown.markdown(feedback_markdown, extensions=["tables"])

        return TranslationFeedbackResult(
            correct_translation=assessment.correct_translation,
            score=assessment.score,
            word_feedback=assessment.word_feedback,
            feedback_html=feedback_html,
        )

    def _validate_level(self, level: str) -> None:
        if level not in self.config.level_options:
            raise ValueError(f"Unsupported level: {level}")

    def _validate_language(self, language: str) -> None:
        supported_languages = {option["value"] for option in self.config.language_options}
        if language not in supported_languages:
            raise ValueError(f"Unsupported language: {language}")
