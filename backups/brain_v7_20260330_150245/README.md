# SoulLink Brain v7.0 — LIF + Hebbian + STDP

## Caractéristiques

### Modèle Neuronal
- **LIF (Leaky Integrate-and-Fire)**: Modèle biologique réaliste
- **Potentiel membranaire**: V_REST = -70mV, V_THRESH = -55mV
- **Période réfractaire**: 3ms après chaque spike
- **Propagation synaptique**: Signaux visuels sur les connexions

### Apprentissage Synaptique
1. **Hebbian Learning**: Δw = η × pre × post × (1 - |w|)
2. **STDP**: Spike-Timing-Dependent Plasticity
3. **Weight Decay**: Décroissance automatique (0.1%)
4. **Poids dynamiques**: 0.05 → 1.0

### Modules Cognitifs (10)
- Perception (20 neurones)
- Memory (28 neurones)
- Reasoning (22 neurones)
- Learning (16 neurones)
- Attention (12 neurones)
- Output (14 neurones)
- Language (18 neurones)
- Vision (15 neurones)
- Audio (12 neurones)
- Motor (10 neurones)

## Lancement

```bash
python3 brain_v7.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Interface graphique |
| `/api/brain` | Données complètes (neurones, synapses, modules) |
| `/api/status` | Stats basiques |
| `/api/learning` | Stats d'apprentissage |

## Paramètres Modifiables

Dans le code Python:
- `HEBBIAN_LR`: Taux d'apprentissage Hebbian (default: 0.01)
- `STDP_LR`: Taux STDP (default: 0.02)
- `STDP_WINDOW`: Fenêtre temporelle STDP en ms (default: 20.0)
- `WEIGHT_DECAY`: Décroissance des poids (default: 0.001)

## Visualisation

- **Neurones excitateurs**: Couleur du module
- **Neurones inhibiteurs**: Rouge avec croix
- **Spikes**: Glow blanc + anneau cyan
- **Signaux**: Points qui voyagent sur les synapses
- **Oscilloscopes**: Activité par module (6s)

## Auteur

SoulLink Brain - 2026-03-30
