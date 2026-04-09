# Plan de Migration — Deuxième NVMe (2 To)

## Date Prévue
- **Arrivée du disque**: Mercredi 2 avril 2026
- **Capacité**: 2 To

## Phase 1: Préparation (Actuel)
- [x] 100 Go alloués sur NVMe actuel
- [x] Structure créée (neurons, synapses, memories, models, topics, backups)
- [x] Auto-sauvegarde active (toutes les 5 min)
- [x] Configuration pour 300 Go prête

## Phase 2: Installation (Mercredi)
```bash
# Montage du nouveau disque
mkfs.ext4 /dev/nvme1n1
mkdir -p /mnt/nvme2
mount /dev/nvme1n1 /mnt/nvme2

# Migration du Brain
rsync -av /mnt/nvme/soullink_brain/ /mnt/nvme2/soullink_brain/

# Mise à jour config
# base_path -> /mnt/nvme2/soullink_brain
# target_allocation_gb -> 300
```

## Phase 3: Expansion
- **300 Go alloués** pour le cerveau
- **3 millions de neurones** max
- **30 millions de synapses** max
- **Parallélisation** de l'apprentissage (4 workers)

## Capacités Cibles
| Métrique | Actuel (100 Go) | Futur (300 Go) |
|----------|-----------------|----------------|
| Neurones max | 1,000,000 | 3,000,000 |
| Synapses max | 10,000,000 | 30,000,000 |
| Topics | ~1,000 | ~10,000 |
| Modèles | - | Embeddings, Transformers |
| Backup versions | 5 | 10 |

## Schedule de Croissance
- **Morning Peak (7h-12h)**: +50% croissance
- **Afternoon Peak (14h-18h)**: +30% croissance
- **Night (22h-6h)**: Consolidation (renforcement)
