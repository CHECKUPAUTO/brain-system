#!/bin/bash
# SoulLink Brain v7.0 Launcher

echo "🧠 SoulLink Brain v7.0 — LIF + Hebbian + STDP"
echo "⚡ Démarrage..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non installé"
    exit 1
fi

# Vérifier Flask
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installation Flask..."
    pip install flask
fi

# Lancer
python3 brain_v7.py

