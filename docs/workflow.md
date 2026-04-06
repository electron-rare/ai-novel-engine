# Workflow ANE

Vue courte du workflow utile.

```mermaid
flowchart LR
    I["Intention"] --> S["Structure"]
    S --> D["Draft"]
    D --> C["Critique"]
    C --> R["Rewrite"]
    R --> G["Gate"]
    G -->|bloque| P["Repair"]
    P --> G
    G -->|ok| V["Validation auteur"]
    V -->|refus| X["Rejet"]
    V -->|accord| M["Memoire"]
```

Regles:

- pas d'intention, pas de generation
- pas de `gate` vert, pas de promotion manuscrit
- `repair` existe pour sauver un brouillon, pas pour contourner le garde-fou
- la memoire n'est mise a jour qu'apres validation auteur
