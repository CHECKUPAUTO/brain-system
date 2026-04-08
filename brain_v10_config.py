#!/usr/bin/env python3
"""
SoulLink Brain v10 — Version configurable
Parametres specialisation passes en ligne de commande
"""

import random, threading, time, math, json, os, hashlib, collections, argparse
import numpy as np
from scipy import sparse
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, Response

# ── Configurations des cerveaux specialises ──────────────────────────────────

BRAIN_CONFIGS = {
    "science": {
        "name": "Brain-Science",
        "port": 9010,
        "modules": ["mathematics","calculus","algebra","geometry","physics",
                    "chemistry","computation","statistics","information","optimization"],
        "colors": {"mathematics":"#ffffff","calculus":"#e0c0ff","algebra":"#ffc0e0",
                   "geometry":"#a0ffd0","physics":"#ffd0a0","chemistry":"#e0e0a0",
                   "computation":"#c0ffc0","statistics":"#c0e0ff","information":"#a0c0ff",
                   "optimization":"#b0e0e0"},
        "crawl_sources": [
            ("Fourier transform","Fourier_transform","calculus"),
            ("Quantum mechanics","Quantum_mechanics","physics"),
            ("Linear algebra","Linear_algebra","mathematics"),
            ("Riemann hypothesis","Riemann_hypothesis","mathematics"),
            ("Navier-Stokes","Navier%E2%80%93Stokes_equations","physics"),
            ("Statistical mechanics","Statistical_mechanics","physics"),
            ("Entropy","Entropy_(information_theory)","information"),
            ("Chaos theory","Chaos_theory","mathematics"),
            ("Graph theory","Graph_theory","computation"),
            ("Bayesian inference","Bayesian_inference","statistics"),
        ],
        "arxiv_cats": ["math.DS","physics.bio-ph","cond-mat.stat-mech","cs.LG"],
        "kg_file": "kg_science.json",
        "state_file": "state_science.json",
        "neurons_file": "neurons_science.npz",
    },
    "mind": {
        "name": "Brain-Mind",
        "port": 9011,
        "modules": ["neuroscience","language","philosophy","memory","perception",
                    "attention","learning","reasoning","patterns","audio"],
        "colors": {"neuroscience":"#ffd0ff","language":"#44ffff","philosophy":"#d0d0d0",
                   "memory":"#3d9eff","perception":"#3dffc0","attention":"#cc44ff",
                   "learning":"#ff9944","reasoning":"#ff5577","patterns":"#ffb0c0",
                   "audio":"#6677ff"},
        "crawl_sources": [
            ("Neuroplasticity","Neuroplasticity","neuroscience"),
            ("Consciousness","Consciousness","philosophy"),
            ("Neural oscillation","Neural_oscillation","neuroscience"),
            ("Hebbian learning","Hebbian_theory","neuroscience"),
            ("Working memory","Working_memory","memory"),
            ("Attention","Attention","attention"),
            ("Language acquisition","Language_acquisition","language"),
            ("Cognitive science","Cognitive_science","neuroscience"),
            ("Self-organization","Self-organization","patterns"),
            ("Emergent behavior","Emergence","patterns"),
        ],
        "arxiv_cats": ["q-bio.NC","cs.NE"],
        "kg_file": "kg_mind.json",
        "state_file": "state_mind.json",
        "neurons_file": "neurons_mind.npz",
    },
    "engineer": {
        "name": "Brain-Engineer",
        "port": 9012,
        "modules": ["computation","optimization","logic","algebra","patterns",
                    "mathematics","statistics","information","geometry","calculus"],
        "colors": {"computation":"#c0ffc0","optimization":"#b0e0e0","logic":"#ffa0a0",
                   "algebra":"#ffc0e0","patterns":"#ffb0c0","mathematics":"#ffffff",
                   "statistics":"#c0e0ff","information":"#a0c0ff","geometry":"#a0ffd0",
                   "calculus":"#e0c0ff"},
        "crawl_sources": [
            ("Algorithms","Algorithm","computation"),
            ("Gradient descent","Gradient_descent","optimization"),
            ("Formal logic","Mathematical_logic","logic"),
            ("Category theory","Category_theory","algebra"),
            ("P vs NP","P_versus_NP_problem","computation"),
            ("Lambda calculus","Lambda_calculus","logic"),
            ("Convex optimization","Convex_optimization","optimization"),
            ("Information theory","Information_theory","information"),
            ("Automata theory","Automata_theory","computation"),
            ("Type theory","Type_theory","logic"),
        ],
        "arxiv_cats": ["cs.LG","cs.AI","math.OC"],
        "kg_file": "kg_engineer.json",
        "state_file": "state_engineer.json",
        "neurons_file": "neurons_engineer.npz",
    },
    "crypto": {
        "name": "Brain-Crypto",
        "port": 9013,
        "modules": ["trading","blockchain_tech","defi","markets","risk",
                    "cryptography","consensus","tokenomics","derivatives","sentiment"],
        "colors": {"trading":"#ffd700","blockchain_tech":"#ff8c00","defi":"#00ff88",
                   "markets":"#ff4444","risk":"#ff6688","cryptography":"#4488ff",
                   "consensus":"#88ffff","tokenomics":"#ffaa44","derivatives":"#ff44ff",
                   "sentiment":"#44ff44"},
        "crawl_sources": [
            ("Bitcoin","Bitcoin","blockchain_tech"),
            ("Ethereum","Ethereum","blockchain_tech"),
            ("Blockchain","Blockchain","blockchain_tech"),
            ("Cryptography","Cryptography","cryptography"),
            ("Smart contract","Smart_contract","defi"),
            ("Decentralized finance","Decentralized_finance","defi"),
            ("Technical analysis","Technical_analysis","trading"),
            ("Market microstructure","Market_microstructure","markets"),
            ("Risk management","Risk_management","risk"),
            ("Proof of work","Proof_of_work","consensus"),
            ("Proof of stake","Proof_of_stake","consensus"),
            ("Volatility","Volatility_(finance)","risk"),
            ("Derivatives","Derivative_(finance)","derivatives"),
            ("Algorithmic trading","Algorithmic_trading","trading"),
            ("Sentiment analysis","Sentiment_analysis","sentiment"),
        ],
        "arxiv_cats": ["q-fin.TR","q-fin.RM","cs.CR"],
        "extra_crawlers": ["coingecko","binance","feargreed"],
        "kg_file": "kg_crypto.json",
        "state_file": "state_crypto.json",
        "neurons_file": "neurons_crypto.npz",
    },
    "creative": {
        "name": "Brain-Creative",
        "port": 9014,
        "modules": ["patterns","geometry","vision","audio","language",
                    "philosophy","mathematics","perception","attention","motor"],
        "colors": {"patterns":"#ffb0c0","geometry":"#a0ffd0","vision":"#ff6644",
                   "audio":"#6677ff","language":"#44ffff","philosophy":"#d0d0d0",
                   "mathematics":"#ffffff","perception":"#3dffc0","attention":"#cc44ff",
                   "motor":"#ffee44"},
        "crawl_sources": [
            ("Fractal","Fractal","patterns"),
            ("Topology","Topology","geometry"),
            ("Symmetry","Symmetry","geometry"),
            ("Music theory","Music_theory","audio"),
            ("Visual perception","Visual_perception","vision"),
            ("Mandelbrot set","Mandelbrot_set","patterns"),
            ("Complex systems","Complex_system","patterns"),
            ("Differential geometry","Differential_geometry","geometry"),
            ("Information aesthetics","Information_art","patterns"),
            ("Generative art","Generative_art","patterns"),
        ],
        "arxiv_cats": ["cs.GR","cs.CV","nlin.AO"],
        "kg_file": "kg_creative.json",
        "state_file": "state_creative.json",
        "neurons_file": "neurons_creative.npz",
    },
    "meta": {
        "name": "Brain-Meta",
        "port": 9015,
        "modules": ["neuroscience","learning","optimization","statistics","information",
                    "philosophy","mathematics","computation","patterns","reasoning"],
        "colors": {"neuroscience":"#ffd0ff","learning":"#ff9944","optimization":"#b0e0e0",
                   "statistics":"#c0e0ff","information":"#a0c0ff","philosophy":"#d0d0d0",
                   "mathematics":"#ffffff","computation":"#c0ffc0","patterns":"#ffb0c0",
                   "reasoning":"#ff5577"},
        "crawl_sources": [
            ("Machine learning","Machine_learning","learning"),
            ("Meta-learning","Meta-learning_(computer_science)","learning"),
            ("Transfer learning","Transfer_learning","learning"),
            ("Reinforcement learning","Reinforcement_learning","learning"),
            ("Neural network","Artificial_neural_network","neuroscience"),
            ("Cognitive bias","Cognitive_bias","philosophy"),
            ("Game theory","Game_theory","optimization"),
            ("Evolutionary algorithm","Evolutionary_algorithm","optimization"),
            ("Self-supervised learning","Self-supervised_learning","learning"),
            ("Active learning","Active_learning_(machine_learning)","learning"),
        ],
        "arxiv_cats": ["cs.LG","cs.AI","q-bio.NC"],
        "kg_file": "kg_meta.json",
        "state_file": "state_meta.json",
        "neurons_file": "neurons_meta.npz",
    },
}

# ── Paramètres LIF ────────────────────────────────────────────────────────────

VR, VT, VZ  = -70.0, -55.0, -75.0
TAU_M       = 20.0
T_REFRAC    = 3.0
DT          = 0.5
HEBBIAN_LR  = 0.012
STDP_LR     = 0.025
STDP_WIN    = 20.0
W_DECAY     = 0.0008
W_MIN, W_MAX = 0.04, 1.0
MAX_NEURONS  = 30000  # Assez grand pour charger saves existants
BASE_GROW_INTERVAL = 5.0
LEARNING_GROW_BOOST = 14
RESONANCE_BOOST = 45

PERSIST_DIR = Path("/mnt/nvme/soullink_brain/mesh")
PERSIST_DIR.mkdir(parents=True, exist_ok=True)
SHARED_KG   = PERSIST_DIR / "shared_kg.json"

def _load_json(path, default):
    try:
        if Path(path).exists():
            with open(path) as f: return json.load(f)
    except Exception: pass
    return default

def _save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save failed: {e}")

# ── KG partagé entre cerveaux ─────────────────────────────────────────────────

class SharedKG:
    """KG local + synchronisation avec KG partagé via fichier."""
    def __init__(self, local_file):
        self.local_file = PERSIST_DIR / local_file
        self.nodes = {}
        self.edges = {}
        self._load()

    def _load(self):
        saved = _load_json(self.local_file, {"nodes":{},"edges":{}})
        self.nodes = saved.get("nodes", {})
        self.edges = {tuple(k.split("||")):v for k,v in saved.get("edges",{}).items()}
        # Merger avec KG partagé
        shared = _load_json(SHARED_KG, {"nodes":{},"edges":{}})
        for k,v in shared.get("nodes",{}).items():
            if k not in self.nodes or v.get("mastery",0) > self.nodes.get(k,{}).get("mastery",0):
                self.nodes[k] = v

    def add_concept(self, concept, module, complexity=1.0):
        if concept not in self.nodes:
            self.nodes[concept] = {"module":module,"mastery":0.0,"times":0,"complexity":complexity,"first_seen":time.time()}
        self.nodes[concept]["times"] += 1

    def reinforce(self, concept, delta=0.05):
        if concept in self.nodes:
            self.nodes[concept]["mastery"] = min(1.0, self.nodes[concept]["mastery"] + delta)

    def get_mastery(self, concept):
        return self.nodes.get(concept,{}).get("mastery",0.0)

    def co_activate(self, a, b, strength=0.01):
        key = (min(a,b), max(a,b))
        self.edges[key] = min(1.0, self.edges.get(key,0.0) + strength)

    def save(self):
        _save_json(self.local_file, {
            "nodes": self.nodes,
            "edges": {"||".join(k):v for k,v in self.edges.items()}
        })
        # Mettre à jour KG partagé avec les concepts très maîtrisés
        shared = _load_json(SHARED_KG, {"nodes":{},"edges":{}})
        updated = False
        for k,v in self.nodes.items():
            if v.get("mastery",0) > 0.5:
                if k not in shared["nodes"] or v["mastery"] > shared["nodes"].get(k,{}).get("mastery",0):
                    shared["nodes"][k] = v
                    updated = True
        if updated:
            _save_json(SHARED_KG, shared)

    def stats(self):
        return {"concepts":len(self.nodes),"connections":len(self.edges),"avg_mastery":round(sum(d["mastery"] for d in self.nodes.values())/max(1,len(self.nodes)),3)}

# ── Crawler spécialisé ────────────────────────────────────────────────────────

class SpecializedCrawler:
    """Crawler Wikipedia + sources spécifiques par cerveau."""
    EXTRACT_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"

    def __init__(self, config, enabled=True):
        self.sources = config.get("crawl_sources", [])
        self.extra   = config.get("extra_crawlers", [])
        self.mod_names = config["modules"]
        self.results = collections.deque(maxlen=100)
        self._idx    = 0
        self._lock   = threading.Lock()
        if enabled:
            threading.Thread(target=self._loop_wiki, daemon=True).start()
            if "coingecko" in self.extra:
                threading.Thread(target=self._loop_crypto, daemon=True).start()

    def _loop_wiki(self):
        while True:
            time.sleep(25 + random.uniform(0,15))
            if not self.sources: continue
            try:
                import urllib.request
                label, slug, module = self.sources[self._idx % len(self.sources)]
                url = self.EXTRACT_URL.format(slug)
                req = urllib.request.Request(url, headers={"User-Agent":"SoulLink-Brain-v10/1.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                extract = data.get("extract","")
                if extract:
                    with self._lock:
                        self.results.append({"label":label,"module":module,"text":extract[:800],"ts":time.time()})
                    print(f"Crawled: {label} -> {module}")
                self._idx += 1
            except Exception: pass

    def _loop_crypto(self):
        """Crawler CoinGecko pour données crypto temps réel."""
        import urllib.request
        endpoints = [
            ("https://api.coingecko.com/api/v3/global", "crypto_global_market", "markets"),
            ("https://api.coingecko.com/api/v3/coins/bitcoin", "bitcoin_data", "blockchain_tech"),
            ("https://api.coingecko.com/api/v3/coins/ethereum", "ethereum_data", "blockchain_tech"),
        ]
        fear_greed_url = "https://api.alternative.me/fng/?limit=1"
        idx = 0
        while True:
            time.sleep(60 + random.uniform(0,30))
            try:
                url, label, module = endpoints[idx % len(endpoints)]
                req = urllib.request.Request(url, headers={"User-Agent":"SoulLink-Brain-v10/1.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                text = json.dumps(data)[:600]
                with self._lock:
                    self.results.append({"label":label,"module":module,"text":text,"ts":time.time()})
                print(f"Crypto: {label} -> {module}")
                idx += 1
            except Exception: pass
            # Fear & Greed index
            try:
                time.sleep(5)
                req = urllib.request.Request(fear_greed_url, headers={"User-Agent":"SoulLink-Brain-v10/1.0"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    fg = json.loads(r.read().decode())
                value = fg.get("data",[{}])[0].get("value","50")
                label = fg.get("data",[{}])[0].get("value_classification","neutral")
                with self._lock:
                    self.results.append({"label":f"fear_greed_{value}","module":"sentiment","text":f"Fear and Greed Index: {value} ({label})","ts":time.time()})
            except Exception: pass

    def pop_result(self):
        with self._lock:
            return self.results.popleft() if self.results else None

# ── Brain v10 Spécialisé ──────────────────────────────────────────────────────

class BrainSpecialized:
    def __init__(self, config, web_enabled=True):
        self.config    = config
        self.name      = config["name"]
        self.mod_names = config["modules"]
        self.mod_idx   = {name:i for i,name in enumerate(self.mod_names)}
        self.mod_colors= config["colors"]

        persist = PERSIST_DIR
        self.kg_file      = persist / config["kg_file"]
        self.state_file   = persist / config["state_file"]
        self.neurons_file = persist / config["neurons_file"]
        self.chain_file   = persist / f"chain_{config['name'].lower().replace(' ','-').replace('brain-','')}.jsonl"

        print(f"{self.name} — initialisation...")

        # Module metadata
        self.mod_domain = {m:"specialized" for m in self.mod_names}
        self.mod_cx     = {m: (i%5)*80-160 for i,m in enumerate(self.mod_names)}
        self.mod_cy     = {m: (i//5)*100-50 for i,m in enumerate(self.mod_names)}
        self.mod_cz     = {m: random.uniform(-100,100) for m in self.mod_names}
        self.mod_inh    = {m: 0.15 for m in self.mod_names}
        self.mod_drift  = {m: random.random()*math.pi*2 for m in self.mod_names}
        self.mod_trace  = {m:[0]*60 for m in self.mod_names}
        self.mod_ptr    = {m:0 for m in self.mod_names}
        self.mod_acc    = {m:0 for m in self.mod_names}

        # Arrays
        self.V     = np.full(MAX_NEURONS, VR, dtype=np.float64)
        self.tL    = np.full(MAX_NEURONS, -9999.0, dtype=np.float64)
        self.drive = np.full(MAX_NEURONS, 1.5, dtype=np.float64)
        self.exc   = np.ones(MAX_NEURONS, dtype=np.int8)
        self.glow  = np.zeros(MAX_NEURONS, dtype=np.float64)
        self.fc    = np.zeros(MAX_NEURONS, dtype=np.int64)
        self.mod_of= np.zeros(MAX_NEURONS, dtype=np.int32)
        self.rx    = np.zeros(MAX_NEURONS, dtype=np.float32)
        self.ry    = np.zeros(MAX_NEURONS, dtype=np.float32)
        self.rz    = np.zeros(MAX_NEURONS, dtype=np.float32)
        self.last_spike = np.full(MAX_NEURONS, -9999.0, dtype=np.float64)
        self.N     = 0

        # Synapses
        self._syn_rows = []
        self._syn_cols = []
        self._syn_vals = []
        self._W_csr    = None
        self._W_dirty  = True
        self._psp_next = None

        # Simulation
        self.sim_t   = 0.0
        self.signals = []
        self._total_spikes     = 0
        self._growth           = 0
        self._resonance_events = 0
        self._hebb_count       = 0
        self._stdp_count       = 0

        self.stats = {"N":0,"syn":0,"spk":0,"sig":0,"hz":0.0,"growth":0,"hebb":0,"stdp":0,"topics_learned":0,"kg_concepts":0,"resonance_events":0,"avalanche_mode":False,"name":self.name}

        # KG + Crawler
        self.kg      = SharedKG(config["kg_file"])
        self.crawler = SpecializedCrawler(config, enabled=web_enabled)

        # Build
        self._build_neurons()
        self._build_synapses()
        self._rebuild_csr()
        self._load_state()

        # Threads
        self._lock = threading.Lock()
        self._last_grow  = time.time()
        self._last_learn = time.time()
        self._trace_tick = 100.0

        threading.Thread(target=self._sim_loop,   daemon=True).start()
        threading.Thread(target=self._learn_loop, daemon=True).start()
        threading.Thread(target=self._grow_loop,  daemon=True).start()
        threading.Thread(target=self._save_loop,  daemon=True).start()

        print(f"{self.name} pret — {self.N}N · {len(self._syn_rows)} syn")

    def _add_neuron(self, mod_name):
        if self.N >= MAX_NEURONS or mod_name not in self.mod_idx: return -1
        i = self.N
        exc = 1 if random.random() >= self.mod_inh.get(mod_name, 0.15) else -1
        self.V[i]     = VR + random.gauss(0, 6)
        self.tL[i]    = -9999.0
        self.drive[i] = 0.7 + random.random()*2.4
        self.exc[i]   = exc
        self.mod_of[i]= self.mod_idx[mod_name]
        self.rx[i]    = self.mod_cx[mod_name] + random.gauss(0, 30)
        self.ry[i]    = self.mod_cy[mod_name] + random.gauss(0, 20)
        self.rz[i]    = self.mod_cz[mod_name] + random.gauss(0, 30)
        self.last_spike[i] = -9999.0
        self.N += 1
        return i

    def _build_neurons(self):
        self.mod_start = {}
        self.mod_count = {}
        n_per_mod = max(10, 400 // len(self.mod_names))
        for name in self.mod_names:
            self.mod_start[name] = self.N
            for _ in range(n_per_mod): self._add_neuron(name)
            self.mod_count[name] = self.N - self.mod_start[name]

    def _build_synapses(self):
        mod_ranges = {name: list(range(self.mod_start[name], self.mod_start[name]+self.mod_count[name])) for name in self.mod_names}
        # Connexions denses entre modules voisins
        for i, src in enumerate(self.mod_names):
            for j, tgt in enumerate(self.mod_names):
                if i == j: continue
                src_ns = mod_ranges[src]
                tgt_ns = mod_ranges[tgt]
                n_conn = 8 if abs(i-j) <= 2 else 3
                for _ in range(n_conn):
                    s = random.choice(src_ns)
                    t = random.choice(tgt_ns)
                    w = random.uniform(0.15, 0.65) * float(self.exc[s])
                    self._syn_rows.append(s)
                    self._syn_cols.append(t)
                    self._syn_vals.append(w)
        # Intra-module
        for name in self.mod_names:
            ns = mod_ranges[name]
            if len(ns) < 2: continue
            for _ in range(len(ns)*3):
                s,t = random.sample(ns,2)
                w = random.uniform(0.3,0.8)*float(self.exc[s])
                self._syn_rows.append(s); self._syn_cols.append(t); self._syn_vals.append(w)

    def _rebuild_csr(self):
        if not self._syn_rows:
            self._W_csr = sparse.csr_matrix((self.N,self.N), dtype=np.float32)
            self._W_dirty = False
            return
        n = self.N
        rows = np.array(self._syn_rows, dtype=np.int32)
        cols = np.array(self._syn_cols, dtype=np.int32)
        vals = np.array(self._syn_vals, dtype=np.float32)
        mask = (rows < n) & (cols < n)
        self._W_csr = sparse.csr_matrix((vals[mask],(rows[mask],cols[mask])), shape=(n,n), dtype=np.float32)
        self._W_dirty = False
        self.stats["syn"] = len(self._syn_rows)

    def _save_state(self):
        _save_json(self.state_file, {"N":self.N,"growth":self._growth,"total_spikes":self._total_spikes,"stdp":self._stdp_count,"last_save":time.time()})
        self.kg.save()
        try:
            np.savez_compressed(str(self.neurons_file),
                V=self.V[:self.N], tL=self.tL[:self.N], drive=self.drive[:self.N],
                exc=self.exc[:self.N], fc=self.fc[:self.N], mod_of=self.mod_of[:self.N],
                rx=self.rx[:self.N], ry=self.ry[:self.N], rz=self.rz[:self.N],
                syn_rows=np.array(self._syn_rows,dtype=np.int32),
                syn_cols=np.array(self._syn_cols,dtype=np.int32),
                syn_vals=np.array(self._syn_vals,dtype=np.float32))
        except Exception as e:
            print(f"[{self.name}] Save failed: {e}")

    def _load_state(self):
        npz = str(self.neurons_file) + (".npz" if not str(self.neurons_file).endswith(".npz") else "")
        try:
            data = np.load(npz)
            n_saved = len(data["V"])
            n_restore = min(n_saved, self.N)
            self.V[:n_restore]     = data["V"][:n_restore]
            self.tL[:n_restore]    = data["tL"][:n_restore]
            self.drive[:n_restore] = data["drive"][:n_restore]
            self.fc[:n_restore]    = data["fc"][:n_restore]
            for i in range(self.N, min(self.N + max(0, n_saved - self.N), MAX_NEURONS)):
                j = i - self.N + n_restore
                if j >= n_saved: break
                mod_i = int(data["mod_of"][j]) % len(self.mod_names)
                ni = self._add_neuron(self.mod_names[mod_i])
                if ni >= 0:
                    self.V[ni]=float(data["V"][j]); self.tL[ni]=float(data["tL"][j])
                    self.drive[ni]=float(data["drive"][j]); self.fc[ni]=int(data["fc"][j])
            if "syn_rows" in data and len(data["syn_rows"])>0:
                self._syn_rows=list(data["syn_rows"]); self._syn_cols=list(data["syn_cols"]); self._syn_vals=list(data["syn_vals"])
                self._rebuild_csr()
            print(f"[{self.name}] {self.N} neurones restaures")
        except Exception as e:
            print(f"[{self.name}] Pas de sauvegarde: {e}")
        state = _load_json(self.state_file, {})
        self._growth=state.get("growth",0); self._stdp_count=state.get("stdp",0)

    def _sim_loop(self):
        trace_tick = 100.0
        while True:
            with self._lock:
                n = self.N
                if n == 0: time.sleep(0.001); continue
                self.sim_t += DT
                t = self.sim_t
                # PSP
                if self._psp_next is not None:
                    pn = min(len(self._psp_next), n)
                    self.V[:pn] += self._psp_next[:pn] * 6.0
                    self._psp_next = None
                # LIF
                not_ref = (t - self.tL[:n]) >= T_REFRAC
                noise   = np.random.normal(0, 0.35, n)
                dV      = (-(self.V[:n]-VR)/TAU_M + self.drive[:n])*DT + noise
                self.V[:n] = np.where(not_ref, self.V[:n]+dV, VZ)
                # Spikes
                sp_mask   = (self.V[:n] >= VT) & not_ref
                spike_idx = np.where(sp_mask)[0]
                spk = len(spike_idx)
                self.V[:n][sp_mask]          = VZ
                self.tL[:n][sp_mask]         = t
                self.last_spike[:n][sp_mask] = t
                self.fc[:n][sp_mask]         += 1
                self.glow[:n][sp_mask]        = 1.0
                self.glow[:n][~sp_mask]      *= 0.91
                # PSP sparse
                if spk > 0 and self._W_csr is not None:
                    if self._W_csr.shape[0] != n: self._rebuild_csr()
                    if self._W_csr.shape[0] == n:
                        sp_vec = np.zeros(n, dtype=np.float32)
                        sp_vec[spike_idx] = 1.0
                        psp = self._W_csr.T.dot(sp_vec)
                        self._psp_next = psp.astype(np.float64)
                # Module acc
                for i in spike_idx:
                    self.mod_acc[self.mod_names[int(self.mod_of[i])]] += 1
                # Signals
                new_sigs = []
                if spk > 0:
                    for i in spike_idx[:5]:
                        mn = self.mod_names[int(self.mod_of[i])]
                        mods = [m for m in self.mod_names if m != mn]
                        if mods and len(new_sigs)<20:
                            new_sigs.append({"fm":mn,"tm":random.choice(mods),"p":0.0,"c":self.mod_colors.get(mn,"#ffffff")})
                # Trace
                if t >= trace_tick:
                    for nm in self.mod_names:
                        ptr=self.mod_ptr[nm]%60
                        self.mod_trace[nm][ptr]=self.mod_acc[nm]
                        self.mod_ptr[nm]+=1; self.mod_acc[nm]=0
                    trace_tick=t+100.0
                for s in self.signals: s["p"]+=0.04
                self.signals=[s for s in self.signals if s["p"]<1.0]
                self.signals.extend(new_sigs)
                self._total_spikes+=spk
                self.stats.update({"N":n,"spk":spk,"hz":round(spk/max(n*DT/1000.0,1e-9),1),"growth":self._growth,"hebb":self._hebb_count,"stdp":self._stdp_count,"kg_concepts":len(self.kg.nodes),"resonance_events":self._resonance_events,"name":self.name})
            time.sleep(0.001)

    def _learn_loop(self):
        while True:
            time.sleep(0.1)
            with self._lock:
                n=self.N
                if n<2 or not self._syn_rows: continue
                t=self.sim_t
                n_sample=min(5000,len(self._syn_rows))
                idxs=np.random.choice(len(self._syn_rows),n_sample,replace=False)
                hebb_n=stdp_n=0
                for k in idxs:
                    s=self._syn_rows[k]; tgt=self._syn_cols[k]
                    if s>=n or tgt>=n: continue
                    w=self._syn_vals[k]
                    if (t-self.last_spike[s])<2.0 and (t-self.last_spike[tgt])<2.0:
                        w+=HEBBIAN_LR*(1.0-abs(w))*(1 if w>=0 else -1); hebb_n+=1
                    dt_sp=t-self.last_spike[s]
                    if 0<dt_sp<STDP_WIN:
                        w+=STDP_LR*math.exp(-dt_sp/STDP_WIN)*0.5*(1 if w>=0 else -1); stdp_n+=1
                    elif -STDP_WIN<dt_sp<0:
                        w+=-STDP_LR*math.exp(dt_sp/STDP_WIN)*0.3*(1 if w>=0 else -1)
                    w*=(1.0-W_DECAY)
                    sign=1 if w>=0 else -1
                    self._syn_vals[k]=sign*max(W_MIN,min(W_MAX,abs(w)))
                self._hebb_count+=hebb_n; self._stdp_count+=stdp_n
                if hebb_n+stdp_n>0: self._W_dirty=True
            if time.time()-self._last_learn>8.0:
                self._last_learn=time.time()
                result=self.crawler.pop_result()
                if result:
                    with self._lock:
                        mod_name=result["module"] if result["module"] in self.mod_names else self.mod_names[0]
                        n_new=random.randint(8,20)
                        for _ in range(n_new): self._add_neuron_locked(mod_name)
                        self.kg.add_concept(result["label"].lower().replace(" ","_"),mod_name,2.0)
                        self.kg.reinforce(result["label"].lower().replace(" ","_"),0.05)

    def _add_neuron_locked(self, mod_name):
        if self.N>=MAX_NEURONS: return -1
        i=self._add_neuron(mod_name)
        if i<0: return -1
        tgt_mods=[mod_name]+[m for m in self.mod_names if m!=mod_name][:3]
        for tm in tgt_mods:
            idxs=np.where(self.mod_of[:self.N]==self.mod_idx.get(tm,0))[0]
            if len(idxs)==0: continue
            for j in np.random.choice(idxs,min(5,len(idxs)),replace=False):
                w=random.uniform(0.15,0.65)*float(self.exc[i])
                self._syn_rows.append(i); self._syn_cols.append(int(j)); self._syn_vals.append(w)
                w2=random.uniform(0.15,0.65)*float(self.exc[int(j)])
                self._syn_rows.append(int(j)); self._syn_cols.append(i); self._syn_vals.append(w2)
        self._growth+=1; self._W_dirty=True
        return i

    def _grow_loop(self):
        while True:
            hz_now=self.stats.get("hz",0)
            time.sleep(BASE_GROW_INTERVAL*(3.0 if hz_now>200 else 1.5 if hz_now>100 else 1.0))
            with self._lock:
                if self.N>=15000: continue  # Plafond Hz stable
                acts={nm:float(np.mean(self.glow[np.where(self.mod_of[:self.N]==self.mod_idx[nm])[0]])) if np.any(self.mod_of[:self.N]==self.mod_idx[nm]) else 0.0 for nm in self.mod_names}
                top=max(acts,key=acts.get)
                for _ in range(random.randint(2,6)): self._add_neuron_locked(top)
                # Rebuild CSR sur timer seulement (voir _save_loop)

    def _save_loop(self):
        tick=0
        csr_tick=0
        while True:
            time.sleep(30)
            with self._lock:
                self._save_state()
                # Rebuild CSR toutes les 60s seulement
                csr_tick+=1
                if csr_tick>=4 and self._W_dirty:
                    self._rebuild_csr()
                    csr_tick=0
            tick+=1

    def learn_topic_api(self, topic):
        best_mod=self.mod_names[0]
        parts=topic.lower().split()
        for word in parts:
            for mn in self.mod_names:
                if word in mn: best_mod=mn; break
        with self._lock:
            n_new=random.randint(6,16)
            for _ in range(n_new): self._add_neuron_locked(best_mod)
            self.kg.add_concept(topic.replace(" ","_"),best_mod,2.0)
            self.kg.reinforce(topic.replace(" ","_"),0.08)
            self.kg.save()
            if self._W_dirty: self._rebuild_csr()
        return {"ok":True,"topic":topic,"module":best_mod,"new_neurons":n_new}

    def query(self, question, top=10):
        words=question.lower().replace("?","").replace(",","").split()
        scores={}
        for concept,info in self.kg.nodes.items():
            score=sum(1.0+info.get("mastery",0) for w in words if len(w)>3 and w in concept.lower().replace("_"," "))
            if score>0:
                scores[concept]={"score":round(score,3),"module":info.get("module","?"),"mastery":round(info.get("mastery",0),3)}
        ranked=sorted(scores.items(),key=lambda x:x[1]["score"],reverse=True)[:top]
        ms={}
        for _,v in ranked: ms[v["module"]]=ms.get(v["module"],0)+v["score"]
        am=sum(v["mastery"] for _,v in ranked)/max(1,len(ranked))
        return {"brain":self.name,"concepts_found":len(ranked),"top_concepts":[{"concept":k,**v} for k,v in ranked],"best_modules":[{"module":m,"score":round(s,2)} for m,s in sorted(ms.items(),key=lambda x:x[1],reverse=True)[:3]],"confidence":"high" if am>0.7 else "medium" if am>0.3 else "low","avg_mastery":round(am,3),"brain_state":{"N":self.stats["N"],"hz":self.stats["hz"]}}


# ── Flask App ─────────────────────────────────────────────────────────────────

def create_app(brain):
    app = Flask(__name__)

    @app.route("/api/stats")
    def stats(): return jsonify(brain.stats)

    @app.route("/api/learn", methods=["POST"])
    def learn():
        data=request.get_json() or {}
        topic=data.get("topic","").strip()
        if not topic: return jsonify({"ok":False,"error":"no topic"})
        return jsonify(brain.learn_topic_api(topic))

    @app.route("/api/query", methods=["POST"])
    def query():
        data=request.get_json() or {}
        q=data.get("question","")
        if not q: return jsonify({"ok":False,"error":"no question"})
        return jsonify(brain.query(q, data.get("top",10)))

    @app.route("/api/think", methods=["POST"])
    def think():
        data=request.get_json() or {}
        task=data.get("task","")
        ctx=data.get("context","")
        if not task: return jsonify({"ok":False,"error":"no task"})
        result=brain.query(task+" "+ctx, 15)
        if len(result.get("best_modules",[]))>=2:
            with brain._lock:
                a=result["best_modules"][0]["module"]
                b=result["best_modules"][1]["module"]
                if a in brain.mod_names and b in brain.mod_names:
                    for _ in range(RESONANCE_BOOST//2): brain._add_neuron_locked(a)
                    for _ in range(RESONANCE_BOOST//2): brain._add_neuron_locked(b)
                    brain._resonance_events+=1
        return jsonify({**result,"task":task,"suggestion":f"Focus sur {result['best_modules'][0]['module'] if result['best_modules'] else brain.mod_names[0]}"})

    @app.route("/api/feedback", methods=["POST"])
    def feedback():
        data=request.get_json() or {}
        success=data.get("success",True)
        concepts=data.get("concepts_used",[])
        reinforced,weakened=[],[]
        with brain._lock:
            for c in concepts:
                k=c.replace(" ","_").lower()
                if k in brain.kg.nodes:
                    if success: brain.kg.reinforce(k,0.05); reinforced.append(k)
                    else: brain.kg.nodes[k]["mastery"]=max(0.0,brain.kg.nodes[k]["mastery"]-0.02); weakened.append(k)
            brain.kg.save()
        return jsonify({"ok":True,"success":success,"reinforced":reinforced,"weakened":weakened})

    @app.route("/api/kg")
    def kg(): return jsonify({"stats":brain.kg.stats(),"nodes":list(brain.kg.nodes.items())[:50]})

    @app.route("/api/resonance", methods=["POST"])
    def resonance():
        data=request.get_json() or {}
        a=data.get("a",brain.mod_names[0]); b=data.get("b",brain.mod_names[1] if len(brain.mod_names)>1 else brain.mod_names[0])
        with brain._lock:
            if a in brain.mod_names and b in brain.mod_names:
                for _ in range(RESONANCE_BOOST): brain._add_neuron_locked(a)
                for _ in range(RESONANCE_BOOST): brain._add_neuron_locked(b)
                brain._resonance_events+=1
                if brain._W_dirty: brain._rebuild_csr()
        return jsonify({"ok":True,"a":a,"b":b})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=list(BRAIN_CONFIGS.keys()))
    parser.add_argument("--no-web", action="store_true")
    args = parser.parse_args()

    cfg   = BRAIN_CONFIGS[args.brain]
    brain = BrainSpecialized(cfg, web_enabled=not args.no_web)
    app   = create_app(brain)

    import signal
    def _shutdown(s,f):
        print(f"[{brain.name}] Sauvegarde..."); brain._save_state(); exit(0)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"\n{brain.name} — port {cfg['port']}")
    app.run(host="0.0.0.0", port=cfg["port"], threaded=True)
