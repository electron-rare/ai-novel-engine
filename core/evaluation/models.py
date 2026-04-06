from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.json_payload import parse_json_object, string_list

_JUDGE_BLOCKER_ALIASES = {
    "incomplete": "incomplete_scene",
    "lacks_narrative_continuity": "weak_narrative_continuity",
}
_ALLOWED_JUDGE_BLOCKERS = {
    "weak_narrative_continuity",
    "incomplete_scene",
    "missing_risky_decision",
    "missing_immediate_consequence",
}


@dataclass(frozen=True)
class NarrativeJudgeReport:
    ready_for_manuscript: bool
    summary: str
    blockers: list[str]
    recommendations: list[str]
    error: str | None = None
    raw: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        blockers = _normalize_blockers(self.blockers)
        recommendations = _normalize_recommendations(self.recommendations)
        summary = self.summary.strip() or "Diagnostic narratif indisponible."
        error = _normalize_error(self.error)
        ready = bool(self.ready_for_manuscript) and not blockers

        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "recommendations", recommendations)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "error", error)
        object.__setattr__(self, "ready_for_manuscript", ready)

    @classmethod
    def from_response_text(cls, text: str) -> "NarrativeJudgeReport":
        raw = parse_json_object(text)
        blockers = _normalize_blockers(string_list(raw.get("blockers")))
        recommendations = _normalize_recommendations(string_list(raw.get("recommendations")))
        ready_default = not blockers
        ready_for_manuscript = bool(raw.get("ready_for_manuscript", ready_default))
        summary = str(raw.get("summary", "")).strip() or "Diagnostic narratif indisponible."
        return cls(
            ready_for_manuscript=ready_for_manuscript,
            summary=summary,
            blockers=blockers,
            recommendations=recommendations,
            error=_normalize_error(raw.get("error")),
            raw=raw,
        )

    @classmethod
    def unavailable(cls, error: str) -> "NarrativeJudgeReport":
        return cls(
            ready_for_manuscript=True,
            summary="Le juge narratif secondaire est indisponible; le gate principal reste seul applicable.",
            blockers=[],
            recommendations=[],
            error=error.strip() or "Erreur de juge inconnue.",
            raw={"error": error.strip() or "Erreur de juge inconnue."},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "ready_for_manuscript": self.ready_for_manuscript,
            "summary": self.summary,
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
            "error": self.error,
        }


class NarrativeJudge(ABC):
    @abstractmethod
    def evaluate(
        self,
        *,
        chapter_slug: str,
        intention: str,
        structure_markdown: str,
        draft_markdown: str,
        story_context: str,
    ) -> NarrativeJudgeReport:
        raise NotImplementedError


def _normalize_error(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_blockers(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        label = _JUDGE_BLOCKER_ALIASES.get(value.strip(), value.strip())
        # Preserve unknown blocker labels so secondary-judge drift stays visible
        # instead of being treated as an implicit "no blocker".
        if not label or label in normalized:
            continue
        normalized.append(label)
    return normalized


def _normalize_recommendations(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in normalized:
            continue
        normalized.append(text)
    return normalized
