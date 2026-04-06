from __future__ import annotations

import os

from core.evaluation.models import NarrativeJudge, NarrativeJudgeReport
from core.generation.provider import (
    clone_provider_with_model,
    GenerationProvider,
    GenerationRequest,
    ProviderError,
)
from core.prompts import PromptStore


class ProviderNarrativeJudge(NarrativeJudge):
    def __init__(
        self,
        *,
        provider: GenerationProvider,
        prompt_store: PromptStore,
        max_tokens: int = 384,
    ):
        self.provider = provider
        self.prompt_store = prompt_store
        self.max_tokens = max_tokens

    def evaluate(
        self,
        *,
        chapter_slug: str,
        intention: str,
        structure_markdown: str,
        draft_markdown: str,
        story_context: str,
    ) -> NarrativeJudgeReport:
        prompt = self.prompt_store.render(
            "judge_narrative",
            chapter_slug=chapter_slug,
            intention=intention,
            structure_markdown=structure_markdown,
            draft_markdown=draft_markdown,
            story_context=story_context,
        )
        try:
            first = self.provider.generate(
                GenerationRequest(
                    stage="judge",
                    prompt=prompt,
                    response_format="json",
                    temperature=0.1,
                    max_tokens=self.max_tokens,
                )
            )
            return NarrativeJudgeReport.from_response_text(first.content)
        except (ProviderError, ValueError) as first_error:
            retry_prompt = self.prompt_store.render(
                "judge_narrative_retry",
                chapter_slug=chapter_slug,
                intention=intention,
                structure_markdown=structure_markdown,
                draft_markdown=draft_markdown,
                story_context=story_context,
                parse_error=str(first_error),
                invalid_response=getattr(locals().get("first"), "content", ""),
            )
            try:
                second = self.provider.generate(
                    GenerationRequest(
                        stage="judge",
                        prompt=retry_prompt,
                        response_format="json",
                        temperature=0.1,
                        max_tokens=self.max_tokens,
                    )
                )
                return NarrativeJudgeReport.from_response_text(second.content)
            except (ProviderError, ValueError) as second_error:
                return NarrativeJudgeReport.unavailable(
                    f"Le juge narratif a echoue apres deux tentatives: {second_error}"
                )


def build_narrative_judge_from_env(
    *,
    provider: GenerationProvider,
    prompt_store: PromptStore,
) -> NarrativeJudge | None:
    judge_model = os.environ.get("ANE_JUDGE_MODEL", "").strip()
    if not judge_model:
        return None

    judge_provider = clone_provider_with_model(provider, judge_model)
    return ProviderNarrativeJudge(provider=judge_provider, prompt_store=prompt_store)
