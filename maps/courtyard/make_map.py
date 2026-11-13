"""Generate mp_courtyard_dm.map - a small town-square multiplayer map for MOH:AA / Breakthrough.

Run:  py -3 make_map.py   (writes mp_courtyard_dm.map next to this script)
All geometry is axis-aligned boxes; units are game units (a player is ~96 tall).
"""
from pathlib import Path

MAP_NAME = "mp_courtyard_dm"

# texture name -> "contents surfaceflags value" (copied from stock maps)
FLAGS = {
    "sky/mohday1": "0 276 0",
    "normandy/wood_plank": "0 16384 0",
    "general_structure/beam_wood1": "0 16384 0",
}

brushes = []   # (x1,y1,z1,x2,y2,z2,texture)
entities = []  # dicts


def box(x1, y1, z1, x2, y2, z2, tex):
    x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2)); z1, z2 = sorted((z1, z2))
    brushes.append((x1, y1, z1, x2, y2, z2, tex))


def brush_text(i, b):
    x1, y1, z1, x2, y2, z2, tex = b
    f = FLAGS.get(tex, "0 0 0")
    planes = [
        ((x1, 0, 0), (x1, 1, 0), (x1, 0, 1)),  # -X
        ((x2, 0, 0), (x2, 0, 1), (x2, 1, 0)),  # +X
        ((0, y1, 0), (0, y1, 1), (1, y1, 0)),  # -Y
        ((0, y2, 0), (1, y2, 0), (0, y2, 1)),  # +Y
        ((0, 0, z1), (1, 0, z1), (0, 1, z1)),  # -Z
        ((0, 0, z2), (0, 1, z2), (1, 0, z2)),  # +Z
    ]
    out = [f"// brush {i}", "{"]
    for p in planes:
        pts = " ".join("( %g %g %g )" % q for q in p)
        out.append(f"{pts} {tex} 0 0 0.00 1 1 {f}")
    out.append("}")
    return "\n".join(out)


# ---------------------------------------------------------------- shell
SKY = "sky/mohday1"
S, T = 1600, 32          # sky box half-size and thickness
TOP, BOT = 1088, -160
box(-S, -S, BOT, S, S, BOT + T, SKY)          # bottom
box(-S, -S, TOP - T, S, S, TOP, SKY)          # top
box(-S, -S, BOT, -S + T, S, TOP, SKY)         # west
box(S - T, -S, BOT, S, S, TOP, SKY)           # east
box(-S, -S, BOT, S, -S + T, TOP, SKY)         # south
box(-S, S - T, BOT, S, S, TOP, SKY)           # north

IN = S - T               # inner face of sky box
box(-IN, -IN, -96, IN, IN, 0, "central_europe/small_cobble")   # ground

# ------------------------------------------------- perimeter building row
# playable area is -1280..1280; facades fill 1280..IN on every side
P = 1280
facade = ["algiers/brick1", "algiers/plasterwal4b1", "mohtest/fltwall1grim2_1"]
heights = [448, 544, 384, 512, 576]
seg = 512
k = 0
for a in range(-IN, IN, seg):
    b = min(a + seg, IN)
    h = heights[k % len(heights)]; tex = facade[k % len(facade)]
    box(a, P, 0, b, IN, h, tex)        # north row
    box(a, -IN, 0, b, -P, heights[(k + 2) % 5], facade[(k + 1) % 3])  # south row
    k += 1
k = 0
for a in range(-P, P, seg):
    b = min(a + seg, P)
    box(P, a, 0, IN, b, heights[(k + 1) % 5], facade[(k + 2) % 3])     # east row
    box(-IN, a, 0, -P, b, heights[(k + 3) % 5], facade[k % 3])        # west row
    k += 1

# ------------------------------------------------------- corner houses
for sx in (-1, 1):
    for sy in (-1, 1):
        x1, x2 = sx * 600, sx * 1000
        y1, y2 = sy * 600, sy * 1000
        h = 352 if sx == sy else 288
        tex = "algiers/brick1" if sx == sy else "algiers/plasterwal4b1"
        box(x1, y1, 0, x2, y2, h, tex)
        # roof trim / parapet ledge
        box(x1 - sx * 16, y1 - sy * 16, h, x2 + sx * 16, y2 + sy * 16, h + 24,
            "general_structure/jh_conc512c")

# -------------------------------------------------- central monument
C = "general_structure/jh_conc512c"
box(-160, -160, 0, 160, 160, 32, C)
box(-112, -112, 32, 112, 112, 64, C)
box(-40, -40, 64, 40, 40, 320, C)
box(-56, -56, 320, 56, 56, 344, C)

# ------------------------------------- raised wooden platform (south side)
W = "normandy/wood_plank"
BEAM = "general_structure/beam_wood1"
box(-400, -1280, 112, 400, -1056, 128, W)                  # deck
for px in (-392, -8, 376):                                 # support posts
    box(px, -1072, 0, px + 16, -1056, 112, BEAM)
box(-400, -1072, 128, -120, -1056, 168, BEAM)              # rails, gap in middle
box(120, -1072, 128, 400, -1056, 168, BEAM)
for side in (-1, 1):                                       # stairs at both ends
    for i in range(8):
        xa = side * 400
        xb = side * (656 - 32 * i)
        box(xa, -1280, 0, xb, -1120, 16 * (i + 1), W)

# --------------------------------------------- balcony walkway (north side)
box(-1280, 1104, 160, -600, 1280, 176, W)
box(-1280, 1104, 0, -1264, 1120, 160, BEAM)
for i in range(10):                                        # stair up to balcony
    box(-600, 1104, 0, -600 + 32 * (10 - i), 1280, 16 * (i + 1), W)

# ------------------------------------------------------- cover objects
def crate(x, y, z=0, s=64):
    box(x - s / 2, y - s / 2, z, x + s / 2, y + s / 2, z + s, W)

for x, y in [(-420, 240), (-356, 240), (-420, 304), (440, -260), (504, -260),
             (300, 420), (-300, -420), (900, 0), (-900, 40), (0, 760), (0, -760),
             (1220, 1220), (-1220, -1220), (1220, -1220)]:
    crate(x, y)
crate(-388, 272, 64)          # stacked
crate(472, -260, 64)

LOW = "general_structure/jh_conc512c"
for x1, y1, x2, y2 in [(-520, -40, -496, 120), (496, -120, 520, 40),
                       (-120, 480, 120, 504), (-120, -504, 120, -480),
                       (1040, 400, 1200, 424), (-1200, -424, -1040, -400),
                       (1040, -460, 1064, -300), (-1064, 300, -1040, 460)]:
    box(x1, y1, 0, x2, y2, 48, LOW)

# ------------------------------------------------------------ entities
worldspawn = {
    "classname": "worldspawn",
    "message": "Courtyard",
    "suncolor": "1 0.95 0.85",
    "sundirection": "-50 30 0",
    "sundiffuse": "1",
    "sundiffusecolor": "0.75 0.8 0.9",
    "ambientlight": "40 38 36",
    "ambient": "40",
    "scale": "1",
    "farplane": "0",
}

entities.append({"classname": "info_player_start", "origin": "0 -400 24", "angle": "90"})

def spawn(cls, x, y, ang, z=24):
    entities.append({"classname": cls, "origin": f"{x} {y} {z}", "angle": str(ang)})

for y in (-900, -600, -300, 0, 300, 600, 900, 1150):
    spawn("info_player_allied", -1150, y, 0)
    spawn("info_player_axis", 1150, -y, 180)
dm_points = [(-800, 0, 0), (800, 0, 180), (0, 1100, 270), (0, -900, 90),
             (-1100, 1150, 315), (1100, -1150, 135), (-1150, -1150, 45), (1150, 1150, 225),
             (-500, 500, 315), (500, -500, 135), (500, 500, 225), (-500, -500, 45),
             (300, 0, 180), (-300, 0, 0)]
for x, y, a in dm_points:
    spawn("info_player_deathmatch", x, y, a)
spawn("info_player_deathmatch", -900, 1190, 270, 200)   # on balcony
spawn("info_player_deathmatch", 0, -1170, 90, 152)      # on platform

for x, y in [(-800, 0), (800, 0), (0, 800), (0, -800), (0, 0),
             (-1100, -1100), (1100, 1100), (-1100, 1100), (1100, -1100)]:
    entities.append({"classname": "light", "origin": f"{x} {y} 360",
                     "light": "450", "_color": "1.0 0.92 0.8"})


def ent_text(i, e, body=""):
    lines = [f"// entity {i}", "{"] + [f'"{k}" "{v}"' for k, v in e.items()]
    if body:
        lines.append(body)
    lines.append("}")
    return "\n".join(lines)


parts = [ent_text(0, worldspawn, "\n".join(brush_text(i, b) for i, b in enumerate(brushes)))]
parts += [ent_text(i + 1, e) for i, e in enumerate(entities)]
out = Path(__file__).with_name(MAP_NAME + ".map")
out.write_text("\n".join(parts) + "\n", encoding="ascii")
print(f"wrote {out} : {len(brushes)} brushes, {len(entities)} entities")
