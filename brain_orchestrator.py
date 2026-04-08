#!/usr/bin/env python3
"""
SoulLink Brain Orchestrateur
Consulte les 6 cerveaux en parallèle et fusionne les réponses
"""
import threading, time, json, urllib.request, urllib.error
from flask import Flask, jsonify, request
from pathlib import Path

# ── Config cerveaux ───────────────────────────────────────────────────────────

BRAINS = {
    "science":  {"port": 9010, "url": "http://localhost:9010", "speciality": ["physics","math","chemistry","computation"]},
    "mind":     {"port": 9011, "url": "http://localhost:9011", "speciality": ["neuroscience","language","philosophy","memory"]},
    "engineer": {"port": 9012, "url": "http://localhost:9012", "speciality": ["optimization","logic","algebra","computation"]},
    "crypto":   {"port": 9013, "url": "http://localhost:9013", "speciality": ["trading","blockchain","defi","markets","crypto","finance","bitcoin","ethereum"]},
    "creative": {"port": 9014, "url": "http://localhost:9014", "speciality": ["patterns","geometry","art","vision","design"]},
    "meta":     {"port": 9015, "url": "http://localhost:9015", "speciality": ["learning","optimization","meta","reinforcement"]},
}

SHARED_KG = Path("/mnt/nvme/soullink_brain/mesh/shared_kg.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _call(brain_key, endpoint, method="GET", data=None, timeout=3):
    """Appel HTTP vers un cerveau."""
    url = BRAINS[brain_key]["url"] + endpoint
    try:
        payload = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type":"application/json"} if payload else {},
            method=method
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e), "brain": brain_key}

def _call_parallel(endpoint, method="GET", data=None, brain_keys=None):
    """Appelle plusieurs cerveaux en parallèle."""
    keys = brain_keys or list(BRAINS.keys())
    results = {}
    threads = []

    def fetch(key):
        results[key] = _call(key, endpoint, method, data)

    for key in keys:
        t = threading.Thread(target=fetch, args=(key,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=5)

    return results

def _select_brains(query):
    """Sélectionne les cerveaux les plus pertinents selon la query."""
    query_lower = query.lower()
    scores = {}
    for key, cfg in BRAINS.items():
        score = sum(1 for kw in cfg["speciality"] if kw in query_lower)
        scores[key] = score
    # Toujours inclure le meta-cerveau
    scores["meta"] = scores.get("meta", 0) + 0.5
    # Retourner top 3 + meta
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    selected = list(set([k for k,_ in top] + ["meta"]))
    return selected

def _merge_concepts(results):
    """Fusionne les concepts de plusieurs cerveaux, déduplique et trie."""
    all_concepts = {}
    for brain_key, result in results.items():
        if "error" in result: continue
        for c in result.get("top_concepts", []):
            concept = c["concept"]
            if concept not in all_concepts or c["score"] > all_concepts[concept]["score"]:
                all_concepts[concept] = {**c, "source_brain": brain_key}
    return sorted(all_concepts.values(), key=lambda x: x["score"], reverse=True)[:20]

def _aggregate_confidence(results):
    """Calcule la confiance agrégée."""
    confidences = [r.get("confidence","low") for r in results.values() if "confidence" in r]
    if not confidences: return "low"
    weights = {"high":3,"medium":2,"low":1}
    avg = sum(weights.get(c,1) for c in confidences) / len(confidences)
    return "high" if avg >= 2.5 else "medium" if avg >= 1.5 else "low"

# ── Flask Orchestrateur ───────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/api/mesh/status")
def mesh_status():
    """État de tous les cerveaux."""
    results = _call_parallel("/api/stats")
    mesh = {}
    total_N = total_syn = 0
    for key, r in results.items():
        if "error" not in r:
            mesh[key] = {"N":r.get("N",0),"hz":r.get("hz",0),"syn":r.get("syn",0),"kg":r.get("kg_concepts",0),"port":BRAINS[key]["port"]}
            total_N   += r.get("N",0)
            total_syn += r.get("syn",0)
        else:
            mesh[key] = {"status":"offline","error":r["error"],"port":BRAINS[key]["port"]}
    # KG partagé
    try:
        shared = json.load(open(SHARED_KG))
        shared_concepts = len(shared.get("nodes",{}))
    except: shared_concepts = 0

    return jsonify({
        "ok": True,
        "mesh": mesh,
        "total": {"N":total_N,"syn":total_syn,"brains":len([v for v in mesh.values() if "hz" in v]),"shared_kg":shared_concepts},
        "ts": time.strftime("%H:%M:%S")
    })

@app.route("/api/mesh/think", methods=["POST"])
def mesh_think():
    """Consulte les cerveaux pertinents en parallele et fusionne."""
    data = request.get_json() or {}
    task    = data.get("task","")
    context = data.get("context","")
    if not task: return jsonify({"ok":False,"error":"no task"})

    # Sélectionner cerveaux pertinents
    selected = _select_brains(task + " " + context)
    payload  = {"task":task,"context":context}

    # Appel parallèle
    results = _call_parallel("/api/think", method="POST", data=payload, brain_keys=selected)

    # Fusion
    merged_concepts = _merge_concepts(results)
    confidence = _aggregate_confidence(results)

    # Meilleurs modules par cerveau
    brain_insights = []
    for key, r in results.items():
        if "error" not in r and r.get("best_modules"):
            brain_insights.append({
                "brain": key,
                "confidence": r.get("confidence","low"),
                "best_module": r["best_modules"][0]["module"] if r["best_modules"] else "?",
                "suggestion": r.get("suggestion",""),
                "N": r.get("brain_state",{}).get("N",0),
                "hz": r.get("brain_state",{}).get("hz",0),
            })

    return jsonify({
        "ok": True,
        "task": task,
        "brains_consulted": selected,
        "confidence": confidence,
        "concepts_found": len(merged_concepts),
        "top_concepts": merged_concepts[:10],
        "brain_insights": brain_insights,
        "suggestion": f"Cerveaux {', '.join(selected)} consultés",
    })

@app.route("/api/mesh/learn", methods=["POST"])
def mesh_learn():
    """Broadcast un concept vers les cerveaux pertinents."""
    data  = request.get_json() or {}
    topic = data.get("topic","").strip()
    if not topic: return jsonify({"ok":False,"error":"no topic"})

    selected = _select_brains(topic)
    payload  = {"topic":topic}
    results  = _call_parallel("/api/learn", method="POST", data=payload, brain_keys=selected)

    total_neurons = sum(r.get("new_neurons",0) for r in results.values() if "error" not in r)
    return jsonify({
        "ok": True,
        "topic": topic,
        "brains_updated": selected,
        "total_new_neurons": total_neurons,
        "details": {k:r for k,r in results.items() if "error" not in r}
    })

@app.route("/api/mesh/query", methods=["POST"])
def mesh_query():
    """Recherche semantique sur tous les cerveaux."""
    data     = request.get_json() or {}
    question = data.get("question","")
    if not question: return jsonify({"ok":False,"error":"no question"})

    selected = _select_brains(question)
    payload  = {"question":question,"top":10}
    results  = _call_parallel("/api/query", method="POST", data=payload, brain_keys=selected)
    merged   = _merge_concepts(results)

    return jsonify({
        "ok": True,
        "question": question,
        "brains_queried": selected,
        "concepts_found": len(merged),
        "top_concepts": merged[:15],
        "shared_kg_size": len(json.load(open(SHARED_KG)).get("nodes",{})) if SHARED_KG.exists() else 0,
    })

@app.route("/api/mesh/feedback", methods=["POST"])
def mesh_feedback():
    """Feedback broadcast vers les cerveaux pertinents."""
    data = request.get_json() or {}
    task    = data.get("task","")
    success = data.get("success",True)
    concepts= data.get("concepts_used",[])

    selected = _select_brains(task + " " + " ".join(concepts))
    payload  = {"task":task,"success":success,"concepts_used":concepts}
    results  = _call_parallel("/api/feedback", method="POST", data=payload, brain_keys=selected)

    return jsonify({"ok":True,"success":success,"brains_updated":selected,"results":{k:r for k,r in results.items() if "error" not in r}})

@app.route("/api/mesh/sync")
def mesh_sync():
    """Force synchronisation du KG partagé entre tous les cerveaux."""
    # Lire tous les KGs
    all_nodes = {}
    for key in BRAINS:
        r = _call(key, "/api/kg")
        if "nodes" in r:
            for concept, info in r["nodes"]:
                if concept not in all_nodes or info.get("mastery",0) > all_nodes.get(concept,{}).get("mastery",0):
                    all_nodes[concept] = info

    # Sauvegarder KG partagé
    try:
        shared = {"nodes":all_nodes,"edges":{}}
        with open(SHARED_KG,"w") as f: json.dump(shared, f)
        synced = len(all_nodes)
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

    return jsonify({"ok":True,"shared_concepts":synced,"msg":"KG synchronise entre tous les cerveaux"})

@app.route("/api/mesh/crypto/pulse")
def crypto_pulse():
    """Etat special du cerveau crypto — marchés + sentiment."""
    r = _call("crypto", "/api/stats")
    kg = _call("crypto", "/api/kg")
    if "error" in r:
        return jsonify({"ok":False,"error":"Brain-Crypto offline"})

    # Concepts crypto les plus maîtrisés
    top_concepts = sorted(
        [(k,v) for k,v in (kg.get("nodes") or [])],
        key=lambda x: x[1].get("mastery",0),
        reverse=True
    )[:10] if kg.get("nodes") else []

    return jsonify({
        "ok": True,
        "brain": "Brain-Crypto",
        "N": r.get("N",0),
        "hz": r.get("hz",0),
        "kg_concepts": r.get("kg_concepts",0),
        "top_concepts": [{"concept":k,"mastery":round(v.get("mastery",0),3),"module":v.get("module","?")} for k,v in top_concepts],
        "ts": time.strftime("%H:%M:%S")
    })

@app.route("/")
def index():
    return jsonify({
        "name": "SoulLink Brain Orchestrateur",
        "version": "1.0",
        "brains": list(BRAINS.keys()),
        "endpoints": [
            "GET  /api/mesh/status",
            "POST /api/mesh/think",
            "POST /api/mesh/learn",
            "POST /api/mesh/query",
            "POST /api/mesh/feedback",
            "GET  /api/mesh/sync",
            "GET  /api/mesh/crypto/pulse",
        ]
    })

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9020)
    args = parser.parse_args()
    print(f"\nOrchestrator SoulLink Brain — port {args.port}")
    print(f"Cerveaux: {list(BRAINS.keys())}")
    app.run(host="0.0.0.0", port=args.port, threaded=True)
