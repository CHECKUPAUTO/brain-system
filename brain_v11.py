#!/usr/bin/env python3
"""
SoulLink Brain v11.0 — PYTORCH GPU SINGULARITY
══════════════════════════════════════════════════════════════════
Backend PyTorch CUDA — target 5000-10000 Hz
Fallback automatique NumPy si pas de GPU
Compatible drop-in avec v10 — même API
RTX 4060 — 8GB VRAM
══════════════════════════════════════════════════════════════════
"""

import random, threading, time, math, json, hashlib, collections, argparse
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, Response
import numpy as np
from scipy import sparse as sp_cpu

# ── Backend GPU auto-detect ───────────────────────────────────────────────────
try:
    import torch
    if torch.cuda.is_available():
        DEVICE    = torch.device("cuda")
        GPU_OK    = True
        GPU_NAME  = torch.cuda.get_device_name(0)
        VRAM_GB   = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {GPU_NAME} ({VRAM_GB:.1f}GB VRAM)")
    else:
        DEVICE   = torch.device("cpu")
        GPU_OK   = False
        GPU_NAME = "CPU (PyTorch)"
        print("PyTorch CPU mode")
    TORCH_OK = True
except ImportError:
    TORCH_OK = False
    GPU_OK   = False
    GPU_NAME = "NumPy fallback"
    print("PyTorch non disponible — NumPy fallback")

# ── Persistance ───────────────────────────────────────────────────────────────
PERSIST_DIR = Path("/mnt/nvme/soullink_brain")
MESH_DIR    = Path("/mnt/nvme/soullink_brain/mesh")
PERSIST_DIR.mkdir(parents=True, exist_ok=True)
MESH_DIR.mkdir(parents=True, exist_ok=True)

def _load_json(path, default):
    try:
        if Path(path).exists():
            with open(path) as f: return json.load(f)
    except Exception: pass
    return default

def _save_json(path, data):
    try:
        with open(path,"w") as f: json.dump(data, f, indent=2)
    except Exception as e: print(f"Save failed: {e}")

# ── LIF Parameters ────────────────────────────────────────────────────────────
VR, VT, VZ   = -70.0, -55.0, -75.0
TAU_M        = 20.0
T_REFRAC     = 3.0
DT           = 0.5
HEBBIAN_LR   = 0.012
STDP_LR      = 0.025
STDP_WIN     = 20.0
W_DECAY      = 0.0008
W_MIN, W_MAX = 0.04, 1.0
MAX_NEURONS  = 50000
BASE_GROW_INTERVAL = 5.0
RESONANCE_BOOST    = 45

# ── Import configs v10 ────────────────────────────────────────────────────────
import sys
sys.path.insert(0, str(PERSIST_DIR))
from brain_v10_config import BRAIN_CONFIGS, SharedKG, SpecializedCrawler

# ── Helpers GPU/CPU transparents ──────────────────────────────────────────────

def _t(arr, dtype=torch.float64):
    """NumPy → Tensor GPU."""
    if TORCH_OK:
        return torch.tensor(arr, dtype=dtype, device=DEVICE)
    return arr

def _n(tensor):
    """Tensor GPU → NumPy."""
    if TORCH_OK and isinstance(tensor, torch.Tensor):
        return tensor.cpu().numpy()
    return tensor

def _zeros(n, dtype=torch.float64):
    if TORCH_OK: return torch.zeros(n, dtype=dtype, device=DEVICE)
    return np.zeros(n, dtype=np.float64)

def _full(n, val, dtype=torch.float64):
    if TORCH_OK: return torch.full((n,), val, dtype=dtype, device=DEVICE)
    return np.full(n, val, dtype=np.float64)

def _where(cond, a, b):
    if TORCH_OK: return torch.where(cond, a, b)
    return np.where(cond, a, b)

def _randn(n):
    if TORCH_OK: return torch.randn(n, dtype=torch.float64, device=DEVICE) * 0.35
    return np.random.normal(0, 0.35, n)

# ── Brain V11 ─────────────────────────────────────────────────────────────────

class BrainV11:
    def __init__(self, config, web_enabled=True):
        self.config    = config
        self.name      = config["name"]
        self.mod_names = config["modules"]
        self.mod_idx   = {n:i for i,n in enumerate(self.mod_names)}
        self.mod_colors= config["colors"]

        persist = MESH_DIR
        self.kg_file      = persist / config["kg_file"]
        self.state_file   = persist / config["state_file"]
        self.neurons_file = persist / config["neurons_file"].replace(".npz","_v11.npz")
        self.chain_file   = persist / f"chain_v11_{config['name'].lower().replace(' ','_')}.jsonl"

        print(f"{self.name} v11 — {GPU_NAME}")

        # Module metadata
        self.mod_cx = {m:(i%5)*80-160 for i,m in enumerate(self.mod_names)}
        self.mod_cy = {m:(i//5)*100-50 for i,m in enumerate(self.mod_names)}
        self.mod_cz = {m:random.uniform(-100,100) for m in self.mod_names}
        self.mod_inh= {m:0.15 for m in self.mod_names}
        self.mod_drift={m:random.random()*math.pi*2 for m in self.mod_names}
        self.mod_trace={m:[0]*60 for m in self.mod_names}
        self.mod_ptr  ={m:0 for m in self.mod_names}
        self.mod_acc  ={m:0 for m in self.mod_names}

        # ── Arrays CPU (ref)
        self.N = 0
        self._V_cpu    = np.full(MAX_NEURONS, VR,      dtype=np.float64)
        self._tL_cpu   = np.full(MAX_NEURONS, -9999.0, dtype=np.float64)
        self._dr_cpu   = np.full(MAX_NEURONS, 1.5,     dtype=np.float64)
        self._exc_cpu  = np.ones(MAX_NEURONS,           dtype=np.int8)
        self._glow_cpu = np.zeros(MAX_NEURONS,          dtype=np.float64)
        self._fc_cpu   = np.zeros(MAX_NEURONS,          dtype=np.int64)
        self._mod_cpu  = np.zeros(MAX_NEURONS,          dtype=np.int32)
        self._rx_cpu   = np.zeros(MAX_NEURONS,          dtype=np.float32)
        self._ry_cpu   = np.zeros(MAX_NEURONS,          dtype=np.float32)
        self._rz_cpu   = np.zeros(MAX_NEURONS,          dtype=np.float32)
        self._ls_cpu   = np.full(MAX_NEURONS, -9999.0, dtype=np.float64)

        # ── Tensors GPU
        self._V_gpu  = self._tL_gpu = self._dr_gpu = None
        self._gl_gpu = self._fc_gpu = self._ls_gpu = None
        self._gpu_n  = 0
        self._gpu_ready = False

        # ── Synapses sparse (CPU build, GPU transfer)
        self._syn_rows = []
        self._syn_cols = []
        self._syn_vals = []
        self._W_csr    = None   # sparse CPU (scipy)
        self._W_gpu    = None   # sparse GPU (torch.sparse_csr)
        self._W_dirty  = True
        self._psp_buf  = None   # tensor GPU PSP

        # ── Queue non-bloquante neurogenese
        self._neuron_queue = collections.deque()

        # ── Simulation
        self.sim_t   = 0.0
        self.signals = []
        self._total_spikes     = 0
        self._growth           = 0
        self._resonance_events = 0
        self._hebb_count       = 0
        self._stdp_count       = 0

        self.stats = {
            "N":0,"syn":0,"spk":0,"hz":0.0,"growth":0,
            "hebb":0,"stdp":0,"kg_concepts":0,"resonance_events":0,
            "name":self.name,"gpu":GPU_OK,"gpu_name":GPU_NAME,
        }

        # ── KG + Crawler
        self.kg      = SharedKG(config["kg_file"])
        self.crawler = SpecializedCrawler(config, enabled=web_enabled)

        # ── Init
        self._build_neurons()
        self._build_synapses()
        self._upload_gpu()
        self._load_state()

        self._lock       = threading.Lock()   # lock principal (sim)
        self._grow_lock  = threading.Lock()   # lock neurogenese separee
        self._last_learn = time.time()

        threading.Thread(target=self._sim_loop,       daemon=True).start()
        threading.Thread(target=self._learn_loop,     daemon=True).start()
        threading.Thread(target=self._grow_loop,      daemon=True).start()
        threading.Thread(target=self._integrate_loop, daemon=True).start()
        threading.Thread(target=self._save_loop,      daemon=True).start()

        print(f"{self.name} v11 pret — {self.N}N · {len(self._syn_rows)} syn · {'GPU' if GPU_OK else 'CPU'}")

    # ── Construction ──────────────────────────────────────────────────────────

    def _add_neuron_cpu(self, mod_name):
        if self.N >= MAX_NEURONS or mod_name not in self.mod_idx: return -1
        i = self.N
        exc = 1 if random.random() >= self.mod_inh.get(mod_name, 0.15) else -1
        self._V_cpu[i]    = VR + random.gauss(0, 6)
        self._tL_cpu[i]   = -9999.0
        self._dr_cpu[i]   = 0.7 + random.random()*2.4
        self._exc_cpu[i]  = exc
        self._mod_cpu[i]  = self.mod_idx[mod_name]
        self._rx_cpu[i]   = self.mod_cx[mod_name] + random.gauss(0, 30)
        self._ry_cpu[i]   = self.mod_cy[mod_name] + random.gauss(0, 20)
        self._rz_cpu[i]   = self.mod_cz[mod_name] + random.gauss(0, 30)
        self._ls_cpu[i]   = -9999.0
        self.N += 1
        return i

    def _build_neurons(self):
        self.mod_start = {}; self.mod_count = {}
        n_per = max(10, 400 // len(self.mod_names))
        for name in self.mod_names:
            self.mod_start[name] = self.N
            for _ in range(n_per): self._add_neuron_cpu(name)
            self.mod_count[name] = self.N - self.mod_start[name]

    def _build_synapses(self):
        mod_ranges = {n: list(range(self.mod_start[n], self.mod_start[n]+self.mod_count[n])) for n in self.mod_names}
        for i, src in enumerate(self.mod_names):
            for j, tgt in enumerate(self.mod_names):
                if i == j: continue
                sn = mod_ranges[src]; tn = mod_ranges[tgt]
                n_c = 8 if abs(i-j)<=2 else 3
                for _ in range(n_c):
                    s=random.choice(sn); t=random.choice(tn)
                    w=random.uniform(0.15,0.65)*float(self._exc_cpu[s])
                    self._syn_rows.append(s); self._syn_cols.append(t); self._syn_vals.append(w)
        for name in self.mod_names:
            ns = mod_ranges[name]
            if len(ns)<2: continue
            for _ in range(len(ns)*3):
                s,t=random.sample(ns,2)
                self._syn_rows.append(s); self._syn_cols.append(t)
                self._syn_vals.append(random.uniform(0.3,0.8)*float(self._exc_cpu[s]))

    def _upload_gpu(self):
        """Upload arrays CPU → GPU tensors."""
        n = self.N
        if n == 0: return
        try:
            if TORCH_OK:
                self._V_gpu  = torch.tensor(self._V_cpu[:n],   dtype=torch.float64, device=DEVICE)
                self._tL_gpu = torch.tensor(self._tL_cpu[:n],  dtype=torch.float64, device=DEVICE)
                self._dr_gpu = torch.tensor(self._dr_cpu[:n],  dtype=torch.float64, device=DEVICE)
                self._gl_gpu = torch.tensor(self._glow_cpu[:n],dtype=torch.float64, device=DEVICE)
                self._fc_gpu = torch.tensor(self._fc_cpu[:n],  dtype=torch.int64,   device=DEVICE)
                self._ls_gpu = torch.tensor(self._ls_cpu[:n],  dtype=torch.float64, device=DEVICE)
            else:
                self._V_gpu  = self._V_cpu[:n].copy()
                self._tL_gpu = self._tL_cpu[:n].copy()
                self._dr_gpu = self._dr_cpu[:n].copy()
                self._gl_gpu = self._glow_cpu[:n].copy()
                self._fc_gpu = self._fc_cpu[:n].copy()
                self._ls_gpu = self._ls_cpu[:n].copy()

            self._rebuild_sparse_gpu()
            self._gpu_n     = n
            self._gpu_ready = True
        except Exception as e:
            print(f"[{self.name}] GPU upload error: {e}")
            self._gpu_ready = False

    def _rebuild_sparse_gpu(self):
        """Construit la matrice sparse en format optimisé GPU."""
        n = self.N
        if not self._syn_rows:
            self._W_csr = sp_cpu.csr_matrix((n,n), dtype=np.float32)
            self._W_gpu = None
            self._W_dirty = False
            return

        rows = np.array(self._syn_rows, dtype=np.int32)
        cols = np.array(self._syn_cols, dtype=np.int32)
        vals = np.array(self._syn_vals, dtype=np.float32)
        mask = (rows < n) & (cols < n)

        # Sparse CPU (scipy) — toujours disponible
        self._W_csr = sp_cpu.csr_matrix(
            (vals[mask], (rows[mask], cols[mask])), shape=(n,n), dtype=np.float32
        )

        # Sparse GPU (PyTorch sparse_csr) pour multiplication ultra-rapide
        if TORCH_OK:
            try:
                crow = torch.tensor(self._W_csr.indptr,  dtype=torch.int32, device=DEVICE)
                col  = torch.tensor(self._W_csr.indices, dtype=torch.int32, device=DEVICE)
                val  = torch.tensor(self._W_csr.data,    dtype=torch.float32, device=DEVICE)
                self._W_gpu = torch.sparse_csr_tensor(crow, col, val, size=(n,n), device=DEVICE)
            except Exception as e:
                # Fallback: sparse COO
                try:
                    indices = torch.tensor(
                        np.array([rows[mask], cols[mask]], dtype=np.int64), device=DEVICE
                    )
                    values = torch.tensor(vals[mask], dtype=torch.float32, device=DEVICE)
                    self._W_gpu = torch.sparse_coo_tensor(indices, values, (n,n), device=DEVICE).coalesce()
                except Exception as e2:
                    print(f"Sparse GPU fallback aussi echoue: {e2}")
                    self._W_gpu = None

        self._W_dirty = False
        self.stats["syn"] = len(self._syn_rows)

    # ── Simulation ────────────────────────────────────────────────────────────

    def _sim_loop(self):
        """Boucle LIF — PyTorch GPU quand disponible."""
        trace_tick = 100.0
        while True:
            if not self._gpu_ready:
                time.sleep(0.001); continue

            with self._lock:
                n = self._gpu_n
                if n == 0: time.sleep(0.001); continue

                self.sim_t += DT
                t = self.sim_t

                # ── PSP du tick precedent
                if self._psp_buf is not None:
                    try:
                        pn = min(len(self._psp_buf), n, self._gpu_n)
                        if pn > 0:
                            if TORCH_OK:
                                self._V_gpu[:pn] = self._V_gpu[:pn] + self._psp_buf[:pn].to(torch.float64) * 6.0
                            else:
                                self._V_gpu[:pn] = self._V_gpu[:pn] + self._psp_buf[:pn] * 6.0
                    except Exception: pass
                    self._psp_buf = None

                # ── LIF GPU vectorise
                if TORCH_OK:
                    not_ref = (t - self._tL_gpu[:n]) >= T_REFRAC
                    noise   = torch.randn(n, dtype=torch.float64, device=DEVICE) * 0.35
                    dV      = (-(self._V_gpu[:n] - VR) / TAU_M + self._dr_gpu[:n]) * DT + noise
                    self._V_gpu[:n] = torch.where(not_ref, self._V_gpu[:n] + dV,
                                                  torch.full((n,), VZ, dtype=torch.float64, device=DEVICE))
                    sp_mask   = (self._V_gpu[:n] >= VT) & not_ref
                    spike_idx = torch.where(sp_mask)[0]
                    spk       = int(spike_idx.shape[0])
                    self._V_gpu[:n][sp_mask]  = VZ
                    self._tL_gpu[:n][sp_mask] = t
                    self._ls_gpu[:n][sp_mask] = t
                    self._fc_gpu[:n][sp_mask] = self._fc_gpu[:n][sp_mask] + 1
                    self._gl_gpu[:n][sp_mask]  = 1.0
                    self._gl_gpu[:n][~sp_mask] = self._gl_gpu[:n][~sp_mask] * 0.91
                else:
                    not_ref = (t - self._tL_gpu[:n]) >= T_REFRAC
                    noise   = np.random.normal(0, 0.35, n)
                    dV      = (-(self._V_gpu[:n] - VR) / TAU_M + self._dr_gpu[:n]) * DT + noise
                    self._V_gpu[:n] = np.where(not_ref, self._V_gpu[:n] + dV, VZ)
                    sp_mask   = (self._V_gpu[:n] >= VT) & not_ref
                    spike_idx = np.where(sp_mask)[0]
                    spk       = len(spike_idx)
                    self._V_gpu[:n][sp_mask]  = VZ
                    self._tL_gpu[:n][sp_mask] = t
                    self._ls_gpu[:n][sp_mask] = t
                    self._fc_gpu[:n][sp_mask] += 1
                    self._gl_gpu[:n][sp_mask]  = 1.0
                    self._gl_gpu[:n][~sp_mask] *= 0.91

                # ── PSP via sparse matmul GPU
                if spk > 0:
                    if self._W_gpu is not None and TORCH_OK:
                        try:
                            if self._W_gpu.shape[0] == n:
                                sp_vec = torch.zeros(n, dtype=torch.float32, device=DEVICE)
                                sp_vec[spike_idx] = 1.0
                                psp = torch.mv(self._W_gpu.to(torch.float32).t(), sp_vec)
                                self._psp_buf = psp
                        except Exception as e:
                            # Fallback scipy
                            if self._W_csr is not None and self._W_csr.shape[0] == n:
                                sp_v = np.zeros(n, dtype=np.float32)
                                sp_v[spike_idx.cpu().numpy()] = 1.0
                                psp_np = self._W_csr.T.dot(sp_v)
                                self._psp_buf = torch.tensor(psp_np, device=DEVICE)
                    elif self._W_csr is not None:
                        if self._W_csr.shape[0] == n:
                            sp_v = np.zeros(n, dtype=np.float32)
                            if TORCH_OK:
                                sp_v[spike_idx.cpu().numpy()] = 1.0
                            else:
                                sp_v[spike_idx] = 1.0
                            psp_np = self._W_csr.T.dot(sp_v)
                            self._psp_buf = psp_np if not TORCH_OK else torch.tensor(psp_np, device=DEVICE)

                # ── Signaux + trace
                new_sigs = []
                if spk > 0:
                    si = spike_idx[:5]
                    if TORCH_OK: si = si.cpu().numpy()
                    for i in si:
                        mn = self.mod_names[int(self._mod_cpu[i])]
                        others = [m for m in self.mod_names if m != mn]
                        if others and len(new_sigs)<20:
                            new_sigs.append({"fm":mn,"tm":random.choice(others),"p":0.0,"c":self.mod_colors.get(mn,"#fff")})
                        self.mod_acc[mn] = self.mod_acc.get(mn,0)+1

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

                hz = round(spk/max(n*DT/1000.0, 1e-9), 1)
                self.stats.update({
                    "N":n,"spk":spk,"hz":hz,"growth":self._growth,
                    "hebb":self._hebb_count,"stdp":self._stdp_count,
                    "kg_concepts":len(self.kg.nodes),
                    "resonance_events":self._resonance_events,
                    "gpu":GPU_OK,"gpu_name":GPU_NAME,
                })

            time.sleep(0.0005)  # 0.5ms → 2000 Hz theorique

    # ── STDP + Hebbian ────────────────────────────────────────────────────────

    def _learn_loop(self):
        while True:
            time.sleep(0.05)
            with self._grow_lock:
                n = self._gpu_n
                if n < 2 or not self._syn_rows: continue
                t = self.sim_t
                n_sample = min(10000, len(self._syn_rows))
                idxs = np.random.choice(len(self._syn_rows), n_sample, replace=False)
                s_arr = np.array([self._syn_rows[k] for k in idxs], dtype=np.int32)
                t_arr = np.array([self._syn_cols[k] for k in idxs], dtype=np.int32)
                w_arr = np.array([self._syn_vals[k] for k in idxs], dtype=np.float64)
                valid = (s_arr < n) & (t_arr < n)
                s_v=s_arr[valid]; t_v=t_arr[valid]; w_v=w_arr[valid]; iv=idxs[valid]
                if len(s_v)==0: continue
                # Recuperer last spikes
                if TORCH_OK:
                    ls_s = self._ls_gpu[s_v].cpu().numpy()
                    ls_t = self._ls_gpu[t_v].cpu().numpy()
                else:
                    ls_s = self._ls_gpu[s_v]; ls_t = self._ls_gpu[t_v]
                dt_sp = t - ls_s
                hebb = (dt_sp < 2.0) & ((t - ls_t) < 2.0)
                w_v[hebb] += HEBBIAN_LR*(1.0-np.abs(w_v[hebb]))
                ltp = (dt_sp>0) & (dt_sp<STDP_WIN)
                w_v[ltp] += STDP_LR*np.exp(-dt_sp[ltp]/STDP_WIN)*0.5
                ltd = (dt_sp<0) & (dt_sp>-STDP_WIN)
                w_v[ltd] += -STDP_LR*np.exp(dt_sp[ltd]/STDP_WIN)*0.3
                w_v *= (1.0-W_DECAY)
                signs = np.sign(w_v); signs[signs==0]=1
                w_v = signs*np.clip(np.abs(w_v), W_MIN, W_MAX)
                for k_l, k_g in enumerate(iv): self._syn_vals[k_g]=float(w_v[k_l])
                self._hebb_count+=int(np.sum(hebb)); self._stdp_count+=int(np.sum(ltp))
                self._W_dirty=True

            if time.time()-self._last_learn>8.0:
                self._last_learn=time.time()
                result=self.crawler.pop_result()
                if result:
                    mn=result["module"] if result["module"] in self.mod_names else self.mod_names[0]
                    self._neuron_queue.extend([mn]*random.randint(8,20))
                    self.kg.add_concept(result["label"].lower().replace(" ","_"),mn,2.0)
                    self.kg.reinforce(result["label"].lower().replace(" ","_"),0.05)

    # ── Neurogenese non-bloquante ─────────────────────────────────────────────

    def _integrate_loop(self):
        """Integre les nouveaux neurones toutes les 2s sans bloquer la sim."""
        while True:
            time.sleep(2.0)
            if not self._neuron_queue: continue
            batch = []
            while self._neuron_queue and len(batch)<50:
                batch.append(self._neuron_queue.popleft())
            if not batch: continue
            with self._grow_lock:
                n_before = self.N
                for mod_name in batch:
                    if self.N >= MAX_NEURONS: break
                    i = self._add_neuron_cpu(mod_name)
                    if i < 0: continue
                    tgts = [mod_name]+[m for m in self.mod_names if m!=mod_name][:3]
                    for tm in tgts:
                        ex = [j for j in range(n_before) if self._mod_cpu[j]==self.mod_idx.get(tm,0)]
                        if not ex: continue
                        for j in random.sample(ex, min(5,len(ex))):
                            w=random.uniform(0.15,0.65)*float(self._exc_cpu[i])
                            self._syn_rows.append(i); self._syn_cols.append(j); self._syn_vals.append(w)
                            w2=random.uniform(0.15,0.65)*float(self._exc_cpu[j])
                            self._syn_rows.append(j); self._syn_cols.append(i); self._syn_vals.append(w2)
                    self._growth+=1
                # Re-upload GPU seulement si N <= 500
                if self.N <= 5000:
                    with self._lock:
                        self._upload_gpu()

    def _grow_loop(self):
        while True:
            hz=self.stats.get("hz",0)
            time.sleep(BASE_GROW_INTERVAL*(4.0 if hz>1000 else 3.0 if hz>500 else 2.0 if hz>200 else 1.0))
            if self.N>=3000: continue  # Palier 3000
            if TORCH_OK and self._gpu_ready:
                acts={nm:float(self._gl_gpu[np.where(self._mod_cpu[:self.N]==self.mod_idx[nm])[0]].mean().cpu()) if np.any(self._mod_cpu[:self.N]==self.mod_idx[nm]) else 0.0 for nm in self.mod_names}
            else:
                acts={nm:0.0 for nm in self.mod_names}
            top=max(acts,key=acts.get)
            self._neuron_queue.extend([top]*random.randint(3,8))

    # ── Persistance ───────────────────────────────────────────────────────────

    def _save_state(self):
        if self._gpu_ready and TORCH_OK and self._gpu_n>0:
            n=self._gpu_n
            self._V_cpu[:n]  = self._V_gpu[:n].cpu().numpy()
            self._tL_cpu[:n] = self._tL_gpu[:n].cpu().numpy()
            self._fc_cpu[:n] = self._fc_gpu[:n].cpu().numpy()
        _save_json(self.state_file, {"N":self.N,"growth":self._growth,"stdp":self._stdp_count,"last_save":time.time()})
        self.kg.save()
        try:
            np.savez_compressed(str(self.neurons_file),
                V=self._V_cpu[:self.N],tL=self._tL_cpu[:self.N],
                drive=self._dr_cpu[:self.N],exc=self._exc_cpu[:self.N],
                fc=self._fc_cpu[:self.N],mod_of=self._mod_cpu[:self.N],
                rx=self._rx_cpu[:self.N],ry=self._ry_cpu[:self.N],rz=self._rz_cpu[:self.N],
                syn_rows=np.array(self._syn_rows,dtype=np.int32),
                syn_cols=np.array(self._syn_cols,dtype=np.int32),
                syn_vals=np.array(self._syn_vals,dtype=np.float32))
        except Exception as e: print(f"[{self.name}] NPZ save failed: {e}")

    def _load_state(self):
        npz=str(self.neurons_file)
        if not npz.endswith(".npz"): npz+=".npz"
        try:
            data=np.load(npz); ns=len(data["V"]); nr=min(ns,self.N)
            self._V_cpu[:nr]=data["V"][:nr]; self._tL_cpu[:nr]=data["tL"][:nr]
            self._dr_cpu[:nr]=data["drive"][:nr]; self._fc_cpu[:nr]=data["fc"][:nr]
            for i in range(self.N, min(self.N+max(0,ns-self.N), MAX_NEURONS)):
                j=i-self.N+nr
                if j>=ns: break
                mn=self.mod_names[int(data["mod_of"][j])%len(self.mod_names)]
                ni=self._add_neuron_cpu(mn)
                if ni>=0:
                    self._V_cpu[ni]=float(data["V"][j]); self._tL_cpu[ni]=float(data["tL"][j])
                    self._dr_cpu[ni]=float(data["drive"][j]); self._fc_cpu[ni]=int(data["fc"][j])
            if "syn_rows" in data and len(data["syn_rows"])>0:
                self._syn_rows=list(data["syn_rows"]); self._syn_cols=list(data["syn_cols"]); self._syn_vals=list(data["syn_vals"])
            print(f"[{self.name}] {self.N} neurones restaures, {len(self._syn_rows)} synapses")
        except Exception as e: print(f"[{self.name}] Pas de sauvegarde: {e}")
        self._upload_gpu()
        state=_load_json(self.state_file,{})
        self._growth=state.get("growth",0); self._stdp_count=state.get("stdp",0)

    def _save_loop(self):
        tick=0
        while True:
            time.sleep(30)
            with self._grow_lock:
                self._save_state()
            tick+=1

    # ── API ───────────────────────────────────────────────────────────────────

    def learn_topic_api(self, topic):
        best_mod=self.mod_names[0]
        for word in topic.lower().split():
            for mn in self.mod_names:
                if word in mn: best_mod=mn; break
        n_new=random.randint(10,25)
        self._neuron_queue.extend([best_mod]*n_new)
        self.kg.add_concept(topic.replace(" ","_"),best_mod,2.0)
        self.kg.reinforce(topic.replace(" ","_"),0.08)
        self.kg.save()
        return {"ok":True,"topic":topic,"module":best_mod,"new_neurons":n_new}

    def query(self, question, top=10):
        words=question.lower().replace("?","").replace(",","").split()
        scores={}
        for concept,info in self.kg.nodes.items():
            score=sum(1.0+info.get("mastery",0) for w in words if len(w)>3 and w in concept.lower().replace("_"," "))
            if score>0: scores[concept]={"score":round(score,3),"module":info.get("module","?"),"mastery":round(info.get("mastery",0),3)}
        ranked=sorted(scores.items(),key=lambda x:x[1]["score"],reverse=True)[:top]
        ms={}
        for _,v in ranked: ms[v["module"]]=ms.get(v["module"],0)+v["score"]
        am=sum(v["mastery"] for _,v in ranked)/max(1,len(ranked))
        return {"brain":self.name,"concepts_found":len(ranked),"top_concepts":[{"concept":k,**v} for k,v in ranked],"best_modules":[{"module":m,"score":round(s,2)} for m,s in sorted(ms.items(),key=lambda x:x[1],reverse=True)[:3]],"confidence":"high" if am>0.7 else "medium" if am>0.3 else "low","avg_mastery":round(am,3),"brain_state":{"N":self.stats["N"],"hz":self.stats["hz"],"gpu":GPU_OK}}


# ── Flask App ─────────────────────────────────────────────────────────────────

def create_app(brain):
    app=Flask(__name__)

    @app.route("/api/stats")
    def stats(): return jsonify(brain.stats)

    @app.route("/api/learn",methods=["POST"])
    def learn():
        data=request.get_json() or {}; t=data.get("topic","").strip()
        if not t: return jsonify({"ok":False,"error":"no topic"})
        return jsonify(brain.learn_topic_api(t))

    @app.route("/api/query",methods=["POST"])
    def query():
        data=request.get_json() or {}; q=data.get("question","")
        if not q: return jsonify({"ok":False,"error":"no question"})
        return jsonify(brain.query(q,data.get("top",10)))

    @app.route("/api/think",methods=["POST"])
    def think():
        data=request.get_json() or {}; task=data.get("task",""); ctx=data.get("context","")
        if not task: return jsonify({"ok":False,"error":"no task"})
        result=brain.query(task+" "+ctx,15)
        if len(result.get("best_modules",[]))>=2:
            a=result["best_modules"][0]["module"]; b=result["best_modules"][1]["module"]
            if a in brain.mod_names and b in brain.mod_names:
                brain._neuron_queue.extend([a]*RESONANCE_BOOST//2+[b]*RESONANCE_BOOST//2)
                brain._resonance_events+=1
        return jsonify({**result,"task":task})

    @app.route("/api/feedback",methods=["POST"])
    def feedback():
        data=request.get_json() or {}; success=data.get("success",True); concepts=data.get("concepts_used",[])
        reinforced,weakened=[],[]
        for c in concepts:
            k=c.replace(" ","_").lower()
            if k in brain.kg.nodes:
                if success: brain.kg.reinforce(k,0.05); reinforced.append(k)
                else: brain.kg.nodes[k]["mastery"]=max(0.0,brain.kg.nodes[k]["mastery"]-0.02); weakened.append(k)
        brain.kg.save()
        return jsonify({"ok":True,"success":success,"reinforced":reinforced,"weakened":weakened})

    @app.route("/api/kg")
    def kg(): return jsonify({"stats":brain.kg.stats(),"nodes":list(brain.kg.nodes.items())[:50]})

    @app.route("/api/gpu")
    def gpu_info():
        info={"gpu_available":GPU_OK,"gpu_name":GPU_NAME,"backend":"PyTorch" if TORCH_OK else "NumPy"}
        if GPU_OK and TORCH_OK:
            try:
                info["vram_total_mb"]=round(torch.cuda.get_device_properties(0).total_memory/1024**2)
                info["vram_used_mb"]=round(torch.cuda.memory_allocated()/1024**2)
                info["vram_free_mb"]=info["vram_total_mb"]-info["vram_used_mb"]
            except: pass
        return jsonify(info)

    return app


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--brain",required=True,choices=list(BRAIN_CONFIGS.keys()))
    parser.add_argument("--port",type=int,default=None)
    parser.add_argument("--no-web",action="store_true")
    args=parser.parse_args()
    cfg=BRAIN_CONFIGS[args.brain]; port=args.port or cfg["port"]
    brain=BrainV11(cfg,web_enabled=not args.no_web)
    app=create_app(brain)
    import signal
    def _shutdown(s,f): print(f"[{brain.name}] Sauvegarde..."); brain._save_state(); exit(0)
    signal.signal(signal.SIGTERM,_shutdown)
    print(f"\n{brain.name} v11 — port {port} — {'GPU '+GPU_NAME if GPU_OK else 'CPU'}")
    app.run(host="0.0.0.0",port=port,threaded=True)
