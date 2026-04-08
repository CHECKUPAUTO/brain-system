# SoulLink Brain v9 — Mathematical Singularity

## Architecture
- 24 modules cérébraux (perception, memory, reasoning, physics, neuroscience...)
- JAX GPU vectorisé (RTX 4060) + fallback CPU
- STDP + Hebbian plasticity + neuronal avalanches
- Sleep consolidation + metacognition
- Wikipedia/arXiv/GitHub/PubMed autonomous crawler
- Knowledge Graph persistant (396+ concepts)
- Agent integration API (Niveau 3)

## Démarrage
```bash
systemctl start brain-v9      # Cerveau
systemctl start brain-crawler # Crawler autonome
```

## API
- GET  /api/stats
- GET  /api/kg
- POST /api/learn    {"topic": "..."}
- POST /api/query    {"question": "..."}
- POST /api/think    {"task": "...", "context": "..."}
- POST /api/feedback {"task": "...", "success": true, "concepts_used": [...]}
- POST /api/context  {"task": "...", "context": "...", "history": [...]}

## Stats actuelles
- ~2500 neurones actifs
- 396 concepts dans le KG
- JAX GPU backend
