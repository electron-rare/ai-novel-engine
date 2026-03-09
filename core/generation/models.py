from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re

from core.chapters import ChapterId


def _strip_code_fence(text: str) -> str:
    payload = text.strip()
    if not payload.startswith("```"):
        return payload
    lines = payload.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return payload


def _remove_trailing_commas(payload: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", payload)


def _extract_json_object(payload: str) -> str | None:
    start = payload.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(payload)):
        char = payload[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return payload[start : index + 1]
    return payload[start:]


def _close_json_delimiters(payload: str) -> str:
    stack: list[str] = []
    in_string = False
    escaped = False
    for char in payload:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in {"}", "]"} and stack and char == stack[-1]:
            stack.pop()

    repaired = payload.rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1].rstrip()
    if in_string:
        repaired += '"'
    return repaired + "".join(reversed(stack))


def _json_candidates(text: str) -> list[str]:
    payload = _strip_code_fence(text)
    candidates = [payload]

    extracted = _extract_json_object(payload)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    repaired: list[str] = []
    for candidate in list(candidates):
        trimmed = _remove_trailing_commas(candidate)
        if trimmed not in candidates and trimmed not in repaired:
            repaired.append(trimmed)
        closed = _close_json_delimiters(trimmed)
        if closed not in candidates and closed not in repaired:
            repaired.append(closed)
    candidates.extend(repaired)
    return candidates


def _parse_json_object(text: str) -> dict[str, object]:
    last_error: Exception | None = None
    for candidate in _json_candidates(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if not isinstance(data, dict):
            raise ValueError("La réponse JSON attendue doit être un objet.")
        return data
    raise ValueError(str(last_error) if last_error else "Réponse JSON illisible.")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _record_list(value: object, required_key: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {str(key): str(val).strip() for key, val in item.items() if str(val).strip()}
        if record.get(required_key):
            normalized.append(record)
    return normalized


@dataclass(frozen=True)
class StructurePlan:
    chapter_id: ChapterId
    markdown: str


@dataclass(frozen=True)
class ControlReport:
    summary: str
    deviations: list[str]
    recommendations: list[str]
    rewrite_required: bool
    raw: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_response_text(cls, text: str) -> "ControlReport":
        raw = _parse_json_object(text)
        summary = str(raw.get("summary", "")).strip() or "Aucun résumé fourni."
        deviations = _string_list(raw.get("deviations"))
        recommendations = _string_list(raw.get("recommendations"))
        rewrite_required = bool(raw.get("rewrite_required", deviations or recommendations))
        return cls(
            summary=summary,
            deviations=deviations,
            recommendations=recommendations,
            rewrite_required=rewrite_required,
            raw=raw,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "deviations": list(self.deviations),
            "recommendations": list(self.recommendations),
            "rewrite_required": self.rewrite_required,
        }

    def to_markdown(self, chapter_id: ChapterId) -> str:
        verdict = "oui" if self.rewrite_required else "non"
        deviations = "\n".join(f"- {item}" for item in self.deviations) or "- Aucun écart majeur."
        recommendations = "\n".join(f"- {item}" for item in self.recommendations) or "- Aucune recommandation."
        return (
            f"# Critique — {chapter_id.slug}\n\n"
            f"## Résumé\n{self.summary}\n\n"
            f"## Réécriture requise\n{verdict}\n\n"
            f"## Écarts\n{deviations}\n\n"
            f"## Recommandations\n{recommendations}\n"
        )


@dataclass(frozen=True)
class MemoryUpdate:
    chapter_summary: str
    characters: list[dict[str, str]]
    locations: list[dict[str, str]]
    timeline_events: list[dict[str, str]]
    raw: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_response_text(cls, text: str) -> "MemoryUpdate":
        raw = _parse_json_object(text)
        chapter_summary = str(raw.get("summary", "")).strip() or "Résumé indisponible."
        characters = _record_list(raw.get("characters"), "name")
        locations = _record_list(raw.get("locations"), "name")
        timeline_events = _record_list(raw.get("timeline_events"), "event")
        return cls(
            chapter_summary=chapter_summary,
            characters=characters,
            locations=locations,
            timeline_events=timeline_events,
            raw=raw,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.chapter_summary,
            "characters": list(self.characters),
            "locations": list(self.locations),
            "timeline_events": list(self.timeline_events),
        }


@dataclass(frozen=True)
class ManuscriptGateReport:
    ready_for_manuscript: bool
    summary: str
    blockers: list[str]
    recommendations: list[str]
    heuristic_blockers: list[str]
    raw: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_response_text(cls, text: str) -> "ManuscriptGateReport":
        raw = _parse_json_object(text)
        blockers = _string_list(raw.get("blockers"))
        heuristic_blockers = _string_list(raw.get("heuristic_blockers"))
        recommendations = _string_list(raw.get("recommendations"))
        ready_default = not blockers and not heuristic_blockers
        ready_for_manuscript = bool(raw.get("ready_for_manuscript", ready_default))
        summary = str(raw.get("summary", "")).strip() or "Diagnostic manuscrit indisponible."
        return cls(
            ready_for_manuscript=ready_for_manuscript and not blockers and not heuristic_blockers,
            summary=summary,
            blockers=blockers,
            recommendations=recommendations,
            heuristic_blockers=heuristic_blockers,
            raw=raw,
        )

    @classmethod
    def from_heuristics(
        cls,
        *,
        blockers: list[str],
        recommendations: list[str],
        summary: str,
    ) -> "ManuscriptGateReport":
        return cls(
            ready_for_manuscript=False,
            summary=summary,
            blockers=list(blockers),
            recommendations=list(recommendations),
            heuristic_blockers=list(blockers),
            raw={},
        )

    def all_blockers(self) -> list[str]:
        ordered: list[str] = []
        for value in [*self.heuristic_blockers, *self.blockers]:
            if value not in ordered:
                ordered.append(value)
        return ordered

    def to_dict(self) -> dict[str, object]:
        return {
            "ready_for_manuscript": self.ready_for_manuscript,
            "summary": self.summary,
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
            "heuristic_blockers": list(self.heuristic_blockers),
        }


@dataclass(frozen=True)
class GenerationContext:
    root: Path
    chapter_id: ChapterId
    intention_path: Path
    intention_text: str
    structure_path: Path
    draft_dir: Path
    draft_v1_path: Path
    critique_path: Path
    draft_v2_path: Path
    gate_path: Path
    meta_path: Path
    manuscript_path: Path
    memory_summary_path: Path
    memory_index_dir: Path
    story_context: str

    def repair_path(self, attempt: int) -> Path:
        return self.draft_dir / f"repair_v{attempt}.md"


@dataclass(frozen=True)
class GenerationOutcome:
    chapter_id: ChapterId
    accepted: bool
    status: str
    draft_path: Path
    critique_path: Path
    gate_path: Path
    meta_path: Path
    manuscript_path: Path | None
    quality_blockers: list[str] = field(default_factory=list)
