"""Create stand-in .tga files in compilebase for every image a map's shaders reference
but that is missing as .tga. MOHlight crashes ("Not a JPEG file" / radiosity stop) when a
shader points at a .tga that is not there. Stand-ins are only used by the compiler.

usage: py -3 fix_missing_tga.py <map file>
"""
import re, struct, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent / "main"
mp = Path(sys.argv[1]).read_text(encoding="latin1")
tex = set(t.lower() for t in re.findall(r"\)\s+([A-Za-z0-9_\-/]+)\s+-?[\d.]+\s+-?[\d.]+\s+-?[\d.]+", mp))
shaders = {}
for f in (BASE / "scripts").glob("*.shader"):
    t = f.read_text(encoding="latin1")
    for m in re.finditer(r"^\s*(textures/[^\s{]+)\s*\{(.*?)^\}", t, re.M | re.S):
        shaders[m.group(1).lower()] = m.group(2)

def tga(path, rgb=(110, 100, 90)):
    path.parent.mkdir(parents=True, exist_ok=True)
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 8, 8, 24, 0)
    path.write_bytes(hdr + bytes([rgb[2], rgb[1], rgb[0]]) * 64)

made = 0
for t in sorted(tex):
    name = "textures/" + t
    refs = [name + ".tga"]
    body = shaders.get(name, "")
    refs += re.findall(r"(?:map|clampmap|qer_editorimage)\s+([^\s$]+\.tga)", body, re.I)
    for r in refs:
        p = BASE / r
        if not p.exists() and not any(p.parent.glob(p.stem + ".*")) or (not p.exists() and r.lower().endswith(".tga") and r in refs[1:]):
            tga(p); made += 1
print(f"{len(tex)} textures checked, {made} stand-in .tga files created")
