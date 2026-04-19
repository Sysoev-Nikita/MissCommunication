import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class OpenAIApiLogger:
    def __init__(self, enabled: bool, log_file: Path) -> None:
        self.enabled = enabled
        self.log_file = log_file

    def log_event(
        self,
        stage: str,
        request_kind: str,
        model: str,
        messages: List[Dict[str, Any]],
        response: Any,
        parsed_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        response_dump = response.model_dump(mode="json")
        usage = response_dump.get("usage") or {}
        choices = response_dump.get("choices") or []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "request_kind": request_kind,
            "model": model,
            "message_count": len(messages),
            "request_characters": sum(len(str(message.get("content", ""))) for message in messages),
            "messages": messages,
            "usage": usage,
            "response_characters": len(json.dumps(response_dump, ensure_ascii=False)),
            "response": response_dump,
            "response_text": self._extract_response_text(choices),
            "parsed_payload": parsed_payload,
        }

        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False))
            file.write("\n")

    @staticmethod
    def _extract_response_text(choices: List[Dict[str, Any]]) -> str:
        parts: List[str] = []

        for choice in choices:
            message = choice.get("message") or {}
            content = message.get("content")

            if isinstance(content, str):
                parts.append(content)
                continue

            if isinstance(content, list):
                for chunk in content:
                    if not isinstance(chunk, dict):
                        continue
                    if chunk.get("type") in ("text", "output_text"):
                        parts.append(str(chunk.get("text", "")))

        return "\n".join(part for part in parts if part)
