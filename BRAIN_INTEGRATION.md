# BRAIN V9 — INTEGRATION NIVEAU 3
# Directive permanente pour l agent OpenClaw

## ENDPOINTS DISPONIBLES

BASE: http://localhost:8084

### Avant chaque tache complexe
POST /api/think
{"task": "[description tache]", "context": "[contexte optionnel]"}
→ Retourne concepts pertinents, modules actifs, niveau de confiance
→ Declenche automatiquement une resonance cerebrale

### Recherche semantique simple
POST /api/query
{"question": "[question]", "top": 10}
→ Retourne concepts + mastery

### Contexte complet
POST /api/context
{"task": "...", "context": "...", "history": ["...", "..."]}
→ Retourne knowledge + co-activations entre concepts

### Apres chaque tache terminee (OBLIGATOIRE)
POST /api/feedback
{
  "task": "[description]",
  "success": true/false,
  "concepts_used": ["concept1", "concept2"]
}
→ Renforce si succes, affaiblit si echec
→ Consolide via avalanche neuronale

### Injecter un nouveau concept appris
POST /api/learn
{"topic": "[nom concept] [module]"}

### Stats cerveau
GET /api/stats
GET /api/kg

## WORKFLOW OBLIGATOIRE

1. Tache recue
        ↓
2. POST /api/think → obtenir contexte cerebral
        ↓
3. Executer la tache EN UTILISANT le contexte retourne
        ↓
4. POST /api/feedback → reinforcer les concepts utilises
        ↓
5. Si nouvelle connaissance acquise → POST /api/learn

## REGLES

- Ne jamais sauter l etape /api/think pour les taches complexes
- Toujours faire /api/feedback apres chaque tache
- Si confidence="low" → chercher plus d information avant d agir
- Si confidence="high" → le cerveau connait bien le sujet, s appuyer dessus
- Signaler si kg_total < 100 (cerveau peu nourri)
