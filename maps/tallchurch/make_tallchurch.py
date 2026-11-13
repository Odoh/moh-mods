"""Clone Destroyed Village (mohdm2) with the church tower 3x taller.

Original tower: base 0-40, shaft 40-488 (with ladder), belfry 560-808,
spire 824-1536. We keep the door, belfry and spire proportions, stretch only
the shaft, and lift everything above it, so total height = 3 x 1536 = 4608.
The sky ceiling (top ~1572) is raised by the same amount so the spire fits.

Run: py -3 make_tallchurch.py  ->  mp_tallchurch_dm.map
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mapedit import Brush, Patch, parse, write  # noqa: E402

SRC = Path(__file__).with_name("mohdm2_orig.map")
OUT = Path(__file__).with_name("mp_tallchurch_dm.map")

# tower footprint (x0, x1, y0, y1) with a little padding
X0, X1, Y0, Y1 = -880, -512, -1112, -744
SHAFT_LO, SHAFT_HI = 40.0, 488.0
TOP = 1536.0
EXTRA = 2 * TOP                      # +3072 -> 3x total height
K = (SHAFT_HI - SHAFT_LO + EXTRA) / (SHAFT_HI - SHAFT_LO)
SKY_CUT, SKY_LIFT = 1500.0, EXTRA + 256


def tower_z(p):
    x, y, z = p
    if z <= SHAFT_LO:
        return p
    if z <= SHAFT_HI:
        return (x, y, SHAFT_LO + (z - SHAFT_LO) * K)
    return (x, y, z + EXTRA)


def sky_z(p):
    x, y, z = p
    return (x, y, z + SKY_LIFT) if z >= SKY_CUT else p


def box_brush(x1, y1, z1, x2, y2, z2, tex, params):
    planes = [
        ((x1, 0, 0), (x1, 1, 0), (x1, 0, 1)), ((x2, 0, 0), (x2, 0, 1), (x2, 1, 0)),
        ((0, y1, 0), (0, y1, 1), (1, y1, 0)), ((0, y2, 0), (1, y2, 0), (0, y2, 1)),
        ((0, 0, z1), (1, 0, z1), (0, 1, z1)), ((0, 0, z2), (0, 1, z2), (1, 0, z2)),
    ]
    return Brush([" ".join("( %g %g %g )" % q for q in p) + f" {tex} {params}" for p in planes])


def retexture(brush, tex, flags, scale=None):
    """Replace every face's texture, keeping offsets/rotation; set content/surface flags."""
    new = []
    for l in brush.lines:
        head, sep, tail = l.rpartition(")")
        parts = tail.split()
        # parts: texture xoff yoff rot xscale yscale contents surface value [extras...]
        if len(parts) >= 9:
            parts[0] = tex
            if scale:
                parts[4], parts[5] = scale.split()
            parts[6:9] = flags.split()
            parts = parts[:9]
        new.append(head + sep + " " + " ".join(parts))
    brush.lines = new


def inside(b):
    (a, c) = b
    return a[0] >= X0 and c[0] <= X1 and a[1] >= Y0 and c[1] <= Y1


def main():
    ents = parse(SRC.read_text(encoding="latin1"))
    moved = sky_count = ents_moved = low_sky = floors = 0
    for e in ents:
        if e.get("classname") == "worldspawn":
            e.set("message", "Destroyed Village - Tall Tower")
            e.set("farplane", "9000")
        for p in e.prims:
            b = p.bounds()
            if not b:
                continue
            if isinstance(p, Brush) and any(t.startswith("sky") for t in p.textures()):
                if b[1][2] >= SKY_CUT:
                    p.transform(sky_z)
                    sky_count += 1
                elif e.get("classname") == "worldspawn":
                    # low sky walls/ceilings around the outer ring look like a white
                    # floor from the tower top: keep them solid but invisible
                    retexture(p, "common/clip", "196608 2193 0")
                    low_sky += 1
                continue
            if (isinstance(p, Brush) and e.get("classname") == "worldspawn"
                    and p.textures() == {"common/caulk"} and -100 <= b[1][2] <= -90
                    and (b[1][0] - b[0][0]) * (b[1][1] - b[0][1]) > 250000):
                # invisible outer-ring floors -> visible mud
                retexture(p, "brest/mud_set1", "0 0 0", scale="4 4")
                floors += 1
                continue
            if inside(b):
                p.transform(tower_z)
                moved += 1
        o = e.get("origin")
        if o and not e.prims:
            x, y, z = map(float, o.split())
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                x, y, z = tower_z((x, y, z))
                e.set("origin", f"{x:g} {y:g} {z:g}")
                ents_moved += 1

    # From the top of the tower you can see past the original sky walls, where
    # only the blank bottom of the skybox shows (white). Add a big outer sky box
    # with a muddy ground plane so there is countryside to look at.
    world = next(e for e in ents if e.get("classname") == "worldspawn")
    E, T = 7000, 64
    ZB, ZT = -400, 5000
    world.prims.append(box_brush(-E, -E, -200, E, E, -110, "brest/mud_set1", "0 0 0.00 4 4 0 0 0"))
    sky = "0 0 0.00 1 1 0 276 0"
    for b in [(-E - T, -E - T, ZB - T, E + T, E + T, ZB),      # floor
              (-E - T, -E - T, ZT, E + T, E + T, ZT + T),      # ceiling
              (-E - T, -E - T, ZB, -E, E + T, ZT),             # west
              (E, -E - T, ZB, E + T, E + T, ZT),               # east
              (-E, -E - T, ZB, E, -E, ZT),                     # south
              (-E, E, ZB, E, E + T, ZT)]:                      # north
        world.prims.append(box_brush(*b, "sky/m5l2", sky))

    OUT.write_text(write(ents), encoding="latin1")
    print(f"stretch factor {K:.2f}; tower prims moved {moved}; sky prims raised {sky_count}; point entities moved {ents_moved}")
    print(f"low sky brushes -> clip: {low_sky}; outer caulk floors -> mud: {floors}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
