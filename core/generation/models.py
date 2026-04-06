from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from core.chapters import ChapterId
from core.evaluation.models import NarrativeJudgeReport
from core.json_payload import (
    close_json_delimiters as _close_json_delimiters,
    extract_json_object as _extract_json_object,
    json_candidates as _json_candidates,
    parse_json_object as _parse_json_object,
    record_list as _record_list,
    remove_trailing_commas as _remove_trailing_commas,
    string_list as _string_list,
    strip_code_fence as _strip_code_fence,
)

_GATE_BLOCKER_ALIASES = {
    "incomplete": "incomplete_scene",
    "lacks_narrative_continuity": "weak_narrative_continuity",
}
_ALLOWED_GATE_BLOCKERS = {
    "too_short",
    "truncated_ending",
    "outline_like",
    "weak_narrative_continuity",
    "incomplete_scene",
    "missing_risky_decision",
    "missing_immediate_consequence",
}


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
    judge_blockers: list[str] = field(default_factory=list)
    judge_report: NarrativeJudgeReport | None = None
    raw: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        blockers = _normalize_gate_blockers(self.blockers)
        heuristic_blockers = _normalize_gate_blockers(self.heuristic_blockers)
        judge_blockers = _normalize_gate_blockers(self.judge_blockers)
        recommendations = _normalize_recommendations(self.recommendations)
        summary = self.summary.strip() or "Diagnostic manuscrit indisponible."
        ready = bool(self.ready_for_manuscript) and not blockers and not heuristic_blockers and not judge_blockers

        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "heuristic_blockers", heuristic_blockers)
        object.__setattr__(self, "judge_blockers", judge_blockers)
        object.__setattr__(self, "recommendations", recommendations)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "ready_for_manuscript", ready)

    @classmethod
    def from_response_text(cls, text: str) -> "ManuscriptGateReport":
        raw = _parse_json_object(text)
        blockers = _normalize_gate_blockers(_string_list(raw.get("blockers")))
        heuristic_blockers = _normalize_gate_blockers(_string_list(raw.get("heuristic_blockers")))
        judge_blockers = _normalize_gate_blockers(_string_list(raw.get("judge_blockers")))
        recommendations = _normalize_recommendations(_string_list(raw.get("recommendations")))
        judge_report_payload = raw.get("judge_report")
        judge_report = None
        if isinstance(judge_report_payload, dict):
            judge_report = NarrativeJudgeReport.from_response_text(json.dumps(judge_report_payload, ensure_ascii=False))
            if not judge_blockers:
                judge_blockers = list(judge_report.blockers)
        ready_default = not blockers and not heuristic_blockers and not judge_blockers
        ready_for_manuscript = bool(raw.get("ready_for_manuscript", ready_default))
        summary = str(raw.get("summary", "")).strip() or "Diagnostic manuscrit indisponible."
        return cls(
            ready_for_manuscript=ready_for_manuscript,
            summary=summary,
            blockers=blockers,
            recommendations=recommendations,
            heuristic_blockers=heuristic_blockers,
            judge_blockers=judge_blockers,
            judge_report=judge_report,
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
            judge_blockers=[],
            judge_report=None,
            raw={},
        )

    def all_blockers(self) -> list[str]:
        ordered: list[str] = []
        for value in [*self.heuristic_blockers, *self.blockers, *self.judge_blockers]:
            if value not in ordered:
                ordered.append(value)
        return ordered

    def with_judge_report(self, judge_report: NarrativeJudgeReport) -> "ManuscriptGateReport":
        recommendations = list(self.recommendations)
        for item in judge_report.recommendations:
            if item not in recommendations:
                recommendations.append(item)

        summary = self.summary
        if judge_report.summary and judge_report.summary not in summary:
            summary = f"{self.summary} | Juge narratif: {judge_report.summary}"

        return ManuscriptGateReport(
            ready_for_manuscript=self.ready_for_manuscript and judge_report.ready_for_manuscript and not judge_report.blockers,
            summary=summary,
            blockers=list(self.blockers),
            recommendations=recommendations,
            heuristic_blockers=list(self.heuristic_blockers),
            judge_blockers=list(judge_report.blockers),
            judge_report=judge_report,
            raw={
                **self.raw,
                "judge_report": judge_report.to_dict(),
                "judge_blockers": list(judge_report.blockers),
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "ready_for_manuscript": self.ready_for_manuscript,
            "summary": self.summary,
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
            "heuristic_blockers": list(self.heuristic_blockers),
            "judge_blockers": list(self.judge_blockers),
            "judge_report": self.judge_report.to_dict() if self.judge_report is not None else None,
        }


def _normalize_gate_blockers(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        label = _GATE_BLOCKER_ALIASES.get(value.strip(), value.strip())
        # Preserve unknown blocker labels so the gate cannot silently flip to ready
        # when prompts or local models start emitting a new diagnostic code.
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
