from __future__ import annotations

import re
import argparse
from pathlib import Path
import sys

from core.chapters import ChapterConflictError, ChapterError, ChapterId, resolve_chapter_file
from core.generation.pipeline import GenerationPipeline
from core.generation.provider import ProviderConfigurationError, ProviderError
from core.project.loader import ProjectState


def cmd_status(root: Path):
    project = ProjectState(root)
    state = project.summary()

    print("\nAI Novel Engine — Project Status\n")

    current = state["current_chapter"]
    if current is None:
        print("Chapitre courant : aucun")
    else:
        print(f"Chapitre courant : {current}")

    print("\nDossiers:")
    for label, key in (
        ("Structure", "structure"),
        ("Brouillons", "drafts"),
        ("Manuscrit", "manuscript"),
        ("Memoire", "memory"),
    ):
        print(f"- {label:<10}: {state['directories'][key]}")

    latest_drafts = state["latest_drafts"]
    if latest_drafts:
        print("\nDerniers brouillons:")
        for chapter_slug, draft_name in sorted(latest_drafts.items()):
            print(f"- {chapter_slug}: {draft_name}")
    else:
        print("\nDerniers brouillons: aucun")

    latest_repairs = state["latest_repairs"]
    if latest_repairs:
        print("\nDernières réparations:")
        for chapter_slug, repair_name in sorted(latest_repairs.items()):
            print(f"- {chapter_slug}: {repair_name}")
    else:
        print("\nDernières réparations: aucune")

    failures = state["failed_chapters"]
    if failures:
        print("\nChapitres en échec:")
        for item in failures:
            retry_suffix = ""
            if item["retry_stages"]:
                retry_suffix = f" | réessais JSON: {', '.join(item['retry_stages'])}"
            status_message = f" | message: {item['last_status_message']}" if item["last_status_message"] else ""
            print(
                f"- {item['chapter']}: status={item['status']} | failed_stage={item['failed_stage']} | meta={item['meta_path']}{retry_suffix}{status_message}"
            )
    else:
        print("\nChapitres en échec: aucun")

    quality_blocked = state["quality_blocked_chapters"]
    if quality_blocked:
        print("\nBloqués par garde-fou:")
        for item in quality_blocked:
            retry_suffix = ""
            if item["retry_stages"]:
                retry_suffix = f" | réessais JSON: {', '.join(item['retry_stages'])}"
            blockers_suffix = ""
            if item["quality_blockers"]:
                blockers_suffix = f" | blockers: {', '.join(item['quality_blockers'])}"
            repair_suffix = ""
            if item["repair_attempts"]:
                repair_models = ", ".join(item["repair_models"]) if item["repair_models"] else "provider_courant"
                repair_suffix = f" | réparations: {item['repair_attempts']} ({repair_models})"
            status_message = f" | message: {item['last_status_message']}" if item["last_status_message"] else ""
            print(
                f"- {item['chapter']}: status={item['status']} | failed_stage={item['failed_stage']} | brouillon={item['draft_path']} | gate={item['gate_path']} | meta={item['meta_path']}{blockers_suffix}{repair_suffix}{retry_suffix}{status_message}"
            )
    else:
        print("\nBloqués par garde-fou: aucun")

    awaiting_acceptance = state["awaiting_acceptance"]
    if awaiting_acceptance:
        print("\nEn attente de validation:")
        for item in awaiting_acceptance:
            retry_suffix = ""
            if item["retry_stages"]:
                retry_suffix = f" | réessais JSON: {', '.join(item['retry_stages'])}"
            repair_suffix = ""
            if item["repair_attempts"]:
                repair_models = ", ".join(item["repair_models"]) if item["repair_models"] else "provider_courant"
                repair_suffix = f" | réparations: {item['repair_attempts']} ({repair_models})"
            status_message = f" | message: {item['last_status_message']}" if item["last_status_message"] else ""
            print(
                f"- {item['chapter']}: status={item['status']} | brouillon={item['draft_path']} | critique={item['critique_path']} | gate={item['gate_path']}{repair_suffix}{retry_suffix}{status_message}"
            )
    else:
        print("\nEn attente de validation: aucun")

    print("")
    return 0


def cmd_intention_create(root: Path, chapter_value: str | None = None, input_func=input):
    intentions_dir = root / "notes" / "intentions"
    intentions_dir.mkdir(parents=True, exist_ok=True)

    raw_chapter = chapter_value or input_func("Numéro du chapitre (ex: 08) : ").strip()
    if not re.match(r'^[a-zA-Z0-9_]+$', raw_chapter):
        print("Numéro de chapitre invalide (alphanumériques et _ uniquement).")
        return 1
    chapter = ChapterId.parse(raw_chapter)

    path = resolve_chapter_file(intentions_dir, chapter)
    if path.exists():
        print(f"Une intention existe déjà : {path}")
        return 1

    print("\nDécris l'intention (finir par Ctrl+D / Ctrl+Z):\n")
    lines = []
    try:
        while True:
            lines.append(input_func(""))
    except EOFError:
        pass

    content = "\n".join(line for line in lines if line is not None).strip()
    if not content:
        print("Intention vide. Annulé.")
        return 1

    canonical_path = intentions_dir / chapter.filename
    canonical_path.write_text(
        f"# Intention — Chapitre {chapter.label}\n\n{content}\n",
        encoding="utf-8",
    )

    print(f"Intention créée : {canonical_path}\n")
    return 0


def _approval_callback_from_flags(force_accept: bool | None):
    if force_accept is None:
        return None
    return lambda _report, _path: force_accept


def cmd_generate_chapter(
    root: Path,
    chapter_value: str,
    provider=None,
    input_func=input,
    *,
    force_accept: bool | None = None,
):
    pipeline = GenerationPipeline(root, provider=provider, input_func=input_func)
    outcome = pipeline.generate_chapter(
        chapter_value,
        approval_callback=_approval_callback_from_flags(force_accept),
    )

    print("")
    print(f"Chapitre traité : {outcome.chapter_id.slug}")
    print(f"Statut         : {outcome.status}")
    print(f"Brouillon final : {outcome.draft_path}")
    print(f"Critique       : {outcome.critique_path}")
    print(f"Garde-fou      : {outcome.gate_path}")
    print(f"Métadonnées    : {outcome.meta_path}")
    if outcome.accepted and outcome.manuscript_path is not None:
        print(f"Manuscrit      : {outcome.manuscript_path}")
    else:
        print("Manuscrit      : non promu")
    if outcome.quality_blockers:
        print(f"Blockers       : {', '.join(outcome.quality_blockers)}")
    print("")
    return 0


def _add_approval_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--approve", action="store_true", help="Promouvoir sans confirmation interactive.")
    group.add_argument("--reject", action="store_true", help="Refuser sans confirmation interactive.")


def _force_accept_from_namespace(namespace: argparse.Namespace) -> bool | None:
    if getattr(namespace, "approve", False):
        return True
    if getattr(namespace, "reject", False):
        return False
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m cli.main")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status")

    intention_parser = subparsers.add_parser("intention")
    intention_subparsers = intention_parser.add_subparsers(dest="intention_command")
    intention_create = intention_subparsers.add_parser("create")
    intention_create.add_argument("--chapter")

    generate_parser = subparsers.add_parser("generate")
    generate_subparsers = generate_parser.add_subparsers(dest="generate_target")
    generate_chapter = generate_subparsers.add_parser("chapter")
    generate_chapter.add_argument("--chapter", required=True)
    _add_approval_flags(generate_chapter)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--chapter", required=True)
    _add_approval_flags(write_parser)

    return parser


def main(argv: list[str] | None = None, root: Path | None = None):
    args = argv if argv is not None else sys.argv[1:]
    project_root = root or Path.cwd()
    parser = build_parser()
    namespace = parser.parse_args(args)

    if not args or namespace.command == "status":
        return cmd_status(project_root)

    try:
        if namespace.command == "intention" and namespace.intention_command == "create":
            return cmd_intention_create(project_root, chapter_value=namespace.chapter)

        if namespace.command == "generate" and namespace.generate_target == "chapter":
            return cmd_generate_chapter(
                project_root,
                namespace.chapter,
                force_accept=_force_accept_from_namespace(namespace),
            )

        if namespace.command == "write":
            return cmd_generate_chapter(
                project_root,
                namespace.chapter,
                force_accept=_force_accept_from_namespace(namespace),
            )
    except (ChapterError, ChapterConflictError, RuntimeError, ProviderConfigurationError, ProviderError) as exc:
        print(f"\nErreur: {exc}\n")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
