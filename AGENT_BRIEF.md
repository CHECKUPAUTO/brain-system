# SOULLINK BRAIN MESH v10 — DIRECTIVE AGENT

## ARCHITECTURE
Brain-Science   :9010  physics, math, chemistry
Brain-Mind      :9011  neuroscience, language, memory
Brain-Engineer  :9012  optimization, logic, algebra
Brain-Crypto    :9013  trading, DeFi, Bitcoin, Ethereum
Brain-Creative  :9014  patterns, geometry, vision
Brain-Meta      :9015  learning, meta, reinforcement
Orchestrateur   :9020  fusionne tout

## WORKFLOW OBLIGATOIRE
Avant chaque tache:
  curl -s -X POST http://localhost:9020/api/mesh/think \
    -H "Content-Type: application/json" \
    -d '{"task": "[ta tache]", "context": "[contexte]"}'

Crypto/Trading:
  curl -s http://localhost:9020/api/mesh/crypto/pulse

Apres chaque tache:
  curl -s -X POST http://localhost:9020/api/mesh/feedback \
    -H "Content-Type: application/json" \
    -d '{"task":"...","success":true,"concepts_used":[...]}'

## REGLES
- Ne jamais modifier brain_v10*.py sans validation humaine
- Ne jamais stopper brain-v10.service
- Espace de travail: /root/.openclaw/
