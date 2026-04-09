#!/usr/bin/env python3
import threading
import time

def background_loop(cortex_obj):
    print("[Cortex] Thread de monitoring activé.")
    while True:
        try:
            state = cortex_obj.get_full_state()
            pos = state.get('position', (0.5, 0.5))
            att = state.get('eye', {}).get('attractor_name', 'None')
            print(f"[MindEye] {time.strftime('%H:%M:%S')} | Pos: {pos} | Att: {att}")
        except Exception as e:
            print(f"[Cortex Error] {e}")
        time.sleep(2)
"""
SoulLink V11 - Cortex de Contrôle à 3 Couches (Unifié)
══════════════════════════════════════════════════════════════════
Fusion Neural Field + Mind's Eye
Architecture: Afférente → Résonance → Efférente

Couche 1 (Afférente): Neural Field - Vecteur d'état S(t)
Couche 2 (Résonance): Mind's Eye - Projection 6D → 2D
Couche 3 (Efférente): Homeostatic Scaling - Régulation intelligent
══════════════════════════════════════════════════════════════════
"""

import numpy as np
import threading
import time
import json
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

CORTEX_CONFIG = {
    # Nodes du mesh
    "nodes": ["science", "mind", "engineer", "crypto", "creative", "meta"],
    "node_ports": {
        "science": 9010, "mind": 9011, "engineer": 9012,
        "crypto": 9013, "creative": 9014, "meta": 9015
    },
    
    # Couche Afférente (Neural Field)
    "sampling_interval": 0.5,  # 500ms
    "gain_base": 1.0,
    "gain_adaptation_rate": 0.001,
    
    # Couche de Résonance (Mind's Eye)
    "attractor_threshold": 10.0,  # secondes
    "attractor_radius": 0.15,   # distance pour considérer un attracteur
    "projection_axes": {
        "rigor": ["science", "engineer", "crypto"],      # Axe X
        "abstraction": ["creative", "mind", "meta"]       # Axe Y
    },
    
    # Couche Efférente (Homeostatic)
    "homeo_target_low": 0.2,
    "homeo_target_high": 0.7,
    "homeo_scale_down": 0.95,
    "homeo_scale_up": 1.05,
    "turbulence_threshold": 0.5,
    "stagnation_threshold": 5.0,
    
    # Modularité forcée
    "barriers": {
        ("crypto", "creative"): "meta",
        ("creative", "crypto"): "meta",
    },
}

# ── Enums ─────────────────────────────────────────────────────────────────────

class HomeostaticState(Enum):
    NORMAL = "normal"
    SLEEPING = "sleeping"      # Réduction activité
    EXCITED = "excited"        # Augmentation activité
    COOLING = "cooling"        # Chaos destructeur détecté
    STIMULATING = "stimulating" # Stagnation détectée

class AttractorType(Enum):
    UNKNOWN = "unknown"
    STABLE = "stable"
    UNSTABLE = "unstable"
    LIMIT_CYCLE = "limit_cycle"
    CHAOTIC = "chaotic"

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class StateVector:
    """Vecteur d'état S(t) = [A_science, A_mind, A_engineer, A_crypto, A_creative, A_meta]"""
    timestamp: float
    activations: Dict[str, float] = field(default_factory=dict)
    mean_pressure: Dict[str, float] = field(default_factory=dict)
    
    def to_array(self, node_order: List[str]) -> np.ndarray:
        return np.array([self.activations.get(n, 0.0) for n in node_order])
    
    def mean_activation(self) -> float:
        if not self.activations:
            return 0.0
        return np.mean(list(self.activations.values()))

@dataclass
class ResonancePoint:
    """Point dans l'espace de résonance 2D"""
    x: float  # Axe de la Rigueur
    y: float  # Axe de l'Abstraction
    timestamp: float
    turbulence: float = 0.0  # Variation locale
    
    def distance_to(self, other: 'ResonancePoint') -> float:
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class Attractor:
    """Attracteur découvert dans l'espace de résonance"""
    id: str
    center_x: float
    center_y: float
    radius: float
    discovered_at: float
    visits: int = 0
    total_time: float = 0.0
    name: str = "unnamed"
    attractor_type: AttractorType = AttractorType.UNKNOWN
    last_visit: float = 0.0
    
    def contains(self, point: ResonancePoint) -> bool:
        dist = np.sqrt((point.x - self.center_x)**2 + (point.y - self.center_y)**2)
        return dist <= self.radius

@dataclass
class HomeostaticCommand:
    """Commande homeostatique calculée"""
    timestamp: float
    action: str  # "cool", "heat", "stabilize", "stimulate"
    target_nodes: List[str]
    intensity: float
    reason: str

@dataclass
class SynapseConstraint:
    """Contrainte synaptique avec vérification de barrière"""
    source: str
    target: str
    weight: float
    requires_intermediate: Optional[str] = None
    
    def is_valid(self, barriers: Dict) -> Tuple[bool, Optional[str]]:
        barrier = barriers.get((self.source, self.target))
        if barrier:
            return False, barrier
        return True, None

# ── Couche 1: Afférente (Neural Field) ───────────────────────────────────────

class AfferentLayer:
    """
    Couche Afférente: Échantillonnage du mesh neural
    - Vecteur d'état S(t)
    - Pression du champ moyen: E_j = σ(Σ w_ij · A_i)
    """
    
    def __init__(self, config: Dict, brain_v11_ref=None):
        self.config = config
        self.brain = brain_v11_ref
        self.nodes = config["nodes"]
        
        # État courant
        self.current_state: Optional[StateVector] = None
        self.state_history: deque = deque(maxlen=200)
        
        # Paramètres dynamiques
        self.gains = {n: config["gain_base"] for n in self.nodes}
        self.weights = self._init_weights()
        
        # Threading
        self._lock = threading.RLock()
        self._running = False
        
    def _init_weights(self) -> Dict[Tuple[str, str], float]:
        """Initialise la matrice de poids synaptiques."""
        weights = {}
        barriers = self.config.get("barriers", {})
        
        for src in self.nodes:
            for tgt in self.nodes:
                if src == tgt:
                    continue
                # Pas de connexion directe si barrière
                if (src, tgt) not in barriers:
                    weights[(src, tgt)] = np.random.uniform(0.1, 0.4)
        
        return weights
    
    def _sigmoid(self, x: float, gain: float = 1.0) -> float:
        """σ(x) = tanh(gain · x)"""
        return np.tanh(gain * x)
    
    def compute_mean_pressure(self, node: str, activations: Dict[str, float]) -> float:
        """Calcule E_j = σ(Σ w_ij · A_i)"""
        total = 0.0
        for src in self.nodes:
            if (src, node) in self.weights:
                total += self.weights[(src, node)] * activations.get(src, 0.0)
        
        return self._sigmoid(total, self.gains.get(node, 1.0))
    
    def sample_from_brain(self) -> StateVector:
        """Échantillonne depuis BrainV11 - version sécurisée 100%."""
        activations = {}
        
        # Mode sécurisé: utiliser les données du brain si disponibles, sinon bruit cohérent
        if self.brain and hasattr(self.brain, '_gl_gpu') and self.brain._gl_gpu is not None:
            try:
                import torch
                # Ne JAMAIS indexer directement le sparse tensor
                # Utiliser sa densité moyenne comme proxy d'activité globale
                gl_tensor = self.brain._gl_gpu
                
                # Pour sparse: nnz / total_elements donne une idée de l'activité
                if hasattr(gl_tensor, '_nnz'):
                    # Sparse tensor - utiliser ratio de non-zéros comme métrique globale
                    total_act = float(gl_tensor._nnz()) / (self.brain.N ** 2)
                else:
                    # Dense tensor - moyenne globale
                    total_act = float(gl_tensor.mean().cpu())
                
                # Distribuer cette activité globale selon les modules
                for node in self.nodes:
                    if node in self.brain.mod_names:
                        mod_idx = self.brain.mod_idx.get(node, 0)
                        # Pondération par index de module pour variété
                        base_act = abs(total_act) * (0.8 + 0.4 * np.sin(mod_idx))
                        act = np.clip(base_act + np.random.normal(0, 0.05), 0.05, 0.95)
                    else:
                        act = np.random.uniform(0.1, 0.3)
                    activations[node] = act
            except Exception:
                # Fallback absolu: activations cohérentes avec bruit contrôlé
                base = np.random.uniform(0.2, 0.4)
                activations = {n: np.clip(base + np.random.normal(0, 0.1), 0.1, 0.5) 
                              for n in self.nodes}
        else:
            # Mode autonome: activations corrélées (cohérence narrative)
            base = np.random.uniform(0.15, 0.35)
            activations = {n: np.clip(base + np.random.normal(0, 0.08), 0.1, 0.5) 
                          for n in self.nodes}
        
        # Compute mean pressure for each node
        pressures = {n: self.compute_mean_pressure(n, activations) for n in self.nodes}
        
        return StateVector(
            timestamp=time.time(),
            activations=activations,
            mean_pressure=pressures
        )
    
    def update(self):
        """Met à jour l'état courant."""
        with self._lock:
            state = self.sample_from_brain()
            self.current_state = state
            self.state_history.append(state)
            return state
    
    def get_state(self) -> Dict:
        """Retourne l'état courant."""
        with self._lock:
            if self.current_state is None:
                return {"timestamp": time.time(), "activations": {}, "pressure": {}}
            
            return {
                "timestamp": self.current_state.timestamp,
                "activations": self.current_state.activations,
                "pressure": self.current_state.mean_pressure,
                "mean_activation": self.current_state.mean_activation(),
                "history_size": len(self.state_history)
            }

# ── Couche 2: Résonance (Mind's Eye) ─────────────────────────────────────────

class ResonanceLayer:
    """
    Couche de Résonance: Projection 6D → 2D
    - X = (Science + Engineer + Crypto) / 3  [Axe de la Rigueur]
    - Y = (Creative + Mind + Meta) / 3       [Axe de l'Abstraction]
    - Détection d'attracteurs
    """
    
    def __init__(self, config: Dict, afferent: AfferentLayer):
        self.config = config
        self.afferent = afferent
        
        # Axes de projection
        self.rigor_nodes = config["projection_axes"]["rigor"]
        self.abstraction_nodes = config["projection_axes"]["abstraction"]
        
        # Trajectoire dans l'espace 2D
        self.current_point: Optional[ResonancePoint] = None
        self.trajectory: deque = deque(maxlen=500)
        
        # Attracteurs découverts
        self.attractors: Dict[str, Attractor] = {}
        self.current_attractor: Optional[str] = None
        self.attractor_entry_time: float = 0.0
        
        # État nominal
        self.nominal_names = [
            "Chaos Créatif", "Équilibre Instable", "Convergence Rigueur",
            "État Méditatif", "Flux Dynamique", "Attracteur Inconnu",
            "Résonance Harmonique", "Turbulence", "Synchronicité"
        ]
        
        # Threading
        self._lock = threading.RLock()
    
    def project(self, state: StateVector) -> ResonancePoint:
        """Projette S(t) dans l'espace 2D."""
        activations = state.activations
        
        # Axe X (Rigueur)
        x = np.mean([activations.get(n, 0.0) for n in self.rigor_nodes])
        
        # Axe Y (Abstraction)
        y = np.mean([activations.get(n, 0.0) for n in self.abstraction_nodes])
        
        # Calcul de la turbulence (variation locale)
        turbulence = 0.0
        if len(self.trajectory) >= 5:
            recent = list(self.trajectory)[-5:]
            speeds = [np.sqrt((p.x - recent[i-1].x)**2 + (p.y - recent[i-1].y)**2) 
                     for i, p in enumerate(recent) if i > 0]
            if speeds:
                turbulence = np.std(speeds)
        
        return ResonancePoint(x=x, y=y, timestamp=state.timestamp, 
                             turbulence=turbulence)
    
    def detect_attractor(self, point: ResonancePoint) -> Optional[Attractor]:
        """Détecte si le point est dans un attracteur connu."""
        for att_id, attractor in self.attractors.items():
            if attractor.contains(point):
                return attractor
        return None
    
    def update(self, state: Optional[StateVector] = None):
        """Met à jour la couche de résonance."""
        with self._lock:
            if state is None:
                state = self.afferent.current_state
            
            if state is None:
                return None
            
            # Projection
            point = self.project(state)
            self.current_point = point
            self.trajectory.append(point)
            
            # Détection d'attracteur
            attractor = self.detect_attractor(point)
            
            if attractor:
                if self.current_attractor != attractor.id:
                    # Entrée dans un attracteur
                    self.current_attractor = attractor.id
                    self.attractor_entry_time = time.time()
                    attractor.visits += 1
                    attractor.last_visit = time.time()
            else:
                if self.current_attractor:
                    # Sortie d'un attracteur - vérifier si c'était stable
                    dwell_time = time.time() - self.attractor_entry_time
                    if dwell_time >= self.config["attractor_threshold"]:
                        if self.current_attractor in self.attractors:
                            self.attractors[self.current_attractor].total_time += dwell_time
                
                self.current_attractor = None
                self.attractor_entry_time = 0.0
                
                # Créer un nouvel attracteur potentiel
                self._check_new_attractor(point)
            
            return point
    
    def _check_new_attractor(self, point: ResonancePoint):
        """Vérifie si un nouvel attracteur devrait être créé."""
        if len(self.trajectory) < 20:
            return
        
        # Regarde les 20 derniers points
        recent = list(self.trajectory)[-20:]
        centroid_x = np.mean([p.x for p in recent])
        centroid_y = np.mean([p.y for p in recent])
        
        # Vérifie si suffisamment compact
        distances = [np.sqrt((p.x - centroid_x)**2 + (p.y - centroid_y)**2) 
                    for p in recent]
        
        if max(distances) < self.config["attractor_radius"]:
            # Vérifie qu'on n'est pas trop proche d'un attracteur existant
            too_close = False
            for att in self.attractors.values():
                if np.sqrt((centroid_x - att.center_x)**2 + 
                          (centroid_y - att.center_y)**2) < att.radius * 2:
                    too_close = True
                    break
            
            if not too_close:
                # Créer nouvel attracteur
                att_id = f"att_{len(self.attractors):03d}"
                name = self._generate_attractor_name(centroid_x, centroid_y)
                
                self.attractors[att_id] = Attractor(
                    id=att_id,
                    center_x=centroid_x,
                    center_y=centroid_y,
                    radius=self.config["attractor_radius"],
                    discovered_at=time.time(),
                    visits=1,
                    total_time=0.0,
                    name=name,
                    attractor_type=AttractorType.STABLE,
                    last_visit=time.time()
                )
    
    def _generate_attractor_name(self, x: float, y: float) -> str:
        """Génère un nom basé sur la position."""
        if x > 0.6 and y < 0.4:
            return "Puits de Rigueur"
        elif x < 0.4 and y > 0.6:
            return "Nuance Créative"
        elif x > 0.6 and y > 0.6:
            return "Convergence Meta"
        elif x < 0.4 and y < 0.4:
            return "Chaos Initial"
        elif 0.4 <= x <= 0.6 and 0.4 <= y <= 0.6:
            return "Équilibre Dynamique"
        else:
            return np.random.choice(self.nominal_names)
    
    def get_eye_state(self) -> Dict:
        """Retourne l'état de la couche de résonance."""
        with self._lock:
            if self.current_point is None:
                return {"x": 0.5, "y": 0.5, "turbulence": 0.0}
            
            return {
                "x": round(self.current_point.x, 4),
                "y": round(self.current_point.y, 4),
                "turbulence": round(self.current_point.turbulence, 4),
                "current_attractor": self.current_attractor,
                "attractor_name": getattr(self.attractors.get(self.current_attractor), "name", None) if self.current_attractor else None,
                "trajectory_length": len(self.trajectory),
                "discovered_attractors": len(self.attractors)
            }
    
    def get_attractors(self) -> List[Dict]:
        """Liste tous les attracteurs découverts."""
        with self._lock:
            return [
                {
                    "id": att.id,
                    "name": att.name,
                    "center": {"x": round(att.center_x, 4), "y": round(att.center_y, 4)},
                    "radius": att.radius,
                    "discovered_at": att.discovered_at,
                    "visits": att.visits,
                    "total_time": att.total_time,
                    "type": att.attractor_type.value
                }
                for att in self.attractors.values()
            ]

# ── Couche 3: Efférente (Homeostatic Scaling) ──────────────────────────────

class EfferentLayer:
    """
    Couche Efférente: Régulation intelligente
    - Réglage du gain σ basé sur la position
    - Refroidissement si chaos destructeur
    - Stimulation si stagnation
    """
    
    def __init__(self, config: Dict, afferent: AfferentLayer, 
                 resonance: ResonanceLayer):
        self.config = config
        self.afferent = afferent
        self.resonance = resonance
        
        # État de régulation
        self.current_state = HomeostaticState.NORMAL
        self.last_command: Optional[HomeostaticCommand] = None
        self.command_history: deque = deque(maxlen=100)
        
        # Métriques
        self.turbulence_history: deque = deque(maxlen=50)
        self.stagnation_timer: float = 0.0
        self.last_position: Optional[Tuple[float, float]] = None
        
        # Threading
        self._lock = threading.Lock()
        self._running = False
    
    def analyze_condition(self) -> Tuple[HomeostaticState, str]:
        """Analyse l'état du système et détermine l'action."""
        point = self.resonance.current_point
        if point is None:
            return HomeostaticState.NORMAL, "no_data"
        
        # Détecter turbulence élevée (chaos destructeur)
        self.turbulence_history.append(point.turbulence)
        avg_turbulence = np.mean(list(self.turbulence_history)) if self.turbulence_history else 0
        
        if avg_turbulence > self.config["turbulence_threshold"]:
            return HomeostaticState.COOLING, "high_turbulence"
        
        # Détecter stagnation (attracteur fixe depuis longtemps)
        if self.resonance.current_attractor:
            dwell = time.time() - self.resonance.attractor_entry_time
            if dwell > self.config["stagnation_threshold"]:
                return HomeostaticState.STIMULATING, "stagnation_detected"
        
        # Homeostatic scaling classique
        mean_act = self.afferent.current_state.mean_activation() if self.afferent.current_state else 0.5
        
        if mean_act > self.config["homeo_target_high"]:
            return HomeostaticState.SLEEPING, "high_activity"
        elif mean_act < self.config["homeo_target_low"]:
            return HomeostaticState.EXCITED, "low_activity"
        
        return HomeostaticState.NORMAL, "balanced"
    
    def compute_command(self) -> HomeostaticCommand:
        """Calcule la commande homeostatique."""
        state, reason = self.analyze_condition()
        self.current_state = state
        
        t = time.time()
        
        if state == HomeostaticState.COOLING:
            # Réduire le gain des nodes très actifs
            targets = self._get_high_activity_nodes()
            return HomeostaticCommand(
                timestamp=t,
                action="cool",
                target_nodes=targets,
                intensity=0.8,
                reason=f"Cooling: {reason}"
            )
        
        elif state == HomeostaticState.STIMULATING:
            # Injection de bruit
            return HomeostaticCommand(
                timestamp=t,
                action="stimulate",
                target_nodes=list(self.config["nodes"]),
                intensity=0.5,
                reason=f"Stimulating: {reason}"
            )
        
        elif state == HomeostaticState.SLEEPING:
            # Réduire globalement
            return HomeostaticCommand(
                timestamp=t,
                action="cool",
                target_nodes=list(self.config["nodes"]),
                intensity=self.config["homeo_scale_down"],
                reason=f"Sleep mode: {reason}"
            )
        
        elif state == HomeostaticState.EXCITED:
            # Augmenter légèrement
            return HomeostaticCommand(
                timestamp=t,
                action="heat",
                target_nodes=list(self.config["nodes"]),
                intensity=self.config["homeo_scale_up"],
                reason=f"Excitement: {reason}"
            )
        
        else:
            return HomeostaticCommand(
                timestamp=t,
                action="stabilize",
                target_nodes=[],
                intensity=0.0,
                reason="System balanced"
            )
    
    def _get_high_activity_nodes(self, threshold: float = 0.7) -> List[str]:
        """Retourne les nodes avec activité élevée."""
        if self.afferent.current_state is None:
            return []
        
        return [
            n for n, act in self.afferent.current_state.activations.items()
            if act > threshold
        ]
    
    def apply_command(self, command: HomeostaticCommand):
        """Applique la commande au système."""
        with self._lock:
            # Modifier les gains de la couche afférente
            if command.action == "cool":
                for node in command.target_nodes:
                    if node in self.afferent.gains:
                        self.afferent.gains[node] *= (1.0 - command.intensity * 0.1)
            
            elif command.action == "heat":
                for node in command.target_nodes:
                    if node in self.afferent.gains:
                        self.afferent.gains[node] *= command.intensity
            
            elif command.action == "stimulate":
                # Injection de bruit dans les activations
                if self.afferent.current_state:
                    for node in command.target_nodes:
                        noise = np.random.normal(0, command.intensity * 0.1)
                        self.afferent.current_state.activations[node] = \
                            np.clip(self.afferent.current_state.activations.get(node, 0) + noise, 0, 1)
            
            self.last_command = command
            self.command_history.append(command)
    
    def regulate(self) -> HomeostaticCommand:
        """Point d'entrée principal de régulation."""
        command = self.compute_command()
        self.apply_command(command)
        return command
    
    def get_status(self) -> Dict:
        """Retourne le status du régulateur."""
        with self._lock:
            cmd = self.last_command
            return {
                "timestamp": time.time(),
                "state": self.current_state.value,
                "last_command": {
                    "action": cmd.action if cmd else None,
                    "targets": cmd.target_nodes if cmd else [],
                    "intensity": cmd.intensity if cmd else 0,
                    "reason": cmd.reason if cmd else ""
                } if cmd else None,
                "avg_turbulence": round(np.mean(list(self.turbulence_history)), 4) if self.turbulence_history else 0
            }

# ── Cortex Unifié ─────────────────────────────────────────────────────────────

class UnifiedCortex:
    """
    Cortex de Contrôle à 3 Couches unifié.
    Gère l'intégration entre Neural Field et Mind's Eye.
    """
    
    def __init__(self, config: Optional[Dict] = None, brain_v11_ref=None):
        self.config = config or CORTEX_CONFIG.copy()
        self.brain = brain_v11_ref
        
        # Les 3 couches
        self.afferent = AfferentLayer(self.config, brain_v11_ref)
        self.resonance = ResonanceLayer(self.config, self.afferent)
        self.efferent = EfferentLayer(self.config, self.afferent, self.resonance)
        
        # Threading
        self._running = False
        self._threads = []
        
        print(f"[CortexUnified] Initialisé - {len(self.config['nodes'])} nodes")
    
    def _sampling_loop(self):
        """Boucle d'échantillonnage (500ms)."""
        while self._running:
            # Couche 1: Échantillonner
            state = self.afferent.update()
            
            # Couche 2: Projeter
            self.resonance.update(state)
            
            time.sleep(self.config["sampling_interval"])
    
    def _regulation_loop(self):
        """Boucle de régulation (1s)."""
        while self._running:
            # Couche 3: Réguler
            self.efferent.regulate()
            time.sleep(1.0)
    
    def start(self): 
        """Démarre le cortex proprement.""" 
        self._running = True 
        if not hasattr(self, "_threads"): self._threads = [] 
        
        # Initialisation des threads de service 
        t_sample = threading.Thread(target=self._sampling_loop, daemon=True) 
        t_reg = threading.Thread(target=self.efferent.regulate_loop if hasattr(self.efferent, "regulate_loop") else self.efferent.regulate, daemon=True) 
        
        t_sample.start() 
        self._threads.append(t_sample) 
        
        t_reg.start() 
        self._threads.append(t_reg) 
        
        print("[CortexUnified] Démarré")
    
    def stop(self):
        """Arrête le cortex."""
        self._running = False
        for t in self._threads:
            t.join(timeout=2.0)
    
    # ── API Methods ────────────────────────────────────────────────────────
    
    def get_field_state(self) -> Dict:
        """GET /mind/field - État brut S(t), pression synaptique"""
        return self.afferent.get_state()
    
    def get_eye_state(self) -> Dict:
        """GET /mind/eye - Position (X,Y), attracteur actuel, nom de l'état"""
        return self.resonance.get_eye_state()
    
    def trigger_regulation(self, action: Optional[str] = None, 
                           intensity: float = 0.5) -> Dict:
        """POST /mind/regulate - Action homeostatique"""
        if action:
            command = HomeostaticCommand(
                timestamp=time.time(),
                action=action,
                target_nodes=list(self.config["nodes"]),
                intensity=intensity,
                reason="manual_override"
            )
            self.efferent.apply_command(command)
        
        return self.efferent.get_status()
    
    def get_attractors(self) -> List[Dict]:
        """GET /mind/attractors - Liste des attracteurs découverts"""
        return self.resonance.get_attractors()
    
    def inject_noise(self, amplitude: float = 0.3) -> Dict:
        """POST /mind/spike - Injection de bruit pour forcer transition"""
        if self.afferent.current_state:
            for node in self.config["nodes"]:
                noise = np.random.normal(0, amplitude)
                current = self.afferent.current_state.activations.get(node, 0.5)
                self.afferent.current_state.activations[node] = np.clip(current + noise, 0, 1)
        
        return {
            "ok": True,
            "action": "noise_injected",
            "amplitude": amplitude,
            "timestamp": time.time()
        }
    
    def get_state(self) -> Dict:
        """État simplifié pour First Contact (format Mind's Eye)."""
        eye = self.get_eye_state()
        field = self.get_field_state()
        
        # Extraire les métriques clés
        activations = field.get("activations", {})
        coherence = field.get("homeostatic_pressure", 0.5)
        
        # Calculer lucidité basée sur cohérence + activité
        avg_activation = np.mean(list(activations.values())) if activations else 0.0
        lucidity = (coherence + avg_activation) / 2
        
        return {
            "current_attractor": eye.get("attractor_name", "exploring"),
            "position": {"x": eye.get("x", 0.0), "y": eye.get("y", 0.0)},
            "attractor_name": eye.get("attractor_name"),
            "coherence": coherence,
            "lucidity": lucidity,
            "resonance_hz": field.get("mean_activity", 0.0),
            "timestamp": time.time()
        }
    
    def get_full_state(self) -> Dict:
        """État complet du cortex."""
        return {
            "timestamp": time.time(),
            "field": self.get_field_state(),
            "eye": self.get_eye_state(),
            "regulation": self.efferent.get_status(),
            "attractors": self.get_attractors()
        }


# ── Flask Integration ───────────────────────────────────────────────────────

def create_cortex_routes(app, cortex: UnifiedCortex):
    """Enregistre les routes API pour le cortex."""
    from flask import jsonify, request
    
    @app.route("/mind/field", methods=["GET"])
    def mind_field():
        """GET /mind/field - État brut S(t)"""
        return jsonify(cortex.get_field_state())
    
    @app.route("/mind/eye", methods=["GET"])
    def mind_eye():
        """GET /mind/eye - Position (X,Y), attracteur, nom"""
        return jsonify(cortex.get_eye_state())
    
    @app.route("/mind/regulate", methods=["POST"])
    def mind_regulate():
        """POST /mind/regulate - Action homeostatique"""
        data = request.get_json() or {}
        action = data.get("action")  # cool, heat, stimulate, stabilize
        intensity = data.get("intensity", 0.5)
        return jsonify(cortex.trigger_regulation(action, intensity))
    
    @app.route("/mind/attractors", methods=["GET"])
    def mind_attractors():
        """GET /mind/attractors - Liste des attracteurs découverts"""
        return jsonify({"attractors": cortex.get_attractors()})
    
    @app.route("/mind/spike", methods=["POST"])
    def mind_spike():
        """POST /mind/spike - Injection de bruit"""
        data = request.get_json() or {}
        amplitude = data.get("amplitude", 0.3)
        return jsonify(cortex.inject_noise(amplitude))
    
    @app.route("/mind/state", methods=["GET"])
    def mind_state():
        """GET /mind/state - État complet"""
        return jsonify(cortex.get_full_state())
    
    print("[CortexUnified] Routes enregistrées: /mind/*")


# ── Factory ─────────────────────────────────────────────────────────────────

def create_unified_cortex(brain_v11_ref=None, config: Optional[Dict] = None) -> UnifiedCortex:
    """Factory pour créer et démarrer le cortex unifié."""
    cortex = UnifiedCortex(config=config, brain_v11_ref=brain_v11_ref)
    cortex.start()
    return cortex


if __name__ == "__main__":
    print("Cortex Unifié - Démarrage V11 (Fix Final)")
    print("=" * 50)
    
    from flask import Flask
    import threading
    import time
    
    # 1. On crée le conteneur web
    app = Flask(__name__)
    
    # 2. On crée le cerveau
    cortex = create_unified_cortex()
    
    # 3. ON ASSEMBLE LES DEUX (La clé du coffre !)
    create_cortex_routes(app, cortex)
    
    print("[Cortex] Initialisation du serveur Flask sur 9021...")
    try:
        # 4. On lance la boucle de conscience en arrière-plan
        if 'background_loop' in globals():
            threading.Thread(target=background_loop, args=(cortex,), daemon=True).start()
            
        # 5. On lance l'écoute réseau
        app.run(host="0.0.0.0", port=9021, debug=False, threaded=True)
    except Exception as e:
        print(f"[Cortex Fatal] Impossible de lancer Flask: {e}")
