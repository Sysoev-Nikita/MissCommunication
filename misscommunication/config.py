import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    templates_dir: Path
    static_dir: Path
    prompts_dir: Path
    openai_api_key: Optional[str]
    secret_key: str
    default_level: str = "A1"
    default_language: str = "german"
    recent_generation_memory_size: int = 12
    study_item_reuse_probability: float = 0.7
    phrase_generation_model: str = "gpt-5.4-nano"
    translation_check_model: str = "gpt-5.4-mini"
    feedback_model: str = "gpt-5.4-nano"
    openai_reasoning_effort: str = "low"
    openai_api_logging_enabled: bool = True
    openai_api_log_file: Path = Path("logs/openai_api.jsonl")
    language_options: Tuple[Dict[str, str], ...] = field(
        default_factory=lambda: (
            {"value": "german", "label": "Немецкий"},
            {"value": "english", "label": "Английский"},
            {"value": "french", "label": "Французский"},
            {"value": "spanish", "label": "Испанский"},
            {"value": "italian", "label": "Итальянский"},
        )
    )
    level_options: Tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")
    ui_text: Dict[str, str] = field(
        default_factory=lambda: {
            "page_title": "Miss Communication",
            "context_placeholder": "Контекст",
            "translation_placeholder": "Введите ваш перевод здесь...",
            "phrase_generation_error": "Не удалось сгенерировать фразу. Попробуйте еще раз.",
            "translation_check_error": "Не удалось проверить перевод. Попробуйте еще раз.",
            "invalid_input_error": "Нужны исходная фраза и ваш перевод.",
        }
    )

    @property
    def frontend_config(self) -> Dict[str, Any]:
        return {
            "generatePhraseUrl": "/generate_phrase",
            "checkTranslationUrl": "/check_translation",
            "studyItemsUrl": "/study-items",
            "characterImages": {
                "idle": "/static/images/neutral_positive.webp",
                "happy": "/static/images/happy.webp",
                "neutral": "/static/images/neutral_positive.webp",
                "sad": "/static/images/sad.webp",
                "disappointed": "/static/images/disappointed.webp",
            },
        }

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()

        base_dir = Path(__file__).resolve().parent.parent

        return cls(
            base_dir=base_dir,
            templates_dir=base_dir / "templates",
            static_dir=base_dir / "static",
            prompts_dir=base_dir / "prompts",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            secret_key=os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex()),
            default_level=os.getenv("DEFAULT_LEVEL", "A1"),
            default_language=os.getenv("DEFAULT_LANGUAGE", "german"),
            recent_generation_memory_size=int(os.getenv("RECENT_GENERATION_MEMORY_SIZE", "12")),
            study_item_reuse_probability=float(os.getenv("STUDY_ITEM_REUSE_PROBABILITY", "0.7")),
            phrase_generation_model=os.getenv("PHRASE_GENERATION_MODEL", "gpt-5.4-nano"),
            translation_check_model=os.getenv("TRANSLATION_CHECK_MODEL", "gpt-5.4-mini"),
            feedback_model=os.getenv("FEEDBACK_MODEL", "gpt-5.4-nano"),
            openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
            openai_api_logging_enabled=_get_bool_env("OPENAI_API_LOGGING_ENABLED", default=True),
            openai_api_log_file=base_dir / os.getenv("OPENAI_API_LOG_FILE", "logs/openai_api.jsonl"),
        )


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
