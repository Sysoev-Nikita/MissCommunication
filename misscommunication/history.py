from typing import List

from flask import session


class SessionGenerationStore:
    SESSION_KEY = "recent_generation_signatures"

    def __init__(self, memory_size: int) -> None:
        self.memory_size = memory_size

    def recent_signatures(self) -> List[str]:
        return list(session.get(self.SESSION_KEY, []))

    def remember_signature(self, signature: str) -> None:
        recent_signatures = self.recent_signatures()
        recent_signatures.append(signature)
        session[self.SESSION_KEY] = recent_signatures[-self.memory_size :]
        session.modified = True
