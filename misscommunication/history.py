from uuid import uuid4
from typing import Dict, List

from flask import session


class SessionHistoryStore:
    def __init__(self, max_history_length: int, base_message: Dict[str, str]) -> None:
        self.max_history_length = max_history_length
        self.base_message = base_message
        self._histories = {}  # type: Dict[str, List[Dict[str, str]]]

    def get_history(self) -> List[Dict[str, str]]:
        user_id = session.get("user_id")
        if not user_id:
            user_id = str(uuid4())
            session["user_id"] = user_id

        if user_id not in self._histories:
            self._histories[user_id] = [self.base_message.copy()]

        return self._histories[user_id]

    def append(self, history: List[Dict[str, str]], role: str, content: str) -> None:
        history.append({"role": role, "content": content})
        while len(history) > self.max_history_length + 1:
            history.pop(1)
