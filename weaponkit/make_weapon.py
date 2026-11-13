"""Build custom MOH:AA / Breakthrough weapon variants for OpenMoHAA.

Each recipe copies a stock weapon .tik out of the game's pak files, changes
some settings, packs it into maintt/user-<id>.pk3 and adds a key bind to
maintt/weaponkit.cfg so you can give it to yourself in game (cheats needed).

Usage (from any folder):
    py -3 make_weapon.py              list recipes
    py -3 make_weapon.py rockethose   build + install one recipe
    py -3 make_weapon.py all          build + install every recipe
    py -3 make_weapon.py --remove ID  uninstall one recipe's pk3

Rules learned the hard way (see HOWTO.md):
  * "name" must stay a STOCK weapon name, or the first-person animations,
    fire animation and ammo display fall back to "unarmed".
  * Full-auto (no "semiauto") only works for weapontype smg or mg.
  * Ammo pools are capped per player: heavy=5, grenade=5, rifle=200,
    pistol=200, smg=300, shotgun=50, mg=500.
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

GAME = Path(r"C:\Program Files\GOG Galaxy\Games\Medal of Honor - Allied Assault War Chest")
OUT = Path(__file__).resolve().parent / "build"
PREFIXES = ("sp", "dm", "realism", "sprealism", "dmrealism")

# ---------------------------------------------------------------------------
# Recipes. "set" values replace every variant of a key (plain, sp, dm,
# realism...). "remove" deletes keys. "bind" is the key that gives it in game.
# ---------------------------------------------------------------------------
RECIPES = {
    "rockethose": {
        "title": "Rocket Hose - fully automatic bazooka",
        "base": "models/weapons/bazooka.tik",
        "bind": "g",
        "set": {
            "name": '"Bazooka"',
            "weapontype": "mg",
            "ammotype": '"mg"',
            "clipsize": "30",
            "firedelay": "0.12",
            "startammo": "300",
            "maxfiremovement": "1.0",
            "rank": "620 620",
        },
        "remove": ["semiauto"],
    },
    "barndoor": {
        "title": "Barn Door - shotgun firing 80 pellets in a huge cone",
        "base": "models/weapons/shotgun.tik",
        "bind": "F7",
        "set": {
            "name": '"Shotgun"',
            "bulletcount": "80",
            "bulletspread": "300 300 400 400",
            "bulletdamage": "6",
            "firedelay": "1.2",
            "rank": "621 621",
        },
    },
    "pocketartillery": {
        "title": "Pocket Artillery - Colt 45 that fires tank shells",
        "base": "models/weapons/colt45.tik",
        "bind": "F8",
        "set": {
            "name": '"Colt 45"',
            "firetype": "projectile",
            "projectile": "models/projectiles/wk_artilleryshell.tik",
            "meansofdeath": "rocket",
            "firedelay": "0.8",
            "clipsize": "3",
            "rank": "622 622",
        },
        "extra": ["cache models/projectiles/wk_artilleryshell.tik"],
        # The stock tank shell is invisible (+dontdraw) and flies at 6000, so
        # use a visible bazooka rocket with artillery damage and explosion.
        "projectiles": {
            "wk_artilleryshell": {
                "base": "models/projectiles/bazookashell_dm.tik",
                "set": {
                    "speed": "2200",
                    "hitdamage": "450",
                    "knockback": "700",
                    "explosionmodel": "models/fx/explosionartilleryshell.tik",
                },
                "extra": ["cache models/fx/explosionartilleryshell.tik"],
            },
        },
    },
    "grenadehose": {
        "title": "Grenade Hose - Thompson that sprays bouncing grenades",
        "base": "models/weapons/thompsonsmg.tik",
        "bind": "F10",
        "set": {
            "name": '"Thompson"',
            "firetype": "projectile",
            "projectile": "models/projectiles/m2fgrenade_primary.tik",
            "firedelay": "0.08",
            "rank": "623 623",
        },
        "extra": ["cache models/projectiles/m2fgrenade_primary.tik"],
    },
    "laserbeam": {
        "title": "Laser Beam - MG with zero spread and absurd fire rate",
        "base": "models/weapons/bar.tik",
        "bind": "F11",
        "set": {
            "name": '"BAR"',
            "bulletspread": "0 0 0 0",
            "firespreadmult": "0 0 0 0",
            "firedelay": "0.02",
            "clipsize": "200",
            "startammo": "500",
            "bulletdamage": "8",
            "rank": "624 624",
        },
        "remove": ["semiauto"],
    },
    "shovegun": {
        "title": "Shove Gun - harmless rifle that launches people",
        "base": "models/weapons/m1_garand.tik",
        "bind": "[",
        "set": {
            "name": '"M1 Garand"',
            "bulletdamage": "1",
            "bulletknockback": "3000",
            "rank": "625 625",
        },
    },
    "smokehose": {
        "title": "Smoke Machine - SMG that sprays smoke grenades",
        "base": "models/weapons/mp40.tik",
        "bind": "]",
        "set": {
            "name": '"MP40"',
            "firetype": "projectile",
            "projectile": "models/projectiles/m18_smoke_grenade_primary.tik",
            "firedelay": "0.3",
            "rank": "626 626",
        },
        "extra": ["cache models/projectiles/m18_smoke_grenade_primary.tik"],
    },
    # ---- single-player content brought into multiplayer -------------------
    "silenced": {
        "title": "Hi-Standard Silenced - single-player OSS pistol, stock stats",
        "base": "models/weapons/silencedpistol.tik",
        "bind": "INS",
        "set": {},
    },
    "mg42carry": {
        "title": "Carryable MG42 - single-player deployable machine gun (experimental)",
        "base": "models/weapons/mg42carryable.tik",
        "bind": "HOME",
        "set": {},
    },
    "stukagun": {
        "title": "Stuka Gun - StG 44 firing the Stuka's explosive cannon rounds",
        "base": "models/weapons/mp44.tik",
        "bind": "PGUP",
        "set": {
            "name": '"StG 44"',
            "firetype": "projectile",
            "projectile": "models/projectiles/stukaround.tik",
            "firedelay": "0.12",
            "rank": "627 627",
        },
        "extra": ["cache models/projectiles/stukaround.tik"],
    },
    "nebelwerfer": {
        "title": "Hand Nebelwerfer - full-auto launcher firing single-player rocket-artillery rockets",
        "base": "models/weapons/bazooka.tik",
        "bind": "DEL",
        "set": {
            "name": '"Bazooka"',
            "weapontype": "mg",
            "ammotype": '"mg"',
            "projectile": "models/projectiles/nebelwerferproj.tik",
            "clipsize": "6",
            "firedelay": "0.2",
            "startammo": "120",
            "maxfiremovement": "1.0",
            "rank": "628 628",
        },
        "remove": ["semiauto"],
        "extra": ["cache models/projectiles/nebelwerferproj.tik"],
    },
    "mortar": {
        "title": "Shoulder Mortar - Panzerschreck lobbing single-player mortar shells",
        "base": "models/weapons/panzerschreck.tik",
        "bind": "END",
        "set": {
            "name": '"Panzerschreck"',
            "ammotype": '"mg"',
            "projectile": "models/projectiles/granatwerferproj.tik",
            "clipsize": "4",
            "firedelay": "0.6",
            "startammo": "60",
            "rank": "629 629",
        },
        "extra": ["cache models/projectiles/granatwerferproj.tik"],
    },
    "tanksniper": {
        "title": "Tank Sniper - scoped KAR98 firing T-34 cannon shells",
        "base": "models/weapons/kar98sniper.tik",
        "bind": "PGDN",
        "set": {
            "name": '"KAR98 - Sniper"',
            "firetype": "projectile",
            "projectile": "models/projectiles/t34shell.tik",
            "meansofdeath": "rocket",
            "rank": "630 630",
        },
        "extra": ["cache models/projectiles/t34shell.tik"],
    },
}


def read_stock(path):
    """Return the text of a stock file, preferring the last pak that has it."""
    found = None
    for pak in sorted(GAME.glob("main/*.pk3")) + sorted(GAME.glob("maintt/*.pk3")):
        if pak.name.startswith("user-"):
            continue
        with zipfile.ZipFile(pak) as z:
            for n in z.namelist():
                if n.lower() == path.lower():
                    found = z.read(n).decode("latin1")
    if found is None:
        raise SystemExit(f"stock file not found: {path}")
    return found.replace("\r\n", "\n")


def server_block_insert(text, lines, before_ammotype=False):
    """Insert lines into the server block: after 'classname Weapon/Projectile',
    or (new weapon keys) just before the primary 'ammotype' line so they come
    after 'firetype'."""
    if before_ammotype:
        m = re.search(r"^(\s*)ammotype\b", text, flags=re.M | re.I)
        if m:
            add = "".join(f"{m.group(1)}{l}\n" for l in lines)
            return text[: m.start()] + add + text[m.start():]
    m = re.search(r"^(\s*)classname\s+(Weapon|Projectile)\s*$", text, flags=re.M | re.I)
    if not m:
        raise SystemExit("could not find 'classname Weapon/Projectile' in base tik")
    indent = m.group(1)
    add = "".join(f"\n{indent}{l}" for l in lines)
    return text[: m.end()] + add + text[m.end():]


def set_key(text, key, value):
    pat = re.compile(
        r"^(\s*)((?:(?:%s)\s+)?)(%s)\b[^\n]*$" % ("|".join(PREFIXES), re.escape(key)),
        flags=re.M | re.I,
    )
    text, n = pat.subn(lambda m: f"{m.group(1)}{m.group(2)}{key}\t\t{value}\t// weaponkit", text)
    if n == 0:
        text = server_block_insert(text, [f"{key}\t\t{value}\t// weaponkit"], before_ammotype=True)
    return text


def remove_key(text, key):
    pat = re.compile(r"^(\s*)((?:(?:%s)\s+)?)%s\b[^\n]*$" % ("|".join(PREFIXES), re.escape(key)), flags=re.M | re.I)
    return pat.sub(lambda m: f"{m.group(1)}// {key} removed by weaponkit", text)


def make_text(r):
    text = read_stock(r["base"])
    for k, v in r.get("set", {}).items():
        text = set_key(text, k, v)
    for k in r.get("remove", []):
        text = remove_key(text, k)
    if r.get("extra"):
        text = server_block_insert(text, r["extra"])
    return text


def build(rid):
    r = RECIPES[rid]
    text = make_text(r)
    text = f"// {r['title']}\n// generated by weaponkit/make_weapon.py from {r['base']}\n" + text

    tik_rel = f"models/weapons/wk_{rid}.tik"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"wk_{rid}.tik").write_text(text, encoding="latin1")
    pk3 = OUT / f"user-{rid}.pk3"
    with zipfile.ZipFile(pk3, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(tik_rel, text.encode("latin1"))
        for pid, pr in r.get("projectiles", {}).items():
            ptext = f"// projectile for {rid}, generated by weaponkit from {pr['base']}\n" + make_text(pr)
            (OUT / f"{pid}.tik").write_text(ptext, encoding="latin1")
            z.writestr(f"models/projectiles/{pid}.tik", ptext.encode("latin1"))
    shutil.copy(pk3, GAME / "maintt" / pk3.name)
    print(f"installed {pk3.name}: give {tik_rel}  (key {r.get('bind', '-')})")
    return tik_rel


def wtype_of(rid):
    t = RECIPES[rid].get("set", {}).get("weapontype")
    if t:
        return t
    m = re.search(r"^\s*weapontype\s+(\w+)", read_stock(RECIPES[rid]["base"]), flags=re.M)
    return m.group(1) if m else None


def write_binds():
    lines = ["// weaponkit binds - generated by make_weapon.py (needs cheats on)"]
    for rid, r in RECIPES.items():
        if (GAME / "maintt" / f"user-{rid}.pk3").exists() and r.get("bind"):
            wt = wtype_of(rid)
            use = f"; wait 10; useweaponclass {wt}" if wt else ""
            lines.append(f'bind {r["bind"]} "give models/weapons/wk_{rid}.tik{use}"')
    lines.append('echo "weaponkit binds loaded"')
    (GAME / "maintt" / "weaponkit.cfg").write_text("\n".join(lines) + "\n", encoding="ascii")
    print("wrote maintt/weaponkit.cfg")


def main(argv):
    if not argv:
        for rid, r in RECIPES.items():
            print(f"{rid:16} key {r.get('bind', '-'):4} {r['title']}")
        return
    if argv[0] == "--remove":
        p = GAME / "maintt" / f"user-{argv[1]}.pk3"
        if p.exists():
            p.unlink()
            print("removed", p.name)
        write_binds()
        return
    ids = list(RECIPES) if argv[0] == "all" else argv
    for rid in ids:
        if rid not in RECIPES:
            raise SystemExit(f"unknown recipe {rid}")
        build(rid)
    write_binds()


if __name__ == "__main__":
    main(sys.argv[1:])
