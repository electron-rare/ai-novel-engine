from __future__ import annotations

from pathlib import Path
import json

from core.chapters import ChapterId, discover_chapter_dirs, discover_chapter_files


class ProjectState:
    """
    Detects and summarizes the current state of a writing project.
    Read-only, file-based, human-readable.
    """

    def __init__(self, root: Path):
        self.root = root
        self.manuscript = root / "manuscrit"
        self.structure = root / "structure" / "chapitres"
        self.drafts = root / "brouillons" / "chapitres"
        self.memory = root / "memoire"
        self.memory_chapters = self.memory / "chapitres"
        self.intentions = root / "notes" / "intentions"

    def detect_current_chapter(self) -> str | None:
        chapters = self.known_chapters()
        if not chapters:
            return None
        return chapters[-1].slug

    def known_chapters(self) -> list[ChapterId]:
        chapters: set[ChapterId] = set()
        for chapter, _path in discover_chapter_files(self.intentions):
            chapters.add(chapter)
        for chapter, _path in discover_chapter_files(self.structure):
            chapters.add(chapter)
        for chapter, _path in discover_chapter_files(self.manuscript):
            chapters.add(chapter)
        for chapter, _path in discover_chapter_files(self.memory_chapters):
            chapters.add(chapter)
        for chapter, _path in discover_chapter_dirs(self.drafts):
            chapters.add(chapter)
        return sorted(chapters)

    def latest_drafts(self) -> dict[str, str]:
        latest: dict[str, str] = {}
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if meta:
                artifacts = meta.get("artifacts", {})
                if isinstance(artifacts, dict):
                    repair_latest = artifacts.get("repair_latest")
                    if isinstance(repair_latest, str) and repair_latest.strip():
                        latest[chapter.slug] = Path(repair_latest).name
                        continue

            candidates = sorted(path.name for path in draft_dir.glob("draft_v*.md"))
            if candidates:
                latest[chapter.slug] = candidates[-1]
        return latest

    def latest_repairs(self) -> dict[str, str]:
        latest: dict[str, str] = {}
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if not meta:
                continue
            artifacts = meta.get("artifacts", {})
            if not isinstance(artifacts, dict):
                continue
            repair_latest = artifacts.get("repair_latest")
            if isinstance(repair_latest, str) and repair_latest.strip():
                latest[chapter.slug] = Path(repair_latest).name
        return latest

    def failed_chapters(self) -> list[dict[str, object]]:
        failures: list[dict[str, object]] = []
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if not meta or meta.get("status") != "failed":
                continue
            failures.append(
                {
                    "chapter": chapter.slug,
                    "status": str(meta.get("status", "")),
                    "failed_stage": str(meta.get("failed_stage", "")),
                    "meta_path": str(draft_dir / "meta.json"),
                    "retry_stages": self._retry_stages(meta),
                    "last_status_message": str(meta.get("last_status_message", "")).strip(),
                }
            )
        return failures

    def quality_blocked_chapters(self) -> list[dict[str, object]]:
        blocked: list[dict[str, object]] = []
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if not meta or meta.get("status") != "quality_blocked":
                continue
            artifacts = meta.get("artifacts", {})
            if not isinstance(artifacts, dict):
                artifacts = {}
            raw_blockers = meta.get("quality_blockers")
            quality_blockers = []
            if isinstance(raw_blockers, list):
                quality_blockers = [str(item).strip() for item in raw_blockers if str(item).strip()]
            blocked.append(
                {
                    "chapter": chapter.slug,
                    "status": str(meta.get("status", "")),
                    "failed_stage": str(meta.get("failed_stage", "")),
                    "meta_path": str(draft_dir / "meta.json"),
                    "draft_path": str(artifacts.get("repair_latest") or artifacts.get("draft_v2", draft_dir / "draft_v2.md")),
                    "gate_path": str(artifacts.get("gate_v1", draft_dir / "gate_v1.json")),
                    "quality_blockers": quality_blockers,
                    "retry_stages": self._retry_stages(meta),
                    "repair_attempts": int(meta.get("repair_attempts", 0) or 0),
                    "repair_models": self._repair_models(meta),
                    "last_status_message": str(meta.get("last_status_message", "")).strip(),
                }
            )
        return blocked

    def awaiting_acceptance(self) -> list[dict[str, object]]:
        pending: list[dict[str, object]] = []
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if not meta or meta.get("status") != "awaiting_acceptance":
                continue
            artifacts = meta.get("artifacts", {})
            if not isinstance(artifacts, dict):
                artifacts = {}
            pending.append(
                {
                    "chapter": chapter.slug,
                    "status": str(meta.get("status", "")),
                    "draft_path": str(artifacts.get("repair_latest") or artifacts.get("draft_v2", draft_dir / "draft_v2.md")),
                    "critique_path": str(artifacts.get("critique_v1", draft_dir / "critique_v1.md")),
                    "gate_path": str(artifacts.get("gate_v1", draft_dir / "gate_v1.json")),
                    "meta_path": str(draft_dir / "meta.json"),
                    "retry_stages": self._retry_stages(meta),
                    "repair_attempts": int(meta.get("repair_attempts", 0) or 0),
                    "repair_models": self._repair_models(meta),
                    "last_status_message": str(meta.get("last_status_message", "")).strip(),
                }
            )
        return pending

    def retry_stages(self) -> dict[str, list[str]]:
        retries: dict[str, list[str]] = {}
        for chapter, draft_dir in discover_chapter_dirs(self.drafts):
            meta = self._load_meta(draft_dir)
            if not meta:
                continue
            stages = self._retry_stages(meta)
            if stages:
                retries[chapter.slug] = stages
        return retries

    def summary(self) -> dict[str, object]:
        return {
            "project_root": str(self.root),
            "current_chapter": self.detect_current_chapter(),
            "known_chapters": [chapter.slug for chapter in self.known_chapters()],
            "directories": {
                "structure": self.structure.exists(),
                "drafts": self.drafts.exists(),
                "manuscript": self.manuscript.exists(),
                "memory": self.memory.exists(),
            },
            "has_structure": self.structure.exists(),
            "has_memory": self.memory.exists(),
            "latest_drafts": self.latest_drafts(),
            "latest_repairs": self.latest_repairs(),
            "failed_chapters": self.failed_chapters(),
            "quality_blocked_chapters": self.quality_blocked_chapters(),
            "awaiting_acceptance": self.awaiting_acceptance(),
            "retry_stages": self.retry_stages(),
        }

    def _load_meta(self, draft_dir: Path) -> dict[str, object] | None:
        meta_path = draft_dir / "meta.json"
        if not meta_path.exists():
            return None
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _retry_stages(self, meta: dict[str, object]) -> list[str]:
        raw = meta.get("retry_stages")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def _repair_models(self, meta: dict[str, object]) -> list[str]:
        raw = meta.get("repair_models")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]
