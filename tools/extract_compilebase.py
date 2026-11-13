"""Build a loose-file "compilebase" folder for MOHlight.

MOHlight (MOHTools) crashes on big maps when it reads textures out of the game's
.pk3 files. This copies just what one map needs -- its textures, the images its
shaders point at, all shader scripts, and the prop models it places -- into
<out>/main as plain files. Then light with:  MOHlight.exe -gamedir <out> -moddir main <map>
Afterwards run fix_missing_tga.py on the same map.

usage: py -3 extract_compilebase.py <map file> <out folder> [game folder]
"""
import glob
import re
import sys
import zipfile
from pathlib import Path

GAME = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(
    r"C:\Program Files\GOG Galaxy\Games\Medal of Honor - Allied Assault War Chest")
mp = Path(sys.argv[1]).read_text(encoding="latin1")
out = Path(sys.argv[2]) / "main"

idx = {}
for p in sorted(glob.glob(str(GAME / "main" / "*.pk3"))):
    for n in zipfile.ZipFile(p).namelist():
        idx[n.lower()] = (p, n)


def read(k):
    p, n = idx[k]
    return zipfile.ZipFile(p).read(n)


want = set()
shaders = {}
for k in idx:
    if k.startswith("scripts/") and (k.endswith(".shader") or "shaderlist" in k):
        want.add(k)
        if k.endswith(".shader"):
            t = read(k).decode("latin1")
            for m in re.finditer(r"^\s*(textures/[^\s{]+)\s*\{(.*?)^\}", t, re.M | re.S):
                shaders[m.group(1).lower()] = m.group(2)


def add_img(path):
    base = re.sub(r"\.(tga|jpg)$", "", path.lower())
    for ext in (".tga", ".jpg", ".dds"):
        if base + ext in idx:
            want.add(base + ext)


tex = set(t.lower() for t in re.findall(r"\)\s+([A-Za-z0-9_\-/]+)\s+-?[\d.]+\s+-?[\d.]+\s+-?[\d.]+", mp))
for t in tex:
    name = "textures/" + t
    add_img(name)
    body = shaders.get(name, "")
    for m in re.findall(r"(?:map|clampmap|qer_editorimage|animmap\s+[\d.]+)\s+([^\s$]+\.(?:tga|jpg))", body, re.I):
        add_img(m)
    for m in re.findall(r"skyparms\s+(\S+)", body, re.I):
        for suf in ("_rt", "_bk", "_lf", "_ft", "_up", "_dn"):
            add_img(m + suf)

# prop models placed by entities ("model" keys ending in .tik)
seen = set()


def add_tik(k):
    if k in seen or k not in idx:
        return
    seen.add(k)
    want.add(k)
    path = None
    for line in read(k).decode("latin1").splitlines():
        s = line.split("//")[0].strip()
        m = re.match(r"path\s+(\S+)", s, re.I)
        if m:
            path = m.group(1).lower().strip("/")
        m = re.match(r"\S+\s+(\S+\.(?:skd|skb|skc|tik))", s, re.I)
        if m and path and (path + "/" + m.group(1).lower()) in idx:
            want.add(path + "/" + m.group(1).lower())
        m = re.match(r"\$include\s+(\S+)", s, re.I)
        if m:
            add_tik(m.group(1).lower())


for m in re.findall(r'"model"\s+"([^"*][^"]*\.tik)"', mp):
    add_tik(re.sub(r"/+", "/", "models/" + m.lower()))
folders = {"/".join(w.split("/")[:-1]) for w in list(want) if w.startswith("models/")}
for k in idx:
    if "/".join(k.split("/")[:-1]) in folders and k.endswith((".tga", ".jpg")):
        want.add(k)

size = 0
for k in sorted(want):
    p, n = idx[k]
    data = zipfile.ZipFile(p).read(n)
    dst = out / n
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    size += len(data)
print(f"{len(tex)} map textures; {len(want)} files ({size / 1e6:.0f} MB) copied to {out}")
