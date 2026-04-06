# Cartes de fonctionnalite - 16 mars 2026

Cartographie courte des fonctionnalites, de leur valeur et de leur etat reel.

Mise a jour : 16 mars 2026 (lot refonte).

## Carte 1 - Ecriture sous contrainte

| Fonction | Valeur auteur | Surface | Etat | Suite |
|---|---|---|---|---|
| Intention obligatoire | empeche la generation sans cadre | `IntentionGate`, CLI | livre | garder la collision `chapitre_1` / `chapitre_01` visible |
| Pipeline narratif strict | garde un processus lisible | `GenerationPipeline` | livre | continuer a le garder runtime-agnostic |
| Validation auteur | pas de promotion automatique | CLI, callbacks | livre | un cockpit futur peut juste aider, pas decider |

## Carte 2 - Qualite narrative

| Fonction | Valeur | Surface | Etat | Suite |
|---|---|---|---|---|
| Critique JSON | diagnostic compacte | `ControlReport` | livre | ne pas laisser gonfler le schema |
| Gate manuscrit | bloque prose insuffisante | `ManuscriptGateReport` | livre | ajuster seulement apres reruns stables |
| Repair automatique | tente de sauver un brouillon | `repair_vN` | livre | cibler `outline_like` et `truncated_ending` |
| Output primer (a faire) | force la prose en debut de sortie | `prompts/draft_v1.txt` | **planifie** | terminer le prompt par un incipit partiel |
| Few-shot BAD/GOOD (a faire) | montre ce qui est interdit | `draft_v1`, `rewrite_v1`, `repair_v1` | **planifie** | 1 exemple mauvais + 1 bon en 3-5 lignes |
| Structure → narrative summary (a faire) | empeche outline_like a la source | `GenerationPipeline._build_draft_prompt()` | **planifie** | pattern GOAT-Storytelling-Agent |

## Carte 3 - Memoire externe

| Fonction | Valeur | Surface | Etat | Suite |
|---|---|---|---|---|
| Resume chapitre | relance rapide | `memoire/chapitres` | livre | garder le format court |
| Index personnages/lieux | continuité lisible | `memoire/index/*.json` | livre | deja dedupes |
| Chronologie | garde les evenements | `chronologie.json` | corrigee | surveiller les reruns de meme chapitre |

## Carte 4 - Runtime interchangeable

| Fonction | Valeur | Surface | Etat | Suite |
|---|---|---|---|---|
| Provider OpenAI-compatible | decouple ANE du runtime | `OpenAICompatibleProvider` | livre | garder le contrat minimal |
| Routage `provider:model` | change de backend sans rewriter le pipeline | `ANE_MODEL` | livre | continuer sur `llama.cpp` |
| Contournement `llama.cpp` | sort des crashes Ollama natifs | `ollama_runtime=openai_compatible` | stable | :8091 valide pour qwen2.5:7b + mistral-nemo |
| Lot `french_models` | test des modeles francophones | `automation/next_lots.toml` | **nouveau** | mistral-nemo:latest, requalification en cours |

## Carte 5 - Exploitation

| Fonction | Valeur operateur | Surface | Etat | Suite |
|---|---|---|---|---|
| Reports machine | evidence pack par lot | `automation/reports/` | livre | garder les workspaces utiles |
| Analyse stderr | lit les causes frequentes | `scripts/reports_ops.py` | amelioree | ajouter si besoin des regroupements par etape |
| TUI lots | supervision lot courant | `scripts/next_lots_tui.py` | livre | garder focalise |
| TUI ops | vue projet + lots + logs | `scripts/ops_tui.py` | livre | enrichir seulement si le terrain le demande |

## Carte 6 - Documentation

| Fonction | Valeur | Etat | Suite |
|---|---|---|---|
| Contextes / memoires / plans dates | reprise rapide | remis a niveau | garder les dates coherentes |
| Spec systeme | base commune | livree | servir de reference courte |
| Veille OSS | eviter de reinventer l'ecosysteme | enrichie | GOAT, prometheus-eval, story-eval, outlines, DeepEval, lm-format-enforcer, SCORE, KazKozDev/NovelGenerator, CroissantLLM, EQ-bench suite, FrenchBench, CamemBERT perplexite |

## Carte 7 - Qualite code (nouvelle)

| Probleme | Impact | Fichier | Priorite | Fix prevu |
|---|---|---|---|---|
| 4 bare `except Exception` | masque erreurs de prog | `core/next_lots.py` | P1 | restreindre a `(OSError, json.JSONDecodeError, ValueError)` |
| `generate_chapter()` 150 LOC | maintenance difficile | `core/generation/pipeline.py` | **livre** | `_finish_stage()` extrait (phase 2) |
| `metadata` dict non-type | erreurs silencieuses | `core/generation/pipeline.py` | P3 | `ChapterMetadata(TypedDict)` — reporte 20+ signatures |
| `_close_json_delimiters()` fragile | echecs JSON silencieux | `core/generation/models.py` | **livre** | rebuild car-par-car, mismatched + stray closers (phase 3) |
| 3 fonctions near-identiques | duplication de logique | `core/project/loader.py` | **livre** | `_iter_chapters_with_status()` (phase 2) |
| couverture CLI 35% | regressions non detectees | `cli/main.py` | **livre** | 6 nouveaux tests : invalid chapter, duplicate, empty, no args, ProviderError x2 (phase 4) |
| couverture `core/reporting.py` 3 tests | fonctions utilitaires non testees | `core/reporting.py` | **livre** | 21 tests : safe_read_json, safe_stamp, extract_stderr, classification_count, folder_timestamp, latest_report_run, log_label (phase 4) |
| `_is_outline_like()` manque bullet-only | prose 0.5b en listes pures non bloquee | `core/generation/pipeline.py` | **livre** | `dense_bullet_list`: 4+ lignes bullet = outline_like solo; 2 nouveaux tests; 111 tests verts |
