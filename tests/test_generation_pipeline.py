from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from cli.main import main
from core.chapters import ChapterConflictError, ChapterId, resolve_chapter_file
from core.evaluation.models import NarrativeJudgeReport
from core.generation.models import ControlReport, ManuscriptGateReport, MemoryUpdate
from core.generation.pipeline import GenerationPipeline
from core.generation.provider import (
    GenerationRequest,
    MockGenerationProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderConfigurationError,
    ProviderError,
)
from core.runtime.health import probe_runtime_health
from core.runtime.models import RuntimeProfile
from core.project.loader import ProjectState


class GenerationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        intentions_dir = self.root / "notes" / "intentions"
        intentions_dir.mkdir(parents=True, exist_ok=True)
        (intentions_dir / "chapitre_01.md").write_text(
            "# Intention — Chapitre 01\n\nInstaller la voix.\nCréer une tension sourde.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _narrative_text(self, *, ending: str = ".") -> str:
        sentence = (
            "Ariane longe le quai vide, compte les fenetres allumees, ecoute les pas derriere elle "
            "et serre dans sa poche un billet humide qui pourrait la condamner."
        )
        text = " ".join(sentence for _ in range(12)).strip()
        if ending:
            text = text.rstrip(".!?…\"' ")
            text = f"{text}{ending}"
        return f"{text}\n"

    def _provider(self) -> MockGenerationProvider:
        return MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre est narratif et peut etre promu.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": {
                    "summary": "Le chapitre installe une menace diffuse autour de l'héroïne.",
                    "characters": [{"name": "Ariane", "description": "Héroïne troublée par un signe avant-coureur."}],
                    "locations": [{"name": "Port-Vieux", "description": "Quartier bruissant où la tension s'installe."}],
                    "timeline_events": [{"event": "Ariane perçoit le premier signe du basculement.", "order_hint": "soir"}],
                },
            }
        )

    def _make_outcome(self, *, accepted: bool) -> SimpleNamespace:
        return SimpleNamespace(
            accepted=accepted,
            status="accepted" if accepted else "rejected",
            chapter_id=ChapterId.parse("1"),
            draft_path=self.root / "brouillons" / "chapitres" / "chapitre_01" / "draft_v2.md",
            critique_path=self.root / "brouillons" / "chapitres" / "chapitre_01" / "critique_v1.md",
            gate_path=self.root / "brouillons" / "chapitres" / "chapitre_01" / "gate_v1.json",
            meta_path=self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json",
            manuscript_path=(self.root / "manuscrit" / "chapitre_01.md") if accepted else None,
            quality_blockers=[],
        )

    def test_generation_without_intention_fails_before_provider_call(self):
        project_root = Path(self.temp_dir.name) / "missing"
        project_root.mkdir(parents=True, exist_ok=True)
        provider = self._provider()
        pipeline = GenerationPipeline(project_root, provider=provider)

        with self.assertRaises(RuntimeError):
            pipeline.generate_chapter("1", approval_callback=lambda _report, _path: False)

        self.assertEqual(provider.requests, [])
        self.assertFalse((project_root / "brouillons").exists())
        self.assertFalse((project_root / "structure").exists())

    def test_chapter_normalization_and_conflict_detection(self):
        chapter = ChapterId.parse("1")
        self.assertEqual(chapter.slug, "chapitre_01")

        intentions_dir = self.root / "notes" / "intentions"
        (intentions_dir / "chapitre_1.md").write_text("# Intention legacy\n", encoding="utf-8")

        with self.assertRaises(ChapterConflictError):
            resolve_chapter_file(intentions_dir, chapter)

    def test_generation_rejection_keeps_intermediate_artifacts_only(self):
        provider = self._provider()
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("1", approval_callback=lambda _report, _path: False)

        self.assertFalse(outcome.accepted)
        structure_path = self.root / "structure" / "chapitres" / "chapitre_01.md"
        draft_dir = self.root / "brouillons" / "chapitres" / "chapitre_01"
        self.assertTrue(structure_path.exists())
        self.assertTrue((draft_dir / "draft_v1.md").exists())
        self.assertTrue((draft_dir / "critique_v1.md").exists())
        self.assertTrue((draft_dir / "draft_v2.md").exists())
        self.assertTrue((draft_dir / "gate_v1.json").exists())
        self.assertFalse((self.root / "manuscrit" / "chapitre_01.md").exists())
        self.assertFalse((self.root / "memoire").exists())

        meta = json.loads((draft_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "rejected")
        self.assertEqual(meta["completed_stages"], ["structure", "draft", "critique", "rewrite", "gate"])
        self.assertEqual(meta["stage_attempts"], {"structure": 1, "draft": 1, "critique": 1, "rewrite": 1, "gate": 1})
        self.assertEqual(meta["provider"], {"kind": "MockGenerationProvider", "base_url": None, "model": None})

    def test_generation_acceptance_promotes_manuscript_and_memory(self):
        provider = self._provider()
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        manuscript_path = self.root / "manuscrit" / "chapitre_01.md"
        memory_summary = self.root / "memoire" / "chapitres" / "chapitre_01.md"
        characters_index = self.root / "memoire" / "index" / "personnages.json"
        locations_index = self.root / "memoire" / "index" / "lieux.json"
        timeline_index = self.root / "memoire" / "index" / "chronologie.json"

        self.assertTrue(manuscript_path.exists())
        self.assertIn("Ariane longe le quai", manuscript_path.read_text(encoding="utf-8"))
        self.assertTrue(memory_summary.exists())
        self.assertTrue(characters_index.exists())
        self.assertTrue(locations_index.exists())
        self.assertTrue(timeline_index.exists())

        characters = json.loads(characters_index.read_text(encoding="utf-8"))
        self.assertEqual(characters["Ariane"]["chapters"], ["chapitre_01"])

        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "accepted")
        self.assertEqual(meta["stage_attempts"]["gate"], 1)
        self.assertEqual(meta["stage_attempts"]["memory"], 1)
        self.assertEqual(meta["provider"]["kind"], "MockGenerationProvider")

    def test_judge_is_disabled_by_default(self):
        provider = self._provider()
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertNotIn("judge", [request.stage for request in provider.requests])
        gate_payload = json.loads(outcome.gate_path.read_text(encoding="utf-8"))
        self.assertIsNone(gate_payload["judge_report"])
        self.assertEqual(gate_payload["judge_blockers"], [])

    def test_judge_report_is_merged_into_gate_metadata_when_enabled(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre est narratif et peut etre promu.",
                    "blockers": [],
                    "recommendations": ["resserrer la chute"],
                    "heuristic_blockers": [],
                },
                "judge": {
                    "ready_for_manuscript": True,
                    "summary": "La decision finale est nette et sa consequence immediate est visible.",
                    "blockers": [],
                    "recommendations": ["rendre la tension du milieu plus nette"],
                },
                "memory": {
                    "summary": "Le chapitre installe une menace diffuse autour de l'héroïne.",
                    "characters": [{"name": "Ariane", "description": "Héroïne troublée par un signe avant-coureur."}],
                    "locations": [{"name": "Port-Vieux", "description": "Quartier bruissant où la tension s'installe."}],
                    "timeline_events": [{"event": "Ariane perçoit le premier signe du basculement.", "order_hint": "soir"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with mock.patch.dict("os.environ", {"ANE_JUDGE_MODEL": "ollama:qwen2.5:7b"}, clear=False):
            outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "gate", "judge", "memory"],
        )
        gate_payload = json.loads(outcome.gate_path.read_text(encoding="utf-8"))
        self.assertEqual(gate_payload["judge_blockers"], [])
        self.assertEqual(
            gate_payload["judge_report"]["summary"],
            "La decision finale est nette et sa consequence immediate est visible.",
        )
        self.assertIn("Juge narratif", gate_payload["summary"])
        self.assertIn("rendre la tension du milieu plus nette", gate_payload["recommendations"])

        meta = json.loads(outcome.meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["gate_report"]["judge_report"]["blockers"], [])

    def test_judge_blockers_trigger_repair(self):
        repaired_text = self._narrative_text()
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon reste prudent.",
                    "rewrite_required": True,
                    "deviations": ["La scene n'ose pas aller jusqu'au point de bascule."],
                    "recommendations": ["Rendre l'acte final plus couteux."],
                },
                "rewrite": self._narrative_text(),
                "gate": [
                    {
                        "ready_for_manuscript": True,
                        "summary": "Le chapitre est formellement exploitable.",
                        "blockers": [],
                        "recommendations": [],
                        "heuristic_blockers": [],
                    },
                    {
                        "ready_for_manuscript": True,
                        "summary": "La version reparée peut etre promue.",
                        "blockers": [],
                        "recommendations": [],
                        "heuristic_blockers": [],
                    },
                ],
                "judge": [
                    {
                        "ready_for_manuscript": False,
                        "summary": "La scene ne va pas jusqu'a une decision risquee suivie d'un effet immediat.",
                        "blockers": ["missing_risky_decision", "missing_immediate_consequence"],
                        "recommendations": ["forcer une decision couteuse", "montrer aussitot son effet"],
                    },
                    {
                        "ready_for_manuscript": True,
                        "summary": "La scene va jusqu'a une decision risquee et son effet.",
                        "blockers": [],
                        "recommendations": [],
                    },
                ],
                "repair": repaired_text,
                "memory": {
                    "summary": "Le chapitre se clot enfin sur un acte couteux et son effet.",
                    "characters": [{"name": "Ariane", "description": "Va au bout de sa decision."}],
                    "locations": [{"name": "Port-Vieux", "description": "Le lieu absorbe l'onde de choc."}],
                    "timeline_events": [{"event": "Ariane agit et en paie le prix tout de suite.", "order_hint": "nuit"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with mock.patch.dict("os.environ", {"ANE_JUDGE_MODEL": "ollama:qwen2.5:7b"}, clear=False):
            outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.draft_path.name, "repair_v1.md")
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "gate", "judge", "repair", "gate", "judge", "memory"],
        )
        first_gate_meta = json.loads(outcome.meta_path.read_text(encoding="utf-8"))
        self.assertEqual(first_gate_meta["stage_attempts"]["gate"], 2)

    def test_judge_failure_is_non_blocking(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre est narratif et peut etre promu.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "judge": [
                    "Pas de JSON du tout.",
                    "Toujours pas de JSON exploitable.",
                ],
                "memory": {
                    "summary": "Le chapitre installe une menace diffuse autour de l'héroïne.",
                    "characters": [{"name": "Ariane", "description": "Héroïne troublée par un signe avant-coureur."}],
                    "locations": [{"name": "Port-Vieux", "description": "Quartier bruissant où la tension s'installe."}],
                    "timeline_events": [{"event": "Ariane perçoit le premier signe du basculement.", "order_hint": "soir"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with mock.patch.dict("os.environ", {"ANE_JUDGE_MODEL": "ollama:qwen2.5:7b"}, clear=False):
            outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "gate", "judge", "judge", "memory"],
        )
        gate_payload = json.loads(outcome.gate_path.read_text(encoding="utf-8"))
        self.assertEqual(gate_payload["judge_blockers"], [])
        self.assertIn("indisponible", gate_payload["judge_report"]["summary"])
        self.assertIn("deux tentatives", gate_payload["judge_report"]["error"])

    def test_rerunning_accepted_chapter_does_not_duplicate_timeline_events(self):
        GenerationPipeline(self.root, provider=self._provider()).generate_chapter(
            "01",
            approval_callback=lambda _report, _path: True,
        )
        GenerationPipeline(self.root, provider=self._provider()).generate_chapter(
            "01",
            approval_callback=lambda _report, _path: True,
        )

        timeline_index = self.root / "memoire" / "index" / "chronologie.json"
        timeline = json.loads(timeline_index.read_text(encoding="utf-8"))

        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["chapter"], "chapitre_01")
        self.assertEqual(timeline[0]["event"], "Ariane perçoit le premier signe du basculement.")

    def test_generation_retries_invalid_json_for_critique_and_memory(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": [
                    "Résumé libre sans JSON exploitable.",
                    {
                        "summary": "Le brouillon manque d'escalade au milieu.",
                        "rewrite_required": True,
                        "deviations": ["Le conflit tarde à apparaître."],
                        "recommendations": ["Accentuer la menace dans la seconde scène."],
                    },
                ],
                "rewrite": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre est narratif et peut etre promu.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": [
                    "Bloc mémoire illisible et non structuré.",
                    {
                        "summary": "Le chapitre installe une menace diffuse autour de l'héroïne.",
                        "characters": [{"name": "Ariane", "description": "Héroïne troublée par un signe avant-coureur."}],
                        "locations": [{"name": "Port-Vieux", "description": "Quartier bruissant où la tension s'installe."}],
                        "timeline_events": [
                            {"event": "Ariane perçoit le premier signe du basculement.", "order_hint": "soir"}
                        ],
                    },
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "critique", "rewrite", "gate", "memory", "memory"],
        )
        manuscript_path = self.root / "manuscrit" / "chapitre_01.md"
        self.assertTrue(manuscript_path.exists())
        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["retry_stages"], ["critique", "memory"])
        self.assertEqual(meta["stage_attempts"]["critique"], 2)
        self.assertEqual(meta["stage_attempts"]["memory"], 2)

    def test_quality_gate_blocks_outline_like_manuscript(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": (
                    "## Objectif dramatique\n"
                    "- **objectif**: Trouver l'indice.\n"
                    "- **conflit**: Echouer avant l'aube.\n"
                    "- **sortie**: Partir.\n"
                ),
                "repair": [
                    "## Scène\n- **objectif**: Observer.\n- **conflit**: Trembler.\n- **sortie**: Fuir.\n",
                    "## Scène\n- **objectif**: Observer.\n- **conflit**: Trembler.\n- **sortie**: Fuir.\n",
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.status, "quality_blocked")
        self.assertIn("outline_like", outcome.quality_blockers)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "repair", "repair"],
        )
        self.assertFalse((self.root / "manuscrit" / "chapitre_01.md").exists())

        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "quality_blocked")
        self.assertEqual(meta["failed_stage"], "gate")
        self.assertIn("outline_like", meta["quality_blockers"])

    def test_outline_like_triggers_repair_and_promotes_repaired_manuscript(self):
        repaired_text = self._narrative_text()
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon ressemble encore à un plan.",
                    "rewrite_required": True,
                    "deviations": ["Le texte reste structuré comme des notes."],
                    "recommendations": ["Le convertir en narration continue."],
                },
                "rewrite": (
                    "## Objectif dramatique\n"
                    "- **objectif**: Entrer.\n"
                    "- **conflit**: Etre vue.\n"
                    "- **sortie**: Partir.\n"
                ),
                "repair": repaired_text,
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre reparé peut etre promu.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": {
                    "summary": "Le chapitre installe une entrée risquée dans un lieu surveillé.",
                    "characters": [{"name": "Ariane", "description": "Observe et decide vite."}],
                    "locations": [{"name": "Port-Vieux", "description": "Quartier nocturne et tendu."}],
                    "timeline_events": [{"event": "Ariane franchit le seuil interdit.", "order_hint": "nuit"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.draft_path.name, "repair_v1.md")
        self.assertTrue(outcome.manuscript_path and outcome.manuscript_path.exists())
        self.assertEqual(outcome.manuscript_path.read_text(encoding="utf-8"), repaired_text)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "repair", "gate", "memory"],
        )

        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "accepted")
        self.assertEqual(meta["repair_attempts"], 1)
        self.assertEqual(meta["stage_attempts"]["repair"], 1)
        self.assertEqual(meta["stage_attempts"]["gate"], 2)
        self.assertEqual(meta["artifacts"]["repair_latest"], str(self.root / "brouillons" / "chapitres" / "chapitre_01" / "repair_v1.md"))
        self.assertEqual(meta["draft_final"], str(self.root / "brouillons" / "chapitres" / "chapitre_01" / "repair_v1.md"))

    def test_rewrite_strips_code_fences_and_chapter_title_before_promotion(self):
        rewritten = f"```markdown\n# Chapitre 01\n\n{self._narrative_text().strip()}\n```"
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon doit etre reraconte proprement.",
                    "rewrite_required": True,
                    "deviations": ["Le texte garde un habillage markdown inutile."],
                    "recommendations": ["Supprimer les marqueurs de presentation."],
                },
                "rewrite": rewritten,
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "Le chapitre peut etre promu.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": {
                    "summary": "Le chapitre garde sa tension sans habillage markdown.",
                    "characters": [{"name": "Ariane", "description": "Traverse la scene sans filtre meta."}],
                    "locations": [{"name": "Port-Vieux", "description": "Reste nocturne et menaçant."}],
                    "timeline_events": [{"event": "Ariane avance sans retour en arriere.", "order_hint": "nuit"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        manuscript_text = outcome.manuscript_path.read_text(encoding="utf-8")
        self.assertNotIn("```", manuscript_text)
        self.assertNotIn("# Chapitre 01", manuscript_text)
        self.assertTrue(manuscript_text.startswith("Ariane longe le quai"))

    def test_truncated_ending_triggers_repair_before_promotion(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "La fin reste ouverte de facon accidentelle.",
                    "rewrite_required": True,
                    "deviations": ["La derniere phrase est tronquee."],
                    "recommendations": ["Fermer la scene sur une vraie phrase."],
                },
                "rewrite": self._narrative_text().rstrip(".\n") + "\n",
                "repair": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "La fin est maintenant complete.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": {
                    "summary": "Le chapitre se clot sur une decision nette.",
                    "characters": [{"name": "Ariane", "description": "Choisit d'avancer malgré le risque."}],
                    "locations": [{"name": "Port-Vieux", "description": "Zone de transition menaçante."}],
                    "timeline_events": [{"event": "Ariane tranche et passe a l'acte.", "order_hint": "nuit"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.draft_path.name, "repair_v1.md")
        self.assertIn("repair", [request.stage for request in provider.requests])

    def test_too_short_triggers_repair_before_promotion(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le chapitre reste trop court.",
                    "rewrite_required": True,
                    "deviations": ["La scene ne va pas assez loin."],
                    "recommendations": ["Allonger la scene et la consequence."],
                },
                "rewrite": "Ariane pousse la porte et comprend trop tard qu'elle est attendue.\n",
                "repair": self._narrative_text(),
                "gate": {
                    "ready_for_manuscript": True,
                    "summary": "La scene est complete.",
                    "blockers": [],
                    "recommendations": [],
                    "heuristic_blockers": [],
                },
                "memory": {
                    "summary": "La scene s'etire enfin jusqu'a une vraie consequence.",
                    "characters": [{"name": "Ariane", "description": "Va au bout de sa decision."}],
                    "locations": [{"name": "Port-Vieux", "description": "Le lieu absorbe sa décision."}],
                    "timeline_events": [{"event": "Ariane entre malgré l'alerte.", "order_hint": "nuit"}],
                },
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.draft_path.name, "repair_v1.md")
        self.assertIn("repair", [request.stage for request in provider.requests])

    def test_quality_gate_blocks_after_exhausting_repair_passes(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon ressemble encore à un plan.",
                    "rewrite_required": True,
                    "deviations": ["Le texte reste structuré comme des notes."],
                    "recommendations": ["Le convertir en narration continue."],
                },
                "rewrite": (
                    "## Objectif dramatique\n"
                    "- **objectif**: Entrer.\n"
                    "- **conflit**: Etre vue.\n"
                    "- **sortie**: Partir.\n"
                ),
                "repair": [
                    "## Scène\n- **objectif**: Observer.\n- **conflit**: Trembler.\n- **sortie**: Fuir.\n",
                    "## Scène\n- **objectif**: Observer.\n- **conflit**: Trembler.\n- **sortie**: Fuir.\n",
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.status, "quality_blocked")
        self.assertEqual(outcome.draft_path.name, "repair_v2.md")
        self.assertIn("outline_like", outcome.quality_blockers)
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "repair", "repair"],
        )
        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["repair_attempts"], 2)
        self.assertEqual(meta["stage_attempts"]["repair"], 2)
        self.assertEqual(meta["stage_attempts"]["gate"], 3)
        self.assertFalse((self.root / "manuscrit" / "chapitre_01.md").exists())

    def test_quality_gate_blocks_too_short_and_truncated_manuscript(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": "Ariane s'arrete devant la porte, retient son souffle et comprend que le bruit revient\n",
                "repair": [
                    "Ariane avance encore mais la phrase reste suspendue\n",
                    "Ariane avance encore mais la phrase reste suspendue\n",
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.status, "quality_blocked")
        self.assertIn("too_short", outcome.quality_blockers)
        self.assertIn("truncated_ending", outcome.quality_blockers)
        self.assertFalse((self.root / "manuscrit" / "chapitre_01.md").exists())

    def test_force_accept_does_not_bypass_quality_gate(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": "Ariane entend un pas et se retourne\n",
                "repair": [
                    "Ariane entend un pas et se retourne\n",
                    "Ariane entend un pas et se retourne\n",
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        outcome = pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.status, "quality_blocked")
        self.assertFalse((self.root / "manuscrit" / "chapitre_01.md").exists())
        self.assertIn("repair", [request.stage for request in provider.requests])

    def test_generation_retries_invalid_json_for_gate_and_then_fails(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": {
                    "summary": "Le brouillon manque d'escalade au milieu.",
                    "rewrite_required": True,
                    "deviations": ["Le conflit tarde à apparaître."],
                    "recommendations": ["Accentuer la menace dans la seconde scène."],
                },
                "rewrite": self._narrative_text(),
                "gate": ["Toujours pas du JSON.", "Encore une reponse inutilisable."],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with self.assertRaises(ProviderError) as context:
            pipeline.generate_chapter("01", approval_callback=lambda _report, _path: True)

        self.assertIn("après deux tentatives", str(context.exception))
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "rewrite", "gate", "gate"],
        )
        meta = json.loads((self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "failed")
        self.assertEqual(meta["failed_stage"], "gate")
        self.assertEqual(meta["retry_stages"], ["gate"])
        self.assertEqual(meta["stage_attempts"]["gate"], 2)

    def test_generation_fails_if_json_is_invalid_after_two_attempts(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": "# Chapitre 01\n\nUn premier jet tendu.\n",
                "critique": [
                    "Toujours pas du JSON.",
                    "Encore une réponse non exploitable.",
                ],
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with self.assertRaises(ProviderError) as context:
            pipeline.generate_chapter("01", approval_callback=lambda _report, _path: False)

        self.assertIn("après deux tentatives", str(context.exception))
        self.assertEqual(
            [request.stage for request in provider.requests],
            ["structure", "draft", "critique", "critique"],
        )

        meta = json.loads(
            (self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json").read_text(encoding="utf-8")
        )
        self.assertEqual(meta["status"], "failed")
        self.assertEqual(meta["failed_stage"], "critique")
        self.assertEqual(meta["retry_stages"], ["critique"])
        self.assertEqual(meta["stage_attempts"]["critique"], 2)

    def test_provider_error_preserves_existing_artifacts_and_marks_failure(self):
        provider = MockGenerationProvider(
            {
                "structure": "# Structure — chapitre_01\n\n## Objectif dramatique\nPoser une menace.\n",
                "draft": ProviderError("Panne réseau pendant le brouillon."),
            }
        )
        pipeline = GenerationPipeline(self.root, provider=provider)

        with self.assertRaises(ProviderError):
            pipeline.generate_chapter("1", approval_callback=lambda _report, _path: False)

        structure_path = self.root / "structure" / "chapitres" / "chapitre_01.md"
        meta_path = self.root / "brouillons" / "chapitres" / "chapitre_01" / "meta.json"
        self.assertTrue(structure_path.exists())
        self.assertTrue(meta_path.exists())
        self.assertFalse((self.root / "brouillons" / "chapitres" / "chapitre_01" / "draft_v1.md").exists())

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["status"], "failed")
        self.assertEqual(meta["failed_stage"], "draft")
        self.assertIn("Panne réseau", meta["error"])
        self.assertEqual(meta["stage_attempts"], {"structure": 1, "draft": 1})

    def test_project_status_reports_latest_draft(self):
        provider = self._provider()
        pipeline = GenerationPipeline(self.root, provider=provider)
        pipeline.generate_chapter("1", approval_callback=lambda _report, _path: False)

        state = ProjectState(self.root).summary()
        self.assertEqual(state["current_chapter"], "chapitre_01")
        self.assertEqual(state["latest_drafts"], {"chapitre_01": "draft_v2.md"})

    def test_project_status_reports_failures_quality_blocked_and_waiting_acceptance(self):
        failed_dir = self.root / "brouillons" / "chapitres" / "chapitre_01"
        failed_dir.mkdir(parents=True, exist_ok=True)
        (failed_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_01",
                    "status": "failed",
                    "failed_stage": "critique",
                    "retry_stages": ["critique"],
                    "last_status_message": "Échec à l'étape critique.",
                    "artifacts": {
                        "draft_v2": str(failed_dir / "draft_v2.md"),
                        "critique_v1": str(failed_dir / "critique_v1.md"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        blocked_dir = self.root / "brouillons" / "chapitres" / "chapitre_03"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        (blocked_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_03",
                    "status": "quality_blocked",
                    "failed_stage": "gate",
                    "retry_stages": ["gate"],
                    "quality_blockers": ["too_short", "truncated_ending"],
                    "last_status_message": "Promotion bloquée par le garde-fou manuscrit.",
                    "repair_attempts": 2,
                    "repair_models": ["ollama:qwen2.5:1.5b", "ollama:qwen2.5:7b"],
                    "artifacts": {
                        "draft_v2": str(blocked_dir / "draft_v2.md"),
                        "repair_latest": str(blocked_dir / "repair_v2.md"),
                        "gate_v1": str(blocked_dir / "gate_v1.json"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        awaiting_dir = self.root / "brouillons" / "chapitres" / "chapitre_02"
        awaiting_dir.mkdir(parents=True, exist_ok=True)
        (awaiting_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_02",
                    "status": "awaiting_acceptance",
                    "retry_stages": ["memory"],
                    "last_status_message": "Brouillon final prêt pour validation.",
                    "repair_attempts": 1,
                    "repair_models": ["apple-coreml:qwen3.5-4b-onnx-q4f16"],
                    "artifacts": {
                        "draft_v2": str(awaiting_dir / "draft_v2.md"),
                        "repair_latest": str(awaiting_dir / "repair_v1.md"),
                        "critique_v1": str(awaiting_dir / "critique_v1.md"),
                        "gate_v1": str(awaiting_dir / "gate_v1.json"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        state = ProjectState(self.root).summary()
        self.assertEqual(
            state["failed_chapters"],
            [
                {
                    "chapter": "chapitre_01",
                    "status": "failed",
                    "failed_stage": "critique",
                    "meta_path": str(failed_dir / "meta.json"),
                    "retry_stages": ["critique"],
                    "last_status_message": "Échec à l'étape critique.",
                }
            ],
        )
        self.assertEqual(
            state["awaiting_acceptance"],
            [
                {
                    "chapter": "chapitre_02",
                    "status": "awaiting_acceptance",
                    "draft_path": str(awaiting_dir / "repair_v1.md"),
                    "critique_path": str(awaiting_dir / "critique_v1.md"),
                    "gate_path": str(awaiting_dir / "gate_v1.json"),
                    "meta_path": str(awaiting_dir / "meta.json"),
                    "retry_stages": ["memory"],
                    "repair_attempts": 1,
                    "repair_models": ["apple-coreml:qwen3.5-4b-onnx-q4f16"],
                    "last_status_message": "Brouillon final prêt pour validation.",
                }
            ],
        )
        self.assertEqual(
            state["quality_blocked_chapters"],
            [
                {
                    "chapter": "chapitre_03",
                    "status": "quality_blocked",
                    "failed_stage": "gate",
                    "meta_path": str(blocked_dir / "meta.json"),
                    "draft_path": str(blocked_dir / "repair_v2.md"),
                    "gate_path": str(blocked_dir / "gate_v1.json"),
                    "quality_blockers": ["too_short", "truncated_ending"],
                    "retry_stages": ["gate"],
                    "repair_attempts": 2,
                    "repair_models": ["ollama:qwen2.5:1.5b", "ollama:qwen2.5:7b"],
                    "last_status_message": "Promotion bloquée par le garde-fou manuscrit.",
                }
            ],
        )
        self.assertEqual(state["retry_stages"], {"chapitre_01": ["critique"], "chapitre_02": ["memory"], "chapitre_03": ["gate"]})
        self.assertEqual(state["latest_drafts"], {"chapitre_02": "repair_v1.md", "chapitre_03": "repair_v2.md"})
        self.assertEqual(state["latest_repairs"], {"chapitre_02": "repair_v1.md", "chapitre_03": "repair_v2.md"})

    def test_project_status_reports_corrupted_meta(self):
        broken_dir = self.root / "brouillons" / "chapitres" / "chapitre_04"
        broken_dir.mkdir(parents=True, exist_ok=True)
        (broken_dir / "meta.json").write_text('{"status": "failed"', encoding="utf-8")

        state = ProjectState(self.root).summary()

        self.assertEqual(
            state["corrupted_meta"],
            [
                {
                    "chapter": "chapitre_04",
                    "meta_path": str(broken_dir / "meta.json"),
                    "error": "JSONDecodeError: Expecting ',' delimiter (line 1, column 20)",
                }
            ],
        )

    def test_cli_write_alias_runs_pipeline(self):
        output = io.StringIO()

        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_instance = pipeline_cls.return_value
            pipeline_instance.generate_chapter.return_value = self._make_outcome(accepted=False)

            with redirect_stdout(output):
                exit_code = main(["write", "--chapter", "1"], root=self.root)

        self.assertEqual(exit_code, 0)
        pipeline_cls.assert_called_once()
        pipeline_instance.generate_chapter.assert_called_once_with("1", approval_callback=None)
        self.assertIn("Chapitre traité : chapitre_01", output.getvalue())

    def test_cli_generate_approve_uses_non_interactive_acceptance(self):
        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_instance = pipeline_cls.return_value

            def generate(chapter, approval_callback=None):
                self.assertEqual(chapter, "1")
                self.assertIsNotNone(approval_callback)
                self.assertTrue(
                    approval_callback(
                        ControlReport("ok", [], [], False),
                        self.root / "brouillons" / "chapitres" / "chapitre_01" / "draft_v2.md",
                    )
                )
                return self._make_outcome(accepted=True)

            pipeline_instance.generate_chapter.side_effect = generate
            exit_code = main(["generate", "chapter", "--chapter", "1", "--approve"], root=self.root)

        self.assertEqual(exit_code, 0)

    def test_cli_generate_reject_uses_non_interactive_rejection(self):
        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_instance = pipeline_cls.return_value

            def generate(chapter, approval_callback=None):
                self.assertEqual(chapter, "1")
                self.assertIsNotNone(approval_callback)
                self.assertFalse(
                    approval_callback(
                        ControlReport("ok", [], [], False),
                        self.root / "brouillons" / "chapitres" / "chapitre_01" / "draft_v2.md",
                    )
                )
                return self._make_outcome(accepted=False)

            pipeline_instance.generate_chapter.side_effect = generate
            exit_code = main(["generate", "chapter", "--chapter", "1", "--reject"], root=self.root)

        self.assertEqual(exit_code, 0)

    def test_cli_reject_and_approve_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit) as context:
            main(["write", "--chapter", "1", "--approve", "--reject"], root=self.root)

        self.assertEqual(context.exception.code, 2)

    def test_status_output_includes_failures_quality_gate_and_waiting_acceptance(self):
        failed_dir = self.root / "brouillons" / "chapitres" / "chapitre_01"
        failed_dir.mkdir(parents=True, exist_ok=True)
        (failed_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_01",
                    "status": "failed",
                    "failed_stage": "memory",
                    "retry_stages": ["critique"],
                    "last_status_message": "Échec à l'étape memory: timeout.",
                    "artifacts": {},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        blocked_dir = self.root / "brouillons" / "chapitres" / "chapitre_03"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        (blocked_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_03",
                    "status": "quality_blocked",
                    "failed_stage": "gate",
                    "retry_stages": ["gate"],
                    "quality_blockers": ["outline_like"],
                    "last_status_message": "Promotion bloquée par le garde-fou manuscrit.",
                    "repair_attempts": 2,
                    "repair_models": ["ollama:qwen2.5:1.5b", "ollama:qwen2.5:7b"],
                    "artifacts": {
                        "draft_v2": str(blocked_dir / "draft_v2.md"),
                        "repair_latest": str(blocked_dir / "repair_v2.md"),
                        "gate_v1": str(blocked_dir / "gate_v1.json"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        awaiting_dir = self.root / "brouillons" / "chapitres" / "chapitre_02"
        awaiting_dir.mkdir(parents=True, exist_ok=True)
        (awaiting_dir / "meta.json").write_text(
            json.dumps(
                {
                    "chapter": "chapitre_02",
                    "status": "awaiting_acceptance",
                    "retry_stages": ["memory"],
                    "last_status_message": "Brouillon final prêt pour validation.",
                    "repair_attempts": 1,
                    "repair_models": ["apple-coreml:qwen3.5-4b-onnx-q4f16"],
                    "artifacts": {
                        "draft_v2": str(awaiting_dir / "draft_v2.md"),
                        "repair_latest": str(awaiting_dir / "repair_v1.md"),
                        "critique_v1": str(awaiting_dir / "critique_v1.md"),
                        "gate_v1": str(awaiting_dir / "gate_v1.json"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        broken_dir = self.root / "brouillons" / "chapitres" / "chapitre_04"
        broken_dir.mkdir(parents=True, exist_ok=True)
        (broken_dir / "meta.json").write_text('{"status": "failed"', encoding="utf-8")

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"], root=self.root)

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Chapitres en échec:", rendered)
        self.assertIn("status=failed", rendered)
        self.assertIn("failed_stage=memory", rendered)
        self.assertIn("timeout", rendered)
        self.assertIn("Dernières réparations:", rendered)
        self.assertIn("Bloqués par garde-fou:", rendered)
        self.assertIn("status=quality_blocked", rendered)
        self.assertIn("outline_like", rendered)
        self.assertIn("réparations: 2", rendered)
        self.assertIn("En attente de validation:", rendered)
        self.assertIn("status=awaiting_acceptance", rendered)
        self.assertIn("chapitre_02", rendered)
        self.assertIn("Métadonnées corrompues:", rendered)
        self.assertIn("chapitre_04", rendered)
        self.assertIn("JSONDecodeError", rendered)


class ProviderConfigTests(unittest.TestCase):
    def test_provider_config_reads_global_and_stage_token_budgets(self):
        config = ProviderConfig.from_env(
            {
                "ANE_PROVIDER": "openai_compatible",
                "ANE_BASE_URL": "http://127.0.0.1:8100",
                "ANE_MODEL": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                "ANE_TIMEOUT": "45",
                "ANE_MAX_TOKENS": "512",
                "ANE_MAX_TOKENS_CRITIQUE": "384",
                "ANE_MAX_TOKENS_MEMORY": "192",
            }
        )

        self.assertEqual(config.max_tokens, 512)
        self.assertEqual(config.timeout, 45.0)
        self.assertEqual(config.stage_max_tokens, {"critique": 384, "memory": 192})
        self.assertEqual(config.max_tokens_for_stage("draft"), 512)
        self.assertEqual(config.max_tokens_for_stage("critique"), 384)

    def test_provider_config_reads_gate_token_budget(self):
        config = ProviderConfig.from_env(
            {
                "ANE_BASE_URL": "http://127.0.0.1:8100",
                "ANE_MODEL": "ollama:qwen2.5:7b",
                "ANE_MAX_TOKENS": "512",
                "ANE_MAX_TOKENS_GATE": "333",
                "ANE_MAX_TOKENS_REPAIR": "444",
            }
        )

        self.assertEqual(config.stage_max_tokens, {"gate": 333, "repair": 444})
        self.assertEqual(config.max_tokens_for_stage("gate"), 333)
        self.assertEqual(config.max_tokens_for_stage("repair"), 444)

    def test_repair_fallback_policy_uses_expected_models(self):
        pipeline = GenerationPipeline(Path.cwd())
        provider = OpenAICompatibleProvider(
            ProviderConfig(
                provider="openai_compatible",
                base_url="http://127.0.0.1:8100",
                api_key="",
                model="ollama:qwen2.5:1.5b",
                timeout=30.0,
                max_tokens=321,
                stage_max_tokens={},
            )
        )

        self.assertEqual(pipeline._repair_model_for_attempt(provider, 1), "ollama:qwen2.5:1.5b")
        self.assertEqual(pipeline._repair_model_for_attempt(provider, 2), "ollama:qwen2.5:7b")

        apple_provider = OpenAICompatibleProvider(
            ProviderConfig(
                provider="openai_compatible",
                base_url="http://127.0.0.1:8100",
                api_key="",
                model="apple-coreml:qwen2.5-0.5b-instruct-onnx",
                timeout=30.0,
                max_tokens=321,
                stage_max_tokens={},
            )
        )
        self.assertEqual(
            pipeline._repair_model_for_attempt(apple_provider, 2),
            "apple-coreml:qwen2.5-0.5b-instruct-onnx",
        )

    def test_repair_fallback_override_env_wins(self):
        pipeline = GenerationPipeline(Path.cwd())
        provider = OpenAICompatibleProvider(
            ProviderConfig(
                provider="openai_compatible",
                base_url="http://127.0.0.1:8100",
                api_key="",
                model="apple-coreml:qwen3.5-4b-onnx-q4f16",
                timeout=30.0,
                max_tokens=321,
                stage_max_tokens={},
            )
        )

        with mock.patch.dict("os.environ", {"ANE_REPAIR_FALLBACK_MODEL": "ollama:qwen2.5:7b"}, clear=False):
            self.assertEqual(pipeline._repair_model_for_attempt(provider, 2), "ollama:qwen2.5:7b")

    def test_repair_fallback_override_rejects_cross_apple_switch(self):
        pipeline = GenerationPipeline(Path.cwd())
        provider = OpenAICompatibleProvider(
            ProviderConfig(
                provider="openai_compatible",
                base_url="http://127.0.0.1:8100",
                api_key="",
                model="apple-coreml:qwen2.5-0.5b-instruct-onnx",
                timeout=30.0,
                max_tokens=321,
                stage_max_tokens={},
            )
        )

        with mock.patch.dict(
            "os.environ",
            {"ANE_REPAIR_FALLBACK_MODEL": "apple-coreml:qwen3.5-4b-onnx-q4f16"},
            clear=False,
        ):
            with self.assertRaises(ProviderError):
                pipeline._repair_model_for_attempt(provider, 2)

    def test_provider_config_rejects_invalid_ane_max_tokens(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderConfig.from_env(
                {
                    "ANE_BASE_URL": "http://127.0.0.1:8100",
                    "ANE_MODEL": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                    "ANE_MAX_TOKENS": "zero",
                }
            )

    def test_provider_config_rejects_invalid_stage_token_budget(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderConfig.from_env(
                {
                    "ANE_BASE_URL": "http://127.0.0.1:8100",
                    "ANE_MODEL": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                    "ANE_MAX_TOKENS": "256",
                    "ANE_MAX_TOKENS_CRITIQUE": "zero",
                }
            )

    def test_openai_provider_uses_stage_specific_token_budget(self):
        provider = OpenAICompatibleProvider(
            ProviderConfig(
                provider="openai_compatible",
                base_url="http://127.0.0.1:8100",
                api_key="",
                model="apple-coreml:qwen3.5-4b-onnx-q4f16",
                timeout=30.0,
                max_tokens=321,
                stage_max_tokens={"critique": 654},
            )
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                        "choices": [
                            {"message": {"content": "ok"}},
                        ],
                    }
                ).encode("utf-8")

        with mock.patch("core.runtime.client.request.urlopen", return_value=FakeResponse()) as urlopen_mock:
            provider = OpenAICompatibleProvider(
                ProviderConfig(
                    provider="openai_compatible",
                    base_url="http://127.0.0.1:8100",
                    api_key="",
                    model="apple-coreml:qwen3.5-4b-onnx-q4f16",
                    timeout=30.0,
                    max_tokens=321,
                    stage_max_tokens={"critique": 654},
                )
            )
            provider.generate(GenerationRequest(stage="critique", prompt="hello"))

        http_request = urlopen_mock.call_args.args[0]
        payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(payload["max_tokens"], 654)

    def test_explicit_request_budget_overrides_stage_budget(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                        "choices": [
                            {"message": {"content": "ok"}},
                        ],
                    }
                ).encode("utf-8")

        with mock.patch("core.runtime.client.request.urlopen", return_value=FakeResponse()) as urlopen_mock:
            provider = OpenAICompatibleProvider(
                ProviderConfig(
                    provider="openai_compatible",
                    base_url="http://127.0.0.1:8100",
                    api_key="",
                    model="apple-coreml:qwen3.5-4b-onnx-q4f16",
                    timeout=30.0,
                    max_tokens=321,
                    stage_max_tokens={"critique": 654},
                )
            )
            provider.generate(
                GenerationRequest(
                    stage="critique",
                    prompt="hello",
                    max_tokens=111,
                )
            )

        http_request = urlopen_mock.call_args.args[0]
        payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(payload["max_tokens"], 111)

    def test_openai_provider_wraps_timeout_error(self):
        with mock.patch("core.runtime.client.request.urlopen", side_effect=TimeoutError("timed out")):
            provider = OpenAICompatibleProvider(
                ProviderConfig(
                    provider="openai_compatible",
                    base_url="http://127.0.0.1:8100",
                    api_key="",
                    model="ollama:qwen2.5:1.5b",
                    timeout=12.0,
                    max_tokens=321,
                    stage_max_tokens={},
                )
            )
            with self.assertRaises(ProviderError) as context:
                provider.generate(GenerationRequest(stage="structure", prompt="hello"))

        self.assertIn("Timeout du provider", str(context.exception))
        self.assertIn("structure", str(context.exception))

    def test_runtime_health_probe_reads_health_payload(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "status": "ok",
                        "model": "apple-coreml:qwen3.5-4b-onnx-q4f16",
                    }
                ).encode("utf-8")

        profile = RuntimeProfile(
            provider="openai_compatible",
            base_url="http://127.0.0.1:8100",
            api_key="",
            model="apple-coreml:qwen3.5-4b-onnx-q4f16",
            timeout=12.0,
            max_tokens=321,
            stage_max_tokens={},
        )
        health = probe_runtime_health(profile, opener=lambda *_args, **_kwargs: FakeResponse())

        self.assertTrue(health.ok)
        self.assertEqual(health.status, "ok")
        self.assertEqual(health.active_model, "apple-coreml:qwen3.5-4b-onnx-q4f16")


class JsonRepairTests(unittest.TestCase):
    def test_control_report_recovers_json_with_trailing_text(self):
        report = ControlReport.from_response_text(
            'Avant propos inutile\n'
            '{"summary":"Diagnostic bref","rewrite_required":true,'
            '"deviations":["écart 1"],"recommendations":["action 1"]}\n'
            'Texte à ignorer'
        )

        self.assertEqual(report.summary, "Diagnostic bref")
        self.assertTrue(report.rewrite_required)
        self.assertEqual(report.deviations, ["écart 1"])

    def test_control_report_recovers_missing_closing_brace(self):
        report = ControlReport.from_response_text(
            '{"summary":"Diagnostic bref","rewrite_required":true,'
            '"deviations":["écart 1"],"recommendations":["action 1"]'
        )

        self.assertEqual(report.recommendations, ["action 1"])

    def test_memory_update_recovers_trailing_commas(self):
        memory = MemoryUpdate.from_response_text(
            '{"summary":"Résumé",'
            '"characters":[{"name":"Ariane","description":"Heroine"},],'
            '"locations":[{"name":"Port-Vieux","description":"Quartier"},],'
            '"timeline_events":[{"event":"Décision","order_hint":"nuit"},],}'
        )

        self.assertEqual(memory.chapter_summary, "Résumé")
        self.assertEqual(memory.characters[0]["name"], "Ariane")
        self.assertEqual(memory.timeline_events[0]["event"], "Décision")

    def test_narrative_judge_report_recovers_json(self):
        report = NarrativeJudgeReport.from_response_text(
            'Diagnostic a ignorer {"ready_for_manuscript": false,'
            '"summary":"La scene reste trop prudente.",'
            '"blockers":["missing_risky_decision"],'
            '"recommendations":["forcer une decision couteuse"]}'
        )

        self.assertFalse(report.ready_for_manuscript)
        self.assertEqual(report.blockers, ["missing_risky_decision"])
        self.assertEqual(report.recommendations, ["forcer une decision couteuse"])

    def test_narrative_judge_report_normalizes_aliases_and_preserves_unknown_blockers(self):
        report = NarrativeJudgeReport.from_response_text(
            '{"ready_for_manuscript": true,'
            '"summary":"Diagnostic.",'
            '"blockers":["incomplete", "lacks_narrative_continuity", "unknown_label", "incomplete"],'
            '"recommendations":["forcer la fermeture", "forcer la fermeture"]}'
        )

        self.assertFalse(report.ready_for_manuscript)
        self.assertEqual(report.blockers, ["incomplete_scene", "weak_narrative_continuity", "unknown_label"])
        self.assertEqual(report.recommendations, ["forcer la fermeture"])

    def test_gate_report_normalizes_aliases_and_recomputes_ready(self):
        report = ManuscriptGateReport.from_response_text(
            '{"ready_for_manuscript": true,'
            '"summary":"Diagnostic.",'
            '"blockers":["incomplete", "outline_like", "unknown_label"],'
            '"heuristic_blockers":["lacks_narrative_continuity"],'
            '"judge_blockers":["missing_immediate_consequence", "unknown_label"],'
            '"recommendations":["terminer la scene", "terminer la scene"]}'
        )

        self.assertFalse(report.ready_for_manuscript)
        self.assertEqual(report.blockers, ["incomplete_scene", "outline_like", "unknown_label"])
        self.assertEqual(report.heuristic_blockers, ["weak_narrative_continuity"])
        self.assertEqual(report.judge_blockers, ["missing_immediate_consequence", "unknown_label"])
        self.assertEqual(report.recommendations, ["terminer la scene"])

    def test_close_json_delimiters_mismatched_closer_repaired(self):
        from core.generation.models import _close_json_delimiters
        # Array closed with } instead of ] — should produce valid JSON
        result = _close_json_delimiters('{"key": [1, 2}')
        import json as _json
        data = _json.loads(result)
        self.assertEqual(data["key"], [1, 2])

    def test_close_json_delimiters_stray_closer_dropped(self):
        from core.generation.models import _close_json_delimiters
        # Closer with no matching opener at top level — dropped
        result = _close_json_delimiters(']{"key": "val"}')
        import json as _json
        data = _json.loads(result)
        self.assertEqual(data["key"], "val")

    def test_close_json_delimiters_truncated_string_in_array(self):
        from core.generation.models import _close_json_delimiters
        # Array truncated mid-string
        result = _close_json_delimiters('{"items": ["first", "truncated')
        import json as _json
        data = _json.loads(result)
        self.assertEqual(data["items"][0], "first")
        self.assertIn("truncated", data["items"][1])


class NormalizeProseTests(unittest.TestCase):
    """Tests for _normalize_generated_prose: heading stripping and outline cleanup."""

    def _pipeline(self):
        import tempfile
        td = tempfile.mkdtemp()
        return GenerationPipeline(Path(td))

    def test_strips_all_markdown_headings(self):
        p = self._pipeline()
        raw = "### Scène 1 — La femme arrive\nElle avança.\n## Objectif dramatique\nReste neutre.\n"
        result = p._normalize_generated_prose(raw)
        self.assertNotIn("###", result)
        self.assertNotIn("## Objectif", result)
        self.assertIn("Elle avança.", result)
        self.assertIn("Reste neutre.", result)

    def test_strips_h1_chapter_heading(self):
        p = self._pipeline()
        raw = "# Chapitre 01\n\nAriane longe le quai.\n"
        result = p._normalize_generated_prose(raw)
        self.assertNotIn("# Chapitre", result)
        self.assertIn("Ariane longe le quai.", result)

    def test_prose_containing_word_scene_not_flagged(self):
        p = self._pipeline()
        prose = ("Elle entra dans la scène avec une retenue calculee. " * 20).strip() + ".\n"
        result = p._is_outline_like(prose)
        self.assertFalse(result, "Le mot 'scène' dans la prose courante ne doit pas déclencher outline_like")

    def test_scene_heading_label_is_flagged(self):
        p = self._pipeline()
        text = "### Scène 1 — La femme arrive\nElle avança.\n### Scène 2 — La fuite\nElle courut.\n"
        self.assertTrue(p._is_outline_like(text))

    def test_scene_number_label_is_flagged(self):
        p = self._pipeline()
        text = "Scène 1:\nElle avança.\nScène 2:\nElle courut.\n"
        self.assertTrue(p._is_outline_like(text))

    def test_dense_bullet_list_flagged_as_outline_like(self):
        p = self._pipeline()
        text = "- Elle s'arrêta net.\n- La bruine tombait.\n- Une porte s'ouvrit.\n- Elle avança quand même.\n"
        self.assertTrue(p._is_outline_like(text), "4+ bullet lines alone doivent déclencher outline_like")

    def test_few_bullets_in_prose_not_flagged(self):
        p = self._pipeline()
        prose = "Ariane longe le quai vide et ecoute les pas. Elle serre un billet humide.\n"
        prose += "- Un indice ici.\n"
        prose += "Elle decida de repartir sans se retourner.\n"
        self.assertFalse(p._is_outline_like(prose), "1-3 bullet lines dans de la prose ne doit pas déclencher outline_like")

    def test_repair_focus_mentions_judge_blockers(self):
        p = self._pipeline()
        gate_report = ManuscriptGateReport.from_heuristics(
            blockers=["too_short"],
            recommendations=["allonger la scene"],
            summary="Heuristique.",
        ).with_judge_report(
            NarrativeJudgeReport(
                ready_for_manuscript=False,
                summary="La decision risquee manque encore.",
                blockers=["missing_risky_decision", "missing_immediate_consequence"],
                recommendations=["aller jusqu'a l'acte final"],
            )
        )

        focus = p._repair_focus(gate_report)
        self.assertIn("decision risquee concrete", focus)
        self.assertIn("consequence immediate, observable", focus)
        self.assertIn("couter quelque chose d'observable", focus)
        self.assertIn("meme lieu et la meme minute", focus)
        self.assertIn("ne pas finir sur un depart vers la suite", focus)

    def test_sanitize_gate_report_drops_outline_like_without_visual_markers(self):
        p = self._pipeline()
        prose = (
            "La femme marchait vite dans la rue humide. Elle tenait un livre noir contre elle.\n\n"
            "Elle prit une decision risquee et entra dans la ruelle, le souffle court.\n"
        )
        gate_report = ManuscriptGateReport(
            ready_for_manuscript=False,
            summary="Le texte contient encore des marqueurs visuels de plan.",
            blockers=["outline_like"],
            recommendations=["Retirer les titres et les puces."],
            heuristic_blockers=[],
            judge_blockers=[],
            judge_report=None,
            raw={},
        )

        sanitized = p._sanitize_gate_report(prose, gate_report)

        self.assertEqual(sanitized.blockers, [])
        self.assertTrue(sanitized.ready_for_manuscript)
        self.assertIn("aucun marqueur visuel de plan", sanitized.summary)


class IntentionGateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _gate(self):
        from core.intention.gate import IntentionGate
        return IntentionGate(self.root)

    def _make_intention(self, slug: str, content: str = "Intention test.\n") -> None:
        d = self.root / "notes" / "intentions"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{slug}.md").write_text(content, encoding="utf-8")

    def test_has_intention_returns_false_when_dir_missing(self):
        gate = self._gate()
        self.assertFalse(gate.has_intention())
        self.assertFalse(gate.has_intention("1"))

    def test_has_intention_returns_false_when_no_matching_file(self):
        d = self.root / "notes" / "intentions"
        d.mkdir(parents=True, exist_ok=True)
        gate = self._gate()
        self.assertFalse(gate.has_intention("1"))
        self.assertFalse(gate.has_intention())

    def test_has_intention_returns_true_for_matching_chapter(self):
        self._make_intention("chapitre_01")
        gate = self._gate()
        self.assertTrue(gate.has_intention("1"))
        self.assertTrue(gate.has_intention("01"))

    def test_has_intention_any_returns_true_when_any_intention_exists(self):
        self._make_intention("chapitre_03")
        gate = self._gate()
        self.assertTrue(gate.has_intention())

    def test_resolve_intention_path_returns_none_when_missing(self):
        d = self.root / "notes" / "intentions"
        d.mkdir(parents=True, exist_ok=True)
        gate = self._gate()
        self.assertIsNone(gate.resolve_intention_path("2"))

    def test_resolve_intention_path_returns_path_when_exists(self):
        self._make_intention("chapitre_02")
        gate = self._gate()
        path = gate.resolve_intention_path("2")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "chapitre_02.md")

    def test_resolve_intention_path_raises_on_conflict(self):
        from core.chapters import ChapterConflictError
        d = self.root / "notes" / "intentions"
        d.mkdir(parents=True, exist_ok=True)
        (d / "chapitre_01.md").write_text("A\n", encoding="utf-8")
        (d / "chapitre_1.md").write_text("B\n", encoding="utf-8")
        gate = self._gate()
        with self.assertRaises(ChapterConflictError):
            gate.resolve_intention_path("1")

    def test_load_intention_returns_stripped_content(self):
        self._make_intention("chapitre_01", "  Tension sourde.  \n\n")
        gate = self._gate()
        text = gate.load_intention("1")
        self.assertEqual(text, "Tension sourde.")

    def test_load_intention_raises_when_missing(self):
        d = self.root / "notes" / "intentions"
        d.mkdir(parents=True, exist_ok=True)
        gate = self._gate()
        with self.assertRaises(RuntimeError):
            gate.load_intention("99")

    def test_assert_intention_raises_when_no_file_for_chapter(self):
        gate = self._gate()
        with self.assertRaises(RuntimeError) as ctx:
            gate.assert_intention("5")
        self.assertIn("bloquée", str(ctx.exception))

    def test_assert_intention_raises_when_no_intention_at_all(self):
        gate = self._gate()
        with self.assertRaises(RuntimeError) as ctx:
            gate.assert_intention()
        self.assertIn("bloquée", str(ctx.exception))

    def test_assert_intention_passes_when_intention_exists(self):
        self._make_intention("chapitre_01")
        gate = self._gate()
        gate.assert_intention("1")  # should not raise


class PromptStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _store(self):
        from core.prompts import PromptStore
        return PromptStore(self.root)

    def _write_prompt(self, name: str, content: str) -> None:
        d = self.root / "prompts"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}_v1.txt").write_text(content, encoding="utf-8")

    def test_render_substitutes_simple_variable(self):
        self._write_prompt("hello", "Bonjour $hero.")
        store = self._store()
        result = store.render("hello", hero="Monde")
        self.assertEqual(result, "Bonjour Monde.")

    def test_render_normalizes_dict_to_json(self):
        self._write_prompt("meta", "Données: $payload")
        store = self._store()
        result = store.render("meta", payload={"key": "val"})
        self.assertIn('"key"', result)
        self.assertIn('"val"', result)

    def test_render_normalizes_none_to_empty_string(self):
        self._write_prompt("nullable", "Contexte: $ctx.")
        store = self._store()
        result = store.render("nullable", ctx=None)
        self.assertEqual(result, "Contexte: .")

    def test_render_falls_back_to_builtin_prompt(self):
        store = self._store()
        result = store.render("draft", chapter_slug="chapitre_01",
                              intention="test", structure_markdown="# s",
                              story_context="ctx")
        self.assertIn("chapitre_01", result)

    def test_render_raises_when_prompt_not_found(self):
        from core.prompts import PromptNotFoundError
        store = self._store()
        with self.assertRaises(PromptNotFoundError):
            store.render("nonexistent_prompt_xyz", x="y")

    def test_project_prompt_overrides_builtin(self):
        self._write_prompt("draft", "OVERRIDE: $chapter_slug")
        store = self._store()
        result = store.render("draft", chapter_slug="chapitre_02",
                              intention="i", structure_markdown="s",
                              story_context="c")
        self.assertTrue(result.startswith("OVERRIDE:"))
        self.assertIn("chapitre_02", result)

    def test_render_normalizes_list_to_json(self):
        self._write_prompt("list_tpl", "Items: $items")
        store = self._store()
        result = store.render("list_tpl", items=["a", "b"])
        self.assertIn('"a"', result)
        self.assertIn('"b"', result)


class CLIIntentionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_intention_create_writes_file(self):
        from cli.main import cmd_intention_create
        inputs = iter(["Une tension sourde.", EOFError()])

        def fake_input(prompt=""):
            val = next(inputs)
            if isinstance(val, BaseException):
                raise val
            return val

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cmd_intention_create(self.root, chapter_value="1", input_func=fake_input)
        self.assertEqual(exit_code, 0)
        intention_path = self.root / "notes" / "intentions" / "chapitre_01.md"
        self.assertTrue(intention_path.exists())
        content = intention_path.read_text(encoding="utf-8")
        self.assertIn("Une tension sourde.", content)

    def test_cli_status_shows_no_chapter_for_empty_project(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"], root=self.root)
        self.assertEqual(exit_code, 0)
        self.assertIn("aucun", output.getvalue())

    def test_cli_generate_without_intention_exits_nonzero(self):
        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_cls.return_value.generate_chapter.side_effect = RuntimeError(
                "Aucune intention trouvée pour chapitre_01."
            )
            exit_code = main(["generate", "chapter", "--chapter", "1"], root=self.root)
        self.assertNotEqual(exit_code, 0)

    def test_cli_intention_create_rejects_invalid_chapter_format(self):
        from cli.main import cmd_intention_create
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cmd_intention_create(self.root, chapter_value="@@@")
        self.assertEqual(exit_code, 1)
        self.assertIn("invalide", output.getvalue())

    def test_cli_intention_create_rejects_duplicate_intention(self):
        from cli.main import cmd_intention_create
        # Create once
        inputs = iter(["Tension initiale.", EOFError()])
        def fake_input(prompt=""):
            val = next(inputs)
            if isinstance(val, BaseException):
                raise val
            return val
        cmd_intention_create(self.root, chapter_value="3", input_func=fake_input)
        # Try to create again — should fail
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cmd_intention_create(self.root, chapter_value="3")
        self.assertEqual(exit_code, 1)
        self.assertIn("déjà", output.getvalue())

    def test_cli_intention_create_rejects_empty_content(self):
        from cli.main import cmd_intention_create
        inputs = iter([EOFError()])
        def fake_input(prompt=""):
            raise next(inputs)
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cmd_intention_create(self.root, chapter_value="4", input_func=fake_input)
        self.assertEqual(exit_code, 1)
        self.assertIn("vide", output.getvalue())

    def test_cli_no_args_calls_status(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([], root=self.root)
        self.assertEqual(exit_code, 0)
        self.assertIn("AI Novel Engine", output.getvalue())

    def test_cli_provider_error_exits_nonzero(self):
        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_cls.return_value.generate_chapter.side_effect = ProviderError("timeout")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["generate", "chapter", "--chapter", "1"], root=self.root)
        self.assertEqual(exit_code, 1)
        self.assertIn("Erreur", output.getvalue())

    def test_cli_write_alias_provider_error_exits_nonzero(self):
        with mock.patch("cli.main.GenerationPipeline") as pipeline_cls:
            pipeline_cls.return_value.generate_chapter.side_effect = ProviderError("timeout")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["write", "--chapter", "1"], root=self.root)
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
