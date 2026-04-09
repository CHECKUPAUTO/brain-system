# SoulLink Brain v7.0 — Backup

## Archive
- **Fichier**: `brain_v7_backup.tar.gz` (12 KB)
- **Date**: 2026-03-30 15:02
- **Version**: 7.0.0

## Contenu

| Fichier | Description | Taille |
|---------|-------------|--------|
| `brain_v7.py` | Code principal LIF + Hebbian + STDP | 28 KB |
| `config.json` | Configuration des paramètres | 1 KB |
| `README.md` | Documentation complète | 2 KB |
| `VERSIONS.md` | Historique des versions | 1 KB |
| `start.sh` | Script de lancement | 0.5 KB |

## Caractéristiques v7.0

### Modèle Neuronal (LIF)
- Potentiel de repos: -70 mV
- Seuil d'action: -55 mV
- Constante membranaire: 20 ms
- Période réfractaire: 3 ms

### Apprentissage Synaptique
- **Hebbian**: Δw = η × pre × post × (1 - |w|)
- **STDP**: Spike-Timing-Dependent Plasticity
- **Weight Decay**: 0.1% par cycle

### Modules (187 neurones)
- Perception, Memory, Reasoning, Learning, Attention
- Output, Language, Vision, Audio, Motor

### Visualisation
- Canvas HTML5
- Oscilloscopes par module
- Propagation des signaux animée
- Stats temps réel (Hz, spikes, learning)

## Lancement

```bash
tar -xzf brain_v7_backup.tar.gz
cd brain_v7_20260330_150245
./start.sh
```

## API

| Endpoint | Description |
|----------|-------------|
| `/` | Interface graphique |
| `/api/brain` | Données complètes |
| `/api/status` | Stats basiques |
| `/api/learning` | Stats apprentissage |

---

*Sauvegarde créée le 2026-03-30*