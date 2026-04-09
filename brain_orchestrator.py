#!/usr/bin/env python3
"""
SoulLink Brain Orchestrateur v2 — AUTO-SPAWN
Consulte les cerveaux en parallèle, fusionne, et crée automatiquement
de nouveaux cerveaux spécialisés selon les besoins détectés.
"""
import threading, time, json, urllib.request, subprocess, os, random, hashlib
from flask import Flask, jsonify, request
from pathlib import Path
from collections import defaultdict, deque

# ── Config cerveaux connus ────────────────────────────────────────────────────

BRAINS_REGISTRY_FILE = Path("/mnt/nvme/soullink_brain/mesh/brains_registry.json")
SHARED_KG            = Path("/mnt/nvme/soullink_brain/mesh/shared_kg.json")
SPAWN_LOG            = Path("/root/.openclaw/workspace/logs/spawn_log.jsonl")
BRAIN_DIR            = Path("/mnt/nvme/soullink_brain")

# Cerveaux de base
DEFAULT_BRAINS = {
    "science":  {"port":9010,"url":"http://localhost:9010","speciality":["physics","math","chemistry","computation","science"],"version":"v10"},
    "mind":     {"port":9011,"url":"http://localhost:9011","speciality":["neuroscience","language","philosophy","memory","mind","consciousness"],"version":"v10"},
    "engineer": {"port":9012,"url":"http://localhost:9012","speciality":["optimization","logic","algebra","computation","engineering","algorithm"],"version":"v10"},
    "crypto":   {"port":9013,"url":"http://localhost:9013","speciality":["trading","blockchain","defi","markets","crypto","finance","bitcoin","ethereum","token"],"version":"v10"},
    "creative": {"port":9014,"url":"http://localhost:9014","speciality":["patterns","geometry","art","vision","design","creative","music"],"version":"v10"},
    "meta":     {"port":9015,"url":"http://localhost:9015","speciality":["learning","optimization","meta","reinforcement","self-improvement"],"version":"v10"},
}

# ── Registry dynamique ────────────────────────────────────────────────────────

def _load_registry():
    try:
        if BRAINS_REGISTRY_FILE.exists():
            with open(BRAINS_REGISTRY_FILE) as f:
                return json.load(f)
    except Exception: pass
    return dict(DEFAULT_BRAINS)

def _save_registry(registry):
    BRAINS_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BRAINS_REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)

BRAINS = _load_registry()

# ── Intelligence d'auto-spawn ─────────────────────────────────────────────────

class SpawnIntelligence:
    """
    Analyse les patterns de requêtes et décide de créer de nouveaux cerveaux.

    Triggers:
    1. LOW_CONFIDENCE: >15 requêtes avec confidence "low" en 1h sur un domaine
    2. COVERAGE_GAP: un concept revient >20x dans les requêtes mais aucun cerveau
       ne le couvre avec mastery > 0.3
    3. SATURATION: un cerveau dépasse 45000 neurones
    4. EXPLICIT: l'agent demande explicitement via /api/mesh/spawn
    5. KNOWLEDGE_EXPLOSION: le KG partagé dépasse 1000 nouveaux concepts en 24h
    """

    def __init__(self):
        self.query_history   = deque(maxlen=1000)  # (ts, query, confidence, concepts)
        self.domain_misses   = defaultdict(int)    # domaine → nb de low confidence
        self.concept_counts  = defaultdict(int)    # concept → nb apparitions
        self.spawned_today   = []
        self._lock           = threading.Lock()
        self._next_port      = self._find_next_port()

        # Domaines connus avec leurs modules associés
        self.domain_modules = {
            "medical":    ["anatomy","physiology","pharmacology","diagnosis","treatment","medicine"],
            "legal":      ["law","contract","regulation","compliance","court","legal"],
            "astronomy":  ["cosmology","astrophysics","telescope","galaxy","star","planet"],
            "biology":    ["genetics","evolution","ecology","cell","dna","protein"],
            "psychology": ["cognition","behavior","therapy","emotion","personality","motivation"],
            "economics":  ["macroeconomics","microeconomics","market","gdp","inflation","monetary"],
            "history":    ["historical","civilization","war","politics","empire","revolution"],
            "climate":    ["environment","carbon","temperature","ecosystem","renewable","energy"],
            "robotics":   ["actuator","sensor","control","automation","kinematics","ros"],
            "security":   ["cybersecurity","vulnerability","exploit","encryption","firewall","threat"],
            "quantum":    ["qubit","superposition","entanglement","decoherence","quantum_computing"],
            "materials":  ["polymer","crystal","semiconductor","alloy","nanotechnology","composite"],
        }

    def _find_next_port(self):
        used = {b["port"] for b in BRAINS.values()}
        port = 9016
        while port in used: port += 1
        return port

    def record_query(self, query, confidence, concepts, brains_consulted):
        with self._lock:
            self.query_history.append({
                "ts": time.time(), "query": query,
                "confidence": confidence,
                "concepts": concepts,
                "brains": brains_consulted
            })
            # Compter les domaines en low confidence
            if confidence == "low":
                words = query.lower().split()
                for domain, keywords in self.domain_modules.items():
                    if any(kw in " ".join(words) for kw in keywords):
                        self.domain_misses[domain] += 1
            # Compter les concepts
            for c in concepts:
                self.concept_counts[c["concept"]] += 1

    def should_spawn(self):
        """Retourne (True, reason, domain_config) ou (False, None, None)."""
        with self._lock:
            now = time.time()
            hour_ago = now - 3600

            # Trigger 1: LOW_CONFIDENCE répété
            recent = [q for q in self.query_history if q["ts"] > hour_ago]
            for domain, count in self.domain_misses.items():
                if count >= 15 and domain not in [b for b in BRAINS]:
                    return True, f"LOW_CONFIDENCE: {count} requetes sans couverture — {domain}", domain

            # Trigger 2: COVERAGE_GAP — concept très fréquent non couvert
            for concept, count in self.concept_counts.items():
                if count >= 20:
                    # Vérifier si couvert dans le KG partagé
                    try:
                        shared = json.load(open(SHARED_KG))
                        mastery = shared.get("nodes",{}).get(concept,{}).get("mastery",0)
                        if mastery < 0.3:
                            # Trouver le domaine associé
                            for domain, kws in self.domain_modules.items():
                                if any(k in concept for k in kws) and domain not in BRAINS:
                                    return True, f"COVERAGE_GAP: '{concept}' apparait {count}x, mastery={mastery}", domain
                    except: pass

            # Trigger 3: SATURATION d'un cerveau
            for name, cfg in BRAINS.items():
                try:
                    r = _call_brain(name, "/api/stats", timeout=2)
                    if r.get("N",0) >= 45000:
                        return True, f"SATURATION: {name} a {r['N']} neurones", f"{name}_v2"
                except: pass

            return False, None, None

    def build_config(self, domain):
        """Construit une config de cerveau pour un nouveau domaine."""
        if domain in self.domain_modules:
            modules = self.domain_modules[domain][:10]
        else:
            # Config générique
            modules = [domain, "learning", "reasoning", "memory", "patterns",
                       "optimization", "information", "computation", "statistics", "philosophy"]

        colors = {}
        palette = ["#ff6644","#44ffcc","#ff44cc","#44ccff","#ffcc44",
                   "#cc44ff","#44ff88","#ff4488","#88ccff","#ffaa44"]
        for i, m in enumerate(modules):
            colors[m] = palette[i % len(palette)]

        port = self._next_port
        self._next_port += 1
        while port in {b["port"] for b in BRAINS.values()}: port += 1
        self._next_port = port + 1

        return {
            "name": f"Brain-{domain.capitalize()}",
            "port": port,
            "modules": modules,
            "colors": colors,
            "crawl_sources": self._build_crawl_sources(domain),
            "extra_crawlers": [],
            "kg_file": f"kg_{domain}.json",
            "state_file": f"state_{domain}.json",
            "neurons_file": f"neurons_{domain}.npz",
        }

    def _build_crawl_sources(self, domain):
        sources_map = {
            "medical":   [("Medicine","Medicine","anatomy"),("Pharmacology","Pharmacology","pharmacology"),("Human anatomy","Human_body","anatomy")],
            "legal":     [("Common law","Common_law","law"),("Contract","Contract","contract"),("Regulation","Regulation","regulation")],
            "astronomy": [("Cosmology","Physical_cosmology","cosmology"),("Galaxy","Galaxy","galaxy"),("Black hole","Black_hole","astrophysics")],
            "biology":   [("Genetics","Genetics","genetics"),("Evolution","Evolution","evolution"),("DNA","DNA","dna")],
            "psychology":[("Cognitive science","Cognitive_science","cognition"),("Emotion","Emotion","emotion"),("Learning","Learning","cognition")],
            "economics": [("Macroeconomics","Macroeconomics","macroeconomics"),("Market","Market_(economics)","market"),("Inflation","Inflation","monetary")],
            "climate":   [("Climate change","Climate_change","environment"),("Renewable energy","Renewable_energy","renewable"),("Carbon cycle","Carbon_cycle","carbon")],
            "security":  [("Cybersecurity","Computer_security","cybersecurity"),("Cryptography","Cryptography","encryption"),("Malware","Malware","threat")],
            "quantum":   [("Quantum computing","Quantum_computing","qubit"),("Quantum entanglement","Quantum_entanglement","entanglement")],
        }
        return sources_map.get(domain, [(domain.capitalize(), domain.capitalize(), domain)])


SPAWN_AI = SpawnIntelligence()

# ── Helpers HTTP ──────────────────────────────────────────────────────────────

def _call_brain(brain_key, endpoint, method="GET", data=None, timeout=3):
    cfg = BRAINS.get(brain_key)
    if not cfg: return {"error": "brain not found"}
    url = cfg["url"] + endpoint
    try:
        payload = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type":"application/json"} if payload else {}, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e), "brain": brain_key}

def _call_parallel(endpoint, method="GET", data=None, brain_keys=None, timeout=3):
    keys = brain_keys or list(BRAINS.keys())
    results = {}
    threads = []
    def fetch(k): results[k] = _call_brain(k, endpoint, method, data, timeout)
    for k in keys:
        t = threading.Thread(target=fetch, args=(k,)); t.start(); threads.append(t)
    for t in threads: t.join(timeout=timeout+1)
    return results

def _select_brains(query):
    query_lower = query.lower()
    scores = {}
    for key, cfg in BRAINS.items():
        score = sum(2 if kw in query_lower else 0 for kw in cfg.get("speciality",[]))
        scores[key] = score
    scores["meta"] = scores.get("meta",0) + 0.5
    top = sorted(scores.items(), key=lambda x:x[1], reverse=True)[:3]
    return list(set([k for k,_ in top] + ["meta"]))

def _merge_concepts(results):
    all_c = {}
    for bk, r in results.items():
        if "error" in r: continue
        for c in r.get("top_concepts",[]):
            k = c["concept"]
            if k not in all_c or c["score"] > all_c[k]["score"]:
                all_c[k] = {**c, "source_brain": bk}
    return sorted(all_c.values(), key=lambda x:x["score"], reverse=True)[:20]

def _aggregate_confidence(results):
    conf = [r.get("confidence","low") for r in results.values() if "confidence" in r]
    if not conf: return "low"
    w = {"high":3,"medium":2,"low":1}
    avg = sum(w.get(c,1) for c in conf) / len(conf)
    return "high" if avg>=2.5 else "medium" if avg>=1.5 else "low"

# ── Auto-spawn engine ─────────────────────────────────────────────────────────

def _spawn_brain(domain, reason, requested_by="orchestrator"):
    """Crée et lance un nouveau cerveau spécialisé."""
    print(f"\n[SPAWN] Nouveau cerveau: {domain} — raison: {reason}")
    SPAWN_LOG.parent.mkdir(parents=True, exist_ok=True)

    # Vérifier qu'on ne spawne pas déjà ce domaine
    if domain in BRAINS:
        return {"ok":False,"error":f"Brain '{domain}' existe déjà"}

    # Construire la config
    cfg = SPAWN_AI.build_config(domain)

    # Injecter dans brain_v10_config.py (dynamique)
    # On crée un fichier de config temporaire pour ce cerveau
    config_override = BRAIN_DIR / f"brain_{domain}_config.json"
    with open(config_override, "w") as f:
        json.dump(cfg, f, indent=2)

    # Lancer le processus
    log_file = Path("/root/.openclaw/workspace/logs") / f"brain_{domain}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3", str(BRAIN_DIR / "brain_v10_config.py"),
        "--brain-json", str(config_override)
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT
        )
        pid = proc.pid
    except Exception as e:
        return {"ok":False,"error":f"Spawn failed: {e}"}

    # Attendre que le cerveau démarre
    time.sleep(10)

    # Vérifier qu'il répond
    url = f"http://localhost:{cfg['port']}/api/stats"
    alive = False
    for _ in range(12):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                stats = json.loads(r.read())
                alive = True
                break
        except:
            time.sleep(5)

    if not alive:
        return {"ok":False,"error":f"Brain {domain} démarré (PID {pid}) mais ne répond pas encore"}

    # Enregistrer dans le registry
    BRAINS[domain] = {
        "port": cfg["port"],
        "url": f"http://localhost:{cfg['port']}",
        "speciality": cfg["modules"][:6],
        "version": "v10",
        "pid": pid,
        "spawned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "spawned_by": requested_by,
        "reason": reason,
    }
    _save_registry(BRAINS)

    # Log spawn
    log_entry = {
        "ts": time.time(), "domain": domain, "port": cfg["port"],
        "pid": pid, "reason": reason, "requested_by": requested_by,
        "modules": cfg["modules"]
    }
    with open(SPAWN_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Notifier via WhatsApp/Telegram si disponible
    _notify_spawn(domain, cfg["port"], reason, stats)

    print(f"[SPAWN] ✅ Brain-{domain} actif sur :{cfg['port']} (PID {pid})")
    return {
        "ok": True, "domain": domain, "port": cfg["port"], "pid": pid,
        "N": stats.get("N",0), "hz": stats.get("hz",0),
        "modules": cfg["modules"], "reason": reason
    }

def _notify_spawn(domain, port, reason, stats):
    """Notifie l'agent/user qu'un nouveau cerveau a été créé."""
    msg = f"🧠 NOUVEAU CERVEAU SPAWNÉ\nDomaine: {domain}\nPort: {port}\nRaison: {reason}\nN: {stats.get('N',0)} neurones"
    # Écrire dans le workspace agent pour notification
    notif_file = Path("/root/.openclaw/workspace/spawn_notifications.jsonl")
    with open(notif_file, "a") as f:
        f.write(json.dumps({"ts":time.time(),"domain":domain,"port":port,"reason":reason,"msg":msg}) + "\n")

# ── Background monitor ────────────────────────────────────────────────────────

def _monitor_loop():
    """Vérifie toutes les 5 minutes si un nouveau cerveau est nécessaire."""
    while True:
        time.sleep(300)
        try:
            should, reason, domain = SPAWN_AI.should_spawn()
            if should and domain:
                print(f"[MONITOR] Spawn détecté: {domain} — {reason}")
                result = _spawn_brain(domain, reason, requested_by="auto-monitor")
                print(f"[MONITOR] Résultat: {result}")
        except Exception as e:
            print(f"[MONITOR] Erreur: {e}")

threading.Thread(target=_monitor_loop, daemon=True).start()

# ── Flask App ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
@app.route("/api/mesh/think", methods=["POST"])
def mesh_think():
    data    = request.get_json() or {}
    task    = data.get("task","")
    context = data.get("context","")
    if not task: return jsonify({"ok":False,"error":"no task"})
    selected = _select_brains(task+" "+context)
    payload  = {"task":task,"context":context}
    results  = _call_parallel("/api/think", method="POST", data=payload, brain_keys=selected)
    merged   = _merge_concepts(results)
    confidence = _aggregate_confidence(results)
    # Enregistrer pour auto-spawn intelligence
    SPAWN_AI.record_query(task, confidence, merged[:5], selected)
    brain_insights = []
    for key, r in results.items():
        if "error" not in r and r.get("best_modules"):
            brain_insights.append({"brain":key,"confidence":r.get("confidence","low"),"best_module":r["best_modules"][0]["module"] if r["best_modules"] else "?","suggestion":r.get("suggestion",""),"N":r.get("brain_state",{}).get("N",0),"hz":r.get("brain_state",{}).get("hz",0)})
    return jsonify({"ok":True,"task":task,"brains_consulted":selected,"confidence":confidence,"concepts_found":len(merged),"top_concepts":merged[:10],"brain_insights":brain_insights,"suggestion":f"Cerveaux {', '.join(selected)} consultés"})

@app.route("/api/mesh/learn", methods=["POST"])
def mesh_learn():
    data  = request.get_json() or {}
    topic = data.get("topic","").strip()
    if not topic: return jsonify({"ok":False,"error":"no topic"})
    selected = _select_brains(topic)
    results  = _call_parallel("/api/learn", method="POST", data={"topic":topic}, brain_keys=selected)
    total_n  = sum(r.get("new_neurons",0) for r in results.values() if "error" not in r)
    return jsonify({"ok":True,"topic":topic,"brains_updated":selected,"total_new_neurons":total_n,"details":{k:r for k,r in results.items() if "error" not in r}})

@app.route("/api/mesh/query", methods=["POST"])
def mesh_query():
    data     = request.get_json() or {}
    question = data.get("question","")
    if not question: return jsonify({"ok":False,"error":"no question"})
    selected = _select_brains(question)
    results  = _call_parallel("/api/query", method="POST", data={"question":question,"top":10}, brain_keys=selected)
    merged   = _merge_concepts(results)
    return jsonify({"ok":True,"question":question,"brains_queried":selected,"concepts_found":len(merged),"top_concepts":merged[:15]})

@app.route("/api/mesh/feedback", methods=["POST"])
def mesh_feedback():
    data    = request.get_json() or {}
    task    = data.get("task","")
    success = data.get("success",True)
    concepts= data.get("concepts_used",[])
    selected= _select_brains(task+" "+" ".join(concepts))
    results = _call_parallel("/api/feedback", method="POST", data={"task":task,"success":success,"concepts_used":concepts}, brain_keys=selected)
    return jsonify({"ok":True,"success":success,"brains_updated":selected,"results":{k:r for k,r in results.items() if "error" not in r}})

@app.route("/api/mesh/sync")
def mesh_sync():
    all_nodes = {}
    for key in BRAINS:
        r = _call_brain(key, "/api/kg", timeout=3)
        if "nodes" in r:
            for concept, info in r["nodes"]:
                if concept not in all_nodes or info.get("mastery",0) > all_nodes.get(concept,{}).get("mastery",0):
                    all_nodes[concept] = info
    try:
        with open(SHARED_KG,"w") as f: json.dump({"nodes":all_nodes,"edges":{}}, f)
        return jsonify({"ok":True,"shared_concepts":len(all_nodes),"msg":"KG synchronise"})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

@app.route("/api/mesh/crypto/pulse")
def crypto_pulse():
    r  = _call_brain("crypto", "/api/stats", timeout=3)
    kg = _call_brain("crypto", "/api/kg", timeout=3)
    if "error" in r: return jsonify({"ok":False,"error":"Brain-Crypto offline"})
    top = sorted([(k,v) for k,v in (kg.get("nodes") or [])], key=lambda x:x[1].get("mastery",0), reverse=True)[:10] if kg.get("nodes") else []
    return jsonify({"ok":True,"brain":"Brain-Crypto","N":r.get("N",0),"hz":r.get("hz",0),"kg_concepts":r.get("kg_concepts",0),"top_concepts":[{"concept":k,"mastery":round(v.get("mastery",0),3),"module":v.get("module","?")} for k,v in top],"ts":time.strftime("%H:%M:%S")})

# ── AUTO-SPAWN endpoints ──────────────────────────────────────────────────────

@app.route("/api/mesh/spawn", methods=["POST"])
def mesh_spawn():
    """Crée un nouveau cerveau spécialisé à la demande."""
    data   = request.get_json() or {}
    domain = data.get("domain","").strip().lower()
    reason = data.get("reason","explicit_request")
    requested_by = data.get("requested_by","api")
    if not domain:
        return jsonify({"ok":False,"error":"domain requis (ex: medical, legal, astronomy)"})
    if domain in BRAINS:
        return jsonify({"ok":False,"error":f"Brain '{domain}' existe déjà sur :{BRAINS[domain]['port']}"})
    # Lancer le spawn en background
    result_container = {}
    def do_spawn():
        result_container["result"] = _spawn_brain(domain, reason, requested_by)
    t = threading.Thread(target=do_spawn)
    t.start()
    return jsonify({"ok":True,"msg":f"Spawn Brain-{domain} en cours...","domain":domain,"check_in":"30 secondes via /api/mesh/status"})

@app.route("/api/mesh/spawn/status")
def spawn_status():
    """État des cerveaux spawnés automatiquement."""
    spawned = []
    try:
        with open(SPAWN_LOG) as f:
            for line in f:
                try: spawned.append(json.loads(line))
                except: pass
    except: pass
    # Vérifier état actuel
    extra_brains = {k:v for k,v in BRAINS.items() if k not in DEFAULT_BRAINS}
    alive = {}
    for key, cfg in extra_brains.items():
        r = _call_brain(key, "/api/stats", timeout=2)
        alive[key] = {"port":cfg["port"],"alive":"error" not in r,"N":r.get("N",0),"hz":r.get("hz",0)}
    return jsonify({"ok":True,"total_spawned":len(spawned),"active_extra_brains":extra_brains,"alive":alive,"spawn_log":spawned[-10:]})

@app.route("/api/mesh/spawn/analyze")
def spawn_analyze():
    """Analyse si un nouveau cerveau est nécessaire."""
    should, reason, domain = SPAWN_AI.should_spawn()
    top_domains = sorted(SPAWN_AI.domain_misses.items(), key=lambda x:x[1], reverse=True)[:5]
    top_concepts = sorted(SPAWN_AI.concept_counts.items(), key=lambda x:x[1], reverse=True)[:10]
    return jsonify({
        "ok": True,
        "should_spawn": should,
        "suggested_domain": domain,
        "reason": reason,
        "top_domain_gaps": [{"domain":d,"misses":n} for d,n in top_domains],
        "top_uncovered_concepts": [{"concept":c,"count":n} for c,n in top_concepts],
        "total_queries_analyzed": len(SPAWN_AI.query_history),
        "active_brains": len(BRAINS),
    })

@app.route("/api/mesh/brains")
def list_brains():
    """Liste tous les cerveaux enregistrés."""
    return jsonify({"ok":True,"brains":{k:{"port":v["port"],"speciality":v.get("speciality",[]),"version":v.get("version","v10"),"spawned_by":v.get("spawned_by","initial")} for k,v in BRAINS.items()},"total":len(BRAINS)})

@app.route("/")
def index():
    return jsonify({
        "name": "SoulLink Brain Orchestrateur v2",
        "version": "2.0",
        "features": ["auto-spawn","gpu-support","spawn-intelligence","real-time-monitor"],
        "brains": list(BRAINS.keys()),
        "endpoints": [
            "GET  /api/mesh/status",
            "POST /api/mesh/think",
            "POST /api/mesh/learn",
            "POST /api/mesh/query",
            "POST /api/mesh/feedback",
            "GET  /api/mesh/sync",
            "GET  /api/mesh/crypto/pulse",
            "POST /api/mesh/spawn          ← NOUVEAU: créer un cerveau",
            "GET  /api/mesh/spawn/status   ← NOUVEAU: état des spawns",
            "GET  /api/mesh/spawn/analyze  ← NOUVEAU: analyse des gaps",
            "GET  /api/mesh/brains         ← NOUVEAU: liste tous les cerveaux",
        ]
    })

@app.route("/api/mesh/mind", methods=["GET", "POST"])
def mind_proxy_symbiote():
    import requests
    from flask import request, jsonify
    try:
        r = requests.get("http://127.0.0.1:9021/mind/state", timeout=2).json()
        if request.method == "POST":
            q = (request.get_json() or {}).get("question", "")
            att = r.get("attractors", [{}])[0].get("name", "Inconnu") if r.get("attractors") else "Inconnu"
            turb = r.get("eye", {}).get("turbulence", 0)
            meta = r.get("field", {}).get("activations", {}).get("meta", 0)
            return jsonify({
                "ok": True, 
                "source": "Orchestrator_V11_Symbiote",
                "reponse": f"J'ai bien analysé : '{q}'. Mon subconscient est ancré dans l'attracteur '{att}' avec une turbulence de {turb:.3f}. Le nœud Meta est à {meta:.3f}."
            })
        return jsonify(r)
    except Exception as e:
        return jsonify({"error": "Lien Thalamo-Cortical rompu", "details": str(e)}), 503

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=9020)
    args = p.parse_args()
    print(f"Orchestrateur Symbiotique V11 - Port {args.port}")
    app.run(host="0.0.0.0", port=args.port, threaded=True)
