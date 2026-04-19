from typing import Any, Dict, List, Optional

from markupsafe import Markup
from pydantic import BaseModel, Field


class PhraseResponse(BaseModel):
    phrase: str


class WordFeedback(BaseModel):
    word: str
    correctness: str


class StudyRecommendation(BaseModel):
    should_track: bool = False
    item_type: str = ""
    source_text: str = ""


class TranslationAssessment(BaseModel):
    correct_translation: str
    score: int
    word_feedback: List[WordFeedback]
    study_recommendations: List[StudyRecommendation] = Field(default_factory=list)


class TranslationFeedbackResult:
    def __init__(
        self,
        correct_translation: str,
        score: int,
        word_feedback: List[WordFeedback],
        feedback_html: str,
        study_suggestions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.correct_translation = correct_translation
        self.score = score
        self.word_feedback = word_feedback
        self.feedback_html = feedback_html
        self.study_suggestions = study_suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correct_translation": self.correct_translation.rstrip("."),
            "feedback": Markup(self.feedback_html),
            "score": self.score,
            "word_feedback": [item.model_dump() for item in self.word_feedback],
            "study_suggestions": self.study_suggestions,
        }
