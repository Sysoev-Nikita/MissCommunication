from typing import Dict, List, Optional
from uuid import uuid4

from flask import session


class SessionGenerationStore:
    RECENT_SIGNATURES_KEY = "recent_generation_signatures"
    GENERATED_PHRASES_KEY = "generated_phrase_metadata"

    def __init__(self, memory_size: int) -> None:
        self.memory_size = memory_size
        self.pending_phrase_limit = max(memory_size * 4, 12)

    def recent_signatures(self) -> List[str]:
        return list(session.get(self.RECENT_SIGNATURES_KEY, []))

    def remember_signature(self, signature: str) -> None:
        recent_signatures = self.recent_signatures()
        recent_signatures.append(signature)
        session[self.RECENT_SIGNATURES_KEY] = recent_signatures[-self.memory_size :]
        session.modified = True

    def remember_generated_phrase(self, metadata: Dict[str, str]) -> str:
        generated_phrases = list(session.get(self.GENERATED_PHRASES_KEY, []))
        phrase_id = str(uuid4())

        generated_phrases.append(
            {
                "id": phrase_id,
                **metadata,
            }
        )
        session[self.GENERATED_PHRASES_KEY] = generated_phrases[-self.pending_phrase_limit :]
        session.modified = True
        return phrase_id

    def get_generated_phrase(self, phrase_id: str) -> Optional[Dict[str, str]]:
        for metadata in reversed(session.get(self.GENERATED_PHRASES_KEY, [])):
            if metadata.get("id") == phrase_id:
                return metadata
        return None

    def find_generated_phrase(self, phrase: str, language: Optional[str] = None) -> Optional[Dict[str, str]]:
        normalized_phrase = self._normalize(phrase)

        for metadata in reversed(session.get(self.GENERATED_PHRASES_KEY, [])):
            if language and metadata.get("language") != language:
                continue
            if self._normalize(metadata.get("phrase", "")) == normalized_phrase:
                return metadata
        return None

    def discard_generated_phrase(self, phrase_id: str) -> None:
        generated_phrases = list(session.get(self.GENERATED_PHRASES_KEY, []))
        filtered_phrases = [metadata for metadata in generated_phrases if metadata.get("id") != phrase_id]

        if len(filtered_phrases) == len(generated_phrases):
            return

        session[self.GENERATED_PHRASES_KEY] = filtered_phrases
        session.modified = True

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().lower().split())


class SessionStudyStore:
    STUDY_ITEMS_KEY = "study_items"

    def list_items(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        study_items = list(session.get(self.STUDY_ITEMS_KEY, []))
        if language is None:
            return study_items
        return [item for item in study_items if item.get("language") == language]

    def add_item(self, language: str, item_type: str, source_text: str, explanation: str) -> Dict[str, str]:
        existing_item = self.find_item(language, item_type, source_text)
        if existing_item:
            return existing_item

        study_items = self.list_items()
        study_item = {
            "id": str(uuid4()),
            "language": language,
            "item_type": item_type,
            "source_text": source_text.strip(),
            "explanation": explanation.strip(),
        }
        study_items.append(study_item)
        session[self.STUDY_ITEMS_KEY] = study_items
        session.modified = True
        return study_item

    def remove_item(self, item_id: str) -> bool:
        study_items = self.list_items()
        filtered_items = [item for item in study_items if item.get("id") != item_id]
        if len(filtered_items) == len(study_items):
            return False

        session[self.STUDY_ITEMS_KEY] = filtered_items
        session.modified = True
        return True

    def get_item(self, item_id: str) -> Optional[Dict[str, str]]:
        for item in self.list_items():
            if item.get("id") == item_id:
                return item
        return None

    def find_item(self, language: str, item_type: str, source_text: str) -> Optional[Dict[str, str]]:
        normalized_source_text = self._normalize(source_text)
        for item in self.list_items(language):
            if item.get("item_type") != item_type:
                continue
            if self._normalize(item.get("source_text", "")) == normalized_source_text:
                return item
        return None

    def has_items(self, language: str) -> bool:
        return bool(self.list_items(language))

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().lower().split())
