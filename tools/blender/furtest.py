import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bpy
import characters as C
from lib import *
OUT = Path(sys.argv[1])
reset(); world_sky(top=(0.05, 0.25, 0.8), bottom=(0.5, 0.75, 1.0)); snow_ground(); lights(key_energy=5)
g = C.build_goro((-0.15, 0, 0)); g.rotation_euler.z = math.radians(20)
d = C.build_don((1.6, 2.5, 0)); d.rotation_euler.z = math.radians(-25)
ob = bpy.data.objects
add_fur(ob["goro.belly"], C.CREAM, length=0.035, count=3000, children=15)
for n in ("don.torso", "don.headmesh", "don.armmesh_L", "don.armmesh_R"):
    add_fur(ob[n], C.DARK_CHOCO, length=0.09 if "torso" in n else 0.06, count=4000, children=20, clump=0.4, rough=0.02)
add_fur(ob["don.belly"], C.TAN, length=0.07, count=3000, children=20, clump=0.4, rough=0.02)
add_fur(ob["don.muzzle"], C.TAN, length=0.03, count=1500, children=10)
sc = render_settings(samples=32, engine=sys.argv[2] if len(sys.argv) > 2 else "CYCLES")
sc.render.resolution_percentage = 50
camera(loc=(0.3, -2.4, 0.75), target=(0.4, 0.5, 0.9), lens=24)
render_still(OUT)
