from pathlib import Path


class PromptRepository:
    def __init__(self, prompts_dir: Path) -> None:
        self.prompts_dir = prompts_dir

    def load(self, name: str, **kwargs: str) -> str:
        prompt = (self.prompts_dir / name).read_text(encoding="utf-8")
        return prompt.format(**kwargs)
