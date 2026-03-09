from __future__ import annotations

from pathlib import Path
from string import Template
import json


class PromptNotFoundError(FileNotFoundError):
    """Raised when a prompt file is missing."""


class PromptStore:
    def __init__(self, root: Path):
        self.root = root
        self.prompts_dir = root / "prompts"
        self.builtin_prompts_dir = Path(__file__).resolve().parents[1] / "prompts"

    def render(self, name: str, **context: object) -> str:
        path = self.prompts_dir / f"{name}_v1.txt"
        if not path.exists():
            path = self.builtin_prompts_dir / f"{name}_v1.txt"
        if not path.exists():
            raise PromptNotFoundError(f"Prompt introuvable: {path}")

        template = Template(path.read_text(encoding="utf-8"))
        normalized = {key: self._normalize(value) for key, value in context.items()}
        return template.substitute(normalized)

    def _normalize(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)
