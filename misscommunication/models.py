from typing import Any, Dict, List

from markupsafe import Markup
from pydantic import BaseModel


class PhraseResponse(BaseModel):
    phrase: str


class WordFeedback(BaseModel):
    word: str
    correctness: str


class TranslationAssessment(BaseModel):
    correct_translation: str
    score: int
    word_feedback: List[WordFeedback]


class TranslationFeedbackResult:
    def __init__(
        self,
        correct_translation: str,
        score: int,
        word_feedback: List[WordFeedback],
        feedback_html: str,
    ) -> None:
        self.correct_translation = correct_translation
        self.score = score
        self.word_feedback = word_feedback
        self.feedback_html = feedback_html

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correct_translation": self.correct_translation.rstrip("."),
            "feedback": Markup(self.feedback_html),
            "score": self.score,
            "word_feedback": [item.model_dump() for item in self.word_feedback],
        }
