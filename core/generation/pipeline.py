from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Callable, TypeVar

from core.chapters import ChapterId, resolve_chapter_file
from core.generation.models import (
    ControlReport,
    GenerationContext,
    GenerationOutcome,
    ManuscriptGateReport,
    MemoryUpdate,
    StructurePlan,
)
from core.generation.provider import (
    clone_provider_with_model,
    GenerationProvider,
    GenerationRequest,
    OpenAICompatibleProvider,
    ProviderError,
    build_provider_from_env,
)
from core.intention.gate import IntentionGate
from core.prompts import PromptStore


ApprovalCallback = Callable[[ControlReport, Path], bool]
OutputCallback = Callable[[str], None]
ParsedStagePayload = TypeVar("ParsedStagePayload")


class GenerationPipeline:
    def __init__(
        self,
        root: Path,
        provider: GenerationProvider | None = None,
        prompt_store: PromptStore | None = None,
        input_func: Callable[[str], str] = input,
        output_func: OutputCallback = print,
    ):
        self.root = root
        self.provider = provider
        self.prompt_store = prompt_store or PromptStore(root)
        self.input_func = input_func
        self.output_func = output_func
        self.intention_gate = IntentionGate(root)

    def generate_chapter(
        self,
        chapter: object,
        approval_callback: ApprovalCallback | None = None,
    ) -> GenerationOutcome:
        chapter_id = ChapterId.parse(chapter)
        self.intention_gate.assert_intention(chapter_id)
        context = self._build_context(chapter_id)
        provider = self.provider or build_provider_from_env()
        metadata = self._initial_metadata(context, provider)
        self._write_metadata(context.meta_path, metadata)

        structure_plan: StructurePlan | None = None
        draft_v1: str | None = None
        control_report: ControlReport | None = None
        draft_v2: str | None = None
        gate_report: ManuscriptGateReport | None = None
        current_candidate_text: str | None = None
        current_candidate_path: Path = context.draft_v2_path
        current_stage = "setup"

        try:
            current_stage = "structure"
            structure_plan = self._generate_structure(provider, context, metadata)
            self._write_text(context.structure_path, structure_plan.markdown)
            self._complete_stage(metadata, current_stage)
            self._set_status(metadata, "structure_ready", "Structure générée.")
            self._write_metadata(context.meta_path, metadata)

            current_stage = "draft"
            draft_v1 = self._generate_draft(provider, context, structure_plan, metadata)
            self._write_text(context.draft_v1_path, draft_v1)
            self._complete_stage(metadata, current_stage)
            self._set_status(metadata, "draft_ready", "Brouillon initial généré.")
            self._write_metadata(context.meta_path, metadata)

            current_stage = "critique"
            control_report = self._generate_control_report(provider, context, structure_plan, draft_v1, metadata)
            self._write_text(context.critique_path, control_report.to_markdown(context.chapter_id))
            self._complete_stage(metadata, current_stage)
            self._set_status(metadata, "critique_ready", "Critique structurée générée.")
            metadata["control_report"] = control_report.to_dict()
            self._write_metadata(context.meta_path, metadata)

            current_stage = "rewrite"
            draft_v2 = self._rewrite_draft(provider, context, structure_plan, draft_v1, control_report, metadata)
            self._write_text(context.draft_v2_path, draft_v2)
            self._complete_stage(metadata, current_stage)
            self._set_status(metadata, "rewrite_ready", "Brouillon final généré, contrôle manuscrit en cours.")
            metadata["draft_final"] = str(context.draft_v2_path)
            self._write_metadata(context.meta_path, metadata)
            current_candidate_text = draft_v2
            current_candidate_path = context.draft_v2_path

            current_stage = "gate"
            gate_report = self._generate_manuscript_gate_report(
                provider,
                context,
                structure_plan,
                current_candidate_text,
                metadata,
            )
            self._persist_gate_report(metadata, context, gate_report, current_candidate_path)
            self._complete_stage(metadata, current_stage)
            self._write_metadata(context.meta_path, metadata)

            if not gate_report.ready_for_manuscript:
                current_candidate_text, current_candidate_path, gate_report = self._repair_until_ready(
                    provider=provider,
                    context=context,
                    structure_plan=structure_plan,
                    current_candidate_text=current_candidate_text,
                    current_candidate_path=current_candidate_path,
                    gate_report=gate_report,
                    metadata=metadata,
                )
                if not gate_report.ready_for_manuscript:
                    self._set_status(metadata, "quality_blocked", "Promotion bloquée par le garde-fou manuscrit.")
                    metadata["failed_stage"] = current_stage
                    metadata["finished_at"] = self._timestamp()
                    self._write_metadata(context.meta_path, metadata)
                    return GenerationOutcome(
                        chapter_id=chapter_id,
                        accepted=False,
                        status="quality_blocked",
                        draft_path=current_candidate_path,
                        critique_path=context.critique_path,
                        gate_path=context.gate_path,
                        meta_path=context.meta_path,
                        manuscript_path=None,
                        quality_blockers=gate_report.all_blockers(),
                    )

            self._set_status(metadata, "awaiting_acceptance", "Brouillon final prêt pour validation.")
            self._write_metadata(context.meta_path, metadata)

            accepted = (
                approval_callback(control_report, current_candidate_path)
                if approval_callback is not None
                else self._prompt_for_acceptance(control_report, current_candidate_path)
            )
            metadata["accepted"] = accepted

            if not accepted:
                self._set_status(metadata, "rejected", "Promotion refusée par l'auteur.")
                metadata["finished_at"] = self._timestamp()
                self._write_metadata(context.meta_path, metadata)
                return GenerationOutcome(
                    chapter_id=chapter_id,
                    accepted=False,
                    status="rejected",
                    draft_path=current_candidate_path,
                    critique_path=context.critique_path,
                    gate_path=context.gate_path,
                    meta_path=context.meta_path,
                    manuscript_path=None,
                    quality_blockers=gate_report.all_blockers() if gate_report is not None else [],
                )

            current_stage = "memory"
            self._write_text(context.manuscript_path, current_candidate_text)
            self._set_status(
                metadata,
                "manuscript_promoted",
                "Brouillon promu dans le manuscrit, mise à jour mémoire en cours.",
            )
            self._write_metadata(context.meta_path, metadata)
            memory_update = self._generate_memory_update(provider, context, current_candidate_text, metadata)
            self._persist_memory(context, memory_update)
            self._complete_stage(metadata, current_stage)
            self._set_status(metadata, "accepted", "Chapitre accepté et mémoire mise à jour.")
            metadata["finished_at"] = self._timestamp()
            metadata["memory_update"] = memory_update.to_dict()
            self._write_metadata(context.meta_path, metadata)

            return GenerationOutcome(
                chapter_id=chapter_id,
                accepted=True,
                status="accepted",
                draft_path=current_candidate_path,
                critique_path=context.critique_path,
                gate_path=context.gate_path,
                meta_path=context.meta_path,
                manuscript_path=context.manuscript_path,
                quality_blockers=[],
            )
        except ProviderError as exc:
            failed_stage = self._current_running_stage(metadata, current_stage)
            self._set_status(metadata, "failed", f"Échec à l'étape {failed_stage}: {exc}")
            metadata["failed_stage"] = failed_stage
            metadata["error"] = str(exc)
            metadata["finished_at"] = self._timestamp()
            self._write_metadata(context.meta_path, metadata)
            raise
        except ValueError as exc:
            failed_stage = self._current_running_stage(metadata, current_stage)
            self._set_status(metadata, "failed", f"Échec à l'étape {failed_stage}: {exc}")
            metadata["failed_stage"] = failed_stage
            metadata["error"] = str(exc)
            metadata["finished_at"] = self._timestamp()
            self._write_metadata(context.meta_path, metadata)
            raise ProviderError(str(exc)) from exc

    def _build_context(self, chapter_id: ChapterId) -> GenerationContext:
        intention_path = self.intention_gate.resolve_intention_path(chapter_id)
        if intention_path is None:
            raise RuntimeError(f"Aucune intention trouvée pour {chapter_id.slug}.")

        structure_path = resolve_chapter_file(self.root / "structure" / "chapitres", chapter_id)
        manuscript_path = resolve_chapter_file(self.root / "manuscrit", chapter_id)
        memory_summary_path = resolve_chapter_file(self.root / "memoire" / "chapitres", chapter_id)
        draft_dir = self.root / "brouillons" / "chapitres" / chapter_id.slug

        return GenerationContext(
            root=self.root,
            chapter_id=chapter_id,
            intention_path=intention_path,
            intention_text=intention_path.read_text(encoding="utf-8").strip(),
            structure_path=structure_path,
            draft_dir=draft_dir,
            draft_v1_path=draft_dir / "draft_v1.md",
            critique_path=draft_dir / "critique_v1.md",
            draft_v2_path=draft_dir / "draft_v2.md",
            gate_path=draft_dir / "gate_v1.json",
            meta_path=draft_dir / "meta.json",
            manuscript_path=manuscript_path,
            memory_summary_path=memory_summary_path,
            memory_index_dir=self.root / "memoire" / "index",
            story_context=self._build_story_context(chapter_id),
        )

    def _build_story_context(self, chapter_id: ChapterId) -> str:
        sections: list[str] = []

        previous_manuscript = self._latest_existing_file(self.root / "manuscrit", chapter_id.number - 1)
        if previous_manuscript is not None:
            sections.append(
                "## Dernier chapitre accepté\n"
                f"Fichier: {previous_manuscript.name}\n"
                f"{self._read_excerpt(previous_manuscript)}"
            )

        previous_memory = self._latest_existing_file(self.root / "memoire" / "chapitres", chapter_id.number - 1)
        if previous_memory is not None:
            sections.append(
                "## Dernier résumé mémoire\n"
                f"Fichier: {previous_memory.name}\n"
                f"{self._read_excerpt(previous_memory)}"
            )

        for name in ("personnages.json", "lieux.json", "chronologie.json"):
            path = self.root / "memoire" / "index" / name
            if path.exists():
                sections.append(f"## {name}\n{self._read_excerpt(path, limit=2000)}")

        if not sections:
            return "Aucun contexte projet disponible."

        return "\n\n".join(sections)

    def _latest_existing_file(self, directory: Path, max_number: int) -> Path | None:
        if max_number <= 0 or not directory.exists():
            return None

        candidates: list[Path] = []
        for number in range(max_number, 0, -1):
            path = resolve_chapter_file(directory, ChapterId(number))
            if path.exists():
                candidates.append(path)
                break
        return candidates[0] if candidates else None

    def _read_excerpt(self, path: Path, limit: int = 4000) -> str:
        text = path.read_text(encoding="utf-8").strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}\n[...]"

    def _generate_structure(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        metadata: dict[str, object],
    ) -> StructurePlan:
        prompt = self.prompt_store.render(
            "structure",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            story_context=context.story_context,
        )
        self._begin_stage(
            metadata,
            context.meta_path,
            "structure",
            "Génération de la structure en cours.",
        )
        response = provider.generate(GenerationRequest(stage="structure", prompt=prompt))
        markdown = response.content.strip()
        if not markdown:
            raise ProviderError("Le provider a renvoyé une structure vide.")
        return StructurePlan(chapter_id=context.chapter_id, markdown=f"{markdown}\n")

    def _generate_draft(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        metadata: dict[str, object],
    ) -> str:
        prompt = self.prompt_store.render(
            "draft",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            structure_markdown=structure_plan.markdown,
            story_context=context.story_context,
        )
        self._begin_stage(
            metadata,
            context.meta_path,
            "draft",
            "Génération du brouillon initial en cours.",
        )
        response = provider.generate(GenerationRequest(stage="draft", prompt=prompt, temperature=0.4))
        draft = response.content.strip()
        if not draft:
            raise ProviderError("Le provider a renvoyé un brouillon vide.")
        return f"{draft}\n"

    def _generate_control_report(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        draft_v1: str,
        metadata: dict[str, object],
    ) -> ControlReport:
        prompt = self.prompt_store.render(
            "critique",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            structure_markdown=structure_plan.markdown,
            draft_markdown=draft_v1,
        )
        return self._generate_json_payload(
            provider=provider,
            stage="critique",
            prompt=prompt,
            retry_prompt_name="critique_retry",
            parse_response=ControlReport.from_response_text,
            metadata=metadata,
            meta_path=context.meta_path,
            retry_context={
                "chapter_slug": context.chapter_id.slug,
                "intention": context.intention_text,
                "structure_markdown": structure_plan.markdown,
                "draft_markdown": draft_v1,
            },
        )

    def _rewrite_draft(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        draft_v1: str,
        control_report: ControlReport,
        metadata: dict[str, object],
    ) -> str:
        prompt = self.prompt_store.render(
            "rewrite",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            structure_markdown=structure_plan.markdown,
            draft_markdown=draft_v1,
            critique_json=control_report.to_dict(),
        )
        self._begin_stage(
            metadata,
            context.meta_path,
            "rewrite",
            "Réécriture guidée par la critique en cours.",
        )
        response = provider.generate(GenerationRequest(stage="rewrite", prompt=prompt, temperature=0.3))
        draft = response.content.strip()
        if not draft:
            raise ProviderError("Le provider a renvoyé une réécriture vide.")
        return f"{draft}\n"

    def _repair_until_ready(
        self,
        *,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        current_candidate_text: str,
        current_candidate_path: Path,
        gate_report: ManuscriptGateReport,
        metadata: dict[str, object],
    ) -> tuple[str, Path, ManuscriptGateReport]:
        for attempt in range(1, self._repair_max_passes() + 1):
            repair_model = self._repair_model_for_attempt(provider, attempt)
            repair_provider = self._provider_for_repair(provider, repair_model)
            repaired_text = self._repair_draft(
                provider=repair_provider,
                context=context,
                structure_plan=structure_plan,
                current_candidate=current_candidate_text,
                gate_report=gate_report,
                metadata=metadata,
                attempt=attempt,
                repair_model=repair_model,
            )
            repair_path = context.repair_path(attempt)
            self._write_text(repair_path, repaired_text)
            self._complete_stage(metadata, "repair")
            self._record_repair_attempt(metadata, attempt=attempt, model=self._provider_model_name(repair_provider) or repair_model, path=repair_path)
            self._set_status(
                metadata,
                "repair_ready",
                f"Réparation prose v{attempt} générée, nouveau contrôle manuscrit en cours.",
            )
            metadata["draft_final"] = str(repair_path)
            self._write_metadata(context.meta_path, metadata)

            current_candidate_text = repaired_text
            current_candidate_path = repair_path
            gate_report = self._generate_manuscript_gate_report(
                repair_provider,
                context,
                structure_plan,
                current_candidate_text,
                metadata,
            )
            self._persist_gate_report(metadata, context, gate_report, current_candidate_path)
            self._complete_stage(metadata, "gate")
            self._write_metadata(context.meta_path, metadata)
            if gate_report.ready_for_manuscript:
                break

        return current_candidate_text, current_candidate_path, gate_report

    def _repair_draft(
        self,
        *,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        current_candidate: str,
        gate_report: ManuscriptGateReport,
        metadata: dict[str, object],
        attempt: int,
        repair_model: str | None,
    ) -> str:
        prompt = self.prompt_store.render(
            "repair",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            structure_markdown=structure_plan.markdown,
            draft_markdown=current_candidate,
            gate_json=gate_report.to_dict(),
            repair_attempt=attempt,
            repair_model=repair_model or "",
            story_context=context.story_context,
        )
        model_label = repair_model or self._provider_model_name(provider) or "provider_courant"
        self._begin_stage(
            metadata,
            context.meta_path,
            "repair",
            f"Réparation prose v{attempt} en cours avec {model_label}.",
        )
        response = provider.generate(GenerationRequest(stage="repair", prompt=prompt, temperature=0.2))
        repaired = response.content.strip()
        if not repaired:
            raise ProviderError("Le provider a renvoyé une réparation vide.")
        return f"{repaired}\n"

    def _generate_manuscript_gate_report(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        structure_plan: StructurePlan,
        draft_v2: str,
        metadata: dict[str, object],
    ) -> ManuscriptGateReport:
        self._begin_stage(
            metadata,
            context.meta_path,
            "gate",
            "Contrôle manuscrit en cours.",
        )
        heuristic_report = self._heuristic_gate_report(draft_v2)
        if heuristic_report is not None:
            metadata["last_status_message"] = heuristic_report.summary
            return heuristic_report

        prompt = self.prompt_store.render(
            "gate",
            chapter_slug=context.chapter_id.slug,
            intention=context.intention_text,
            structure_markdown=structure_plan.markdown,
            draft_markdown=draft_v2,
        )
        return self._generate_json_payload(
            provider=provider,
            stage="gate",
            prompt=prompt,
            retry_prompt_name="gate_retry",
            parse_response=ManuscriptGateReport.from_response_text,
            metadata=metadata,
            meta_path=context.meta_path,
            retry_context={
                "chapter_slug": context.chapter_id.slug,
                "intention": context.intention_text,
                "structure_markdown": structure_plan.markdown,
                "draft_markdown": draft_v2,
            },
            begin_stage=False,
        )

    def _persist_gate_report(
        self,
        metadata: dict[str, object],
        context: GenerationContext,
        gate_report: ManuscriptGateReport,
        draft_path: Path,
    ) -> None:
        self._write_json(context.gate_path, gate_report.to_dict())
        metadata["gate_report"] = gate_report.to_dict()
        metadata["quality_blockers"] = gate_report.all_blockers()
        metadata["draft_final"] = str(draft_path)

    def _provider_for_repair(self, provider: GenerationProvider, model: str | None) -> GenerationProvider:
        if not model:
            return provider
        return clone_provider_with_model(provider, model)

    def _repair_max_passes(self) -> int:
        raw = os.environ.get("ANE_REPAIR_MAX_PASSES", "2").strip() or "2"
        try:
            value = int(raw)
        except ValueError as exc:
            raise ProviderError("ANE_REPAIR_MAX_PASSES doit être un entier positif.") from exc
        if value <= 0:
            raise ProviderError("ANE_REPAIR_MAX_PASSES doit être supérieur à zéro.")
        return value

    def _repair_model_for_attempt(self, provider: GenerationProvider, attempt: int) -> str | None:
        base_model = self._provider_model_name(provider)
        if attempt <= 1:
            return base_model

        override = os.environ.get("ANE_REPAIR_FALLBACK_MODEL", "").strip()
        candidate = override or self._default_repair_fallback_model(base_model) or base_model
        if self._is_cross_apple_runtime_switch(base_model, candidate):
            raise ProviderError(
                "ANE_REPAIR_FALLBACK_MODEL ne peut pas viser un autre modèle apple-coreml pendant un même smoke. "
                "Relancer le runtime Apple sur le modèle cible ou utiliser un fallback non-Apple."
            )
        return candidate

    def _default_repair_fallback_model(self, model: str | None) -> str | None:
        mapping = {
            "ollama:qwen2.5:1.5b": "ollama:qwen2.5:7b",
            "apple-coreml:qwen2.5-0.5b-instruct-onnx": "ollama:qwen2.5:7b",
            "apple-coreml:qwen3.5-4b-onnx-q4f16": "ollama:qwen2.5:7b",
        }
        if not model:
            return None
        return mapping.get(model)

    def _is_cross_apple_runtime_switch(self, base_model: str | None, candidate: str | None) -> bool:
        if not base_model or not candidate:
            return False
        if base_model == candidate:
            return False
        return base_model.startswith("apple-coreml:") and candidate.startswith("apple-coreml:")

    def _heuristic_gate_report(self, draft_v2: str) -> ManuscriptGateReport | None:
        blockers: list[str] = []
        recommendations: list[str] = []

        if self._word_count(draft_v2) < 180:
            blockers.append("too_short")
            recommendations.append("Allonger le chapitre pour produire une scene complete et continue.")

        if self._has_truncated_ending(draft_v2):
            blockers.append("truncated_ending")
            recommendations.append("Terminer la scene sur une phrase complete avec une vraie fermeture.")

        if self._is_outline_like(draft_v2):
            blockers.append("outline_like")
            recommendations.append("Remplacer les titres et puces par une narration continue en prose.")

        if not blockers:
            return None

        summary = "Le garde-fou manuscrit a bloque la promotion: " + ", ".join(blockers) + "."
        return ManuscriptGateReport.from_heuristics(
            blockers=blockers,
            recommendations=recommendations,
            summary=summary,
        )

    def _word_count(self, text: str) -> int:
        return len(re.findall(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][0-9A-Za-zÀ-ÖØ-öø-ÿ]+)*", text))

    def _has_truncated_ending(self, text: str) -> bool:
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            return not stripped.endswith((".", "!", "?", "…", "»", '"', "'"))
        return True

    def _is_outline_like(self, text: str) -> bool:
        detected_markers: set[str] = set()
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                detected_markers.add("heading_level_2")
            if stripped.startswith("### "):
                detected_markers.add("heading_level_3")
            if stripped.startswith("- "):
                detected_markers.add("bullet_list")
            lowered = stripped.lower()
            if "**objectif**" in lowered or "**conflit**" in lowered or "**sortie**" in lowered:
                detected_markers.add("scene_fields")
            if "scène" in lowered or "scene" in lowered:
                detected_markers.add("scene_heading")
            if len(detected_markers) >= 2:
                return True
        return False

    def _generate_memory_update(
        self,
        provider: GenerationProvider,
        context: GenerationContext,
        accepted_draft: str,
        metadata: dict[str, object],
    ) -> MemoryUpdate:
        prompt = self.prompt_store.render(
            "memory",
            chapter_slug=context.chapter_id.slug,
            accepted_draft=accepted_draft,
            story_context=context.story_context,
        )
        return self._generate_json_payload(
            provider=provider,
            stage="memory",
            prompt=prompt,
            retry_prompt_name="memory_retry",
            parse_response=MemoryUpdate.from_response_text,
            metadata=metadata,
            meta_path=context.meta_path,
            retry_context={
                "chapter_slug": context.chapter_id.slug,
                "accepted_draft": accepted_draft,
                "story_context": context.story_context,
            },
        )

    def _generate_json_payload(
        self,
        *,
        provider: GenerationProvider,
        stage: str,
        prompt: str,
        retry_prompt_name: str,
        parse_response: Callable[[str], ParsedStagePayload],
        metadata: dict[str, object],
        meta_path: Path,
        retry_context: dict[str, object],
        begin_stage: bool = True,
    ) -> ParsedStagePayload:
        if begin_stage:
            self._begin_stage(
                metadata,
                meta_path,
                stage,
                f"Génération de l'étape {stage} en cours.",
            )
        first_response = provider.generate(
            GenerationRequest(stage=stage, prompt=prompt, response_format="json", temperature=0.1)
        )
        first_payload = first_response.content
        try:
            return parse_response(first_payload)
        except ValueError as first_error:
            self._mark_stage_attempt(
                metadata,
                stage,
                retry=True,
                message=f"Réessai JSON sur l'étape {stage} après une réponse invalide.",
            )
            self._set_status(metadata, f"{stage}_retrying", f"Réessai JSON sur l'étape {stage} en cours.")
            self._write_metadata(meta_path, metadata)
            retry_prompt = self.prompt_store.render(
                retry_prompt_name,
                parse_error=str(first_error),
                invalid_response=self._truncate_retry_payload(first_payload),
                **retry_context,
            )
            retry_response = provider.generate(
                GenerationRequest(stage=stage, prompt=retry_prompt, response_format="json", temperature=0.0)
            )
            try:
                return parse_response(retry_response.content)
            except ValueError as second_error:
                raise ProviderError(
                    f"Le provider a renvoyé un JSON invalide pendant l'étape '{stage}' après deux tentatives: "
                    f"première erreur: {first_error}; seconde erreur: {second_error}"
                ) from second_error

    def _truncate_retry_payload(self, payload: str, limit: int = 2000) -> str:
        text = payload.strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}\n[...]"

    def _persist_memory(self, context: GenerationContext, memory_update: MemoryUpdate) -> None:
        self._write_text(
            context.memory_summary_path,
            f"# Mémoire — {context.chapter_id.slug}\n\n{memory_update.chapter_summary}\n",
        )

        self._merge_index_records(
            context.memory_index_dir / "personnages.json",
            context.chapter_id,
            memory_update.characters,
            label_key="name",
        )
        self._merge_index_records(
            context.memory_index_dir / "lieux.json",
            context.chapter_id,
            memory_update.locations,
            label_key="name",
        )
        self._merge_timeline_records(
            context.memory_index_dir / "chronologie.json",
            context.chapter_id,
            memory_update.timeline_events,
        )

    def _merge_index_records(
        self,
        path: Path,
        chapter_id: ChapterId,
        records: list[dict[str, str]],
        label_key: str,
    ) -> None:
        existing: dict[str, dict[str, object]] = {}
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                existing = payload

        for record in records:
            label = record[label_key]
            current = existing.get(label, {"chapters": []})
            chapters = list(current.get("chapters", []))
            if chapter_id.slug not in chapters:
                chapters.append(chapter_id.slug)

            merged = dict(current)
            merged.update(record)
            merged["chapters"] = sorted(chapters)
            existing[label] = merged

        self._write_json(path, existing)

    def _merge_timeline_records(
        self,
        path: Path,
        chapter_id: ChapterId,
        records: list[dict[str, str]],
    ) -> None:
        existing: list[dict[str, str]] = []
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = [
                    {str(key): str(value) for key, value in item.items()}
                    for item in payload
                    if isinstance(item, dict)
                ]

        for record in records:
            merged = dict(record)
            merged["chapter"] = chapter_id.slug
            existing.append(merged)

        self._write_json(path, existing)

    def _prompt_for_acceptance(self, control_report: ControlReport, draft_path: Path) -> bool:
        self.output_func("")
        self.output_func(f"Critique: {control_report.summary}")
        self.output_func(f"Brouillon final: {draft_path}")
        self.output_func(f"Écarts détectés: {len(control_report.deviations)}")
        response = self.input_func("Promouvoir ce brouillon vers le manuscrit ? [y/N]: ").strip().lower()
        return response in {"y", "yes", "o", "oui"}

    def _initial_metadata(self, context: GenerationContext, provider: GenerationProvider) -> dict[str, object]:
        return {
            "chapter": context.chapter_id.slug,
            "started_at": self._timestamp(),
            "status": "started",
            "last_status_message": "Pipeline initialisé.",
            "completed_stages": [],
            "accepted": False,
            "repair_attempts": 0,
            "repair_models": [],
            "stage_attempts": {},
            "retry_stages": [],
            "quality_blockers": [],
            "provider": self._provider_metadata(provider),
            "artifacts": {
                "intention": str(context.intention_path),
                "structure": str(context.structure_path),
                "draft_v1": str(context.draft_v1_path),
                "critique_v1": str(context.critique_path),
                "draft_v2": str(context.draft_v2_path),
                "repair_latest": None,
                "repairs": [],
                "gate_v1": str(context.gate_path),
                "manuscript": str(context.manuscript_path),
                "memory_summary": str(context.memory_summary_path),
            },
        }

    def _provider_metadata(self, provider: GenerationProvider) -> dict[str, object]:
        snapshot = {
            "kind": provider.__class__.__name__,
            "base_url": None,
            "model": None,
        }
        if isinstance(provider, OpenAICompatibleProvider):
            snapshot["base_url"] = provider.config.base_url
            snapshot["model"] = provider.config.model
        return snapshot

    def _current_running_stage(self, metadata: dict[str, object], fallback: str) -> str:
        status = str(metadata.get("status", "")).strip()
        for suffix in ("_running", "_retrying"):
            if status.endswith(suffix):
                return status[: -len(suffix)]
        return fallback

    def _provider_model_name(self, provider: GenerationProvider) -> str | None:
        metadata = self._provider_metadata(provider)
        model = metadata.get("model")
        if not isinstance(model, str):
            return None
        return model.strip() or None

    def _complete_stage(self, metadata: dict[str, object], stage: str) -> None:
        completed = metadata.setdefault("completed_stages", [])
        if not isinstance(completed, list):
            completed = []
            metadata["completed_stages"] = completed
        if stage not in completed:
            completed.append(stage)

    def _record_repair_attempt(
        self,
        metadata: dict[str, object],
        *,
        attempt: int,
        model: str | None,
        path: Path,
    ) -> None:
        metadata["repair_attempts"] = attempt

        repair_models = metadata.setdefault("repair_models", [])
        if not isinstance(repair_models, list):
            repair_models = []
            metadata["repair_models"] = repair_models
        repair_models.append(model or "provider_courant")

        artifacts = metadata.setdefault("artifacts", {})
        if not isinstance(artifacts, dict):
            artifacts = {}
            metadata["artifacts"] = artifacts
        repairs = artifacts.setdefault("repairs", [])
        if not isinstance(repairs, list):
            repairs = []
            artifacts["repairs"] = repairs
        repairs.append(str(path))
        artifacts["repair_latest"] = str(path)

    def _set_status(self, metadata: dict[str, object], status: str, message: str) -> None:
        metadata["status"] = status
        metadata["last_status_message"] = message

    def _mark_stage_attempt(
        self,
        metadata: dict[str, object],
        stage: str,
        *,
        retry: bool = False,
        message: str | None = None,
    ) -> None:
        stage_attempts = metadata.setdefault("stage_attempts", {})
        if not isinstance(stage_attempts, dict):
            stage_attempts = {}
            metadata["stage_attempts"] = stage_attempts
        stage_attempts[stage] = int(stage_attempts.get(stage, 0)) + 1

        if retry:
            retry_stages = metadata.setdefault("retry_stages", [])
            if isinstance(retry_stages, list) and stage not in retry_stages:
                retry_stages.append(stage)

        if message:
            metadata["last_status_message"] = message

    def _begin_stage(
        self,
        metadata: dict[str, object],
        meta_path: Path,
        stage: str,
        message: str,
    ) -> None:
        self._mark_stage_attempt(metadata, stage)
        self._set_status(metadata, f"{stage}_running", message)
        self._write_metadata(meta_path, metadata)

    def _write_metadata(self, path: Path, metadata: dict[str, object]) -> None:
        self._write_json(path, metadata)

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
