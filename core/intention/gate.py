from pathlib import Path

class IntentionGate:
    """
    Hard lock: blocks any generation if no explicit intention exists.
    """

    def __init__(self, project_root: Path):
        self.intentions_dir = project_root / "notes" / "intentions"

    def has_intention(self) -> bool:
        if not self.intentions_dir.exists():
            return False
        intentions = list(self.intentions_dir.glob("chapitre_*.md"))
        return len(intentions) > 0

    def assert_intention(self):
        if not self.has_intention():
            raise RuntimeError(
                "Aucune intention trouvée.\n"
                "L'écriture est volontairement bloquée.\n"
                "Créez d'abord une intention explicite (CLI: intention create)."
            )

