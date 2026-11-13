# MOH: Breakthrough modding notes (OpenMoHAA)

How the custom map, personality bots and wacky weapons on this PC were made, plus
the traps hit along the way. Written 2026-11-12.

## Where everything lives

| What | Location |
|---|---|
| Game (GOG) | `C:\Program Files\GOG Galaxy\Games\Medal of Honor - Allied Assault War Chest` |
| OpenMoHAA download (clean copy) | `C:\Users\joshr\Games\OpenMoHAA` |
| Courtyard map source | `C:\Users\joshr\Games\MOHMaps\courtyard` |
| Map compiler (MOHTools) | `C:\Users\joshr\Games\MOHTools-master` |
| OpenMoHAA source (bot personalities) | `C:\Users\joshr\Games\openmohaa-src` |
| Weapon kit (variant builder) | `C:\Users\joshr\Games\MOHMods\weaponkit` |
| Game settings / logs / screenshots | `%APPDATA%\openmohaa\maintt` |

Installed mods are in the game's `maintt` folder: `user-*.pk3`, `bot_personalities.cfg`,
`weaponkit.cfg`, and the modified `game.dll` (original saved as `game.dll.stock-v0.82.1`).

Desktop shortcuts:
- **MOH Breakthrough (OpenMoHAA)**: normal game.
- **Courtyard - Bot Test**: Courtyard team match with 7 bots.
- **Courtyard - Wacky Weapons**: Courtyard with cheats on, 4 bots and the weapon keys.

---

## 1. Running Breakthrough on Windows 11

1. Buy the GOG *Medal of Honor: Allied Assault War Chest* (it includes Breakthrough).
2. Download `openmohaa-<ver>-windows-x64.zip` from github.com/openmoh/openmohaa/releases
   and check its SHA-256 against the release page.
3. Extract it into the game folder, without overwriting any files.
4. Launch `launch_openmohaa_breakthrough.exe`. (GOG Galaxy's Play button still runs the old game.)

If GOG "repairs" the game, it may delete the OpenMoHAA files. Copy them back from
`C:\Users\joshr\Games\OpenMoHAA`.

## 2. Making a map (Courtyard)

- `make_map.py` writes `mp_courtyard_dm.map` as text, building everything out of boxes.
  Each brush has 6 planes, and the point order sets which way each face points
  (see `brush_text`). Texture names come from the stock `.map` files in
  MOHTools and must exist in the paks.
- The map must be sealed (a sky box around everything), or the compiler reports a leak.
- Compile (run from the MOHTools folder):
  ```
  Q3map.exe   -gamedir "<game folder>" -moddir main  <path>\maps\dm\mp_courtyard_dm.map
  Q3map.exe   -vis -gamedir "<game folder>" -moddir main <same .map>
  MOHlight.exe     -gamedir "<game folder>" -moddir main <same .map>
  ```
  **Trap:** don't end `-gamedir` with a backslash. `"...Chest\"` escapes the quote,
  and Q3map just prints its usage.
- Package `maps/dm/<name>.bsp`, `<name>.scr` and `<name>_precache.scr` into
  `maintt/user-<name>.pk3`. Multiplayer maps go in `maps/dm` (or `maps/obj` for objective maps).
- Play it from the console: `map dm/mp_courtyard_dm`.

### Cloning a stock map (Destroyed Village with a 3x church tower)
- Source `.map` files exist only for the Allied Assault maps in `MOHTools-master\maps\MP`
  (mohdm1-3, 5-7, obj_team1-4). Breakthrough maps can only be cloned at the script level.
- `MOHMaps\tallchurch\mapedit.py` is a small `.map` parser. It finds brush bounds and applies
  transforms to brushes, patches and entity origins. `make_tallchurch.py` finds the tower's
  footprint, stretches its shaft (z 40-488) and lifts everything above it, giving 3x the
  height, then raises the sky ceiling so the spire fits.
- Vis on this map takes about 5 minutes. **MOHlight crashes** on big maps when it reads
  textures from the paks ("Not a JPEG file" / "zip file that was not open"). Fix: point
  `-gamedir` at `MOHMaps\compilebase`, a folder holding only the map's textures, shaders
  and prop models as loose files (no pk3s).
- The pk3 holds the `.bsp`, a copy of the stock `.scr` with `level.script` renamed, `_precache.scr` and `.min`.
- Shortcut: **Destroyed Village - Tall Tower** (free-for-all, 6 bots, weapon keys).
- The map script (`mp_tallchurch_dm.scr`) adds two things:
  - **Tower player:** `g_towerplayer` set to an exact player name, or empty (the default) for every
    human player. That player always spawns in the belfry (z 3650). The script uses OpenMoHAA's
    `event_subscribe "player_spawned" "label"`; the second argument is a label name in the
    same script, not `file::label`.
  - **Darkness:** while the tower player is inside the tower footprint, `$world farplane_color`,
    `farplane` and `skyalpha` turn the map dark, for everyone. Leaving or dying restores them.
  - `isBot <entity>` and `<player>.netname` are the script calls used to pick the player.
  - **Bullet range:** a shot stops at the weapon's `bulletrange`, which is about 4000 for stock guns,
    while the belfry is 3650 up. The script loops over every player's `inventory` and runs
    `<weapon> dmbulletrange 15000` on each, only on this map.
- To repackage after editing the script, rebuild `user-tallchurch.pk3`. No recompile is needed.
- **Seeing far from high up** (stock maps were built for ground level):
  - The map's hand-made visibility groups (`vis_leafgroup`) hid most of the village from the
    tower top. Compile the BSP with `-nomanvis` and skip the `-vis` pass, so everything is drawn.
  - The outer ring had a low sky ceiling (z about 850) that looks white from above.
    `make_tallchurch.py` turns those low sky brushes into `common/clip` (still solid, now
    invisible), retextures the outer caulk floors to mud, and adds a 14000x14000 mud plane
    inside a bigger outer sky box.
  - Before MOHlight, run `py -3 MOHMaps\compilebase\fix_missing_tga.py <map>`. It creates
    stand-in `.tga` files for every image a shader references but doesn't exist; otherwise
    MOHlight stops at "Radiosity" or says "Not a JPEG file".

## 3. Bots

- These cvars must be set before the map loads: `sv_maxbots 8`, `sv_numbots 7`.
- OpenMoHAA 0.82+ builds the bot navigation mesh automatically for any map, custom maps included.
- Stock bots are a simple state machine (attack, investigate sounds, wander) in
  `code/fgame/playerbot*.cpp`. They don't throw grenades, take cover or play objectives.
- `global/bot_run.scr is missing` in the log is harmless. In 0.82.1 that hook is loaded but never run.

### Bot personalities (custom game.dll)
- Profiles live in `maintt/bot_personalities.cfg`, documented at the top of that file.
  Bots take the profile names in order. Changes apply on the next map load.
- The code is in `openmohaa-src/code/fgame/playerbot_personality.{h,cpp}`, plus small
  edits to `playerbot.cpp`, `playerbot.h`, `playerbot_rotation.cpp`, `playerbot_master.cpp`
  and `g_bot.cpp`.
- To rebuild (needs VS 2022 Build Tools with C++, CMake, and WinFlexBison from winget):
  ```
  cmake -S openmohaa-src -B openmohaa-src\.cmake -G "Visual Studio 17 2022" -A x64 ^
        -DBUILD_NO_CLIENT=1 -DFLEX_EXECUTABLE=<win_flex.exe> -DBISON_EXECUTABLE=<win_bison.exe>
  cmake --build openmohaa-src\.cmake --config Release --target fgame
  ```
  Then copy `.cmake\code\server\fgame\Release\game.dll` into the game folder.
- To undo, rename `game.dll.stock-v0.82.1` back to `game.dll`.
- `game.dll` only matters on the machine hosting the game. Other players don't need it.

## 4. Custom weapons (the weapon kit)

```
py -3 C:\Users\joshr\Games\MOHMods\weaponkit\make_weapon.py          # list recipes
py -3 C:\Users\joshr\Games\MOHMods\weaponkit\make_weapon.py all      # build + install all
py -3 C:\Users\joshr\Games\MOHMods\weaponkit\make_weapon.py --remove barndoor
```

How it works: a recipe copies a stock weapon `.tik` out of the paks, changes some
settings, and writes `maintt/user-<id>.pk3` containing `models/weapons/wk_<id>.tik`.
It also writes key binds to `maintt/weaponkit.cfg`. To add a weapon, copy a recipe
in `RECIPES` and change its values.

In game, using the **Courtyard - Wacky Weapons** shortcut:

| Key | Weapon |
|---|---|
| G | Rocket Hose (full-auto bazooka) — **confirmed working** |
| F7 | Barn Door (80-pellet shotgun) |
| F8 | Pocket Artillery (pistol firing tank shells) |
| F10 | Grenade Hose (SMG spraying grenades) |
| F11 | Laser Beam (zero-spread, very fast MG) |
| [ | Shove Gun (1 damage, huge knockback) |
| ] | Smoke Machine (SMG spraying smoke grenades) |

Everything except the Rocket Hose loads and is given in game, but hasn't been play-tested yet.

### Weapon rules (each of these cost a failed attempt)
1. **Cheats.** `give` needs `+set thereisnomonkey 1 +set developer 1 +set cheats 1` on
   the command line. `devmap` alone isn't enough. Without `thereisnomonkey`, the first
   cheat command turns cheats back off, and loading a map with bots resets cheats unless
   `developer` is on.
2. **The name must be a stock weapon name** (for example "Bazooka" or "Thompson"). First-person
   animations, the fire animation and the HUD are looked up by name. An unknown name
   falls back to "unarmed": no model, no ammo display, can't fire.
3. **Full-auto works only for `weapontype smg` or `mg`** (see `global/mike_torso.st`).
   Removing `semiauto` from a heavy, rifle or pistol weapon makes the trigger do nothing.
4. **Ammo is capped per player:** heavy 5, grenade 5, pistol 200, rifle 200, smg 300,
   shotgun 50, mg 500. Use a larger pool (for example `ammotype "mg"`) for high ammo counts.
5. `maxfiremovement 0.2` (bazooka) blocks firing while moving. Set it to `1.0` to allow it.
6. Everyone who plays needs the same `user-*.pk3` files in `maintt`.

## 5. Testing tricks

- Logs: add `+set logfile 2`, then read `%APPDATA%\openmohaa\maintt\qconsole.log`.
- Automated in-game screenshots: `+wait 900 +screenshotJPEG`. They're saved in `...\maintt\screenshots`.
  Windows screen captures can catch whatever window is in front instead.
- To spawn from the command line: `+primarydmweapon smg +join_team freeforall`.
  Simulated `+attackprimary` and `use` don't register in automated runs, so firing
  has to be tested by hand.
