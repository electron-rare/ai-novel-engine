# ANE Runner Contract v1 - 23 mars 2026

Contrat canonique du pont entre `ai-novel-engine` et ses clients applicatifs, en priorite `app_AI-novel-engine`.

## But

Sortir d'un couplage implicite ou un client:

- prepare lui-meme l'arborescence interne d'ANE
- lance `python3 -m cli.main` avec des hypotheses de layout
- parse directement `meta.json` et les cles `artifacts.*`

Le contrat `v1` introduit une frontiere stable:

- une commande runner stable
- une requete JSON stable
- un resultat JSON stable

## Perimetre

Le contrat couvre:

- lancement d'un run de chapitre depuis un client
- passage du contexte auteurial utile au moteur
- restitution d'un resultat lisible sans parser les artefacts internes

Le contrat ne couvre pas:

- le protocole runtime OpenAI-compatible
- les details internes de `meta.json`
- le layout complet du workspace ANE
- le contenu exact des prompts narratifs

## Acteurs et responsabilites

### Client ANE

Le client possede:

- l'UI
- le modele de projet local
- le Keychain et les secrets locaux
- la decision de lancer un run

Le client ne possede pas:

- le layout interne du workspace ANE
- la selection de l'artefact final candidat via `repair_latest` ou `draft_v2`
- la lecture directe de `meta.json` comme contrat public

### ANE Runner

Le runner possede:

- la traduction de la requete en workspace ANE
- l'appel au pipeline auteurial
- la selection du brouillon candidat
- la production du resultat public versionne

### Runtime

Le runtime reste hors contrat runner. Il est deja borne par le contrat OpenAI-compatible documente ailleurs.

## Surface stable

Commande cible:

```bash
python3 -m cli.main runner execute \
  --request /path/to/ane_runner_request_v1.json \
  --result /path/to/ane_runner_result_v1.json
```

Compatibilite transitoire:

- tant que cette commande n'est pas implementee, le pont historique `generate chapter --chapter XX` reste un mode legacy
- ce mode legacy ne doit plus etre etendu comme contrat public

## Requete v1

Nom logique: `ane_runner_request_v1.json`

Champs obligatoires:

| Champ | Type | Role |
|------|------|------|
| `contract_version` | `string` | doit valoir `ane-runner-v1` |
| `chapter` | `string` | identifiant normalisable du chapitre, ex. `01` |
| `project` | `object` | metadonnees auteuriales minimales |
| `scene` | `object` | scene cible ou intention locale |
| `runtime` | `object` | provider, base URL, modele, budgets utiles |
| `execution` | `object` | politique de validation et mode workspace |

Champs optionnels:

| Champ | Type | Role |
|------|------|------|
| `request_id` | `string` | correlation client |
| `locked_history` | `array` | scenes/chapitres precedents verrouilles utiles au contexte |
| `characters` | `array` | personnages structures |
| `world_state` | `object` | lieux, chronologie, index annexes |
| `workspace_override` | `string` | racine explicite si le client force un workspace |

Exemple minimal:

```json
{
  "contract_version": "ane-runner-v1",
  "request_id": "studio-7B5A4D6E",
  "chapter": "01",
  "project": {
    "title": "Projet local",
    "genre": "roman",
    "logline": "Une arrivee de nuit force une decision risquee.",
    "synopsis": "Projet de fiction longue.",
    "writer_note": "Style direct, phrases courtes."
  },
  "scene": {
    "title": "Arrivee de nuit",
    "objective": "Trouver l'indice puis agir",
    "beat": "Monter la tension jusqu'a la decision",
    "mood": "sobre",
    "target_words": 900
  },
  "runtime": {
    "provider": "openai_compatible",
    "base_url": "http://127.0.0.1:8100",
    "model": "mistral:mistral-large-latest"
  },
  "execution": {
    "approval_mode": "approve",
    "workspace_mode": "temporary"
  }
}
```

## Resultat v1

Nom logique: `ane_runner_result_v1.json`

Le resultat est le seul contrat public de sortie pour un client.

Champs obligatoires:

| Champ | Type | Role |
|------|------|------|
| `contract_version` | `string` | doit valoir `ane-runner-v1` |
| `status` | `string` | `accepted`, `rejected`, `awaiting_acceptance`, `quality_blocked` ou `failed` |
| `chapter` | `string` | chapitre normalise |
| `workspace_path` | `string` | workspace du run |
| `draft_path` | `string` | brouillon candidat retenu par ANE |
| `gate_path` | `string` | rapport de gate public pour le run |
| `meta_path` | `string` | artefact legacy encore expose pendant la transition |
| `model_used` | `string` | modele reellement utilise si connu |

Champs optionnels:

| Champ | Type | Role |
|------|------|------|
| `manuscript_path` | `string|null` | manuscrit promu si `accepted` |
| `quality_blockers` | `array` | blockers de garde-fou si presents |
| `error` | `object` | detail machine lisible si echec |
| `artifacts` | `object` | manifeste public restreint des chemins utiles |

Exemple:

```json
{
  "contract_version": "ane-runner-v1",
  "status": "accepted",
  "chapter": "chapitre_01",
  "workspace_path": "/tmp/ane-run-123",
  "draft_path": "/tmp/ane-run-123/brouillons/chapitres/chapitre_01/repair_v1.md",
  "gate_path": "/tmp/ane-run-123/brouillons/chapitres/chapitre_01/gate_v1.json",
  "meta_path": "/tmp/ane-run-123/brouillons/chapitres/chapitre_01/meta.json",
  "manuscript_path": "/tmp/ane-run-123/manuscrit/chapitre_01.md",
  "model_used": "mistral:mistral-large-latest",
  "quality_blockers": []
}
```

## Regles de compatibilite

- `draft_path` est choisi par ANE; le client ne decide pas entre `draft_v2` et `repair_latest`
- `meta_path` reste expose seulement comme artefact legacy de transition
- un client ne doit pas parser `meta.json` pour reconstruire le contrat public
- un client ne doit pas supposer l'existence de `brouillons/chapitres/...` ni de `memoire/index/...`
- l'ajout de nouveaux champs est autorise en `v1` tant qu'ils sont optionnels
- toute suppression ou reinterpretation d'un champ obligatoire exige `v2`

## Migration depuis le pont legacy

Etat actuel:

- le Studio prepare un workspace ANE lui-meme
- le Studio lance `python3 -m cli.main generate chapter --chapter XX --approve`
- le Studio parse `meta.json`

Migration cible:

1. ANE ajoute `runner execute` et ecrit `ane_runner_result_v1.json`
2. le Studio construit `ane_runner_request_v1.json` au lieu d'ecrire l'arborescence ANE
3. le Studio lit uniquement `ane_runner_result_v1.json`
4. `meta.json` redevient un artefact interne et de debug

## Tests minimaux a exiger

### Cote ANE

- test de normalisation du `chapter`
- test d'emission du resultat `v1`
- test de stabilite des champs obligatoires
- test d'echec avec `status=failed` et `error` renseigne

### Cote client

- test de serialisation de la requete `v1`
- test de decodage du resultat `v1`
- test de non-regression: aucun parse direct de `meta.json`

## Decision de gouvernance

Le contrat canonique vit dans `ai-novel-engine`.

- un client peut l'importer, le citer ou le dupliquer
- le texte source de verite reste cote `ai-novel-engine`
