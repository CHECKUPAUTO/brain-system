#!/usr/bin/env python3
"""
SoulLink Brain v8.5 — PERSISTANCE CORRIGÉE

Ce fichier CORRIGE le bug de persistance:
- Sauvegarde COMPLÈTE des neurones (positions, modules, états)
- Sauvegarde COMPLÈTE des synapses (source, target, poids, délai)
- Restauration au démarrage
- Le nombre de neurones ne diminue JAMAIS

Usage:
    python brain_v8.5_persistence.py --port 8084
    
Testé et validé avant déploiement.
"""

import json
import math
import random
import threading
import time
from pathlib import Path
from flask import Flask, Response, request, send_from_directory

# ═══════════════════════════════════════════════════════════════════════════
# PERSISTANCE
# ═══════════════════════════════════════════════════════════════════════════

PERSIST_PATH = Path("/mnt/nvme/soullink_brain")
PERSIST_PATH.mkdir(parents=True, exist_ok=True)
STATE_FILE = PERSIST_PATH / "brain_state.json"

def load_state():
    """Charge l'état COMPLET depuis la sauvegarde"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                neurons = data.get('neurons', [])
                synapses = data.get('synapses', [])
                print(f"📂 État chargé: {len(neurons)} neurones, {len(synapses)} synapses")
                print(f"   total_neurons: {data.get('total_neurons', 0)}, growth: {data.get('growth_events', 0)}")
                return data
        except Exception as e:
            print(f"⚠️ Erreur chargement état: {e}")
    # État par défaut
    return {
        "total_neurons": 0,
        "growth_events": 0,
        "total_spikes": 0,
        "last_save": 0,
        "neurons": [],
        "synapses": []
    }

def save_state(state):
    """Sauvegarde l'état COMPLET"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"💾 État sauvegardé: {len(state.get('neurons', []))} neurones, {len(state.get('synapses', []))} synapses")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde: {e}")

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION LIF
# ═══════════════════════════════════════════════════════════════════════════

VR = -70    # Potentiel de repos
VT = -55    # Seuil de décharge
VZ = -75    # Potentiel de reset
TAU = 20    # Constante de temps
TREF = 3    # Période réfractaire
DT = 0.5    # Pas de temps

# Configuration des modules
MODULES = [
    ['perception', 20, '#3dffc0', 0.15, [-158, 82, 78]],
    ['memory',     28, '#3d9eff', 0.20, [18, 128, -82]],
    ['reasoning',  22, '#ff5577', 0.20, [168, 62, 42]],
    ['learning',   16, '#ff9944', 0.15, [-88, -42, 118]],
    ['attention',  12, '#cc44ff', 0.25, [88, 28, 88]],
    ['output',     14, '#aaff44', 0.15, [208, -32, -48]],
    ['language',   18, '#44ffff', 0.20, [-208, -62, -28]],
    ['vision',     15, '#ff6644', 0.15, [-48, -122, -62]],
    ['audio',      12, '#6677ff', 0.15, [112, -108, -88]],
    ['motor',      10, '#ffee44', 0.10, [238, -88, 68]],
]

# Connexions inter-modules
WIRES = {
    'perception': ['memory', 'attention', 'vision', 'language'],
    'memory': ['reasoning', 'learning', 'language', 'perception'],
    'reasoning': ['output', 'attention', 'memory'],
    'learning': ['memory', 'reasoning', 'perception'],
    'attention': ['perception', 'reasoning', 'vision', 'audio'],
    'output': ['motor', 'language'],
    'language': ['memory', 'output', 'perception'],
    'vision': ['perception', 'attention', 'motor'],
    'audio': ['attention', 'language', 'memory'],
    'motor': ['output', 'vision'],
}

class Brain:
    def __init__(self):
        self.modules = {}
        self.neurons = []
        self.synapses = []
        self.adj = {}
        self.signals = []
        self.stats = {'N': 0, 'syn': 0, 'spk': 0, 'hz': 0, 'growth': 0, 'sig': 0}
        self.sim_time = 0.0
        self.lock = threading.Lock()
        
        # CHARGER l'état précédent
        self.persistent = load_state()
        self.total_neurons = self.persistent.get('total_neurons', 0)
        self.growth_events = self.persistent.get('growth_events', 0)
        self.total_spikes = self.persistent.get('total_spikes', 0)
        self.last_save_time = time.time()
        
        # Initialiser les modules
        self._init_modules()
        
        # RESTAURER ou CRÉER les neurones
        saved_neurons = self.persistent.get('neurons', [])
        saved_synapses = self.persistent.get('synapses', [])
        
        if len(saved_neurons) > 0:
            print(f"🔄 Restauration de {len(saved_neurons)} neurones sauvegardés...")
            self._restore_neurons(saved_neurons)
            print(f"✅ {len(self.neurons)} neurones restaurés")
        else:
            print("🧠 Création initiale des neurones...")
            self._create_neurons()
            print(f"✅ {len(self.neurons)} neurones créés")
        
        if len(saved_synapses) > 0 and len(self.neurons) > 0:
            print(f"🔄 Restauration de {len(saved_synapses)} synapses...")
            self._restore_synapses(saved_synapses)
            print(f"✅ {len(self.synapses)} synapses restaurées")
        else:
            print("🧠 Création initiale des synapses...")
            self._create_synapses()
            print(f"✅ {len(self.synapses)} synapses créées")
        
        # Mettre à jour les stats
        self.stats['N'] = len(self.neurons)
        self.stats['syn'] = len(self.synapses)
        self.stats['growth'] = self.growth_events
        
        print(f"🧠 SoulLink Brain v8.5 — Persistance CORRIGÉE")
        print(f"   Modules: {len(self.modules)}")
        print(f"   Neurones: {len(self.neurons)} (actuels)")
        print(f"   Neurones totaux: {self.total_neurons} (historique)")
        print(f"   Synapses: {len(self.synapses)}")
        print(f"   Port: 8084")
    
    def _init_modules(self):
        """Initialise les modules"""
        for name, n, color, inh, pos in MODULES:
            self.modules[name] = {
                'name': name,
                'color': color,
                'pos': pos,
                'n': n,
                'inh': inh,
                'neurons': [],
                'driftPhase': random.random() * math.pi * 2,
            }
    
    def _create_neurons(self):
        """Crée les neurones initiaux"""
        for mod_name, mod in self.modules.items():
            r = 52 + mod['n'] * 1.4
            for i in range(mod['n']):
                is_inhib = random.random() < mod['inh']
                neuron = {
                    'id': f"{mod_name[:3]}_{i:03d}",
                    'mod': mod_name,
                    'exc': not is_inhib,
                    'v': VR + random.gauss(0, 6),
                    'tL': -9999,
                    'sp': False,
                    'drive': 0.7 + random.random() * 2.2,
                    'imp': 0.3 + random.random() * 0.7,
                    'glow': 0,
                    'vn': 0,
                    'fc': 0,
                    'rx': random.gauss(0, r * 0.5),
                    'ry': random.gauss(0, r * 0.5),
                    'rz': random.gauss(0, r * 0.5),
                }
                self.neurons.append(neuron)
                self.adj[neuron['id']] = []
                mod['neurons'].append(neuron)
        
        self.stats['N'] = len(self.neurons)
        self.total_neurons = max(self.total_neurons, len(self.neurons))
    
    def _restore_neurons(self, saved_neurons):
        """Restaure les neurones depuis la sauvegarde"""
        # Créer un index des modules
        for mod_name, mod in self.modules.items():
            mod['neurons'] = []
        
        for sn in saved_neurons:
            mod_name = sn['mod']
            if mod_name not in self.modules:
                continue
            
            mod = self.modules[mod_name]
            neuron = {
                'id': sn['id'],
                'mod': mod_name,
                'exc': sn['exc'],
                'v': sn['v'],
                'tL': sn.get('tL', -9999),
                'sp': sn.get('sp', False),
                'drive': sn.get('drive', 0.7 + random.random() * 2.2),
                'imp': sn.get('imp', 0.3 + random.random() * 0.7),
                'glow': sn.get('glow', 0),
                'vn': sn.get('vn', 0),
                'fc': sn.get('fc', 0),
                'rx': sn['rx'],
                'ry': sn['ry'],
                'rz': sn['rz'],
            }
            self.neurons.append(neuron)
            self.adj[neuron['id']] = []
            mod['neurons'].append(neuron)
        
        self.stats['N'] = len(self.neurons)
        # Mettre à jour le total_neurons si nécessaire
        if len(self.neurons) > self.total_neurons:
            self.total_neurons = len(self.neurons)
    
    def _create_synapses(self):
        """Crée les synapses initiales"""
        def rand_neuron(mod_name):
            return random.choice(self.modules[mod_name]['neurons'])
        
        def add_syn(s, t):
            raw = 0.15 + random.random() * 0.55
            w = raw if s['exc'] else -raw * 0.7
            d = 1 + random.random() * 8
            self.synapses.append({'s': s, 't': t, 'w': w, 'd': d})
            self.adj[s['id']].append({'t': t, 'w': w, 'd': d})
        
        for src_name, targets in WIRES.items():
            for tgt_name in targets:
                for _ in range(6 + random.randint(0, 6)):
                    add_syn(rand_neuron(src_name), rand_neuron(tgt_name))
        
        for mod in self.modules.values():
            for _ in range(len(mod['neurons']) * 3):
                a = random.choice(mod['neurons'])
                b = random.choice(mod['neurons'])
                if a != b:
                    add_syn(a, b)
        
        self.stats['syn'] = len(self.synapses)
    
    def _restore_synapses(self, saved_synapses):
        """Restaure les synapses depuis la sauvegarde"""
        # Index des neurones par ID
        neuron_index = {n['id']: n for n in self.neurons}
        
        for ss in saved_synapses:
            src_id = ss['s']
            tgt_id = ss['t']
            
            if src_id in neuron_index and tgt_id in neuron_index:
                src = neuron_index[src_id]
                tgt = neuron_index[tgt_id]
                synapse = {
                    's': src,
                    't': tgt,
                    'w': ss['w'],
                    'd': ss['d'],
                }
                self.synapses.append(synapse)
                self.adj[src_id].append({'t': tgt, 'w': ss['w'], 'd': ss['d']})
        
        self.stats['syn'] = len(self.synapses)
    
    def grow(self):
        """Croissance: ajoute un neurone dans un module aléatoire"""
        mod_name = random.choice(list(self.modules.keys()))
        mod = self.modules[mod_name]
        r = 52 + mod['n'] * 1.4
        
        is_inhib = random.random() < mod['inh']
        neuron = {
            'id': f"{mod_name[:3]}_{len(mod['neurons']):03d}",
            'mod': mod_name,
            'exc': not is_inhib,
            'v': VR + random.gauss(0, 6),
            'tL': -9999,
            'sp': False,
            'drive': 0.7 + random.random() * 2.2,
            'imp': 0.3 + random.random() * 0.7,
            'glow': 0,
            'vn': 0,
            'fc': 0,
            'rx': random.gauss(0, r * 0.5),
            'ry': random.gauss(0, r * 0.5),
            'rz': random.gauss(0, r * 0.5),
        }
        
        self.neurons.append(neuron)
        self.adj[neuron['id']] = []
        mod['neurons'].append(neuron)
        
        # Connecter le nouveau neurone
        other = random.choice(self.neurons)
        self.synapses.append({'s': neuron, 't': other, 'w': 0.3, 'd': 5})
        self.adj[neuron['id']].append({'t': other, 'w': 0.3, 'd': 5})
        
        for _ in range(random.randint(1, 3)):
            other = random.choice(self.neurons)
            if other != neuron:
                w = 0.2 + random.random() * 0.3
                self.synapses.append({'s': other, 't': neuron, 'w': w, 'd': 3})
                self.adj[other['id']].append({'t': neuron, 'w': w, 'd': 3})
        
        self.stats['N'] = len(self.neurons)
        self.stats['syn'] = len(self.synapses)
        self.stats['growth'] += 1
        self.total_neurons = max(self.total_neurons, self.stats['N'])
        self.growth_events += 1
    
    def step(self):
        """Simulation LIF - un step"""
        self.sim_time += DT
        spikes = 0
        new_signals = []
        
        for n in self.neurons:
            if n['tL'] > self.sim_time - TREF:
                continue
            
            n['v'] += DT * (n['drive'] - n['v']) / TAU
            
            for conn in self.adj[n['id']]:
                n['v'] += conn['w'] * n.get('vn', 0)
            
            if n['v'] > VT:
                n['sp'] = True
                n['tL'] = self.sim_time
                n['v'] = VZ
                spikes += 1
                n['glow'] = min(1, n['glow'] + 0.3)
                n['fc'] += 1
                
                src_mod = n['mod']
                # Obtenir la couleur du module
                mod = self.modules.get(src_mod)
                color = mod['color'] if mod else '#ffffff'
                for tgt in self.modules:
                    if random.random() < 0.1:
                        new_signals.append({
                            'from_mod': src_mod,
                            'to_mod': tgt,
                            'progress': 0,
                            'color': color if n['exc'] else '#ff4444',
                        })
            else:
                n['sp'] = False
        
        for s in self.signals[:]:
            s['progress'] += 0.1
            if s['progress'] >= 1:
                self.signals.remove(s)
                tgt_mod = self.modules.get(s['to_mod'])
                if tgt_mod and tgt_mod['neurons']:
                    n = random.choice(tgt_mod['neurons'])
                    n['v'] += 0.5 if random.random() < 0.5 else -0.3
        
        self.signals.extend(new_signals)
        self.stats['spk'] = spikes
        self.stats['hz'] = spikes / DT
        self.stats['sig'] = len(self.signals)
    
    def to_json(self):
        """Export state for frontend"""
        return {
            'modules': {name: {
                'name': m['name'],
                'color': m['color'],
                'pos': m['pos'],
                'n': len(m['neurons']),
                'driftPhase': m['driftPhase'],
            } for name, m in self.modules.items()},
            'neurons': [{
                'id': n['id'],
                'mod': n['mod'],
                'exc': n['exc'],
                'v': round(n['v'], 2),
                'glow': round(n['glow'], 3),
                'vn': round(n['vn'], 3),
                'fc': n['fc'],
                'rx': round(n['rx'], 2),
                'ry': round(n['ry'], 2),
                'rz': round(n['rz'], 2),
                'sp': n['sp'],
                'drive': round(n['drive'], 2),
                'imp': round(n['imp'], 2),
            } for n in self.neurons],
            'signals': [{
                'from_mod': s['from_mod'],
                'to_mod': s['to_mod'],
                'progress': round(s['progress'], 2),
                'color': s['color'],
            } for s in self.signals[:100]],
            'stats': {
                'N': self.stats['N'],
                'syn': self.stats['syn'],
                'spk': self.stats['spk'],
                'sig': self.stats['sig'],
                'hz': self.stats['hz'],
                'growth': self.stats['growth'],
                'total_neurons': self.total_neurons,
                'total_spikes': self.total_spikes,
            },
            'sim_time': round(self.sim_time, 1),
        }
    
    def save_full_state(self):
        """Sauvegarde COMPLÈTE de l'état"""
        state = {
            'total_neurons': self.total_neurons,
            'growth_events': self.growth_events,
            'total_spikes': self.total_spikes,
            'last_save': time.time(),
            'neurons': [{
                'id': n['id'],
                'mod': n['mod'],
                'exc': n['exc'],
                'v': float(n['v']),
                'rx': float(n['rx']),
                'ry': float(n['ry']),
                'rz': float(n['rz']),
                'glow': float(n.get('glow', 0)),
                'vn': float(n.get('vn', 0)),
                'fc': n.get('fc', 0),
                'drive': float(n.get('drive', 1.0)),
                'imp': float(n.get('imp', 0.5)),
                'tL': float(n.get('tL', -9999)),
                'sp': n.get('sp', False),
            } for n in self.neurons],
            'synapses': [{
                's': s['s']['id'],
                't': s['t']['id'],
                'w': float(s['w']),
                'd': float(s['d']),
            } for s in self.synapses],
        }
        save_state(state)

# ═══════════════════════════════════════════════════════════════════════════
# INTERFACE HTML
# ═══════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>SoulLink Brain v8.5</title>
    <script src="/three.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a12; color: #fff; font-family: 'Segoe UI', sans-serif; overflow: hidden; }
        #canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; }
        .hud { position: fixed; z-index: 100; background: rgba(10,10,18,0.85); border-radius: 12px; padding: 15px; }
        #stats { top: 20px; left: 20px; border: 1px solid #3d9eff; }
        #stats h2 { color: #3d9eff; margin-bottom: 10px; }
        #stats .stat { display: flex; justify-content: space-between; margin: 5px 0; }
        #stats .label { color: #888; }
        #stats .value { color: #fff; font-weight: bold; }
        #modules { top: 20px; right: 20px; border: 1px solid #ff5577; max-height: 350px; overflow-y: auto; }
        #modules h3 { color: #ff5577; margin-bottom: 10px; }
        #modules .mod { display: flex; align-items: center; margin: 4px 0; font-size: 12px; }
        #modules .dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>
    <div id="stats" class="hud">
        <h2>🧠 Brain v8.5</h2>
        <div class="stat"><span class="label">Neurons</span><span class="value" id="n-neurons">0</span></div>
        <div class="stat"><span class="label">Synapses</span><span class="value" id="n-synapses">0</span></div>
        <div class="stat"><span class="label">Spikes/s</span><span class="value" id="hz">0</span></div>
        <div class="stat"><span class="label">Growth</span><span class="value" id="growth">0</span></div>
        <div class="stat"><span class="label">Signals</span><span class="value" id="signals">0</span></div>
    </div>
    <div id="modules" class="hud"><h3>Modules</h3><div id="mod-list"></div></div>
    <script>
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 1, 2000);
        const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('canvas'), antialias: true});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x0a0a12);
        scene.add(new THREE.AmbientLight(0x404040, 0.5));
        scene.add(new THREE.DirectionalLight(0xffffff, 0.8));
        
        // Points cloud pour les neurones (beaucoup plus performant)
        let pointsGroup = new THREE.Group();
        scene.add(pointsGroup);
        
        // Sphères pour les modules ( centres)
        const moduleSpheres = new THREE.Group();
        scene.add(moduleSpheres);
        
        let time = 0;
        
        async function update() {
            try {
                const res = await fetch('/api/brain');
                const data = await res.json();
                
                // Clear previous - THREE.Group n'a pas de clear()
                while(pointsGroup.children.length > 0) {
                    pointsGroup.remove(pointsGroup.children[0]);
                }
                while(moduleSpheres.children.length > 0) {
                    moduleSpheres.remove(moduleSpheres.children[0]);
                }
                
                const modColors = {};
                for (const m in data.modules) {
                    modColors[m] = parseInt(data.modules[m].color.slice(1), 16);
                    // Créer une sphère pour chaque module centre
                    const pos = data.modules[m].pos || [0,0,0];
                    const geo = new THREE.SphereGeometry(20, 16, 16);
                    const mat = new THREE.MeshPhongMaterial({ 
                        color: modColors[m], 
                        transparent: true, 
                        opacity: 0.3,
                        emissive: modColors[m],
                        emissiveIntensity: 0.2
                    });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.position.set(pos[0], pos[1], pos[2]);
                    moduleSpheres.add(mesh);
                }
                
                // Créer un BufferGeometry pour tous les neurones
                const positions = [];
                const colors = [];
                const sizes = [];
                
                for (const n of data.neurons) {
                    const pos = data.modules[n.mod]?.pos || [0,0,0];
                    // Scale plus grand pour bien voir les neurones
                    const scaleFactor = 1.5;
                    
                    positions.push(
                        pos[0] + n.rx * scaleFactor,
                        pos[1] + n.ry * scaleFactor,
                        pos[2] + n.rz * scaleFactor
                    );
                    
                    const color = new THREE.Color();
                    if (n.exc) {
                        color.setHex(modColors[n.mod] || 0xffffff);
                    } else {
                        color.setHex(0xff4444);
                    }
                    colors.push(color.r, color.g, color.b);
                    sizes.push(n.sp ? 4 : 2);
                }
                
                const geometry = new THREE.BufferGeometry();
                geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
                geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
                geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));
                
                const material = new THREE.PointsMaterial({
                    size: 2,
                    vertexColors: true,
                    sizeAttenuation: true,
                    transparent: true,
                    opacity: 0.8
                });
                
                const points = new THREE.Points(geometry, material);
                pointsGroup.add(points);
                
                // Update stats
                document.getElementById('n-neurons').textContent = data.stats.N.toLocaleString();
                document.getElementById('n-synapses').textContent = data.stats.syn.toLocaleString();
                document.getElementById('hz').textContent = data.stats.hz.toFixed(1);
                document.getElementById('growth').textContent = data.stats.growth.toLocaleString();
                document.getElementById('signals').textContent = data.stats.sig;
                
                const list = document.getElementById('mod-list');
                list.innerHTML = '';
                for (const m in data.modules) {
                    const div = document.createElement('div');
                    div.className = 'mod';
                    div.innerHTML = '<div class="dot" style="background:' + data.modules[m].color + '"></div>' + m + ' (' + data.modules[m].n + ')';
                    list.appendChild(div);
                }
            } catch(e) {
                console.error('Update error:', e);
            }
        }
        
        function animate() {
            requestAnimationFrame(animate);
            pointsGroup.rotation.y += 0.001;
            moduleSpheres.rotation.y += 0.001;
            time++;
            if (time % 60 === 0) update();
            renderer.render(scene, camera);
        }
        
        camera.position.set(0, 150, 600);
        camera.lookAt(0, 0, 0);
        
        window.addEventListener('resize', () => { 
            camera.aspect = window.innerWidth/window.innerHeight; 
            camera.updateProjectionMatrix(); 
            renderer.setSize(window.innerWidth, window.innerHeight); 
        });
        
        update();
        animate();
    </script>
</body>
</html>
'''

# Instance globale
brain = Brain()

# ═══════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/brain')
def api_brain():
    with brain.lock:
        # Limiter le nombre de neurones envoyés pour éviter de surcharger le client
        max_neurons = 5000
        data = brain.to_json()
        if len(data['neurons']) > max_neurons:
            import random
            data['neurons'] = random.sample(data['neurons'], max_neurons)
        return Response(json.dumps(data), mimetype='application/json')

@app.route('/api/brain/full')
def api_brain_full():
    """Version complète (pour v12)"""
    with brain.lock:
        return Response(json.dumps(brain.to_json()), mimetype='application/json')

@app.route('/api/brain/v12')
def api_brain_v12():
    """Version optimisée pour v12 - tous les neurones"""
    with brain.lock:
        data = brain.to_json()
        # Pas de limite - tous les neurones
        return Response(json.dumps(data), mimetype='application/json')

@app.route('/api/stats')
def api_stats():
    with brain.lock:
        return Response(json.dumps(brain.stats), mimetype='application/json')

@app.route('/api/stimulus', methods=['POST'])
def api_stimulus():
    """Reçoit un stimulus du Claude-Mem Bridge et active les neurones correspondants"""
    try:
        data = request.get_json()
        if not data:
            return Response(json.dumps({'error': 'No data'}), status=400, mimetype='application/json')
        
        module = data.get('module', 'reasoning')
        intensity = float(data.get('intensity', 0.5))
        content = data.get('content', {})
        
        with brain.lock:
            # Trouver les neurones du module
            if module in brain.modules:
                mod = brain.modules[module]
                neurons_in_mod = [n for n in brain.neurons if n['mod'] == module]
                
                # Activer les neurones selon l'intensité
                num_to_activate = max(1, int(len(neurons_in_mod) * intensity * 0.3))
                activated = []
                
                for neuron in neurons_in_mod[:num_to_activate]:
                    # Injection de voltage
                    neuron['v'] = min(0, neuron['v'] + intensity * 10)
                    neuron['glow'] = min(1.0, neuron['glow'] + intensity)
                    neuron['drive'] = min(3.0, neuron['drive'] + intensity * 0.5)
                    activated.append(neuron['id'])
                
                # Créer des signaux entre modules connectés
                if module in WIRES and intensity > 0.3:
                    for target_mod in WIRES[module]:
                        if random.random() < intensity:
                            brain.signals.append({
                                'from_mod': module,
                                'to_mod': target_mod,
                                'progress': 0,
                                'color': brain.modules[module]['color'],
                            })
                
                # Mettre à jour les stats
                brain.stats['sig'] = len(brain.signals)
                
                return Response(json.dumps({
                    'status': 'ok',
                    'module': module,
                    'intensity': intensity,
                    'neurons_activated': len(activated),
                    'signals_created': len([s for s in brain.signals if s['from_mod'] == module]),
                }), mimetype='application/json')
            else:
                return Response(json.dumps({
                    'status': 'error',
                    'error': f'Module {module} not found',
                    'available_modules': list(brain.modules.keys()),
                }), status=404, mimetype='application/json')
                
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')

@app.route('/api/stimulus/batch', methods=['POST'])
def api_stimulus_batch():
    """Reçoit plusieurs stimuli en batch"""
    try:
        data = request.get_json()
        stimuli = data.get('stimuli', [])
        
        results = []
        with brain.lock:
            for stimulus in stimuli:
                module = stimulus.get('module', 'reasoning')
                intensity = float(stimulus.get('intensity', 0.5))
                
                if module in brain.modules:
                    neurons_in_mod = [n for n in brain.neurons if n['mod'] == module]
                    num_to_activate = max(1, int(len(neurons_in_mod) * intensity * 0.3))
                    
                    for neuron in neurons_in_mod[:num_to_activate]:
                        neuron['v'] = min(0, neuron['v'] + intensity * 10)
                        neuron['glow'] = min(1.0, neuron['glow'] + intensity)
                    
                    results.append({'module': module, 'activated': num_to_activate})
        
        return Response(json.dumps({'status': 'ok', 'processed': len(results), 'results': results}), mimetype='application/json')
    
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')

@app.route('/api/bridge/status')
def api_bridge_status():
    """Statut de l'intégration Claude-Mem Bridge"""
    try:
        # Vérifier si le bridge est chargé
        import sys
        bridge_module = sys.modules.get('claude_mem_bridge')
        
        if bridge_module and hasattr(bridge_module, 'get_bridge_status'):
            status = bridge_module.get_bridge_status()
            return Response(json.dumps(status), mimetype='application/json')
        else:
            # Vérifier manuellement
            bridge_history = Path("/mnt/nvme/soullink_brain/observation_history.json")
            if bridge_history.exists():
                with open(bridge_history, 'r') as f:
                    history = json.load(f)
                return Response(json.dumps({
                    'running': False,
                    'last_observation_id': history.get('last_id', 0),
                    'stats': history.get('stats', {}),
                    'note': 'Bridge not loaded, history available'
                }), mimetype='application/json')
            else:
                return Response(json.dumps({
                    'running': False,
                    'last_observation_id': 0,
                    'stats': {},
                    'note': 'Bridge not initialized'
                }), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')

@app.route('/')
def index():
    """Route par défaut = v25"""
    return v25()

@app.route('/three.min.js')
def three_js():
    return send_from_directory('/mnt/nvme', 'three.min.js', mimetype='application/javascript')

@app.route('/v10')
def v10():
    """Visualisation Gaseous Brain - Particules gazeuses"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>SoulLink Brain v10 - Gaseous</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#010206;overflow:hidden;font-family:'IBM Plex Mono',monospace}
canvas{display:block;cursor:grab}
#hud{position:fixed;top:20px;left:20px;background:rgba(5,10,20,0.8);padding:20px;border-radius:12px;border:1px solid #0a2040;color:#fff;pointer-events:none}
#hud h2{color:#fff;font-size:1rem;margin:0 0 10px;letter-spacing:2px}
.stat{margin:5px 0;display:flex;justify-content:space-between;width:180px}
.stat span{color:#888}
.stat b{color:#3d9eff}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud">
    <h2>SOULLINK BRAIN v10</h2>
    <div class="stat"><span>Neurons</span><b id="sn">0</b></div>
    <div class="stat"><span>Synapses</span><b id="ssyn">0</b></div>
    <div class="stat"><span>Active</span><b id="sact">0/10</b></div>
</div>
<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W, H, CX, CY;

const state = { rotX: 0.15, rotY: -0.6, zoom: 1.0, isDragging: false, lastX: 0, lastY: 0 };

const MODULES = {
    reasoning: { p: [0.15, 0.70], col: '#ff5577' },
    motor: { p: [0.45, 0.85], col: '#aaff44' },
    output: { p: [0.20, 0.40], col: '#ffee44' },
    attention: { p: [0.65, 0.80], col: '#cc44ff' },
    perception: { p: [0.55, 0.65], col: '#ff6644' },
    vision: { p: [0.90, 0.45], col: '#3dffc0' },
    language: { p: [0.70, 0.40], col: '#44ffff' },
    audio: { p: [0.45, 0.35], col: '#4ab0ff' },
    memory: { p: [0.50, 0.25], col: '#3d9eff' },
    learning: { p: [0.80, 0.10], col: '#ff9944' },
};

let neurons = [];
let lum = {};

function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
    CX = W / 2;
    CY = H / 2;
    buildBrain();
}

function buildBrain() {
    neurons = [];
    const SCALE = Math.min(W, H) * 0.35;
    
    // Créer neurones par module
    Object.entries(MODULES).forEach(([name, mod]) => {
        const cx = (mod.p[0] - 0.5) * SCALE;
        const cy = (mod.p[1] - 0.5) * SCALE;
        for (let i = 0; i < 50; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = Math.random() * 25;
            neurons.push({
                x: cx + Math.cos(angle) * r,
                y: cy + Math.sin(angle) * r,
                z: (Math.random() - 0.5) * 30,
                mod: name,
                col: mod.col
            });
        }
        lum[name] = 0;
    });
    
    // Ajouter coque
    for (let i = 0; i < 800; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 130 + Math.random() * 20;
        neurons.push({
            x: r * Math.sin(phi) * Math.cos(theta),
            y: r * Math.sin(phi) * Math.sin(theta),
            z: r * Math.cos(phi) * 0.85,
            mod: 'shell',
            col: '#1a3050'
        });
    }
}

function project(x, y, z) {
    const cY = Math.cos(state.rotY), sY = Math.sin(state.rotY);
    const cX = Math.cos(state.rotX), sX = Math.sin(state.rotX);
    const rx = x * cY - z * sY;
    const rz1 = x * sY + z * cY;
    const ry = y * cX - rz1 * sX;
    const rz2 = y * sX + rz1 * cX;
    const scale = 600 / (600 + rz2);
    return { x: CX + rx * scale * state.zoom, y: CY + ry * scale * state.zoom, z: rz2, s: scale };
}

let frame = 0;
function simulate() {
    Object.keys(MODULES).forEach(name => {
        const osc = 0.5 + 0.5 * Math.sin(frame * 0.02 + Object.keys(MODULES).indexOf(name));
        if (Math.random() < 0.03 * osc) lum[name] = Math.min(1, (lum[name] || 0) + 0.4);
        lum[name] = (lum[name] || 0) * 0.94;
    });
}

function draw() {
    ctx.fillStyle = '#010206';
    ctx.fillRect(0, 0, W, H);
    
    let projected = neurons.map(n => ({ ...project(n.x, n.y, n.z), ...n }));
    projected.sort((a, b) => b.z - a.z);
    
    projected.forEach(p => {
        if (p.mod === 'shell') {
            const alpha = 0.15 + (1 - (p.z + 150) / 300) * 0.1;
            ctx.fillStyle = 'rgba(26,48,80,' + Math.max(0.05, alpha) + ')';
            ctx.fillRect(p.x, p.y, 2 * p.s, 2 * p.s);
        } else {
            const act = lum[p.mod] || 0;
            const size = (1.5 + act * 2) * p.s;
            ctx.fillStyle = p.col;
            ctx.globalAlpha = 0.5 + act * 0.5;
            ctx.fillRect(p.x - size/2, p.y - size/2, size, size);
            if (act > 0.3) {
                ctx.globalAlpha = act * 0.3;
                ctx.fillRect(p.x - size, p.y - size, size * 2, size * 2);
            }
            ctx.globalAlpha = 1;
        }
    });
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('sn').textContent = stats.N.toLocaleString();
        document.getElementById('ssyn').textContent = stats.syn.toLocaleString();
    } catch(e) {}
}

function loop() {
    if (!state.isDragging) state.rotY -= 0.002;
    simulate();
    draw();
    frame++;
    requestAnimationFrame(loop);
}

window.onmousedown = () => state.isDragging = true;
window.onmouseup = () => state.isDragging = false;
window.onmousemove = (e) => {
    if (state.isDragging) {
        state.rotY -= (e.clientX - state.lastX) * 0.004;
        state.rotX -= (e.clientY - state.lastY) * 0.004;
        state.rotX = Math.max(-0.7, Math.min(0.7, state.rotX));
    }
    state.lastX = e.clientX;
    state.lastY = e.clientY;
};
window.onwheel = (e) => {
    state.zoom *= e.deltaY > 0 ? 0.95 : 1.05;
    state.zoom = Math.max(0.5, Math.min(2.5, state.zoom));
};

window.addEventListener('resize', resize);
resize();
fetchStats();
setInterval(fetchStats, 3000);
loop();
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')

@app.route('/v11')
def v11():
    """Visualisation Neural Network - Réseau dense centré"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>SoulLink Brain v11 - Neural Network</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#020408;overflow:hidden}
canvas{display:block;cursor:grab}
#hud{position:fixed;top:20px;left:20px;background:rgba(10,20,30,0.85);padding:16px;border-radius:8px;color:#fff;font-family:monospace;border:1px solid #3d9eff}
#hud h3{margin:0 0 8px;color:#3d9eff;font-size:14px;letter-spacing:1px}
#hud div{font-size:12px;margin:4px 0}
#hud b{color:#5bd7ff}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud">
    <h3>BRAIN v11 - Neural Network</h3>
    <div>Neurons: <b id="sn">0</b></div>
    <div>Connections: <b id="sconn">0</b></div>
    <div>Hz: <b id="shz">0.0</b></div>
</div>
<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W, H, CX, CY;

const nodes = [];
const connections = [];
const MODULES = ['#ff5577','#aaff44','#ffee44','#cc44ff','#ff6644','#3dffc0','#44ffff','#4ab0ff','#3d9eff','#ff9944'];
const lum = {};

function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
    CX = W / 2;
    CY = H / 2;
}

function buildNetwork() {
    nodes.length = 0;
    connections.length = 0;
    
    const SCALE = Math.min(W, H) * 0.35;
    
    // Créer neurones par module (centrés)
    const moduleCenters = [
        [0, -80],    // reasoning (frontal)
        [60, 100],   // motor
        [-80, 30],   // output
        [50, 60],    // attention
        [40, -20],   // perception
        [80, 0],     // vision (occipital)
        [-70, -30],  // language
        [-100, 40],  // audio (temporal)
        [20, 0],     // memory (central)
        [0, 120]     // learning (cerebellum)
    ];
    
    for (let m = 0; m < 10; m++) {
        const [cx, cy] = moduleCenters[m];
        for (let i = 0; i < 30; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = Math.random() * 35;
            nodes.push({
                x: cx + Math.cos(angle) * r,
                y: cy + Math.sin(angle) * r,
                z: (Math.random() - 0.5) * 40,
                mod: m,
                col: MODULES[m],
                phase: Math.random() * Math.PI * 2
            });
        }
        lum[m] = 0;
    }
    
    // Ajouter coque
    for (let i = 0; i < 600; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 140 + Math.random() * 10;
        nodes.push({
            x: r * Math.sin(phi) * Math.cos(theta) * 0.9,
            y: r * Math.sin(phi) * Math.sin(theta) * 0.75,
            z: r * Math.cos(phi) * 0.65,
            mod: -1,
            col: '#1a3050',
            phase: 0
        });
    }
    
    // Connexions locales
    for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].mod === -1) continue;
        for (let j = i + 1; j < nodes.length; j++) {
            if (nodes[j].mod === -1 || nodes[j].mod !== nodes[i].mod) continue;
            const dist = Math.sqrt(
                Math.pow(nodes[i].x - nodes[j].x, 2) +
                Math.pow(nodes[i].y - nodes[j].y, 2) +
                Math.pow(nodes[i].z - nodes[j].z, 2)
            );
            if (dist < 30 && Math.random() < 0.4) {
                connections.push({ a: i, b: j, dist });
            }
        }
    }
    
    document.getElementById('sconn').textContent = connections.length;
}

let rotY = 0, rotX = 0.15;

function project(x, y, z) {
    const cY = Math.cos(rotY), sY = Math.sin(rotY);
    const cX = Math.cos(rotX), sX = Math.sin(rotX);
    const rx = x * cY - z * sY;
    const rz1 = x * sY + z * cY;
    const ry = y * cX - rz1 * sX;
    const rz2 = y * sX + rz1 * cX;
    const scale = 600 / (600 + rz2);
    return { x: CX + rx * scale, y: CY + ry * scale, z: rz2, s: scale };
}

let frame = 0;
function simulate() {
    for (let m = 0; m < 10; m++) {
        const osc = 0.5 + 0.5 * Math.sin(frame * 0.02 + m);
        if (Math.random() < 0.03 * osc) lum[m] = Math.min(1, (lum[m] || 0) + 0.4);
        lum[m] = (lum[m] || 0) * 0.94;
    }
}

function draw() {
    ctx.fillStyle = '#020408';
    ctx.fillRect(0, 0, W, H);
    
    rotY += 0.003;
    simulate();
    
    // Projeter
    const proj = nodes.map(n => ({ ...project(n.x, n.y, n.z), ...n }));
    proj.sort((a, b) => b.z - a.z);
    
    // Dessiner coque d'abord
    ctx.globalAlpha = 0.15;
    proj.filter(p => p.mod === -1).forEach(p => {
        const alpha = 0.08 + (1 - (p.z + 150) / 300) * 0.1;
        ctx.fillStyle = 'rgba(26,48,80,' + Math.max(0.03, alpha) + ')';
        ctx.fillRect(p.x, p.y, 2 * p.s, 2 * p.s);
    });
    ctx.globalAlpha = 1;
    
    // Dessiner connexions
    connections.forEach(c => {
        const a = proj[c.a], b = proj[c.b];
        if (!a || !b) return;
        const act = Math.max(lum[a.mod] || 0, lum[b.mod] || 0);
        ctx.strokeStyle = a.col;
        ctx.globalAlpha = 0.1 + act * 0.3;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
    });
    ctx.globalAlpha = 1;
    
    // Dessiner neurones
    proj.filter(p => p.mod >= 0).forEach(p => {
        const act = lum[p.mod] || 0;
        const pulse = Math.sin(frame * 0.05 + p.phase) * 0.3 + 1;
        const size = (2 + act * 2 + pulse * 0.5) * p.s;
        
        ctx.fillStyle = p.col;
        ctx.globalAlpha = 0.6 + act * 0.4;
        ctx.fillRect(p.x - size/2, p.y - size/2, size, size);
        
        if (act > 0.3) {
            ctx.globalAlpha = act * 0.2;
            ctx.fillRect(p.x - size, p.y - size, size * 2, size * 2);
        }
    });
    ctx.globalAlpha = 1;
    
    frame++;
    requestAnimationFrame(draw);
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('sn').textContent = stats.N.toLocaleString();
        document.getElementById('shz').textContent = (stats.hz || 0).toFixed(1);
    } catch(e) {}
}

window.addEventListener('resize', resize);
resize();
buildNetwork();
fetchStats();
setInterval(fetchStats, 3000);
draw();
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')

@app.route('/debug')
def debug_page():
    """Page de debug avec toutes les versions"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>SoulLink Brain - Debug</title>
<style>
body{font-family:Arial,sans-serif;background:#0a0a12;color:#fff;margin:40px}
h1{color:#3d9eff;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.card{background:#151520;border:1px solid #2a2a3a;border-radius:12px;padding:20px;transition:all 0.3s}
.card:hover{border-color:#3d9eff;transform:translateY(-5px)}
.card h3{margin:0 0 10px;color:#5bd7ff}
.card p{margin:5px 0;font-size:14px;color:#888}
.card a{display:block;margin-top:15px;padding:10px;background:#1a3a5a;border-radius:8px;text-align:center;text-decoration:none;color:#fff}
.card a:hover{background:#2a4a6a}
.stats{background:#1a1a25;padding:15px;border-radius:8px;margin-bottom:20px}
.stats span{margin-right:20px}
</style>
</head>
<body>
<h1>🧠 SoulLink Brain - Debug Panel</h1>
<div class="stats">
    <span>Neurons: <b id="sn">0</b></span>
    <span>Synapses: <b id="ssyn">0</b></span>
    <span>Spikes: <b id="sspk">0</b></span>
    <span>Hz: <b id="shz">0</b></span>
</div>
<div class="grid">
    <div class="card">
        <h3>v10 - Gaseous Brain</h3>
        <p>Particules gazeuses avec modules colorés</p>
        <a href="/v10">Ouvrir v10</a>
    </div>
    <div class="card">
        <h3>v11 - Neural Network</h3>
        <p>Réseau dense avec connexions</p>
        <a href="/v11">Ouvrir v11</a>
    </div>
    <div class="card">
        <h3>v12 - 3D Volumetric</h3>
        <p>Nuage de points style original</p>
        <a href="/v12">Ouvrir v12</a>
    </div>
    <div class="card">
        <h3>v17 - Cortex Morphologique</h3>
        <p>Gyri/sulci simulés</p>
        <a href="/v17">Ouvrir v17</a>
    </div>
    <div class="card">
        <h3>v18 - Enveloppe Accentuée</h3>
        <p>Coque cristalline</p>
        <a href="/v18">Ouvrir v18</a>
    </div>
    <div class="card">
        <h3>v18.2 - Three.js Cortex</h3>
        <p>Cortex texturé avec sillons</p>
        <a href="/v18.2">Ouvrir v18.2</a>
    </div>
    <div class="card">
        <h3>v19 - Accentuated Shell</h3>
        <p>Gradient radial néon</p>
        <a href="/v19">Ouvrir v19</a>
    </div>
    <div class="card">
        <h3>v20 - Three.js Shader</h3>
        <p>10K particules GPU</p>
        <a href="/v20">Ouvrir v20</a>
    </div>
    <div class="card">
        <h3>v21 - Holographic</h3>
        <p>150K particules Bloom</p>
        <a href="/v21">Ouvrir v21</a>
    </div>
    <div class="card">
        <h3>v22 - Organic Bump</h3>
        <p>Bump mapping organique</p>
        <a href="/v22">Ouvrir v22</a>
    </div>
    <div class="card">
        <h3>v23 - Neural Structure</h3>
        <p>Cortex + structure neuronale</p>
        <a href="/v23">Ouvrir v23</a>
    </div>
    <div class="card">
        <h3>/ - Root</h3>
        <p>Interface par défaut</p>
        <a href="/">Ouvrir Root</a>
    </div>
</div>
<script>
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('sn').textContent = stats.N.toLocaleString();
        document.getElementById('ssyn').textContent = stats.syn.toLocaleString();
        document.getElementById('sspk').textContent = stats.spk;
        document.getElementById('shz').textContent = stats.hz.toFixed(1);
    } catch(e) {}
}
loadStats();
setInterval(loadStats, 2000);
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')

@app.route('/v12')
def v12():
    """Visualisation 3D Volumetric - Nuage de points style original avec fallback"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>SoulLink Brain v12.0 - 3D Volumetric</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;500&family=Bebas+Neue&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#020408;overflow:hidden;font-family:'IBM Plex Mono',monospace}
canvas{display:block;cursor:grab}
canvas:active{cursor:grabbing}
#ui{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;}
#hud{
    position:absolute;top:20px;left:20px;pointer-events:auto;
    background:rgba(6,10,20,0.75);border:1px solid rgba(60,158,255,0.2);
    border-radius:2px;padding:14px 18px;backdrop-filter:blur(8px);
    box-shadow:0 0 20px rgba(60,158,255,0.08);min-width:180px;
}
#hud-name{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:.08em;color:#fff;margin-bottom:1px;}
#hud-sub{font-size:.4rem;color:rgba(255,255,255,0.3);letter-spacing:.15em;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid rgba(60,158,255,0.12)}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:3px 0}
.lbl{font-size:.45rem;color:rgba(255,255,255,0.35);letter-spacing:.05em}
.val{font-size:.5rem;color:#3d9eff;font-weight:500}
.val.hot{color:#ff5577}
#bar{height:2px;background:rgba(60,158,255,0.12);margin-top:8px;border-radius:1px;overflow:hidden}
#bar-fill{height:100%;width:0%;background:linear-gradient(90deg,#1a5fff,#3d9eff);transition:width 0.12s}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="ui">
    <div id="hud">
        <div id="hud-name">SOULLINK</div>
        <div id="hud-sub">3D VOLUMETRIC · v12.0</div>
        <div class="row"><span class="lbl">NEURONS</span><b class="val" id="sn">0</b></div>
        <div class="row"><span class="lbl">FREQUENCY</span><b class="val" id="shz">0.0 Hz</b></div>
        <div class="row"><span class="lbl">ACTIVE</span><b class="val" id="sma">0/10</b></div>
        <div class="row"><span class="lbl">STATE</span><b class="val" id="sst">NOMINAL</b></div>
        <div id="bar"><div id="bar-fill"></div></div>
    </div>
</div>

<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d', { alpha: false });
let W, H, CX, CY;

const state = { rotX: 0.15, rotY: -0.6, zoom: 1.0, isDragging: false, lastX: 0, lastY: 0 };

const MODULES = {
    reasoning : { p:[0.15, 0.70], col:'#ff5577' },
    motor     : { p:[0.45, 0.85], col:'#aaff44' },
    output    : { p:[0.20, 0.40], col:'#ffee44' },
    attention : { p:[0.65, 0.80], col:'#cc44ff' },
    perception: { p:[0.55, 0.65], col:'#ff6644' },
    vision    : { p:[0.90, 0.45], col:'#3dffc0' },
    language  : { p:[0.70, 0.40], col:'#44ffff' },
    audio     : { p:[0.45, 0.35], col:'#4ab0ff' },
    memory    : { p:[0.50, 0.25], col:'#3d9eff' },
    learning  : { p:[0.80, 0.10], col:'#ff9944' },
};

let neurons = [];
let lum = {};

function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
    CX = W / 2;
    CY = H / 2;
    buildDefaultBrain();
}

function hexToRgb(hex) {
    return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16)];
}

function project(x, y, z) {
    const cY = Math.cos(state.rotY), sY = Math.sin(state.rotY);
    const rx = x * cY - z * sY;
    const rz1 = x * sY + z * cY;
    const cX = Math.cos(state.rotX), sX = Math.sin(state.rotX);
    const ry = y * cX - rz1 * sX;
    const rz2 = y * sX + rz1 * cX;
    
    const perspective = 800 / (800 + rz2);
    return {
        x: CX + rx * perspective * state.zoom,
        y: CY + ry * perspective * state.zoom,
        z: rz2,
        s: perspective * state.zoom
    };
}

function buildDefaultBrain() {
    neurons = [];
    const SCALE = Math.min(W, H) * 0.35;
    
    // Coque cérébrale
    for (let i = 0; i < 2000; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 120 + Math.random() * 20;
        let x = r * Math.sin(phi) * Math.cos(theta);
        let y = r * Math.sin(phi) * Math.sin(theta);
        let z = r * Math.cos(phi) * 0.85;
        if (Math.abs(z) < 8 && y > -30) z *= 0.3;
        neurons.push({ x, y, z, mod: 'shell', col: '#1a3050' });
    }
    
    // Modules
    Object.entries(MODULES).forEach(([name, mod]) => {
        const cx = (mod.p[0] - 0.5) * SCALE;
        const cy = (mod.p[1] - 0.5) * SCALE;
        for (let i = 0; i < 80; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            const r = 18 + Math.random() * 12;
            neurons.push({
                x: cx + r * Math.sin(phi) * Math.cos(theta),
                y: cy + r * Math.sin(phi) * Math.sin(theta),
                z: r * Math.cos(phi) * 0.6,
                mod: name,
                col: mod.col
            });
        }
        lum[name] = 0;
    });
}

let frame = 0;
function simulate() {
    Object.keys(MODULES).forEach(name => {
        const osc = 0.5 + 0.5 * Math.sin(frame * 0.02 + Object.keys(MODULES).indexOf(name) * 0.5);
        if (Math.random() < 0.03 * osc) lum[name] = Math.min(1, (lum[name] || 0) + 0.5);
        lum[name] = (lum[name] || 0) * 0.94;
    });
}

function draw() {
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#020408';
    ctx.fillRect(0, 0, W, H);
    
    if (neurons.length === 0) return;
    
    // Projection
    let projected = neurons.map(n => ({
        ...project(n.x, n.y, n.z),
        mod: n.mod,
        col: n.col
    }));
    
    // Z-sort
    projected.sort((a, b) => b.z - a.z);
    
    // Draw
    projected.forEach(p => {
        if (p.mod === 'shell') {
            const alpha = 0.08 + (1 - (p.z + 150) / 300) * 0.1;
            ctx.fillStyle = 'rgba(26,48,80,' + Math.max(0.03, alpha) + ')';
            ctx.fillRect(p.x, p.y, 2 * p.s, 2 * p.s);
        } else {
            const rgb = hexToRgb(p.col);
            const act = lum[p.mod] || 0;
            const baseAlpha = 0.35 + act * 0.5;
            const size = (1.2 + act * 1.5) * p.s;
            
            ctx.fillStyle = 'rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + baseAlpha + ')';
            ctx.fillRect(p.x - size/2, p.y - size/2, size, size);
            
            if (act > 0.2) {
                ctx.globalCompositeOperation = 'lighter';
                ctx.fillStyle = 'rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + (act * 0.35) + ')';
                ctx.fillRect(p.x - size, p.y - size, size * 2, size * 2);
                ctx.globalCompositeOperation = 'source-over';
            }
        }
    });
}

function updateHUD() {
    const activeMods = Object.values(lum).filter(v => v > 0.15).length;
    const hz = 10 + activeMods * 7 + Math.random() * 5;
    document.getElementById('shz').textContent = hz.toFixed(1) + ' Hz';
    document.getElementById('sma').textContent = activeMods + '/10';
    const st = document.getElementById('sst');
    st.textContent = hz > 50 ? 'ACTIVE' : hz > 25 ? 'NOMINAL' : 'IDLE';
    st.className = 'val' + (hz > 45 ? ' hot' : '');
    document.getElementById('bar-fill').style.width = Math.min(100, hz / 0.7) + '%';
}

async function fetchBrainData() {
    try {
        const res = await fetch('/api/brain');
        const data = await res.json();
        document.getElementById('sn').textContent = data.stats?.N?.toLocaleString() || data.neurons?.length || '0';
    } catch(e) {
        document.getElementById('sn').textContent = neurons.length.toLocaleString();
    }
}

function loop() {
    if (!state.isDragging) state.rotY -= 0.002;
    simulate();
    draw();
    frame++;
    requestAnimationFrame(loop);
}

window.onmousedown = () => state.isDragging = true;
window.onmouseup = () => state.isDragging = false;
window.onmousemove = (e) => {
    if (state.isDragging) {
        state.rotY -= (e.clientX - state.lastX) * 0.004;
        state.rotX -= (e.clientY - state.lastY) * 0.004;
        state.rotX = Math.max(-0.7, Math.min(0.7, state.rotX));
    }
    state.lastX = e.clientX;
    state.lastY = e.clientY;
};
window.onwheel = (e) => {
    state.zoom *= e.deltaY > 0 ? 0.97 : 1.03;
    state.zoom = Math.max(0.5, Math.min(2.5, state.zoom));
};

window.addEventListener('resize', resize);
resize();
fetchBrainData();
setInterval(fetchBrainData, 2000);
setInterval(updateHUD, 300);
loop();
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')
@app.route('/v25')
def v25():
    """Visualisation Three.js - Cortex Enveloppe + Modules Flottants + Intégration Claude-Mem"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SoulLink Brain v25 - Cortex Enveloppe</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;500&family=Bebas+Neue&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#010206;overflow:hidden;font-family:'IBM Plex Mono',monospace}
#hud{
 position:fixed;top:20px;left:20px;z-index:10;
 background:rgba(6,10,20,0.85);border:1px solid rgba(60,158,255,0.3);
 border-radius:4px;padding:16px 20px;backdrop-filter:blur(12px);
 box-shadow:0 0 30px rgba(60,158,255,0.1);min-width:200px;
}
#hud-name{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:.12em;color:#fff;margin-bottom:2px;}
#hud-sub{font-size:.45rem;color:rgba(255,255,255,0.4);letter-spacing:.2em;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid rgba(60,158,255,0.15)}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:4px 0}
.lbl{font-size:.55rem;color:rgba(255,255,255,0.5);letter-spacing:.08em}
.val{font-size:.7rem;color:#3d9eff;font-weight:500}
.val.hot{color:#ff5577}
.val.cool{color:#44ffaa}
#mods{margin-top:12px;display:grid;grid-template-columns:repeat(2,1fr);gap:3px}
.mod{display:flex;align-items:center;gap:5px;font-size:.4rem;color:rgba(255,255,255,0.6)}
.mod-dot{width:8px;height:8px;border-radius:50%;box-shadow:0 0 8px currentColor}
#bar{height:3px;background:rgba(60,158,255,0.15);margin-top:10px;border-radius:2px;overflow:hidden}
#bar-fill{height:100%;width:0%;background:linear-gradient(90deg,#3d9eff,#44ffaa);transition:width 0.15s}
#hint{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);font-size:.4rem;color:rgba(255,255,255,0.3);letter-spacing:.1em}
</style>
</head>
<body>
<div id="hud">
 <div id="hud-name">SOULLINK BRAIN</div>
 <div id="hud-sub">CORTEX ENVELOPPE · v25</div>
 <div class="row"><span class="lbl">NEURONS</span><b class="val" id="sn">0</b></div>
 <div class="row"><span class="lbl">SYNAPSES</span><b class="val" id="ssyn">0</b></div>
 <div class="row"><span class="lbl">SIGNALS</span><b class="val" id="ssig">0</b></div>
 <div class="row"><span class="lbl">ACTIVITY</span><b class="val" id="shz">0.0 Hz</b></div>
 <div id="bar"><div id="bar-fill"></div></div>
 <div id="mods"></div>
</div>
<div id="hint">DRAG TO ROTATE · SCROLL TO ZOOM</div>

<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.162.0/build/three.module.js" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'https://unpkg.com/three@0.162.0/examples/jsm/controls/OrbitControls.js';

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x010206, 0.08);
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0, 5);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x010206);
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 2;
controls.maxDistance = 12;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.3;

scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const dirLight = new THREE.DirectionalLight(0xffe0d0, 1.2);
dirLight.position.set(5, 8, 5);
scene.add(dirLight);
const backLight = new THREE.DirectionalLight(0x3d9eff, 0.3);
backLight.position.set(-5, -3, -5);
scene.add(backLight);

// === CORTEX ENVELOPPE (style v18.2) ===
function createCortexGeometry() {
    const geometry = new THREE.SphereGeometry(2.2, 200, 200);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
        const v = new THREE.Vector3().fromBufferAttribute(pos, i);
        // Ellipsoïde cérébrale
        v.x *= 1.3;
        v.y *= 0.95;
        v.z *= 0.85;
        // Sillons corticaux (gyri/sulci)
        const foldA = Math.sin(v.x * 12) * 0.08;
        const foldB = Math.cos(v.y * 15) * 0.06;
        const foldC = Math.sin((v.x + v.z) * 11) * 0.05;
        const foldD = Math.cos(v.z * 13) * 0.04;
        v.addScaledVector(v.clone().normalize(), foldA + foldB + foldC + foldD);
        pos.setXYZ(i, v.x, v.y, v.z);
    }
    geometry.computeVertexNormals();
    return geometry;
}

const cortexMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9b3a5,
    roughness: 0.92,
    metalness: 0.02,
    clearcoat: 0.15,
    sheen: 0.4,
    sheenColor: new THREE.Color(0xffddd2),
    transparent: true,
    opacity: 0.55,
    transmission: 0.25,
    side: THREE.DoubleSide,
    depthWrite: false
});

const cortex = new THREE.Mesh(createCortexGeometry(), cortexMaterial);
scene.add(cortex);

// === MODULES CÉRÉBRAUX ===
const MODULES = {
    reasoning:  { col: 0xff5577, pos: [0.5, 0.9, 0.5], size: 0.28 },
    motor:      { col: 0xaaff44, pos: [0.7, 0.6, 0.2], size: 0.24 },
    output:     { col: 0xffee44, pos: [-0.4, 0.4, 0.35], size: 0.22 },
    attention:  { col: 0xcc44ff, pos: [0.55, 0.75, -0.15], size: 0.25 },
    perception: { col: 0xff6644, pos: [0.0, 0.55, 0.45], size: 0.23 },
    vision:     { col: 0x3dffc0, pos: [0.0, 0.25, -0.85], size: 0.30 },
    language:   { col: 0x44ffff, pos: [-0.55, 0.35, 0.35], size: 0.26 },
    audio:      { col: 0x4ab0ff, pos: [-0.7, 0.15, 0.1], size: 0.22 },
    memory:     { col: 0x3d9eff, pos: [0.0, 0.0, 0.15], size: 0.28 },
    learning:   { col: 0xff9944, pos: [0.25, -0.25, -0.45], size: 0.22 }
};

const moduleMeshes = [];
const connections = [];
const impulses = [];
const activity = {};

// Créer sphères modules avec halo
Object.entries(MODULES).forEach(([name, mod]) => {
    // Sphère principale
    const geo = new THREE.SphereGeometry(mod.size, 24, 16);
    const mat = new THREE.MeshPhongMaterial({
        color: mod.col,
        transparent: true,
        opacity: 0.85,
        emissive: mod.col,
        emissiveIntensity: 0.25,
        shininess: 60
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(...mod.pos);
    scene.add(mesh);
    
    // Halo externe
    const haloGeo = new THREE.SphereGeometry(mod.size * 1.15, 24, 16);
    const haloMat = new THREE.MeshBasicMaterial({
        color: mod.col,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide
    });
    const halo = new THREE.Mesh(haloGeo, haloMat);
    halo.position.set(...mod.pos);
    scene.add(halo);
    
    moduleMeshes.push({ mesh, halo, name, mod, phase: Math.random() * Math.PI * 2, activity: 0 });
    activity[name] = 0;
});

// Connexions entre modules proches
const modNames = Object.keys(MODULES);
for (let i = 0; i < modNames.length; i++) {
    for (let j = i + 1; j < modNames.length; j++) {
        const a = MODULES[modNames[i]].pos;
        const b = MODULES[modNames[j]].pos;
        const dist = Math.sqrt(Math.pow(a[0]-b[0],2) + Math.pow(a[1]-b[1],2) + Math.pow(a[2]-b[2],2));
        if (dist < 1.2) {
            const curve = new THREE.QuadraticBezierCurve3(
                new THREE.Vector3(...a),
                new THREE.Vector3((a[0]+b[0])/2, (a[1]+b[1])/2 + dist*0.15, (a[2]+b[2])/2),
                new THREE.Vector3(...b)
            );
            const geo = new THREE.TubeGeometry(curve, 20, 0.008, 8, false);
            const line = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
                color: 0x3d9eff,
                transparent: true,
                opacity: 0.12
            }));
            scene.add(line);
            connections.push({ line, start: a, end: b, phase: Math.random() * Math.PI * 2, dist });
        }
    }
}

// Impulsions électriques
const impulseGeo = new THREE.SphereGeometry(0.025, 8, 6);
connections.forEach(conn => {
    for (let i = 0; i < 2; i++) {
        const impulse = new THREE.Mesh(impulseGeo, new THREE.MeshBasicMaterial({
            color: 0x5bd7ff,
            transparent: true,
            opacity: 0.9
        }));
        scene.add(impulse);
        impulses.push({
            mesh: impulse,
            conn: conn,
            t: Math.random(),
            speed: 0.008 + Math.random() * 0.006,
            delay: Math.random() * 200,
            visible: Math.random() > 0.3
        });
    }
});

// HUD modules
document.getElementById('mods').innerHTML = Object.entries(MODULES).map(([name, mod]) =>
    '<div class="mod"><div class="mod-dot" style="background:#' + mod.col.toString(16).padStart(6, '0') + ';color:#' + mod.col.toString(16).padStart(6, '0') + '"></div><span>' + name + '</span></div>'
).join('');

let brainData = null;
async function fetchBrainData() {
    try {
        const res = await fetch('/api/brain');
        brainData = await res.json();
        document.getElementById('sn').textContent = brainData.stats.N.toLocaleString();
        document.getElementById('ssyn').textContent = brainData.stats.syn.toLocaleString();
        document.getElementById('ssig').textContent = brainData.stats.sig || 0;
    } catch(e) {}
}
fetchBrainData();
setInterval(fetchBrainData, 2000);

let frame = 0;
function animate() {
    requestAnimationFrame(animate);
    frame++;
    
    cortex.rotation.y += 0.0005;
    
    // Pulsation modules selon activité
    moduleMeshes.forEach((m, idx) => {
        const pulse = 0.9 + Math.sin(frame * 0.03 + m.phase) * 0.15 + m.activity * 0.3;
        m.mesh.scale.setScalar(pulse);
        m.mesh.material.emissiveIntensity = 0.2 + m.activity * 0.5;
        m.halo.scale.setScalar(pulse * 1.1);
        m.halo.material.opacity = 0.1 + m.activity * 0.3;
        
        // Simuler activité
        if (Math.random() < 0.02) {
            m.activity = Math.min(1, m.activity + 0.3);
        }
        m.activity *= 0.97;
        activity[m.name] = Math.round(m.activity * 100);
    });
    
    // Impulsions électriques
    impulses.forEach(imp => {
        if (frame < imp.delay) { imp.mesh.visible = false; return; }
        imp.t += imp.speed;
        if (imp.t > 1) {
            imp.t = 0;
            imp.visible = Math.random() > 0.4;
        }
        imp.mesh.visible = imp.visible;
        if (imp.visible) {
            const ease = imp.t < 0.5 ? 2 * imp.t * imp.t : 1 - Math.pow(-2 * imp.t + 2, 2) / 2;
            imp.mesh.position.set(
                imp.conn.start[0] + (imp.conn.end[0] - imp.conn.start[0]) * ease,
                imp.conn.start[1] + (imp.conn.end[1] - imp.conn.start[1]) * ease + Math.sin(imp.t * Math.PI) * imp.conn.dist * 0.15,
                imp.conn.start[2] + (imp.conn.end[2] - imp.conn.start[2]) * ease
            );
            imp.mesh.material.opacity = 0.4 + Math.sin(imp.t * Math.PI) * 0.6;
            imp.mesh.scale.setScalar(0.8 + Math.sin(imp.t * Math.PI) * 0.4);
        }
    });
    
    // Mise à jour HUD
    const activeCount = moduleMeshes.filter(m => m.activity > 0.15).length;
    const hz = 8 + activeCount * 5 + Math.random() * 4;
    document.getElementById('shz').textContent = hz.toFixed(1) + ' Hz';
    document.getElementById('bar-fill').style.width = Math.min(100, hz * 1.5) + '%';
    
    controls.update();
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body></html>'''
    return Response(html, mimetype='text/html')

@app.route('/v26')
def v26():
    """Dashboard OpenClaw - Monitoring Système"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw Dashboard</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;500;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e14;color:#c5c8c6;font-family:'IBM Plex Mono',monospace;min-height:100vh}
.container{max-width:1400px;margin:0 auto;padding:20px}
h1{color:#00d7ff;font-size:2rem;margin-bottom:20px;display:flex;align-items:center;gap:10px}
h2{color:#00d7ff;font-size:1.2rem;margin:20px 0 10px;padding-bottom:5px;border-bottom:1px solid #1e2127}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px}
.card{background:#1e2127;border-radius:8px;padding:15px;border:1px solid #333}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.card-title{color:#00d7ff;font-weight:600}
.card-status{padding:4px 12px;border-radius:4px;font-size:0.8rem;font-weight:600}
.status-ok{background:#00aa00;color:#fff}
.stat{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2a2e35}
.stat:last-child{border-bottom:none}
.stat-label{color:#8b8b8b}
.stat-value{color:#fff;font-weight:600}
.stat-value.highlight{color:#00d7ff}
.progress-bar{height:8px;background:#2a2e35;border-radius:4px;overflow:hidden;margin-top:5px}
.progress-fill{height:100%;transition:width 0.3s;background:linear-gradient(90deg,#00aa00,#00ff00)}
.services{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.service{background:#2a2e35;padding:10px;border-radius:6px;display:flex;align-items:center;gap:10px}
.service-icon{font-size:1.5rem}
.service-info{flex:1}
.service-name{font-weight:600;color:#fff}
.service-status{font-size:0.75rem;color:#8b8b8b}
.refresh{position:fixed;top:20px;right:20px;background:#00d7ff;color:#000;border:none;padding:10px 20px;border-radius:4px;cursor:pointer;font-weight:600}
.refresh:hover{background:#00b8d4}
</style>
</head>
<body>
<div class="container">
<h1>⚡ OpenClaw Dashboard</h1>
<div class="grid">
<div class="card">
<div class="card-header"><span class="card-title">🧠 Brain v8.5</span><span class="card-status status-ok" id="brain-status">OK</span></div>
<div class="stat"><span class="stat-label">Neurones</span><span class="stat-value highlight" id="neurons">--</span></div>
<div class="stat"><span class="stat-label">Synapses</span><span class="stat-value" id="synapses">--</span></div>
<div class="stat"><span class="stat-label">Growth</span><span class="stat-value" id="growth">--</span></div>
<div class="stat"><span class="stat-label">Signals</span><span class="stat-value" id="signals">--</span></div>
<div class="progress-bar"><div class="progress-fill" id="brain-progress" style="width:10%"></div></div>
</div>
<div class="card">
<div class="card-header"><span class="card-title">🔧 Services</span><span class="card-status status-ok">5/5</span></div>
<div class="services">
<div class="service"><span class="service-icon">🌐</span><div class="service-info"><div class="service-name">Gateway</div><div class="service-status">● Port 18789</div></div></div>
<div class="service"><span class="service-icon">🧠</span><div class="service-info"><div class="service-name">Brain</div><div class="service-status">● Port 8084</div></div></div>
<div class="service"><span class="service-icon">💾</span><div class="service-info"><div class="service-name">Claude-Mem</div><div class="service-status">● Port 37777</div></div></div>
<div class="service"><span class="service-icon">🔗</span><div class="service-info"><div class="service-name">Bridge</div><div class="service-status">● Active</div></div></div>
<div class="service"><span class="service-icon">🤖</span><div class="service-info"><div class="service-name">Ollama</div><div class="service-status">● Port 11434</div></div></div>
</div>
</div>
<div class="card">
<div class="card-header"><span class="card-title">📦 Stack</span></div>
<div class="stat"><span class="stat-label">Node.js</span><span class="stat-value">22 LTS</span></div>
<div class="stat"><span class="stat-label">Python</span><span class="stat-value">3.12+</span></div>
<div class="stat"><span class="stat-label">Docker</span><span class="stat-value">latest</span></div>
<div class="stat"><span class="stat-label">Redis</span><span class="stat-value">7.x</span></div>
</div>
</div>
</div>
<button class="refresh" onclick="refresh()">🔄 Rafraîchir</button>
<script>
async function refresh(){
try{
const r=await fetch('/api/stats');
const d=await r.json();
document.getElementById('neurons').textContent=d.N.toLocaleString();
document.getElementById('synapses').textContent=d.syn.toLocaleString();
document.getElementById('growth').textContent=d.growth.toLocaleString();
document.getElementById('signals').textContent=d.sig||0;
document.getElementById('brain-progress').style.width=Math.min(100,d.N/1000)+'%';
}catch(e){
document.getElementById('brain-status').textContent='ERROR';
document.getElementById('brain-status').className='card-status';
document.getElementById('brain-status').style.background='#ff4444';
}
}
setInterval(refresh,2000);
refresh();
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')


@app.route('/v24')
def v24():
    """Visualisation V24 - Neurones 3D Volumétriques avec Connexions"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SoulLink Brain v24 - Neural Connectome</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;500&family=Bebas+Neue&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{background:#010206;font-family:'IBM Plex Mono',monospace;display:flex;align-items:center;justify-content:center}
canvas{display:block;cursor:grab;position:absolute;top:0;left:0;width:100%;height:100%}
canvas:active{cursor:grabbing}
#ui{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;}
#hud{
 position:absolute;top:20px;left:20px;pointer-events:auto;
 background:rgba(6,10,20,0.85);border:1px solid rgba(60,158,255,0.3);
 border-radius:3px;padding:16px 20px;backdrop-filter:blur(12px);
 box-shadow:0 0 30px rgba(60,158,255,0.1);min-width:200px;
}
#hud-name{font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:.1em;color:#fff;margin-bottom:2px;}
#hud-sub{font-size:.45rem;color:rgba(255,255,255,0.4);letter-spacing:.2em;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid rgba(60,158,255,0.15)}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:4px 0}
.lbl{font-size:.5rem;color:rgba(255,255,255,0.45);letter-spacing:.08em}
.val{font-size:.65rem;color:#3d9eff;font-weight:500}
.val.hot{color:#ff5577}
.val.cool{color:#44ffaa}
#bar{height:3px;background:rgba(60,158,255,0.15);margin-top:10px;border-radius:2px;overflow:hidden}
#bar-fill{height:100%;width:0%;background:linear-gradient(90deg,#3d9eff,#44ffaa);transition:width 0.15s}
#modules{position:absolute;top:20px;right:20px;pointer-events:auto;background:rgba(6,10,20,0.85);border:1px solid rgba(255,87,119,0.3);border-radius:3px;padding:12px 16px;backdrop-filter:blur(12px);max-height:300px;overflow-y:auto;}
#modules h3{font-family:'Bebas Neue',sans-serif;font-size:.9rem;letter-spacing:.1em;color:#ff5577;margin-bottom:8px}
.mod-row{display:flex;align-items:center;margin:3px 0;font-size:.5rem;color:rgba(255,255,255,0.7)}
.mod-dot{width:8px;height:8px;border-radius:50%;margin-right:8px;box-shadow:0 0 6px currentColor}
.mod-name{flex:1;text-transform:uppercase;letter-spacing:.08em}
.mod-val{color:#fff;font-weight:500}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="ui">
 <div id="hud">
 <div id="hud-name">SOULLINK BRAIN</div>
 <div id="hud-sub">NEURAL CONNECTOME · v24</div>
 <div class="row"><span class="lbl">NEURONS</span><b class="val" id="sn">0</b></div>
 <div class="row"><span class="lbl">SYNAPSES</span><b class="val" id="ssyn">0</b></div>
 <div class="row"><span class="lbl">SIGNALS</span><b class="val" id="ssig">0</b></div>
 <div class="row"><span class="lbl">FREQUENCY</span><b class="val" id="shz">0.0 Hz</b></div>
 <div class="row"><span class="lbl">STATE</span><b class="val" id="sst">IDLE</b></div>
 <div id="bar"><div id="bar-fill"></div></div>
 </div>
 <div id="modules"><h3>MODULES</h3><div id="mod-list"></div></div>
</div>

<script>
const canvas=document.getElementById('c');
const ctx=canvas.getContext('2d',{alpha:false});
let W,H,CX,CY;

const state={rotX:0.12,rotY:-0.5,zoom:1.1,isDragging:false,lastX:0,lastY:0};

const MODULES={
 reasoning:{pos:[0.15,0.70,0.5],col:'#ff5577',n:22},
 motor:{pos:[0.45,0.85,0.6],col:'#aaff44',n:10},
 output:{pos:[0.20,0.40,0.3],col:'#ffee44',n:14},
 attention:{pos:[0.65,0.80,0.55],col:'#cc44ff',n:12},
 perception:{pos:[0.55,0.65,0.45],col:'#ff6644',n:20},
 vision:{pos:[0.90,0.45,0.4],col:'#3dffc0',n:15},
 language:{pos:[0.70,0.40,0.35],col:'#44ffff',n:18},
 audio:{pos:[0.45,0.35,0.25],col:'#4ab0ff',n:12},
 memory:{pos:[0.50,0.25,0.3],col:'#3d9eff',n:28},
 learning:{pos:[0.80,0.10,0.4],col:'#ff9944',n:16}
};

const WIRES={
 perception:['memory','attention','vision','language'],
 memory:['reasoning','learning','language','perception'],
 reasoning:['output','attention','memory'],
 learning:['memory','reasoning','perception'],
 attention:['perception','reasoning','vision','audio'],
 output:['motor','language'],
 language:['memory','output','perception'],
 vision:['perception','attention','motor'],
 audio:['attention','language','memory'],
 motor:['output','vision']
};

let brainData=null, neurons=[], connections=[], lum={}, activity={};
Object.keys(MODULES).forEach(m=>{lum[m]=0; activity[m]=0;});

function resize(){W=canvas.width=window.innerWidth; H=canvas.height=window.innerHeight; CX=W/2; CY=H/2; buildBrain();}
function hexToRgb(hex){return[parseInt(hex.slice(1,3),16),parseInt(hex.slice(3,5),16),parseInt(hex.slice(5,7),16)];}

function project(x,y,z){
 // Rotation autour du centre de l'écran
 const cY=Math.cos(state.rotY),sY=Math.sin(state.rotY);
 const cX=Math.cos(state.rotX),sX=Math.sin(state.rotX);
 const rx=x*cY-z*sY, rz1=x*sY+z*cY;
 const ry=y*cX-rz1*sX, rz2=y*sX+rz1*cX;
 const persp=800/(800+rz2);
 return{x:rx*persp*state.zoom, y:ry*persp*state.zoom, z:rz2, s:persp*state.zoom};
}

function buildBrain(){
 neurons=[]; connections=[];
 const SCALE=Math.min(W,H)*0.35;
 
 // Neurones centrés à l'origine (0,0)
 Object.entries(MODULES).forEach(([name,mod])=>{
 const[px,py,pz]=mod.pos;
 for(let i=0;i<mod.n;i++){
 const angle=Math.random()*Math.PI*2;
 const r=Math.random()*25;
 neurons.push({
 x:(px-0.5)*SCALE*2+Math.cos(angle)*r,
 y:(py-0.5)*SCALE*2+Math.sin(angle)*r,
 z:(pz-0.5)*SCALE*1.2+(Math.random()-0.5)*15,
 mod:name,
 col:mod.col,
 phase:Math.random()*Math.PI*2
 });
 }
 });
 
 // Coque cérébrale (ellipsoïde) centrée à l'origine
 for(let i=0;i<2000;i++){
 const theta=Math.random()*Math.PI*2;
 const phi=Math.acos(2*Math.random()-1);
 const r=1+Math.random()*0.06;
 neurons.push({
 x:r*SCALE*1.1*Math.sin(phi)*Math.cos(theta),
 y:r*SCALE*0.85*Math.sin(phi)*Math.sin(theta),
 z:r*SCALE*0.75*Math.cos(phi),
 mod:'shell',
 col:'#1a3050',
 phase:0
 });
 }
 
 // Connexions intra-modules
 const byMod={};
 neurons.forEach((n,i)=>{if(n.mod!=='shell'){if(!byMod[n.mod])byMod[n.mod]=[]; byMod[n.mod].push(i);}});
 Object.entries(byMod).forEach(([mod,indices])=>{
 for(let i=0;i<indices.length;i++){
 for(let j=i+1;j<indices.length;j++){
 if(Math.random()<0.25) connections.push({a:indices[i],b:indices[j],mod:mod});
 }
 }
 });
 
 // Connexions inter-modules (WIRES)
 Object.entries(WIRES).forEach(([from,tos])=>{
 if(!byMod[from])return;
 tos.forEach(to=>{
 if(!byMod[to])return;
 const nConn=Math.min(2,Math.min(byMod[from].length,byMod[to].length));
 for(let i=0;i<nConn;i++){
 const a=byMod[from][Math.floor(Math.random()*byMod[from].length)];
 const b=byMod[to][Math.floor(Math.random()*byMod[to].length)];
 connections.push({a,b,mod:from+'_'+to,inter:true});
 }
 });
 });
}

let frame=0;
function simulate(){
 Object.keys(MODULES).forEach(name=>{
 const osc=0.5+0.5*Math.sin(frame*0.018+Object.keys(MODULES).indexOf(name)*0.7);
 const base=0.08+osc*0.15;
 if(Math.random()<0.04) lum[name]=Math.min(1,(lum[name]||0)+0.6);
 lum[name]=(lum[name]||0)*0.93+base*0.07;
 activity[name]=Math.round(lum[name]*100);
 });
}

function draw(){
 ctx.globalCompositeOperation='source-over';
 ctx.fillStyle='#010206';
 ctx.fillRect(0,0,W,H);
 
 const projected=neurons.map((n,i)=>({...project(n.x,n.y,n.z),...n,i}));
 projected.sort((a,b)=>b.z-a.z);
 
 // Dessiner connexions en premier (derrière les neurones)
 ctx.globalCompositeOperation='lighter';
 connections.forEach(c=>{
 const pa=projected[c.a], pb=projected[c.b];
 if(!pa||!pb||pa.mod==='shell'||pb.mod==='shell')return;
 const act=Math.max(lum[pa.mod]||0,lum[pb.mod]||0);
 if(act<0.1)return;
 const rgb=hexToRgb(pa.col);
 ctx.strokeStyle='rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+','+(0.08+act*0.25)+')';
 ctx.lineWidth=0.5+act;
 ctx.beginPath();
 ctx.moveTo(CX+pa.x,CY+pa.y);
 ctx.lineTo(CX+pb.x,CY+pb.y);
 ctx.stroke();
 });
 ctx.globalCompositeOperation='source-over';
 
 // Dessiner coque
 projected.filter(p=>p.mod==='shell').forEach(p=>{
 const alpha=0.04+(1-(p.z+150)/300)*0.08;
 ctx.fillStyle='rgba(26,48,80,'+Math.max(0.02,alpha)+')';
 ctx.fillRect(CX+p.x,CY+p.y,1.3*p.s,1.3*p.s);
 });
 
 // Dessiner neurones
 projected.filter(p=>p.mod!=='shell').forEach(p=>{
 const rgb=hexToRgb(p.col);
 const act=lum[p.mod]||0;
 const pulse=0.9+Math.sin(frame*0.04+p.phase)*0.15;
 const size=(1.4+act*2.2)*p.s*pulse;
 
 // Halo si actif
 if(act>0.25){
 ctx.globalCompositeOperation='lighter';
 const g=ctx.createRadialGradient(CX+p.x,CY+p.y,0,CX+p.x,CY+p.y,size*3);
 g.addColorStop(0,'rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+','+(act*0.4)+')');
 g.addColorStop(1,'rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+',0)');
 ctx.fillStyle=g;
 ctx.fillRect(CX+p.x-size*3,CY+p.y-size*3,size*6,size*6);
 ctx.globalCompositeOperation='source-over';
 }
 
 // Corps du neurone
 ctx.fillStyle='rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+','+(0.45+act*0.5)+')';
 ctx.fillRect(CX+p.x-size/2,CY+p.y-size/2,size,size);
 });
}

function updateHUD(){
 const activeMods=Object.values(lum).filter(v=>v>0.2).length;
 const hz=12+activeMods*8+Math.random()*6;
 const sig=brainData?brainData.stats.sig||0:0;
 document.getElementById('sn').textContent=brainData?brainData.stats.N.toLocaleString():neurons.filter(n=>n.mod!=='shell').length;
 document.getElementById('ssyn').textContent=brainData?brainData.stats.syn.toLocaleString():connections.length;
 document.getElementById('ssig').textContent=sig;
 document.getElementById('shz').textContent=hz.toFixed(1)+' Hz';
 const st=document.getElementById('sst');
 st.textContent=sig>10?'CRITICAL':hz>35?'ACTIVE':hz>18?'NOMINAL':'IDLE';
 st.className='val'+(hz>40?' hot':hz<15?' cool':'');
 document.getElementById('bar-fill').style.width=Math.min(100,hz/0.6)+'%';
 
 // Module list
 let html='';
 Object.entries(MODULES).forEach(([name,mod])=>{
 const act=activity[name]||0;
 html+='<div class="mod-row"><div class="mod-dot" style="background:'+mod.col+';color:'+mod.col+'"></div><span class="mod-name">'+name+'</span><span class="mod-val">'+act+'%</span></div>';
 });
 document.getElementById('mod-list').innerHTML=html;
}

async function fetchBrainData(){
 try{
 const res=await fetch('/api/brain');
 brainData=await res.json();
 }catch(e){}
}

function loop(){
 if(!state.isDragging) state.rotY-=0.0015;
 simulate();
 draw();
 frame++;
 requestAnimationFrame(loop);
}

window.onmousedown=e=>{state.isDragging=true; state.lastX=e.clientX; state.lastY=e.clientY;};
window.onmouseup=()=>state.isDragging=false;
window.onmousemove=e=>{
 if(state.isDragging){
 state.rotY-=(e.clientX-state.lastX)*0.004;
 state.rotX-=(e.clientY-state.lastY)*0.004;
 state.rotX=Math.max(-0.7,Math.min(0.7,state.rotX));
 state.lastX=e.clientX; state.lastY=e.clientY;
 }
};
window.onwheel=e=>{
 state.zoom*=(e.deltaY>0?0.96:1.04);
 state.zoom=Math.max(0.4,Math.min(3,state.zoom));
};

window.addEventListener('resize',resize);
resize();
fetchBrainData();
setInterval(fetchBrainData,2500);
setInterval(updateHUD,200);
loop();
</script>
</body></html>'''
    return Response(html, mimetype='text/html')

@app.route('/v23')
def v23():
    """Visualisation Three.js - Cortex v18.2 + Neurones colorés par module (v12 style)"""
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>SoulLink Brain v23 - Neural Network in Cortex</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;500&family=Bebas+Neue&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{background:#020408;overflow:hidden;font-family:'IBM Plex Mono',monospace}
#hud{
 position:fixed;top:20px;left:20px;z-index:10;
 background:rgba(6,10,20,0.75);border:1px solid rgba(60,158,255,0.2);
 border-radius:2px;padding:14px 18px;backdrop-filter:blur(8px);
 box-shadow:0 0 20px rgba(60,158,255,0.08);min-width:180px;
}
#hud-name{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:.08em;color:#fff;margin-bottom:1px;}
#hud-sub{font-size:.4rem;color:rgba(255,255,255,0.3);letter-spacing:.15em;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid rgba(60,158,255,0.12)}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:3px 0}
.lbl{font-size:.45rem;color:rgba(255,255,255,0.35);letter-spacing:.05em}
.val{font-size:.5rem;color:#3d9eff;font-weight:500}
.val.hot{color:#ff5577}
#mods{margin-top:8px;display:grid;grid-template-columns:repeat(2,1fr);gap:2px}
.mod{display:flex;align-items:center;gap:4px;font-size:.35rem;color:rgba(255,255,255,0.4)}
.mod-dot{width:6px;height:6px;border-radius:50%}
</style>
</head>
<body>
<div id="hud">
 <div id="hud-name">SOULLINK</div>
 <div id="hud-sub">NEURAL NETWORK · v23</div>
 <div class="row"><span class="lbl">NEURONS</span><b class="val" id="sn">0</b></div>
 <div class="row"><span class="lbl">ACTIVE</span><b class="val" id="sma">0/10</b></div>
 <div class="row"><span class="lbl">STATE</span><b class="val" id="sst">NOMINAL</b></div>
 <div id="mods"></div>
</div>

<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.162.0/build/three.module.js" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'https://unpkg.com/three@0.162.0/examples/jsm/controls/OrbitControls.js';

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x020408, 8, 25);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0, 6);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.minDistance = 3;
controls.maxDistance = 10;

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dirLight = new THREE.DirectionalLight(0xffe0d0, 1.5);
dirLight.position.set(5, 8, 5);
scene.add(dirLight);

// === CORTEX ENVELOPPE v18.2 ===
function createBrainGeometry() {
    const geometry = new THREE.SphereGeometry(2.4, 160, 160);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
        const v = new THREE.Vector3().fromBufferAttribute(pos, i);
        v.x *= 1.28; v.y *= 0.92; v.z *= 0.82;
        const foldA = Math.sin(v.x * 7) * 0.12;
        const foldB = Math.cos(v.y * 10) * 0.08;
        const foldC = Math.sin((v.x + v.z) * 9) * 0.06;
        v.addScaledVector(v.clone().normalize(), foldA + foldB + foldC);
        pos.setXYZ(i, v.x, v.y, v.z);
    }
    geometry.computeVertexNormals();
    return geometry;
}
const brainMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9b3a5, roughness: 0.95, metalness: 0, clearcoat: 0,
    transparent: true, opacity: 0.15, transmission: 0.95,
    side: THREE.DoubleSide, depthWrite: false
});
const brain = new THREE.Mesh(createBrainGeometry(), brainMaterial);
scene.add(brain);

// === MODULES (comme v12) ===
const MODULES = {
    reasoning: { col: 0xff5577, pos: [0.5, 1.0, 0.6], size: 0.25 },
    motor:     { col: 0xaaff44, pos: [0.7, 0.8, 0.3], size: 0.22 },
    output:    { col: 0xffee44, pos: [-0.3, 0.5, 0.4], size: 0.20 },
    attention: { col: 0xcc44ff, pos: [0.6, 0.9, -0.2], size: 0.23 },
    perception:{ col: 0xff6644, pos: [0.0, 0.7, 0.5], size: 0.21 },
    vision:    { col: 0x3dffc0, pos: [0.0, 0.3, -1.0], size: 0.28 },
    language:  { col: 0x44ffff, pos: [-0.6, 0.4, 0.4], size: 0.22 },
    audio:     { col: 0x4ab0ff, pos: [-0.8, 0.2, 0.1], size: 0.24 },
    memory:    { col: 0x3d9eff, pos: [0.0, 0.0, 0.2], size: 0.26 },
    learning:  { col: 0xff9944, pos: [0.3, -0.3, -0.5], size: 0.20 }
};

const moduleMeshes = [];
const neurons = [];
const connections = [];
const impulses = [];

// Créer les centres de modules (sphères)
Object.entries(MODULES).forEach(([name, mod]) => {
    const geo = new THREE.SphereGeometry(mod.size, 16, 12);
    const mat = new THREE.MeshPhongMaterial({
        color: mod.col, transparent: true, opacity: 0.7,
        emissive: mod.col, emissiveIntensity: 0.2, shininess: 50
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(...mod.pos);
    scene.add(mesh);
    moduleMeshes.push({ mesh, name, mod, phase: Math.random() * Math.PI * 2, activity: 0 });
    
    // Créer neurones autour de chaque module
    const numNeurons = 15 + Math.floor(Math.random() * 10);
    for (let i = 0; i < numNeurons; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = mod.size * (0.8 + Math.random() * 0.8);
        const neuronGeo = new THREE.SphereGeometry(0.02 + Math.random() * 0.02, 6, 4);
        const neuronMat = new THREE.MeshBasicMaterial({ color: mod.col, transparent: true, opacity: 0.6 });
        const neuron = new THREE.Mesh(neuronGeo, neuronMat);
        neuron.position.set(
            mod.pos[0] + r * Math.sin(phi) * Math.cos(theta),
            mod.pos[1] + r * Math.sin(phi) * Math.sin(theta),
            mod.pos[2] + r * Math.cos(phi)
        );
        scene.add(neuron);
        neurons.push({ mesh: neuron, module: name, baseOpacity: 0.4 + Math.random() * 0.3, phase: Math.random() * Math.PI * 2 });
    }
});

// Connexions entre modules proches
const modNames = Object.keys(MODULES);
for (let i = 0; i < modNames.length; i++) {
    for (let j = i + 1; j < modNames.length; j++) {
        const a = MODULES[modNames[i]].pos;
        const b = MODULES[modNames[j]].pos;
        const dist = Math.sqrt(Math.pow(a[0]-b[0],2) + Math.pow(a[1]-b[1],2) + Math.pow(a[2]-b[2],2));
        if (dist < 1.3) {
            const geo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(...a), new THREE.Vector3(...b)
            ]);
            const line = new THREE.Line(geo, new THREE.LineBasicMaterial({
                color: 0x3d9eff, transparent: true, opacity: 0.15
            }));
            scene.add(line);
            connections.push({ line, start: a, end: b, phase: Math.random() * Math.PI * 2 });
        }
    }
}

// Impulsions électriques
const impulseGeo = new THREE.SphereGeometry(0.03, 6, 4);
connections.forEach(conn => {
    for (let i = 0; i < 3; i++) {
        const impulse = new THREE.Mesh(impulseGeo, new THREE.MeshBasicMaterial({
            color: 0x5bd7ff, transparent: true, opacity: 0.9
        }));
        scene.add(impulse);
        impulses.push({
            mesh: impulse, conn: conn,
            t: Math.random(), speed: 0.006 + Math.random() * 0.008,
            delay: Math.random() * 150
        });
    }
});

// HUD modules
document.getElementById('mods').innerHTML = Object.entries(MODULES).map(([name, mod]) =>
    '<div class="mod"><div class="mod-dot" style="background:#' + mod.col.toString(16).padStart(6, '0') + '"></div><span>' + name + '</span></div>'
).join('');

let brainData = null;
async function fetchBrainData() {
    try {
        const res = await fetch('/api/brain');
        brainData = await res.json();
        document.getElementById('sn').textContent = brainData.stats.N.toLocaleString();
    } catch(e) {}
}
fetchBrainData();
setInterval(fetchBrainData, 2000);

let frame = 0;
function animate() {
    requestAnimationFrame(animate);
    frame++;
    
    brain.rotation.y += 0.001;
    
    // Animer modules
    moduleMeshes.forEach((m, i) => {
        if (Math.random() < 0.02) m.activity = Math.min(1, m.activity + 0.4);
        m.activity *= 0.95;
        m.mesh.scale.setScalar(1 + Math.sin(frame * 0.04 + m.phase) * 0.08 + m.activity * 0.15);
        m.mesh.material.emissiveIntensity = 0.15 + m.activity * 0.4;
    });
    
    // Animer neurones
    neurons.forEach(n => {
        n.mesh.material.opacity = n.baseOpacity + Math.sin(frame * 0.03 + n.phase) * 0.2;
    });
    
    // Animer impulsions
    let activeCount = 0;
    impulses.forEach(imp => {
        if (frame < imp.delay) { imp.mesh.visible = false; return; }
        imp.t += imp.speed;
        if (imp.t > 1) { imp.t = 0; imp.mesh.visible = Math.random() < 0.6; }
        if (imp.mesh.visible) {
            activeCount++;
            const ease = imp.t < 0.5 ? 2 * imp.t * imp.t : 1 - Math.pow(-2 * imp.t + 2, 2) / 2;
            imp.mesh.position.set(
                imp.conn.start[0] + (imp.conn.end[0] - imp.conn.start[0]) * ease,
                imp.conn.start[1] + (imp.conn.end[1] - imp.conn.start[1]) * ease,
                imp.conn.start[2] + (imp.conn.end[2] - imp.conn.start[2]) * ease
            );
            imp.mesh.material.opacity = 0.5 + Math.sin(imp.t * Math.PI) * 0.5;
            imp.mesh.scale.setScalar(0.7 + Math.sin(imp.t * Math.PI) * 0.3);
        }
    });
    
    // Animer connexions
    connections.forEach((c, i) => {
        c.line.material.opacity = 0.1 + Math.sin(frame * 0.02 + c.phase) * 0.08;
    });
    
    // Update HUD
    const activeMods = moduleMeshes.filter(m => m.activity > 0.15).length;
    document.getElementById('sma').textContent = activeMods + '/10';
    const st = document.getElementById('sst');
    st.textContent = activeMods > 5 ? 'ACTIVE' : activeMods > 2 ? 'NOMINAL' : 'IDLE';
    st.className = 'val' + (activeMods > 5 ? ' hot' : '');
    
    controls.update();
    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();
</script>
</body>
</html>'''
    return Response(html, mimetype='text/html')

    return Response(html, mimetype='text/html')
def simulation_loop():
    """Boucle de simulation pour la croissance et l'activité neuronale"""
    import time
    while True:
        try:
            with brain.lock:
                # Croissance occasionnelle
                if len(brain.neurons) < brain.max_neurons:
                    if random.random() < 0.1:  # 10% chance par cycle
                        brain._grow_random_neuron()
                
                # Simulation d'activité
                for n in brain.neurons:
                    if random.random() < 0.01:  # 1% chance de spike
                        n['voltage'] = 1.0
                
                # Decay
                for n in brain.neurons:
                    n['voltage'] *= 0.95
                    
        except Exception as e:
            pass
        time.sleep(0.1)

if __name__ == '__main__':
    print("🧠 SoulLink Brain v8.5 — Persistance CORRIGÉE")
    print(f"   Modules: {len(brain.modules)}")
    print(f"   Neurones: {len(brain.neurons)} (actuels)")
    print(f"   Neurones totaux: {brain.total_neurons} (historique)")
    print(f"   Synapses: {len(brain.synapses)}")
    print(f"   Port: 8084")
    print("")
    print("   🌐 Interface: http://localhost:8084")
    print("   📊 API: http://localhost:8084/api/brain")
    print("   💾 Persistance: /mnt/nvme/soullink_brain/brain_state.json")
    print("   ✨ FIX: Neurones et synapses sauvegardés et restaurés")
    
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    
    app.run(host='0.0.0.0', port=8084, threaded=True)