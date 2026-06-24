"""
Forward model sanity test for Task 3.

Tests that a +0.3 g/cc uniform density contrast produces negative gz
(downward attraction) in SimPEG's right-hand z-up coordinate system.

SimPEG convention:
  - Density in g/cc  (NOT kg/m3)
  - gz = UPWARD component of gravity acceleration
  - Mass below receiver -> pulls receiver DOWN -> gz < 0
  - This is OPPOSITE to the downward-positive mGal convention used
    for observed CBA data; so dobs = -CBA when passed to SimPEG.

Run:  .venv\\Scripts\\python.exe scripts/_test_07_forward.py
Expected output:
  Forward test: gz = <negative number> mGal for 0.3 g/cc uniform model
  PASS: forward simulation OK
"""

import sys, os, json
import numpy as np
import discretize
import simpeg
from simpeg import maps
from simpeg.potential_fields import gravity as grav_sim

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESH_JSON = os.path.join(PROJECT_ROOT, "output", "07_mesh_params.json")

if not os.path.exists(MESH_JSON):
    print("SKIP: run Task 2 first to generate mesh params")
    sys.exit(0)

with open(MESH_JSON) as f:
    p = json.load(f)

mesh = discretize.TensorMesh(
    [np.array(p["hx"]), np.array(p["hy"]), np.array(p["hz"])],
    origin=np.array(p["origin"])
)

active_cells = np.ones(mesh.n_cells, dtype=bool)
nC = int(active_cells.sum())

# API adaptation: InjectActiveCells(mesh, active_cells, value_inactive) -- positional OK
actmap = maps.InjectActiveCells(mesh, active_cells, 0.0)

# Single observation point at center of mesh, 2600 m above surface
cx = mesh.origin[0] + mesh.h[0].sum() / 2
cy = mesh.origin[1] + mesh.h[1].sum() / 2
rx_test = np.array([[cx, cy, 2600.0]])

rxList   = [grav_sim.Point(rx_test, components=["gz"])]
srcField = grav_sim.SourceField(receiver_list=rxList)
survey   = grav_sim.Survey(srcField)

# API adaptation: active_cells= is the correct kwarg (ind_active was removed in v0.24)
sim = grav_sim.Simulation3DIntegral(
    mesh, survey=survey,
    rhoMap=actmap,
    active_cells=active_cells,
    store_sensitivities="ram",
)

# API adaptation: density model must be in g/cc, NOT kg/m3
# +300 kg/m3 = +0.3 g/cc  (ESO reference density contrast)
m_test = np.full(nC, 0.3)   # 0.3 g/cc = 300 kg/m3
pred   = sim.dpred(m_test)

# SimPEG sign convention: gz is the UPWARD component.
# Mass below the receiver pulls it DOWNWARD, so gz < 0 for positive density.
# The forward test must assert gz < 0 (downward attraction = physically correct).
# NOTE: This means CBA observed data (downward-positive convention) must be
#       negated before passing to SimPEG: dobs = -CBA_mGal
assert len(pred) == 1, "Expected 1 prediction, got {}".format(len(pred))
assert pred[0] < 0, (
    "Expected negative gz (upward component) for positive density below receiver, "
    "got {:.4f} mGal -- check sign convention".format(pred[0])
)
print("Forward test: gz = {:.4f} mGal for 0.3 g/cc uniform model".format(pred[0]))
print("  (negative = downward attraction, physically correct for SimPEG z-up convention)")
print("PASS: forward simulation OK")
