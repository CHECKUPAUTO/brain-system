#!/usr/bin/env python3
import urllib.request, json, time

BRAIN_API = "http://localhost:8084"

# Topics avec espaces → split() fonctionne correctement
THE_WELL_DATASETS = [
    ("active matter physics",         "physics"),
    ("stellar convection physics",    "physics"),
    ("euler equations physics",       "physics"),
    ("helmholtz acoustics physics",   "physics"),
    ("magnetohydrodynamics physics",  "physics"),
    ("plasma turbulence physics",     "physics"),
    ("shallow water physics",         "physics"),
    ("neutron star physics",          "physics"),
    ("rayleigh benard physics",       "physics"),
    ("rayleigh taylor physics",       "physics"),
    ("turbulent shear physics",       "physics"),
    ("supernova physics",             "physics"),
    ("stellar hydrodynamics physics", "physics"),
    ("radiative transfer physics",    "physics"),
    ("viscoelastic fluid physics",    "physics"),
    ("reaction diffusion chemistry",  "chemistry"),
    ("navier stokes physics",         "physics"),
    ("gravitational waves physics",   "physics"),
    ("plasma physics",                "physics"),
    ("astrophysics simulation",       "physics"),
]

def inject(topic):
    payload = json.dumps({"topic": topic}).encode()
    req = urllib.request.Request(
        f"{BRAIN_API}/api/learn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

def stats():
    with urllib.request.urlopen(f"{BRAIN_API}/api/stats", timeout=3) as r:
        return json.loads(r.read())

s1 = stats()
print(f"AVANT → N:{s1['N']} | KG:{s1['kg_concepts']}\n")

for topic, expected in THE_WELL_DATASETS:
    result = inject(topic)
    got = result.get('module')
    ok = "✓" if got == expected else "⚠"
    print(f"  {ok} {topic} → {got} +{result.get('new_neurons')}N")
    time.sleep(0.3)

s2 = stats()
print(f"\nAPRÈS → N:{s2['N']} | KG:{s2['kg_concepts']}")
print(f"Gain  → +{s2['N']-s1['N']} neurones | +{s2['kg_concepts']-s1['kg_concepts']} concepts")
