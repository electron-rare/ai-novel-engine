import sys
from pathlib import Path

from core.project.loader import ProjectState
from core.intention.gate import IntentionGate


def cmd_status(root: Path):
    project = ProjectState(root)
    state = project.summary()

    print("\nAI Novel Engine — Project Status\n")

    if state["current_chapter"] is None:
        print("📄 Aucun chapitre détecté.")
    else:
        print(f"📄 Chapitre courant : {state['current_chapter']}")

    print(f"📐 Structure présente : {state['has_structure']}")
    print(f"🧠 Mémoire présente   : {state['has_memory']}")
    print("\n(Prochaine étape : définir une intention)\n")


def cmd_intention_create(root: Path):
    intentions_dir = root / "notes" / "intentions"
    intentions_dir.mkdir(parents=True, exist_ok=True)

    chap = input("Numéro du chapitre (ex: 08) : ").strip()
    if not chap:
        print("❌ Numéro de chapitre requis.")
        return

    path = intentions_dir / f"chapitre_{chap}.md"
    if path.exists():
        print(f"⚠️ Une intention existe déjà : {path}")
        return

    print("\nDécris l’intention (finir par Ctrl+D / Ctrl+Z):\n")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    content = "\n".join(lines).strip()
    if not content:
        print("❌ Intention vide. Annulé.")
        return

    path.write_text(
        f"# Intention — Chapitre {chap}\n\n{content}\n",
        encoding="utf-8"
    )

    print(f"✅ Intention créée : {path}\n")


def cmd_write(root: Path):
    gate = IntentionGate(root)

    try:
        gate.assert_intention()
    except RuntimeError as e:
        print("\n⛔ ÉCRITURE BLOQUÉE\n")
        print(str(e))
        print("\n➡️ Utilise : python3 -m cli.main intention create\n")
        return

    print("\n✅ Intention détectée.")
    print("✍️ Écriture autorisée (génération non implémentée).\n")


def main():
    root = Path.cwd()

    # Aucun argument → status
    if len(sys.argv) == 1:
        cmd_status(root)
        return

    # intention create
    if sys.argv[1] == "intention" and len(sys.argv) >= 3:
        if sys.argv[2] == "create":
            cmd_intention_create(root)
            return

    # write
    if sys.argv[1] == "write":
        cmd_write(root)
        return

    # aide
    print("\nCommande inconnue.\n")
    print("Commandes disponibles :")
    print("  python3 -m cli.main               → status")
    print("  python3 -m cli.main intention create")
    print("  python3 -m cli.main write\n")


if __name__ == "__main__":
    main()
