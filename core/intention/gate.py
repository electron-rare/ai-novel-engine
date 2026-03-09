from pathlib import Path

from core.chapters import ChapterId, collect_matching_chapter_files

class IntentionGate:
    """
    Hard lock: blocks any generation if no explicit intention exists.
    """

    def __init__(self, project_root: Path):
        self.intentions_dir = project_root / "notes" / "intentions"

    def has_intention(self, chapter: object | None = None) -> bool:
        if not self.intentions_dir.exists():
            return False
        if chapter is None:
            intentions = list(self.intentions_dir.glob("chapitre_*.md"))
            return len(intentions) > 0
        chapter_id = ChapterId.parse(chapter)
        intentions = collect_matching_chapter_files(self.intentions_dir, chapter_id)
        return len(intentions) > 0

    def resolve_intention_path(self, chapter: object) -> Path | None:
        chapter_id = ChapterId.parse(chapter)
        matches = collect_matching_chapter_files(self.intentions_dir, chapter_id)
        if not matches:
            return None
        if len(matches) > 1:
            from core.chapters import ChapterConflictError

            raise ChapterConflictError(chapter_id, matches)
        return matches[0]

    def load_intention(self, chapter: object) -> str:
        path = self.resolve_intention_path(chapter)
        if path is None:
            chapter_id = ChapterId.parse(chapter)
            raise RuntimeError(f"Aucune intention trouvée pour {chapter_id.slug}.")
        return path.read_text(encoding="utf-8").strip()

    def assert_intention(self, chapter: object | None = None):
        if not self.has_intention(chapter):
            if chapter is None:
                raise RuntimeError(
                    "Aucune intention trouvée.\n"
                    "L'écriture est volontairement bloquée.\n"
                    "Créez d'abord une intention explicite (CLI: intention create)."
                )

            chapter_id = ChapterId.parse(chapter)
            raise RuntimeError(
                f"Aucune intention trouvée pour {chapter_id.slug}.\n"
                "L'écriture est volontairement bloquée.\n"
                "Créez d'abord une intention explicite (CLI: intention create)."
            )
