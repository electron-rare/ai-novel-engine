# Templates utiles

Deux points d'entree selon le mode de travail :

- `STUDIO_PROJECT_TEMPLATE.md` : format Markdown importable par `app_AI-novel-engine`.
- `PLAN_TEMPLATE.docx` : document Word editable pour preparer un plan de roman ou de chapitre hors app.
- `PLAN_ROMAN_COMPLET.docx` : version longue avec actes, 12 chapitres et fiches personnages.
- `FICHE_PERSONNAGES.docx` : fiche de cast orientee desir, contradiction, pression et arcs.
- `PLAN_3_ACTES.docx` : squelette resserre autour des bascules majeures du roman.
- `PACK_ROMAN_FR.docx` : pack complet francise pour preparer un roman avant import ou generation.
- `PACK_POLAR.docx` : pack polar / thriller avec crime, soupcons, fausses pistes et revelation.
- `PACK_FANTASY.docx` : pack fantasy avec monde, magie, factions et quete.
- `PACK_LITTERAIRE.docx` : pack roman litteraire centre voix, tension fine et transformation intime.
- `PACK_SF.docx` : pack science-fiction avec hypothesis, systemes, contraintes et cout technologique.
- `PACK_ROMANTASY.docx` : pack romantasy avec tension relationnelle, pouvoir, dettes et factions.
- `PACK_HUIS_CLOS.docx` : pack huis clos avec espace contraint, pression continue et revelation par confinement.
- `PACK_IDEE_ROMAN.docx` : pack personnalisable a partir d'une idee de roman encore brute.
- `ane-workspace-template/` : squelette minimal pour le moteur CLI `ai-novel-engine`.

Repere important :

- le moteur CLI exige surtout `notes/intentions/chapitre_01.md`
- `memoire/index/personnages.json` peut etre pre-rempli pour injecter un cast de depart
- le plan de chapitre genere par ANE suit le contrat documente dans `ANE_STRUCTURE_TEMPLATE.md`
- la source regenerable du document Word est `PLAN_TEMPLATE_SOURCE.html`
- la source regenerable du document long est `PLAN_ROMAN_COMPLET_SOURCE.html`
- les autres sources regenerables sont `FICHE_PERSONNAGES_SOURCE.html`, `PLAN_3_ACTES_SOURCE.html` et `PACK_ROMAN_FR_SOURCE.html`
- les packs genre sont sources dans `PACK_POLAR_SOURCE.html`, `PACK_FANTASY_SOURCE.html` et `PACK_LITTERAIRE_SOURCE.html`
- les packs additionnels sont sources dans `PACK_SF_SOURCE.html`, `PACK_ROMANTASY_SOURCE.html`, `PACK_HUIS_CLOS_SOURCE.html` et `PACK_IDEE_ROMAN_SOURCE.html`

Exemples :

```bash
cp docs/templates/STUDIO_PROJECT_TEMPLATE.md /tmp/mon-projet.md
cp docs/templates/PLAN_TEMPLATE.docx ~/Desktop/
cp docs/templates/PLAN_ROMAN_COMPLET.docx ~/Desktop/
cp docs/templates/FICHE_PERSONNAGES.docx ~/Desktop/
cp docs/templates/PLAN_3_ACTES.docx ~/Desktop/
cp docs/templates/PACK_ROMAN_FR.docx ~/Desktop/
cp docs/templates/PACK_POLAR.docx ~/Desktop/
cp docs/templates/PACK_FANTASY.docx ~/Desktop/
cp docs/templates/PACK_LITTERAIRE.docx ~/Desktop/
cp docs/templates/PACK_SF.docx ~/Desktop/
cp docs/templates/PACK_ROMANTASY.docx ~/Desktop/
cp docs/templates/PACK_HUIS_CLOS.docx ~/Desktop/
cp docs/templates/PACK_IDEE_ROMAN.docx ~/Desktop/
cp -R docs/templates/ane-workspace-template /tmp/mon-workspace-ane
cd /tmp/mon-workspace-ane
python3 -m cli.main generate chapter --chapter 01
```

Regeneration du DOCX :

```bash
textutil -convert docx docs/templates/PLAN_TEMPLATE_SOURCE.html \
  -output docs/templates/PLAN_TEMPLATE.docx

textutil -convert docx docs/templates/PLAN_ROMAN_COMPLET_SOURCE.html \
  -output docs/templates/PLAN_ROMAN_COMPLET.docx

textutil -convert docx docs/templates/FICHE_PERSONNAGES_SOURCE.html \
  -output docs/templates/FICHE_PERSONNAGES.docx

textutil -convert docx docs/templates/PLAN_3_ACTES_SOURCE.html \
  -output docs/templates/PLAN_3_ACTES.docx

textutil -convert docx docs/templates/PACK_ROMAN_FR_SOURCE.html \
  -output docs/templates/PACK_ROMAN_FR.docx

textutil -convert docx docs/templates/PACK_POLAR_SOURCE.html \
  -output docs/templates/PACK_POLAR.docx

textutil -convert docx docs/templates/PACK_FANTASY_SOURCE.html \
  -output docs/templates/PACK_FANTASY.docx

textutil -convert docx docs/templates/PACK_LITTERAIRE_SOURCE.html \
  -output docs/templates/PACK_LITTERAIRE.docx

textutil -convert docx docs/templates/PACK_SF_SOURCE.html \
  -output docs/templates/PACK_SF.docx

textutil -convert docx docs/templates/PACK_ROMANTASY_SOURCE.html \
  -output docs/templates/PACK_ROMANTASY.docx

textutil -convert docx docs/templates/PACK_HUIS_CLOS_SOURCE.html \
  -output docs/templates/PACK_HUIS_CLOS.docx

textutil -convert docx docs/templates/PACK_IDEE_ROMAN_SOURCE.html \
  -output docs/templates/PACK_IDEE_ROMAN.docx
```
