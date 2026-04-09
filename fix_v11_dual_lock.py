#!/usr/bin/env python3
"""
Fix brain_v11.py — Dual lock architecture
- _sim_lock : simulation uniquement (jamais bloqué par neurogenese)
- _grow_lock: neurogenese + rebuild CSR
- Simulation continue même pendant rebuild GPU
"""
import ast, shutil, time, re

SRC = "/mnt/nvme/soullink_brain/brain_v11.py"
shutil.copy(SRC, f"{SRC}.bk_duallock_{int(time.time())}")
with open(SRC) as f:
    content = f.read()

# 1. Remplacer l'init du lock unique par deux locks
old1 = "        self._lock       = threading.Lock()\n        self._last_learn = time.time()"
new1 = """        self._lock       = threading.Lock()   # lock principal (sim)
        self._grow_lock  = threading.Lock()   # lock neurogenese separee
        self._last_learn = time.time()"""
assert old1 in content, "ERR1"
content = content.replace(old1, new1, 1)
print("OK 1 - dual lock init")

# 2. _integrate_loop — utiliser _grow_lock au lieu de _lock
old2 = "    def _integrate_loop(self):\n        \"\"\"Integre les nouveaux neurones toutes les 2s sans bloquer la sim.\"\"\"\n        while True:\n            time.sleep(2.0)\n            if not self._neuron_queue: continue\n            batch = []\n            while self._neuron_queue and len(batch)<50:\n                batch.append(self._neuron_queue.popleft())\n            if not batch: continue\n            with self._lock:"
new2 = """    def _integrate_loop(self):
        \"\"\"Integre les nouveaux neurones toutes les 2s sans bloquer la sim.\"\"\"
        while True:
            time.sleep(2.0)
            if not self._neuron_queue: continue
            batch = []
            while self._neuron_queue and len(batch)<50:
                batch.append(self._neuron_queue.popleft())
            if not batch: continue
            with self._grow_lock:"""
assert old2 in content, "ERR2"
content = content.replace(old2, new2, 1)
print("OK 2 - _integrate_loop utilise _grow_lock")

# 3. Dans _integrate_loop, l'upload GPU doit prendre les deux locks
old3 = "                # Re-upload GPU\n                self._upload_gpu()"
new3 = """                # Re-upload GPU — prendre sim lock brievement
                with self._lock:
                    self._upload_gpu()"""
assert old3 in content, "ERR3"
content = content.replace(old3, new3, 1)
print("OK 3 - upload GPU avec sim lock")

# 4. _grow_loop utilise _grow_lock
old4 = "    def _grow_loop(self):\n        while True:\n            hz=self.stats.get(\"hz\",0)\n            time.sleep(BASE_GROW_INTERVAL*(4.0 if hz>1000 else 3.0 if hz>500 else 2.0 if hz>200 else 1.0))\n            if self.N>=5000: continue  # Plafond Hz stable\n            if TORCH_OK and self._gpu_ready:"
new4 = """    def _grow_loop(self):
        while True:
            hz=self.stats.get("hz",0)
            time.sleep(BASE_GROW_INTERVAL*(4.0 if hz>1000 else 3.0 if hz>500 else 2.0 if hz>200 else 1.0))
            if self.N>=5000: continue  # Plafond Hz stable
            if TORCH_OK and self._gpu_ready:"""
# Ce pattern existe deja, juste verifier
if old4 in content:
    print("OK 4 - _grow_loop pattern OK")
else:
    print("WARN 4 - _grow_loop pattern different (pas critique)")

# 5. _save_loop — utiliser _grow_lock pour save
old5 = "    def _save_loop(self):\n        tick=0\n        while True:\n            time.sleep(30)\n            with self._lock: self._save_state()"
new5 = """    def _save_loop(self):
        tick=0
        while True:
            time.sleep(30)
            with self._grow_lock:
                self._save_state()"""
assert old5 in content, "ERR5"
content = content.replace(old5, new5, 1)
print("OK 5 - _save_loop utilise _grow_lock")

# 6. _learn_loop — utiliser _grow_lock pour STDP
old6 = "    def _learn_loop(self):\n        while True:\n            time.sleep(0.05)\n            with self._lock:"
new6 = """    def _learn_loop(self):
        while True:
            time.sleep(0.05)
            with self._grow_lock:"""
assert old6 in content, "ERR6"
content = content.replace(old6, new6, 1)
print("OK 6 - _learn_loop utilise _grow_lock")

ast.parse(content)
with open(SRC, 'w') as f:
    f.write(content)
print("\nDUAL LOCK APPLIQUE — syntaxe OK")
