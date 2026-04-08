#!/bin/bash
# SoulLink Brain Mesh — Lancement de tous les cerveaux
# Usage: bash brain_mesh_launch.sh [start|stop|status|restart]

BRAIN_DIR="/mnt/nvme/soullink_brain"
CONFIG="$BRAIN_DIR/brain_v10_config.py"
ORCH="$BRAIN_DIR/brain_orchestrator.py"
LOG_DIR="/mnt/nvme_secondary/openclaw/workspace/logs"
mkdir -p "$LOG_DIR"

BRAINS=("science:9010" "mind:9011" "engineer:9012" "crypto:9013" "creative:9014" "meta:9015")
ORCH_PORT=9020

start_brain() {
    local name=$1
    local port=$2
    echo "Demarrage Brain-$name sur port $port..."
    nohup python3 "$CONFIG" --brain "$name" \
        > "$LOG_DIR/brain_${name}.log" 2>&1 &
    echo $! > "/tmp/brain_${name}.pid"
    echo "  PID: $!"
}

start_orchestrator() {
    echo "Demarrage Orchestrateur sur port $ORCH_PORT..."
    nohup python3 "$ORCH" --port $ORCH_PORT \
        > "$LOG_DIR/orchestrator.log" 2>&1 &
    echo $! > "/tmp/brain_orchestrator.pid"
    echo "  PID: $!"
}

stop_brain() {
    local name=$1
    local pid_file="/tmp/brain_${name}.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        kill $pid 2>/dev/null && echo "Brain-$name (PID $pid) arrete"
        rm -f "$pid_file"
    else
        # Chercher par port
        local port=$(echo "${BRAINS[@]}" | tr ' ' '\n' | grep "^$name:" | cut -d: -f2)
        kill $(lsof -ti:$port) 2>/dev/null && echo "Brain-$name arrete"
    fi
}

status_all() {
    echo "=== Etat du Mesh Brain ==="
    for entry in "${BRAINS[@]}"; do
        name="${entry%%:*}"
        port="${entry##*:}"
        result=$(curl -s --max-time 2 "http://localhost:$port/api/stats" 2>/dev/null)
        if [ -n "$result" ]; then
            N=$(echo $result | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('N',0))" 2>/dev/null)
            hz=$(echo $result | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('hz',0))" 2>/dev/null)
            echo "  Brain-$name :$port → N=$N hz=$hz ✅"
        else
            echo "  Brain-$name :$port → OFFLINE ❌"
        fi
    done
    # Orchestrateur
    orch=$(curl -s --max-time 2 "http://localhost:$ORCH_PORT/" 2>/dev/null)
    if [ -n "$orch" ]; then
        echo "  Orchestrateur :$ORCH_PORT → ✅"
    else
        echo "  Orchestrateur :$ORCH_PORT → OFFLINE ❌"
    fi
}

case "${1:-start}" in
    start)
        echo "=== Lancement SoulLink Brain Mesh ==="
        # Brain-Science déjà actif sur 9010 via systemd, on saute
        for entry in "${BRAINS[@]}"; do
            name="${entry%%:*}"
            port="${entry##*:}"
            if [ "$name" = "science" ]; then
                echo "Brain-science déjà actif (brain-v10.service)"
                continue
            fi
            # Tuer si déjà en cours
            kill $(lsof -ti:$port) 2>/dev/null
            sleep 1
            start_brain "$name" "$port"
            sleep 2
        done
        sleep 3
        start_orchestrator
        echo ""
        echo "Attente 30s pour stabilisation..."
        sleep 30
        status_all
        ;;
    stop)
        echo "=== Arret du Mesh Brain ==="
        for entry in "${BRAINS[@]}"; do
            name="${entry%%:*}"
            port="${entry##*:}"
            [ "$name" = "science" ] && continue  # géré par systemd
            kill $(lsof -ti:$port) 2>/dev/null && echo "Brain-$name arrete"
        done
        kill $(lsof -ti:$ORCH_PORT) 2>/dev/null && echo "Orchestrateur arrete"
        ;;
    status)
        status_all
        ;;
    restart)
        $0 stop
        sleep 3
        $0 start
        ;;
    *)
        echo "Usage: $0 [start|stop|status|restart]"
        ;;
esac
