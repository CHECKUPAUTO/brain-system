#!/usr/bin/env python3
"""
SoulLink Brain — Autonomous Science Crawler
============================================
Sources :
  1. Wikipedia  — découverte autonome par liens internes
  2. arXiv      — abstracts des derniers papiers scientifiques
  3. GitHub     — README + descriptions de repos scientifiques
  4. The Well   — datasets physics (PolymathicAI)
  5. PubMed     — abstracts neurosciences/biophysique

Injecte tout dans brain_v9 via POST /api/learn
Tourne en continu, non-bloquant, respectueux des rate limits
"""

import urllib.request
import urllib.parse
import json
import time
import random
import re
import threading
import logging
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

BRAIN_API   = "http://localhost:8084"
LOG_FILE    = "/root/.openclaw/workspace/science_crawler.log"
STATE_FILE  = "/root/.openclaw/workspace/crawler_state.json"

# Délais entre requêtes (secondes) — respecter les rate limits
DELAY_WIKIPEDIA = (20, 40)
DELAY_ARXIV     = (30, 60)
DELAY_GITHUB    = (15, 30)
DELAY_PUBMED    = (25, 45)

# GitHub token optionnel (60 req/h sans, 5000 req/h avec)
GITHUB_TOKEN = ""   # Mettre ton token ici si tu en as un

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ─── Module mapping ───────────────────────────────────────────────────────────

KEYWORD_MODULE = {
    "physics":        "physics",
    "quantum":        "physics",
    "relativity":     "physics",
    "thermodynamic":  "physics",
    "fluid":          "physics",
    "plasma":         "physics",
    "astrophysic":    "physics",
    "cosmolog":       "physics",
    "nuclear":        "physics",
    "optic":          "physics",
    "mechanic":       "physics",
    "chemistry":      "chemistry",
    "chemical":       "chemistry",
    "molecular":      "chemistry",
    "reaction":       "chemistry",
    "neuroscience":   "neuroscience",
    "neural":         "neuroscience",
    "brain":          "neuroscience",
    "neuron":         "neuroscience",
    "spike":          "neuroscience",
    "synapse":        "neuroscience",
    "cognit":         "neuroscience",
    "calculus":       "calculus",
    "differential":   "calculus",
    "integral":       "calculus",
    "fourier":        "calculus",
    "algebra":        "algebra",
    "matrix":         "algebra",
    "vector":         "algebra",
    "group theory":   "algebra",
    "topology":       "geometry",
    "geometry":       "geometry",
    "manifold":       "geometry",
    "statistic":      "statistics",
    "probabilit":     "statistics",
    "bayesian":       "statistics",
    "stochastic":     "statistics",
    "logic":          "logic",
    "formal":         "logic",
    "algorithm":      "computation",
    "complexity":     "computation",
    "computation":    "computation",
    "automata":       "computation",
    "information":    "information",
    "entropy":        "information",
    "optim":          "optimization",
    "gradient":       "optimization",
    "pattern":        "patterns",
    "fractal":        "patterns",
    "philosoph":      "philosophy",
    "mathematic":     "mathematics",
    "number theory":  "mathematics",
}

def detect_module(text: str) -> str:
    text_lower = text.lower()
    for keyword, module in KEYWORD_MODULE.items():
        if keyword in text_lower:
            return module
    return "mathematics"

# ─── Brain API ────────────────────────────────────────────────────────────────

def inject(topic: str, source: str = "") -> dict:
    try:
        payload = json.dumps({"topic": topic}).encode()
        req = urllib.request.Request(
            f"{BRAIN_API}/api/learn",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
            logging.getLogger(source).info(
                f"✓ {topic[:60]} → {result.get('module')} +{result.get('new_neurons')}N"
            )
            return result
    except Exception as e:
        logging.getLogger(source).warning(f"✗ inject failed: {e}")
        return {}

def brain_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{BRAIN_API}/api/stats", timeout=3) as r:
            return True
    except:
        return False

# ─── État du crawler ──────────────────────────────────────────────────────────

def load_state() -> dict:
    try:
        if Path(STATE_FILE).exists():
            return json.load(open(STATE_FILE))
    except:
        pass
    return {
        "wikipedia_visited": [],
        "arxiv_last_id": "",
        "github_page": 1,
        "pubmed_offset": 0,
        "total_injected": 0,
        "sessions": 0,
    }

def save_state(state: dict):
    try:
        json.dump(state, open(STATE_FILE, "w"), indent=2)
    except Exception as e:
        logging.warning(f"State save failed: {e}")

# ─── SOURCE 1 : Wikipedia Autonome ───────────────────────────────────────────

class WikipediaCrawler:
    """
    Crawl Wikipedia de façon autonome :
    - Commence par des pages seed scientifiques
    - Suit les liens internes pour découvrir de nouveaux sujets
    - Évite les doublons via un historique
    """

    SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
    LINKS_URL   = "https://en.wikipedia.org/api/rest_v1/page/links/{}"

    SEED_TOPICS = [
        "Spiking_neural_network", "Computational_neuroscience",
        "Neuroplasticity", "Hebbian_learning", "Neural_oscillation",
        "Consciousness", "Emergent_behavior", "Complex_system",
        "Self-organization", "Dynamical_system",
        "Partial_differential_equation", "Manifold", "Riemannian_geometry",
        "Symplectic_geometry", "Lie_group", "Representation_theory",
        "Measure_theory", "Functional_analysis", "Operator_algebra",
        "Quantum_field_theory", "String_theory", "Loop_quantum_gravity",
        "Dark_matter", "Black_hole", "Neutron_star",
        "Fluid_dynamics", "Turbulence", "Chaos_theory",
        "Protein_folding", "DNA", "Evolutionary_algorithm",
        "Swarm_intelligence", "Cellular_automaton",
    ]

    def __init__(self, state: dict):
        self.log     = logging.getLogger("Wikipedia")
        self.visited = set(state.get("wikipedia_visited", []))
        self.queue   = list(self.SEED_TOPICS)
        random.shuffle(self.queue)

    def _fetch(self, slug: str) -> dict:
        url = self.SUMMARY_URL.format(urllib.parse.quote(slug))
        req = urllib.request.Request(
            url, headers={"User-Agent": "SoulLink-Brain-v9/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())

    def _fetch_links(self, slug: str) -> list:
        url = self.LINKS_URL.format(urllib.parse.quote(slug))
        req = urllib.request.Request(
            url, headers={"User-Agent": "SoulLink-Brain-v9/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return [item["key"] for item in data.get("items", [])[:20]]

    def run_once(self) -> bool:
        if not self.queue:
            self.queue = list(self.SEED_TOPICS)
            random.shuffle(self.queue)

        slug = self.queue.pop(0)
        if slug in self.visited:
            return False

        try:
            data    = self._fetch(slug)
            extract = data.get("extract", "")
            title   = data.get("title", slug)

            if not extract or len(extract) < 100:
                return False

            module = detect_module(title + " " + extract[:200])
            topic  = f"{title.lower().replace(' ', '_')} {module}"
            inject(topic, "Wikipedia")

            self.visited.add(slug)
            if len(self.visited) > 1000:
                oldest = list(self.visited)[:200]
                for o in oldest:
                    self.visited.discard(o)

            # Découverte : ajouter quelques liens en queue
            try:
                links = self._fetch_links(slug)
                new_links = [l for l in links if l not in self.visited][:5]
                self.queue.extend(new_links)
                self.log.info(f"  Découverts: {len(new_links)} nouveaux liens")
            except:
                pass

            return True

        except Exception as e:
            self.log.warning(f"✗ {slug}: {e}")
            return False

    def get_visited_list(self) -> list:
        return list(self.visited)[:500]

# ─── SOURCE 2 : arXiv ─────────────────────────────────────────────────────────

class ArxivCrawler:
    """
    Crawl les derniers abstracts arXiv sur les catégories scientifiques
    pertinentes pour brain_v9
    """

    BASE_URL = "https://export.arxiv.org/api/query"

    CATEGORIES = [
        ("cs.NE",    "neuroscience"),   # Neural and Evolutionary Computing
        ("cs.LG",    "computation"),    # Machine Learning
        ("physics.bio-ph", "physics"), # Biological Physics
        ("cond-mat.stat-mech", "physics"), # Statistical Mechanics
        ("math.DS",  "mathematics"),   # Dynamical Systems
        ("math.MP",  "physics"),       # Mathematical Physics
        ("q-bio.NC", "neuroscience"),  # Neurons and Cognition
        ("nlin.CD",  "mathematics"),   # Chaotic Dynamics
        ("nlin.AO",  "patterns"),      # Adaptation and Self-Organizing
        ("physics.flu-dyn", "physics"),# Fluid Dynamics
    ]

    def __init__(self, state: dict):
        self.log      = logging.getLogger("arXiv")
        self.cat_idx  = 0
        self.seen_ids = set()

    def _fetch_recent(self, category: str, start: int = 0) -> list:
        params = urllib.parse.urlencode({
            "search_query": f"cat:{category}",
            "start": start,
            "max_results": 5,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        })
        url = f"{self.BASE_URL}?{params}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SoulLink-Brain-v9/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode()

        # Parse XML basique sans bibliothèque externe
        entries = []
        for entry in re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL):
            arxiv_id = re.search(r"<id>(.*?)</id>", entry)
            title    = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            summary  = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            if arxiv_id and title and summary:
                entries.append({
                    "id":      arxiv_id.group(1).strip(),
                    "title":   title.group(1).strip().replace("\n", " "),
                    "summary": summary.group(1).strip().replace("\n", " ")[:500],
                })
        return entries

    def run_once(self) -> bool:
        category, default_module = self.CATEGORIES[self.cat_idx % len(self.CATEGORIES)]
        self.cat_idx += 1

        try:
            entries = self._fetch_recent(category)
            injected = 0
            for entry in entries:
                if entry["id"] in self.seen_ids:
                    continue
                self.seen_ids.add(entry["id"])
                if len(self.seen_ids) > 2000:
                    oldest = list(self.seen_ids)[:500]
                    for o in oldest:
                        self.seen_ids.discard(o)

                module = detect_module(entry["title"] + " " + entry["summary"])
                topic  = f"{entry['title'][:60].lower().replace(' ', '_')} {module}"
                inject(topic, "arXiv")
                injected += 1
                time.sleep(2)

            self.log.info(f"  {category}: {injected} nouveaux abstracts")
            return injected > 0

        except Exception as e:
            self.log.warning(f"✗ arXiv {category}: {e}")
            return False

# ─── SOURCE 3 : GitHub ────────────────────────────────────────────────────────

class GithubCrawler:
    """
    Crawl GitHub pour des repos scientifiques :
    - Trending repos par topic scientifique
    - README et descriptions des grands projets
    - Organisations scientifiques (PolymathicAI, deepmind, etc.)
    """

    SEARCH_URL = "https://api.github.com/search/repositories"
    ORGS_URL   = "https://api.github.com/orgs/{}/repos"
    README_URL = "https://api.github.com/repos/{}/readme"

    SCIENCE_TOPICS = [
        "spiking-neural-network",
        "computational-neuroscience",
        "physics-simulation",
        "scientific-computing",
        "machine-learning-physics",
        "neural-ode",
        "dynamical-systems",
        "fluid-dynamics",
        "quantum-computing",
        "biophysics",
        "neuromorphic-computing",
        "mathematical-modeling",
        "chaos-theory",
        "deep-learning-neuroscience",
        "physics-informed-neural-networks",
    ]

    SCIENCE_ORGS = [
        "PolymathicAI",
        "deepmind",
        "brainpy",
        "AllenInstitute",
        "spikingjelly",
        "neurophysics",
        "openai",
        "EleutherAI",
    ]

    def __init__(self, state: dict):
        self.log      = logging.getLogger("GitHub")
        self.topic_idx = 0
        self.org_idx   = 0
        self.seen_repos = set()
        self.headers   = {"User-Agent": "SoulLink-Brain-v9/1.0"}
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {GITHUB_TOKEN}"

    def _fetch(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())

    def _process_repo(self, repo: dict) -> bool:
        full_name = repo.get("full_name", "")
        if full_name in self.seen_repos:
            return False
        self.seen_repos.add(full_name)

        name        = repo.get("name", "")
        description = repo.get("description", "") or ""
        topics      = repo.get("topics", [])
        language    = repo.get("language", "") or ""

        text   = f"{name} {description} {' '.join(topics)}"
        module = detect_module(text)
        topic  = f"{name.lower().replace('-', '_')} {module}"

        inject(topic, "GitHub")

        # Si le repo a une bonne description, injecter aussi la description
        if len(description) > 30:
            desc_topic = f"{description[:50].lower().replace(' ', '_')} {module}"
            inject(desc_topic, "GitHub")

        return True

    def run_topics(self) -> bool:
        gh_topic = self.SCIENCE_TOPICS[self.topic_idx % len(self.SCIENCE_TOPICS)]
        self.topic_idx += 1

        try:
            params = urllib.parse.urlencode({
                "q": f"topic:{gh_topic}",
                "sort": "stars",
                "per_page": 10,
            })
            data  = self._fetch(f"{self.SEARCH_URL}?{params}")
            repos = data.get("items", [])

            injected = 0
            for repo in repos:
                if self._process_repo(repo):
                    injected += 1
                    time.sleep(1)

            self.log.info(f"  Topic '{gh_topic}': {injected} repos traités")
            return injected > 0

        except Exception as e:
            self.log.warning(f"✗ GitHub topic {gh_topic}: {e}")
            return False

    def run_orgs(self) -> bool:
        org = self.SCIENCE_ORGS[self.org_idx % len(self.SCIENCE_ORGS)]
        self.org_idx += 1

        try:
            repos    = self._fetch(self.ORGS_URL.format(org))
            injected = 0
            for repo in repos[:10]:
                if self._process_repo(repo):
                    injected += 1
                    time.sleep(1)

            self.log.info(f"  Org '{org}': {injected} repos traités")
            return injected > 0

        except Exception as e:
            self.log.warning(f"✗ GitHub org {org}: {e}")
            return False

    def run_once(self) -> bool:
        # Alterner topics et orgs
        if self.topic_idx % 3 == 0:
            return self.run_orgs()
        return self.run_topics()

# ─── SOURCE 4 : PubMed ────────────────────────────────────────────────────────

class PubMedCrawler:
    """
    Crawl PubMed pour des abstracts en neurosciences et biophysique
    """

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    QUERIES = [
        ("spiking neural network brain", "neuroscience"),
        ("neuroplasticity learning memory", "neuroscience"),
        ("neural oscillation synchrony", "neuroscience"),
        ("computational neuroscience model", "neuroscience"),
        ("biophysics membrane potential", "physics"),
        ("protein folding dynamics", "chemistry"),
        ("neural coding information theory", "information"),
        ("synaptic plasticity STDP", "neuroscience"),
        ("brain connectivity graph", "neuroscience"),
        ("consciousness emergence complexity", "neuroscience"),
    ]

    def __init__(self, state: dict):
        self.log      = logging.getLogger("PubMed")
        self.query_idx = 0
        self.seen_ids  = set()

    def _search(self, query: str) -> list:
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": 5,
            "retmode": "json",
            "sort": "date",
        })
        url = f"{self.SEARCH_URL}?{params}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SoulLink-Brain-v9/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return data.get("esearchresult", {}).get("idlist", [])

    def _fetch_summary(self, pmids: list) -> list:
        params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        })
        url = f"{self.SUMMARY_URL}?{params}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SoulLink-Brain-v9/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return list(data.get("result", {}).values())

    def run_once(self) -> bool:
        query, default_module = self.QUERIES[self.query_idx % len(self.QUERIES)]
        self.query_idx += 1

        try:
            pmids = self._search(query)
            new_pmids = [p for p in pmids if p not in self.seen_ids]
            if not new_pmids:
                return False

            summaries = self._fetch_summary(new_pmids)
            injected  = 0

            for article in summaries:
                if not isinstance(article, dict):
                    continue
                pmid  = str(article.get("uid", ""))
                title = article.get("title", "")
                if not title or pmid in self.seen_ids:
                    continue
                self.seen_ids.add(pmid)

                module = detect_module(title + " " + query)
                topic  = f"{title[:60].lower().replace(' ', '_')} {module}"
                inject(topic, "PubMed")
                injected += 1
                time.sleep(2)

            self.log.info(f"  '{query[:40]}': {injected} articles")
            return injected > 0

        except Exception as e:
            self.log.warning(f"✗ PubMed: {e}")
            return False

# ─── SOURCE 5 : The Well (PolymathicAI) ──────────────────────────────────────

class TheWellCrawler:
    """
    Injecte les descriptions détaillées des 16 datasets de The Well
    avec enrichissement progressif
    """

    DATASETS = [
        ("active matter physics",          "Self-propelled particles, collective motion, biological physics simulation"),
        ("convective envelope physics",     "Red supergiant star, stellar convection, turbulent astrophysics"),
        ("euler equations physics",         "Compressible fluid dynamics, shock waves, hyperbolic PDE simulation"),
        ("helmholtz acoustics physics",     "Acoustic scattering, wave propagation, frequency domain physics"),
        ("magnetohydrodynamics physics",    "Plasma physics, magnetic field turbulence, astrophysical MHD"),
        ("shallow water physics",           "Planetary atmosphere, geophysical fluid dynamics, wave equations"),
        ("neutron star physics",            "Neutron star merger, gravitational waves, nuclear matter"),
        ("rayleigh benard physics",         "Thermal convection, buoyancy instability, chaotic fluid dynamics"),
        ("rayleigh taylor physics",         "Interface instability, turbulent mixing, density stratification"),
        ("turbulent shear physics",         "Kelvin-Helmholtz instability, vorticity dynamics, Navier-Stokes"),
        ("supernova physics",               "Core-collapse supernova, shock revival, neutrino transport"),
        ("radiative transfer physics",      "Photon transport, stellar atmosphere, opacity radiation"),
        ("viscoelastic fluid physics",      "Polymer dynamics, elastic turbulence, non-Newtonian rheology"),
        ("reaction diffusion chemistry",    "Gray-Scott model, Turing patterns, chemical pattern formation"),
        ("gravitational waves physics",     "Binary merger, spacetime curvature, LIGO detection"),
        ("quantum field physics",           "Quantum chromodynamics, field theory, particle physics"),
    ]

    def __init__(self):
        self.log = logging.getLogger("TheWell")
        self.idx = 0

    def run_once(self) -> bool:
        if self.idx >= len(self.DATASETS):
            self.idx = 0
        topic, description = self.DATASETS[self.idx]
        self.idx += 1
        inject(topic, "TheWell")
        return True

# ─── ORCHESTRATEUR ────────────────────────────────────────────────────────────

class BrainCrawlerOrchestrator:
    """
    Orchestre tous les crawlers de façon asynchrone
    Chaque crawler tourne dans son propre thread avec son propre rate limit
    """

    def __init__(self):
        self.log      = logging.getLogger("Orchestrator")
        self.state    = load_state()
        self.state["sessions"] += 1
        self.running  = True

        # Init crawlers
        self.wiki     = WikipediaCrawler(self.state)
        self.arxiv    = ArxivCrawler(self.state)
        self.github   = GithubCrawler(self.state)
        self.pubmed   = PubMedCrawler(self.state)
        self.well     = TheWellCrawler()

        self.total    = self.state.get("total_injected", 0)

    def _run_crawler(self, name: str, crawler_fn, delay_range: tuple):
        log = logging.getLogger(name)
        log.info(f"Thread démarré")
        while self.running:
            if not brain_alive():
                log.warning("Brain v9 non accessible — attente 60s")
                time.sleep(60)
                continue
            try:
                success = crawler_fn()
                if success:
                    self.total += 1
                    self.state["total_injected"] = self.total
            except Exception as e:
                log.error(f"Erreur: {e}")
            delay = random.uniform(*delay_range)
            time.sleep(delay)

    def run(self):
        self.log.info(f"=== BrainCrawler démarré — session #{self.state['sessions']} ===")
        self.log.info(f"    Total injecté toutes sessions: {self.total}")

        if not brain_alive():
            self.log.error("Brain v9 API inaccessible sur port 8084 — arrêt")
            return

        # Lancer chaque crawler dans son thread
        threads = [
            threading.Thread(
                target=self._run_crawler,
                args=("Wikipedia", self.wiki.run_once, DELAY_WIKIPEDIA),
                daemon=True, name="t-wiki"
            ),
            threading.Thread(
                target=self._run_crawler,
                args=("arXiv", self.arxiv.run_once, DELAY_ARXIV),
                daemon=True, name="t-arxiv"
            ),
            threading.Thread(
                target=self._run_crawler,
                args=("GitHub", self.github.run_once, DELAY_GITHUB),
                daemon=True, name="t-github"
            ),
            threading.Thread(
                target=self._run_crawler,
                args=("PubMed", self.pubmed.run_once, DELAY_PUBMED),
                daemon=True, name="t-pubmed"
            ),
            threading.Thread(
                target=self._run_crawler,
                args=("TheWell", self.well.run_once, (300, 600)),
                daemon=True, name="t-well"
            ),
        ]

        for t in threads:
            t.start()
            time.sleep(2)  # Décalage entre les démarrages

        self.log.info(f"  {len(threads)} crawlers actifs")

        # Boucle principale — save state toutes les 5 min
        try:
            while True:
                time.sleep(300)
                self.state["wikipedia_visited"] = self.wiki.get_visited_list()
                self.state["total_injected"]    = self.total
                save_state(self.state)

                # Stats
                try:
                    with urllib.request.urlopen(f"{BRAIN_API}/api/stats", timeout=3) as r:
                        stats = json.loads(r.read())
                    self.log.info(
                        f"📊 Brain — N:{stats['N']} | KG:{stats['kg_concepts']} "
                        f"| hz:{stats['hz']} | Total injecté:{self.total}"
                    )
                except:
                    pass

        except KeyboardInterrupt:
            self.log.info("Arrêt demandé — sauvegarde état...")
            self.running = False
            self.state["wikipedia_visited"] = self.wiki.get_visited_list()
            self.state["total_injected"]    = self.total
            save_state(self.state)
            self.log.info("✓ État sauvegardé. Au revoir.")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    orchestrator = BrainCrawlerOrchestrator()
    orchestrator.run()
