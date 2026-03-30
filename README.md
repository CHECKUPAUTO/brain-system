# SoulLink Brain System

> Système cérébral neuronal distribué avec visualisation 3D, apprentissage Hebbian, et persistance

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOULLINK BRAIN SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │  Brain v8.4  │────▶│  TRIBE Brain │────▶│  MSA Server  │     │
│  │  (Port 8084)  │     │  (Port 7440) │     │  (Port 7430) │     │
│  │              │     │              │     │              │     │
│  │ Visualisation│     │ Intelligence │     │  Stockage    │     │
│  │ 3D Neurones  │     │ RAG + Memory │     │  Embeddings  │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    PERSISTENCE LAYER                      │    │
│  │  brain_persistence.py  │  auto_save.py  │  brain.py      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Composants

### Brain v8.4 — Visualisation 3D (Port 8084)

Visualisation temps réel des neurones avec simulation LIF:

- 10 modules cérébraux (perception, memory, reasoning, learning, etc.)
- Neurones animés (spike, glow, normal)
- Signaux inter-modules animés (particules)
- HUD temps réel (N, spikes, synapses, Hz, growth)
- Interactions: Drag, Scroll, Click
- Auto-grow: ajout automatique de neurones
- **Persistance**: Sauvegarde automatique toutes les 30s

```bash
python brain_v8_4_ultimate.py --port 8084
```

### Brain v7.0 — Apprentissage (Backup)

Version avec apprentissage neuronal réel:

- LIF (Leaky Integrate-and-Fire)
- Hebbian Learning: Δw = η × pre × post
- STDP (Spike-Timing-Dependent Plasticity)
- Renforcement synaptique automatique

```bash
python brain_v7.py --port 8084
```

### TRIBE Brain (Port 7440)

Serveur intelligence avec RAG intégré:

- Embeddings BGE-M3 (20004 dimensions + brain_dims)
- Recherche sémantique avec brain_weight
- Indexation textes/fichiers
- Détection d'hallucinations
- Charge cognitive calculée

```bash
python tribe_msa_server.py --port 7440
```

### MSA Server (Port 7430)

Stockage distribué des embeddings:

- Leaf node pour TRIBE
- FAISS index
- SQLite metadata

```bash
python tribe_msa_server.py --port 7430
```

## Installation

```bash
# Dépendances
pip install flask numpy

# Lancer Brain v8.4
python brain_v8/brain_v8_4_ultimate.py --port 8084

# Lancer TRIBE Brain
python tribe/tribe_msa_server.py --port 7440

# Lancer MSA Server
python tribe/tribe_msa_server.py --port 7430
```

## API Endpoints

### Brain v8.4

| Endpoint | Description |
|----------|-------------|
| `GET /` | Interface 3D |
| `GET /api/brain` | État complet du brain |
| `GET /api/stats` | Stats (neurones, spikes, etc.) |

### TRIBE Brain

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /info` | Informations système |
| `POST /embed` | Créer embeddings |
| `POST /search` | Recherche sémantique |
| `POST /index/text` | Indexer texte |
| `POST /index/file` | Indexer fichier |
| `POST /hallucination` | Détecter hallucinations |
| `POST /evaluate` | Évaluer réponse |

## Persistance

Les données sont sauvegardées dans:

```
/mnt/nvme/soullink_brain/
├── brain_state.json      # État Brain (neurones, growth, spikes)
├── neurons/              # Neurones par module
├── synapses/             # Synapses
├── memories/             # Mémoires
└── backups/              # Backups automatiques
```

## Modules Cérébraux

| Module | Neurones | Fonction |
|--------|-----------|----------|
| perception | 20 | Entrée sensorielle |
| memory | 28 | Mémoire à long terme |
| reasoning | 22 | Raisonnement logique |
| learning | 16 | Apprentissage |
| attention | 12 | Attention sélective |
| output | 14 | Sortie motrice |
| language | 18 | Traitement langage |
| vision | 15 | Vision |
| audio | 12 | Audio |
| motor | 10 | Contrôle moteur |

## Paramètres LIF

```python
V_REST = -70.0    # Potentiel de repos (mV)
V_THRESH = -55.0  # Seuil de décharge (mV)
V_RESET = -75.0   # Potentiel de reset (mV)
TAU_M = 20.0      # Constante membranaire (ms)
T_REFRAC = 3.0    # Période réfractaire (ms)
DT = 0.5           # Pas de temps (ms)
```

## Licence

MIT

## Auteur

SoulLink Team
