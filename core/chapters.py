from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_CHAPTER_PATTERN = re.compile(r"^chapitre_(\d+)$", re.IGNORECASE)
_DIGITS_PATTERN = re.compile(r"^\d+$")


class ChapterError(ValueError):
    """Raised when a chapter identifier is invalid."""


class ChapterConflictError(ChapterError):
    """Raised when both canonical and legacy files exist for the same chapter."""

    def __init__(self, chapter: "ChapterId", paths: list[Path]):
        joined = ", ".join(str(path) for path in paths)
        super().__init__(
            f"Conflit de chapitre pour {chapter.slug}: plusieurs fichiers existent ({joined})."
        )
        self.chapter = chapter
        self.paths = paths


@dataclass(frozen=True, order=True)
class ChapterId:
    number: int

    def __post_init__(self):
        if self.number <= 0:
            raise ChapterError("Le numéro de chapitre doit être strictement positif.")

    @classmethod
    def parse(cls, value: object) -> "ChapterId":
        return cls(parse_chapter_number(value))

    @property
    def label(self) -> str:
        return f"{self.number:02d}"

    @property
    def slug(self) -> str:
        return f"chapitre_{self.label}"

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"

    def __str__(self) -> str:
        return self.slug


def parse_chapter_number(value: object) -> int:
    if isinstance(value, ChapterId):
        return value.number

    if isinstance(value, int) and not isinstance(value, bool):
        return value

    if isinstance(value, Path):
        text = value.stem
    else:
        text = str(value).strip()

    if not text:
        raise ChapterError("Numéro de chapitre requis.")

    candidate = text
    if "/" in candidate or "\\" in candidate or candidate.endswith(".md"):
        candidate = Path(candidate).stem

    match = _CHAPTER_PATTERN.fullmatch(candidate)
    if match:
        return int(match.group(1))

    if _DIGITS_PATTERN.fullmatch(candidate):
        return int(candidate)

    raise ChapterError(f"Identifiant de chapitre invalide: {value!r}")


def discover_chapter_files(directory: Path) -> list[tuple[ChapterId, Path]]:
    if not directory.exists():
        return []

    discovered: list[tuple[ChapterId, Path]] = []
    for path in sorted(directory.glob("chapitre_*.md")):
        try:
            chapter = ChapterId.parse(path.stem)
        except ChapterError:
            continue
        discovered.append((chapter, path))
    return discovered


def discover_chapter_dirs(directory: Path) -> list[tuple[ChapterId, Path]]:
    if not directory.exists():
        return []

    discovered: list[tuple[ChapterId, Path]] = []
    for path in sorted(directory.glob("chapitre_*")):
        if not path.is_dir():
            continue
        try:
            chapter = ChapterId.parse(path.name)
        except ChapterError:
            continue
        discovered.append((chapter, path))
    return discovered


def collect_matching_chapter_files(directory: Path, chapter: ChapterId) -> list[Path]:
    paths = [path for candidate, path in discover_chapter_files(directory) if candidate == chapter]
    unique_paths = sorted(set(paths))
    return unique_paths


def resolve_chapter_file(directory: Path, chapter: ChapterId) -> Path:
    matches = collect_matching_chapter_files(directory, chapter)
    if len(matches) > 1:
        raise ChapterConflictError(chapter, matches)
    if matches:
        return matches[0]
    return directory / chapter.filename
