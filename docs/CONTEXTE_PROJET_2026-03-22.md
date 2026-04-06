# Contexte projet - 22 mars 2026

Photographie courte du repo `ai-novel-engine` apres reruns narratifs cibles avec le juge secondaire et revalidation locale `llama.cpp`.

## Intention

Conserver ANE comme moteur narratif strict, inspectable et relancable, tout en rendant les diagnostics de qualite plus actionnables que le simple mix heuristique precedent.

## Etat reel

- le moteur Python reste la source de verite pour le pipeline `intention -> structure -> draft -> critique -> rewrite -> gate -> repair -> memory`
- `core/runtime/` porte maintenant la configuration, la sante, les profils et l'orchestration runtime utiles a ANE
- `core/evaluation/` ajoute un juge narratif secondaire optionnel active par `ANE_JUDGE_MODEL`
- le gate fusionne maintenant heuristiques locales et verdict narratif secondaire dans `gate_v1.json` et `meta.json`
- l'app SwiftUI reste alignee sur cette architecture et sait lancer le pipeline ANE complet
- la suite Python est revalidee a `156` tests verts

## Etat runtime utile

- `:8091` a ete revalide localement le 22 mars 2026 via `llama-server` pour :
  - `ollama:qwen2.5:7b`
  - `ollama:mistral-nemo:latest`
- `:8110` repond a `/health` via tunnel remote, mais le routage chat utile renvoie encore `Temporary failure in name resolution`; ce n'est pas un runtime exploitable pour les reruns ANE
- `:8201` n'a pas ete redemarre dans cette session, mais la procedure operative a ete reconfirmee dans le repo Mascarade reel via `scripts/run_apple_llm_service.sh`
- `automation/next_lots.toml` pointe maintenant vers le vrai repo local Mascarade : `/Users/electron/Documents/Projets/mascarade`

## Resultats narratifs utiles

- `ollama:qwen2.5:7b` rerun avec `ANE_JUDGE_MODEL=ollama:qwen2.5:7b` :
  - verdict final : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_risky_decision`
  - lecture utile : le juge conserve la tension et l'indice, mais isole encore l'absence de decision finale suffisamment couteuse
- `ollama:mistral-nemo:latest` rerun avec `ANE_JUDGE_MODEL=ollama:mistral-nemo:latest` :
  - verdict final : `quality_blocked`
  - blockers finaux : `truncated_ending`, `missing_immediate_consequence`
  - lecture utile : la decision risquee est finalement presente, mais la consequence observable immediate manque encore
- reruns comparables avec budgets manifeste :
  - `qwen2.5:7b` reste `quality_blocked` et confirme que le budget seul ne resout pas la fin de scene
  - `mistral-nemo` descend a `quality_blocked ['truncated_ending']`, ce qui montre que le budget etait bien une partie du probleme
- retouche courte des prompts :
  - effet partiel utile sur `qwen2.5:7b` : disparition de `incomplete_scene`, mais `truncated_ending` et `missing_risky_decision` restent
  - regression sur `mistral-nemo` : retour d'un faux `outline_like` cote gate LLM malgre une prose narrative correcte
- correctif gate + retouche micro-decision :
  - `mistral-nemo` rerun `automation/reports/20260322_mistral_nemo_judge_gatefix` : le faux `outline_like` disparait; le seul blocage final restant est `missing_immediate_consequence`
  - `qwen2.5:7b` rerun `automation/reports/20260322_qwen2_5_7b_judge_gatefix` : `missing_risky_decision` disparait; le seul blocage final restant est `missing_immediate_consequence`
  - lecture utile : les deux modeles convergent maintenant vers le meme manque narratif, ce qui resserre fortement le prochain chantier prompt/repair
- retouche "consequence immediate observable" :
  - `qwen2.5:7b` rerun `automation/reports/20260322_qwen2_5_7b_judge_consequencefix` : `accepted` des la passe `rewrite`, sans `repair`
  - `mistral-nemo` rerun `automation/reports/20260322_mistral_nemo_judge_consequencefix` : regression vers `truncated_ending`, `missing_risky_decision`, `missing_immediate_consequence`
  - lecture utile : la contrainte commune debloque clairement la famille Qwen, mais ne generalise pas a `mistral-nemo`

## Ce qui n'est toujours pas resolu

- `qwen2.5:7b` a maintenant un chemin local `accepted`, mais `mistral-nemo` regresse si on lui applique la meme rigidite de fin de scene
- le prochain chantier n'est plus un prompt commun: il faut probablement une variante ou un profil narratif separe pour `mistral-nemo`
- le runtime remote `:8110` donne un faux sentiment de disponibilite tant que le routage utile echoue encore
