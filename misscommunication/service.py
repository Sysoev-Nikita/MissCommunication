import random
from typing import Dict, List, Optional

import markdown
from openai import OpenAI

from .config import AppConfig
from .history import SessionGenerationStore, SessionStudyStore
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
        "length": ("short", "medium"),
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
        study_store: SessionStudyStore,
    ) -> None:
        self.config = config
        self.client = client
        self.prompts = prompts
        self.generation_store = generation_store
        self.study_store = study_store

    @classmethod
    def from_config(cls, config: AppConfig) -> "LanguageTutorService":
        prompts = PromptRepository(config.prompts_dir)
        generation_store = SessionGenerationStore(
            memory_size=config.recent_generation_memory_size,
        )
        study_store = SessionStudyStore()
        client = OpenAI(api_key=config.openai_api_key)
        return cls(
            config=config,
            client=client,
            prompts=prompts,
            generation_store=generation_store,
            study_store=study_store,
        )

    def generate_phrase(self, level: str, language: str, context: str) -> Dict[str, str]:
        self._validate_level(level)
        self._validate_language(language)

        recent_signatures = self.generation_store.recent_signatures()
        profile = self._pick_generation_profile(level, recent_signatures)
        study_item = self._pick_study_item(language)

        prompt = self.prompts.load(
            "phrase_generation_user.txt",
            language=language,
            level=level,
            context=self._format_context_block(context),
            generation_requirements=self._format_generation_requirements(profile),
            recent_constraints=self._format_recent_constraints(recent_signatures),
            study_focus=self._format_study_focus_block(study_item),
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
        cleaned_phrase = phrase.phrase.rstrip(".")
        active_study_item = self._resolve_active_study_item(
            language=language,
            phrase=cleaned_phrase,
            preferred_study_item=study_item,
        )

        self.generation_store.remember_signature(profile["signature"])
        phrase_id = self.generation_store.remember_generated_phrase(
            {
                "phrase": cleaned_phrase,
                "language": language,
                "communicative_goal": profile["communicative_goal"],
                "sentence_shape": profile["sentence_shape"],
                "grammar_focus": profile["grammar_focus"],
                "study_item_id": active_study_item["id"] if active_study_item else "",
                "study_item_type": active_study_item["item_type"] if active_study_item else "",
                "study_item_source_text": active_study_item["source_text"] if active_study_item else "",
            }
        )

        return {
            "phrase": cleaned_phrase,
            "phrase_id": phrase_id,
        }

    def check_translation(
        self,
        source_phrase: str,
        user_translation: str,
        language: str,
        phrase_id: str = "",
    ) -> TranslationFeedbackResult:
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
        study_suggestions = self._build_study_suggestions(
            language=language,
            source_phrase=source_phrase,
            phrase_id=phrase_id,
            assessment=assessment,
        )

        if phrase_id:
            self.generation_store.discard_generated_phrase(phrase_id)

        return TranslationFeedbackResult(
            correct_translation=assessment.correct_translation,
            score=assessment.score,
            word_feedback=assessment.word_feedback,
            feedback_html=feedback_html,
            study_suggestions=study_suggestions,
        )

    def add_study_item(self, language: str, item_type: str, source_text: str, explanation: str) -> Dict[str, str]:
        return self.study_store.add_item(
            language=language,
            item_type=item_type,
            source_text=source_text,
            explanation=explanation,
        )

    def remove_study_item(self, item_id: str) -> bool:
        return self.study_store.remove_item(item_id)

    def _build_study_suggestions(
        self,
        language: str,
        source_phrase: str,
        phrase_id: str,
        assessment: TranslationAssessment,
    ) -> List[Dict[str, object]]:
        active_phrase = self._resolve_phrase_metadata(
            phrase_id=phrase_id,
            source_phrase=source_phrase,
            language=language,
        )

        if active_phrase and active_phrase.get("study_item_id") and self._should_offer_removal(active_phrase, assessment):
            study_item = self.study_store.get_item(active_phrase["study_item_id"])
            if study_item:
                return [
                    {
                        "action": "remove",
                        "label": study_item["source_text"],
                        "item": study_item,
                    }
                ]

        if assessment.score >= 4:
            return []

        suggestions = []
        seen_sources = set()

        for recommendation in assessment.study_recommendations:
            if not recommendation.should_track:
                continue

            source_text = recommendation.source_text.strip()
            if not source_text:
                continue

            normalized_item_type = self._normalize_item_type(recommendation.item_type)
            normalized_source_text = self._normalize_source_text(source_text)

            if normalized_source_text in seen_sources:
                continue

            if self.study_store.find_item(language, normalized_item_type, source_text):
                continue

            seen_sources.add(normalized_source_text)
            suggestions.append(
                {
                    "action": "add",
                    "label": source_text,
                    "item": {
                        "language": language,
                        "item_type": normalized_item_type,
                        "source_text": source_text,
                        "explanation": source_text,
                    },
                }
            )

        if not suggestions:
            suggestions = self._build_structural_fallback_suggestions(
                language=language,
                source_phrase=source_phrase,
                active_phrase=active_phrase,
                assessment=assessment,
            )

        if not suggestions:
            suggestions = self._build_word_based_fallback_suggestions(
                language=language,
                assessment=assessment,
            )

        return suggestions[:3]

    def _build_structural_fallback_suggestions(
        self,
        language: str,
        source_phrase: str,
        active_phrase: Optional[Dict[str, str]],
        assessment: TranslationAssessment,
    ) -> List[Dict[str, object]]:
        if assessment.score >= 4:
            return []

        suggestions = []
        seen_sources = set()

        grammar_focus = (active_phrase or {}).get("grammar_focus", "").strip()
        if grammar_focus:
            normalized_grammar_focus = self._normalize_source_text(grammar_focus)
            if not self.study_store.find_item(language, "grammar_rule", grammar_focus):
                seen_sources.add(normalized_grammar_focus)
                suggestions.append(
                    self._make_study_suggestion(
                        action="add",
                        label=grammar_focus,
                        item={
                            "language": language,
                            "item_type": "grammar_rule",
                            "source_text": grammar_focus,
                            "explanation": grammar_focus,
                        },
                    )
                )

        construction_candidate = self._extract_construction_candidate(
            source_phrase=source_phrase,
            active_phrase=active_phrase,
            assessment=assessment,
        )
        if construction_candidate:
            normalized_construction = self._normalize_source_text(construction_candidate)
            if (
                normalized_construction not in seen_sources
                and not self.study_store.find_item(language, "construction", construction_candidate)
            ):
                suggestions.append(
                    self._make_study_suggestion(
                        action="add",
                        label=construction_candidate,
                        item={
                            "language": language,
                            "item_type": "construction",
                            "source_text": construction_candidate,
                            "explanation": construction_candidate,
                        },
                    )
                )

        return suggestions[:3]

    def _resolve_phrase_metadata(
        self,
        phrase_id: str,
        source_phrase: str,
        language: str,
    ) -> Optional[Dict[str, str]]:
        if phrase_id:
            metadata = self.generation_store.get_generated_phrase(phrase_id)
            if metadata:
                return metadata

        return self.generation_store.find_generated_phrase(
            phrase=source_phrase,
            language=language,
        )

    def _should_offer_removal(
        self,
        active_phrase: Dict[str, str],
        assessment: TranslationAssessment,
    ) -> bool:
        item_type = active_phrase.get("study_item_type")

        if assessment.score >= 5:
            return True

        if assessment.score < 2:
            return False

        if item_type == "grammar_rule":
            return assessment.score >= 4

        target_text = self._normalize_source_text(active_phrase.get("study_item_source_text", ""))
        if not target_text:
            return assessment.score >= 4

        feedback_for_target = [
            item.correctness
            for item in assessment.word_feedback
            if target_text in self._normalize_source_text(item.word)
            or self._normalize_source_text(item.word) in target_text
        ]

        if not feedback_for_target:
            return assessment.score >= 4

        if item_type == "word":
            return "correct" in feedback_for_target and "incorrect" not in feedback_for_target

        if item_type == "construction":
            if assessment.score >= 4:
                return "incorrect" not in feedback_for_target
            return "correct" in feedback_for_target and "incorrect" not in feedback_for_target

        if assessment.score >= 4:
            return "incorrect" not in feedback_for_target

        return "correct" in feedback_for_target and "incorrect" not in feedback_for_target

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

    def _pick_study_item(self, language: str) -> Optional[Dict[str, str]]:
        study_items = self.study_store.list_items(language)
        if not study_items:
            return None

        if random.random() > self.config.study_item_reuse_probability:
            return None

        return random.choice(study_items)

    def _resolve_active_study_item(
        self,
        language: str,
        phrase: str,
        preferred_study_item: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, str]]:
        if preferred_study_item and self._phrase_contains_study_item(phrase, preferred_study_item):
            return preferred_study_item

        study_items = self.study_store.list_items(language)
        matching_items = [
            item for item in study_items if self._phrase_contains_study_item(phrase, item)
        ]

        if not matching_items:
            if preferred_study_item and preferred_study_item.get("item_type") == "grammar_rule":
                return preferred_study_item
            return None

        matching_items.sort(
            key=lambda item: len(self._normalize_source_text(item.get("source_text", ""))),
            reverse=True,
        )
        return matching_items[0]

    def _build_word_based_fallback_suggestions(
        self,
        language: str,
        assessment: TranslationAssessment,
    ) -> List[Dict[str, object]]:
        suggestions = []
        seen_sources = set()

        for word_feedback in assessment.word_feedback:
            if word_feedback.correctness not in ("incorrect", "partially_correct"):
                continue

            source_text = word_feedback.word.strip(".,!?;:").strip()
            normalized_source_text = self._normalize_source_text(source_text)

            if len(normalized_source_text) < 3:
                continue

            if normalized_source_text in seen_sources:
                continue

            if self.study_store.find_item(language, "word", source_text):
                continue

            seen_sources.add(normalized_source_text)
            suggestions.append(
                self._make_study_suggestion(
                    action="add",
                    label=source_text,
                    item={
                        "language": language,
                        "item_type": "word",
                        "source_text": source_text,
                        "explanation": source_text,
                    },
                )
            )

            if len(suggestions) >= 3:
                break

        return suggestions

    def _phrase_contains_study_item(self, phrase: str, study_item: Dict[str, str]) -> bool:
        normalized_phrase = self._normalize_source_text(phrase)
        normalized_source_text = self._normalize_source_text(study_item.get("source_text", ""))

        if not normalized_phrase or not normalized_source_text:
            return False

        item_type = study_item.get("item_type")
        if item_type == "grammar_rule":
            return False

        if " " in normalized_source_text:
            return normalized_source_text in normalized_phrase

        phrase_tokens = normalized_phrase.split()
        return normalized_source_text in phrase_tokens

    def _extract_construction_candidate(
        self,
        source_phrase: str,
        active_phrase: Optional[Dict[str, str]],
        assessment: TranslationAssessment,
    ) -> str:
        sentence_shape = (active_phrase or {}).get("sentence_shape", "")
        source_words = [item.word.strip(".,!?;:").strip() for item in assessment.word_feedback if item.word.strip(".,!?;:").strip()]

        if sentence_shape in ("yes/no question", "wh-question") and len(source_words) >= 2:
            return " ".join(source_words[:2])

        if sentence_shape == "imperative" and len(source_words) >= 2:
            return " ".join(source_words[:2])

        contiguous_run = []
        best_run = []

        for item in assessment.word_feedback:
            cleaned_word = item.word.strip(".,!?;:").strip()
            if not cleaned_word:
                continue

            if item.correctness in ("incorrect", "partially_correct"):
                contiguous_run.append(cleaned_word)
                if len(contiguous_run) > len(best_run):
                    best_run = contiguous_run[:]
                continue

            contiguous_run = []

        if len(best_run) >= 2:
            return " ".join(best_run[:3])

        return ""

    @staticmethod
    def _make_study_suggestion(action: str, label: str, item: Dict[str, str]) -> Dict[str, object]:
        return {
            "action": action,
            "label": label,
            "item": item,
        }

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

    def _format_study_focus_block(self, study_item: Optional[Dict[str, str]]) -> str:
        if not study_item:
            return "Дополнительного элемента из списка изучения сейчас нет."

        if study_item["item_type"] == "grammar_rule":
            return "\n".join(
                (
                    "Дополнительный учебный фокус:",
                    "- Тип: grammar_rule",
                    "- Правило: {0}".format(study_item["source_text"]),
                    "- Построй фразу так, чтобы для правильного перевода нужно было применить это правило.",
                )
            )

        return "\n".join(
            (
                "Дополнительный учебный фокус:",
                "- Тип: {0}".format(study_item["item_type"]),
                "- Элемент: {0}".format(study_item["source_text"]),
                "- Используй этот элемент естественно и заметно в новой фразе.",
            )
        )

    @staticmethod
    def _normalize_item_type(item_type: str) -> str:
        normalized_item_type = item_type.strip().lower().replace("-", "_")
        if normalized_item_type in ("word", "construction", "grammar_rule"):
            return normalized_item_type
        return "word"

    @staticmethod
    def _normalize_source_text(value: str) -> str:
        cleaned_value = value.strip().strip(".,!?;:").lower()
        return " ".join(cleaned_value.split())

    def _validate_level(self, level: str) -> None:
        if level not in self.config.level_options:
            raise ValueError("Unsupported level: {0}".format(level))

    def _validate_language(self, language: str) -> None:
        supported_languages = {option["value"] for option in self.config.language_options}
        if language not in supported_languages:
            raise ValueError("Unsupported language: {0}".format(language))
