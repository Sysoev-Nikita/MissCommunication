import random
from typing import Dict, List

import markdown
from openai import OpenAI

from .config import AppConfig
from .history import SessionGenerationStore
from .models import PhraseResponse, TranslationAssessment, TranslationFeedbackResult
from .prompts import PromptRepository


GENERATION_DIMENSIONS = {
    "all_levels": {
        "communicative_patterns": (
            {
                "communicative_goal": "neutral statement",
                "sentence_shapes": ("affirmative sentence", "negative sentence"),
            },
            {
                "communicative_goal": "personal reaction",
                "sentence_shapes": ("affirmative sentence", "exclamation"),
            },
            {
                "communicative_goal": "direct question",
                "sentence_shapes": ("yes/no question", "wh-question"),
            },
            {
                "communicative_goal": "request",
                "sentence_shapes": ("imperative", "yes/no question"),
            },
            {
                "communicative_goal": "invitation",
                "sentence_shapes": ("yes/no question", "affirmative sentence"),
            },
            {
                "communicative_goal": "suggestion",
                "sentence_shapes": ("affirmative sentence", "yes/no question"),
            },
            {
                "communicative_goal": "short instruction",
                "sentence_shapes": ("imperative", "negative sentence"),
            },
            {
                "communicative_goal": "opinion",
                "sentence_shapes": ("affirmative sentence", "negative sentence"),
            },
        ),
        "length": (
            "short",
            "medium",
        ),
    },
    "A1": {
        "grammar_focus": (
            "present tense",
            "basic negation",
            "simple question form",
            "can / can't",
            "imperative",
            "possession",
        ),
    },
    "A2": {
        "grammar_focus": (
            "present tense",
            "past tense",
            "future intention",
            "comparison",
            "should / shouldn't",
            "frequency expression",
        ),
    },
    "B1": {
        "grammar_focus": (
            "past tense",
            "future plan",
            "present perfect",
            "obligation or advice",
            "reason and result",
            "conditional idea",
        ),
    },
    "B2": {
        "grammar_focus": (
            "present perfect",
            "passive voice",
            "relative clause",
            "contrast or concession",
            "conditional sentence",
            "indirect question",
        ),
    },
    "C1": {
        "grammar_focus": (
            "hypothetical condition",
            "nuanced contrast",
            "reported idea",
            "advanced modal nuance",
            "formal request",
            "cause and consequence",
        ),
    },
    "C2": {
        "grammar_focus": (
            "subtle hypothetical meaning",
            "nuanced stance",
            "advanced inversion or emphasis",
            "formal or rhetorical question",
            "dense contrast",
            "idiomatic but natural structure",
        ),
    },
}


class LanguageTutorService:
    def __init__(
        self,
        config: AppConfig,
        client: OpenAI,
        prompts: PromptRepository,
        generation_store: SessionGenerationStore,
    ) -> None:
        self.config = config
        self.client = client
        self.prompts = prompts
        self.generation_store = generation_store

    @classmethod
    def from_config(cls, config: AppConfig) -> "LanguageTutorService":
        prompts = PromptRepository(config.prompts_dir)
        generation_store = SessionGenerationStore(
            memory_size=config.recent_generation_memory_size,
        )
        client = OpenAI(api_key=config.openai_api_key)
        return cls(
            config=config,
            client=client,
            prompts=prompts,
            generation_store=generation_store,
        )

    def generate_phrase(self, level: str, language: str, context: str) -> str:
        self._validate_level(level)
        self._validate_language(language)

        recent_signatures = self.generation_store.recent_signatures()
        profile = self._pick_generation_profile(level, recent_signatures)

        prompt = self.prompts.load(
            "phrase_generation_user.txt",
            language=language,
            level=level,
            context=self._format_context_block(context),
            generation_requirements=self._format_generation_requirements(profile),
            recent_constraints=self._format_recent_constraints(recent_signatures),
        )

        response = self.client.beta.chat.completions.parse(
            model=self.config.phrase_generation_model,
            messages=[
                {"role": "system", "content": self.prompts.load("phrase_generation_system.txt")},
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
            response_format=PhraseResponse,
        )

        phrase = response.choices[0].message.parsed
        self.generation_store.remember_signature(profile["signature"])
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

    def _pick_generation_profile(self, level: str, recent_signatures: List[str]) -> Dict[str, str]:
        recent_signature_set = set(recent_signatures[-6:])
        candidate_profiles = self._build_candidate_profiles(level)
        random.shuffle(candidate_profiles)

        for profile in candidate_profiles:
            if profile["signature"] not in recent_signature_set:
                return profile

        return candidate_profiles[0]

    def _build_candidate_profiles(self, level: str) -> List[Dict[str, str]]:
        shared_dimensions = GENERATION_DIMENSIONS["all_levels"]
        level_dimensions = GENERATION_DIMENSIONS[level]
        candidates = []

        for pattern in shared_dimensions["communicative_patterns"]:
            for sentence_shape in pattern["sentence_shapes"]:
                for length in shared_dimensions["length"]:
                    for grammar_focus in level_dimensions["grammar_focus"]:
                        signature = " | ".join(
                            (
                                pattern["communicative_goal"],
                                sentence_shape,
                                grammar_focus,
                                length,
                            )
                        )
                        candidates.append(
                            {
                                "communicative_goal": pattern["communicative_goal"],
                                "sentence_shape": sentence_shape,
                                "grammar_focus": grammar_focus,
                                "length": length,
                                "signature": signature,
                            }
                        )

        return candidates

    def _format_context_block(self, context: str) -> str:
        if not context:
            return "Контекст не задан. Выбери ситуацию самостоятельно."
        return (
            'Пользователь задал смысловой контекст: "{context}". '
            "Сохрани этот контекст, но выражай его через указанную грамматическую форму и тип высказывания."
        ).format(context=context)

    def _format_generation_requirements(self, profile: Dict[str, str]) -> str:
        return "\n".join(
            (
                "- Коммуникативная цель: {communicative_goal}".format(**profile),
                "- Форма предложения: {sentence_shape}".format(**profile),
                "- Грамматический фокус: {grammar_focus}".format(**profile),
                "- Целевая длина: {length}".format(**profile),
            )
        )

    def _format_recent_constraints(self, recent_signatures: List[str]) -> str:
        if not recent_signatures:
            return "Недавних паттернов нет."

        recent_lines = ["- {0}".format(signature) for signature in recent_signatures[-6:]]
        return "\n".join(recent_lines)

    def _validate_level(self, level: str) -> None:
        if level not in self.config.level_options:
            raise ValueError("Unsupported level: {0}".format(level))

    def _validate_language(self, language: str) -> None:
        supported_languages = {option["value"] for option in self.config.language_options}
        if language not in supported_languages:
            raise ValueError("Unsupported language: {0}".format(language))
