"""Tiny MOHAA .map reader/editor: brushes, patches and entities, with brush bounds.

Brush faces are kept as raw lines; geometry edits are affine transforms applied to
the three plane points of every face (planes stay planes), to patch control points
and to entity origins.
"""
import re
from itertools import combinations

PT = re.compile(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)")


class Brush:
    def __init__(self, lines):
        self.lines = lines  # face lines (strings)

    def faces(self):
        out = []
        for l in self.lines:
            pts = [tuple(map(float, m)) for m in PT.findall(l)[:3]]
            tex = PT.split(l)[-1].split()[0] if len(PT.findall(l)) >= 3 else ""
            out.append((pts, tex, l))
        return out

    def textures(self):
        return {t for _, t, _ in self.faces()}

    def planes(self):
        res = []
        for pts, _, _ in self.faces():
            p0, p1, p2 = pts
            t1 = [p0[i] - p1[i] for i in range(3)]
            t2 = [p2[i] - p1[i] for i in range(3)]
            n = [t1[1] * t2[2] - t1[2] * t2[1], t1[2] * t2[0] - t1[0] * t2[2], t1[0] * t2[1] - t1[1] * t2[0]]
            ln = sum(c * c for c in n) ** 0.5 or 1
            n = [c / ln for c in n]
            d = sum(n[i] * p1[i] for i in range(3))
            res.append((n, d))
        return res

    def vertices(self):
        pl = self.planes()
        verts = []
        for a, b, c in combinations(pl, 3):
            (n1, d1), (n2, d2), (n3, d3) = a, b, c
            det = (n1[0] * (n2[1] * n3[2] - n2[2] * n3[1]) - n1[1] * (n2[0] * n3[2] - n2[2] * n3[0])
                   + n1[2] * (n2[0] * n3[1] - n2[1] * n3[0]))
            if abs(det) < 1e-9:
                continue
            # Cramer's rule
            def rep(col, vals):
                m = [list(n1), list(n2), list(n3)]
                for r in range(3):
                    m[r][col] = vals[r]
                return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            v = tuple(rep(i, [d1, d2, d3]) / det for i in range(3))
            if all(sum(n[i] * v[i] for i in range(3)) <= d + 0.05 for n, d in pl):
                verts.append(v)
        return verts

    def bounds(self):
        v = self.vertices()
        if not v:
            return None
        return [min(p[i] for p in v) for i in range(3)], [max(p[i] for p in v) for i in range(3)]

    def transform(self, f):
        new = []
        for l in self.lines:
            ms = list(PT.finditer(l))
            if len(ms) < 3:
                new.append(l)
                continue
            out, last = [], 0
            for m in ms[:3]:
                x, y, z = f(tuple(map(float, m.groups())))
                out.append(l[last:m.start()])
                out.append("( %s %s %s )" % tuple(_fmt(c) for c in (x, y, z)))
                last = m.end()
            out.append(l[last:])
            new.append("".join(out))
        self.lines = new


class Patch:
    def __init__(self, text):
        self.text = text  # full "patchDef2 { ... }" block text

    def transform(self, f):
        # control points are "( x y z u v )"
        def rep(m):
            x, y, z = f((float(m.group(1)), float(m.group(2)), float(m.group(3))))
            return "( %s %s %s %s %s )" % (_fmt(x), _fmt(y), _fmt(z), m.group(4), m.group(5))
        rx = r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)"
        # only control-point rows "( ( x y z u v ) ... )", not the "( w h 0 0 0 )" size line
        self.text = "\n".join(re.sub(rx, rep, l) if l.strip().startswith("( (") else l for l in self.text.split("\n"))

    def bounds(self):
        rows = "\n".join(l for l in self.text.split("\n") if l.strip().startswith("( ("))
        pts = [tuple(map(float, m[:3])) for m in re.findall(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+[-\d.eE+]+\s+[-\d.eE+]+\s*\)", rows)]
        if not pts:
            return None
        return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


class Entity:
    def __init__(self):
        self.keys = []   # list of (key, value) preserving order
        self.prims = []  # Brush / Patch

    def get(self, k, default=None):
        for kk, v in self.keys:
            if kk == k:
                return v
        return default

    def set(self, k, v):
        for i, (kk, _) in enumerate(self.keys):
            if kk == k:
                self.keys[i] = (k, v)
                return
        self.keys.append((k, v))


def _fmt(c):
    r = round(c, 3)
    return str(int(r)) if r == int(r) else ("%.3f" % r).rstrip("0").rstrip(".")


def parse(text):
    lines = text.splitlines()
    ents, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if s == "{":
            e = Entity()
            i += 1
            while i < n:
                s = lines[i].strip()
                if s == "}":
                    break
                if s.startswith('"'):
                    m = re.match(r'"([^"]*)"\s+"([^"]*)"', s)
                    if m:
                        e.keys.append((m.group(1), m.group(2)))
                elif s == "{":
                    # brush or patch
                    j = i + 1
                    if j < n and lines[j].strip().startswith("patchDef") or (j < n and lines[j].strip().startswith("terrainDef")):
                        depth, buf = 0, []
                        k = j
                        while k < n:
                            t = lines[k]
                            buf.append(t)
                            depth += t.count("{") - t.count("}")
                            if depth == 0 and "}" in t:
                                break
                            k += 1
                        e.prims.append(Patch("\n".join(buf)))
                        i = k + 1  # line after patch's closing brace -> brush closing "}"
                    else:
                        buf = []
                        k = j
                        while k < n and lines[k].strip() != "}":
                            if lines[k].strip().startswith("("):
                                buf.append(lines[k])
                            k += 1
                        e.prims.append(Brush(buf))
                        i = k
                i += 1
            ents.append(e)
        i += 1
    return ents


def write(ents):
    out = []
    bi = 0
    for ei, e in enumerate(ents):
        out.append(f"// entity {ei}")
        out.append("{")
        for k, v in e.keys:
            out.append(f'"{k}" "{v}"')
        for p in e.prims:
            out.append(f"// brush {bi}")
            bi += 1
            out.append("{")
            if isinstance(p, Patch):
                out.append(p.text)
            else:
                out.extend(p.lines)
            out.append("}")
        out.append("}")
    return "\n".join(out) + "\n"
