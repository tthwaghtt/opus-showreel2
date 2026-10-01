# opus-showreel2 — HX-01 KESTREL (read me first, every session, and after every context compaction)

DOHA's scroll-driven engineering showreel: an ORIGINAL full-body armored powered suit (HX-01 KESTREL) presented as a
12-sheet engineering drawing package, ~94 s of scroll motion graphics + free 3D inspection mode + synthesized sound.
Concept v2.1 (2026-09-30 16:30): the pilot stands inside a dense internal mechanical layer; 120+ separate armor panels latch onto it.
No flight. Power = **KEEL CORE**, a fictional aneutronic (p-¹¹B) fusion core standing vertically inside a sternum "keel" in the chest.
It is the ONE assumption (ASSUMPTION A-01, calc tag `fiction`); everything else is computed from physics.
Heat, not fuel, sets the limits (two thin back radiators + a wax heat buffer; heat only flows downhill, so the
pilot's chiller condenses at 80 °C above the 70 °C shared loop — the calc sheet checks the temperature order).

## Source of truth (read in this order)
1. `PROGRESS.md` — what is done, what is next, open issues. **Update it at every milestone.**
2. `PLAN.md` — every decision (sections 0–12). Section 10 = contradiction log (v2 from #31, v2.1 from #62), section 11 = v1 → v2 → v2.1 table.
3. `CONTRACT.md` — build rules (files, constraints, visual/motion/number rules, testing).
4. `BLENDER_METHOD.md` — how 3D is made (Blender = shape & surface, code = numbers & motion, sockets, armor panels, helmet, neck, keel core, radiators, MakeHuman pilot).
5. `calc/specs.py` → `calc/specs.json` — ALL engineering numbers. Never hardcode a number that is in specs.
   Part COUNTS and model envelope sizes come from the Blender model manifest, never typed by hand.
   Positions/sizes of the keel core, radiators, trunk arc, atlas ring and pilot joints come from `S.layout`.

## Gate
- **Do not start production (modeling, rendering, web code, test renders) until Doha says "시작".** As of 2026-09-30 the plan v2.1 is
  written and awaiting Doha's review; Doha said to only update the plan documents. Code cleanups are listed in PROGRESS, not done.

## Non-negotiables (user = Doha, first-year mechanical engineering student; reply in casual Korean prose)
- Heavy, metallic, detailed but never cluttered (70/30 rule). Precision is the aesthetic. Nothing stuck on the outside:
  only armor panels, rotation rings, the chest keel and two flush back radiators.
- Three layers: pilot / dense internal mechanical layer / 120+ separate armor panels on over-center latches.
- Design language: curves that follow human muscle masses (~60%) + straight panel lines, sharp chamfers, keel, rings (~40%).
  Human-like from afar, precision-machined up close. No boxy all-straight "toy robot" shapes, no featureless blobs.
- Joints: exposed concentric rings (gold ring = rotation axis), clearance cuts, single sliding caps. NEVER overlapping scales.
- Original design only: must not resemble any film/comic armor. Doha asked for "as identical as possible to Iron Man" — declined
  (PLAN #35, #62); keep only the genre feel. No red, no red-and-gold scheme, no all-gold, no gold faceplate, no round or triangular
  glowing chest disc, no bright chest glow, no mouth slit, no glowing eyes, no external turbines, no forearm tool bay,
  no external pouches/tanks/pipes/antennas.
- Chest: vertical polished-Ti keel ridge between the pectoral plates; the KEEL CORE (vertical spindle Ø76 × 250 mm) sits inside.
  Visible only as ONE faint violet-white line (#B7A6FF) in a thin slit, pulsing at the computed heartbeat
  (standby 7 / walk 28 / heavy 63 / rated 69 BPM). The keel opens in two halves on SHEET 08. Fiction values carry an "A-01" mark on the page.
  The core never leaves the suit: during suit-up its front chest frame swings open like a door, shield always toward the pilot.
- Palette (3D materials): graphite CFRP, gunmetal titanium, platinum-tone polish, anodized titanium-gold, titanium-bronze, gold.
  Gold family 10–15% of the visible exterior (measured from the model), red 0%. Gold comes from physics (Ti anodizing thin film).
- Helmet: kestrel eyes but NOT round — narrow, angular apertures, upper edge 15° (review range 12–18°; the ~27° sketch looked angry
  and childish). The brow is part of the shell (a folded surface), never a separate plate. 4 cameras; no glow.
- Neck must be visible: sculpted neck armor (front ≈67 mm) + gold atlas ring (216 mm pitch, tilted 22° forward) just under the helmet.
- Back: no power pack. Two thin (25 mm) radiator panels in Doha's sketched tapered shape, flush with the back, click-on
  (magnet guides + latches + dry-break coupling). Gold trunk arc rail behind the lumbar spine (no waist ring).
- Pilot = Doha's body: 1.77 m, wingspan 1.82 m (shoulder-to-fingertip 735 mm), legs slightly longer (hip 0.535 H).
  No skin/face visible — flame-resistant flight suit with cooling-garment quilting, thin fabric balaclava, gloves, boots;
  MakeHuman CC0 body with subtle motion (not a mannequin).
- Suit-up: a robot cell assembles parts onto the pilot in our own choreography (load-path order), then the first heartbeat.
  Never copy film choreography.
- NO big decorative title text anywhere. Name only small in the title block ("DRAWN BY DOHA").
- UI colors carry meaning: cyan = measured values, orange = real heat (core waste heat, radiators, wax buffer, damper oil),
  green = approved, yellow = torque paint / caution.
- Every motion is physical (springs SERVO/HEAVY/DETENT), scrubbable as a pure function of scroll progress p
  (heartbeat phase = computed BPM integrated over scene time).
- Sound is mandatory, synthesized, frequencies computed from the design (core heartbeat, cryocooler 50 Hz, motor, gear mesh,
  strain wave, radiator fans 1,100 Hz, chiller, latches).
- The reference repo (tthwaghtt/making-assbitch-cool, branch claude/sleepy-franklin-801eu8) is for techniques only,
  not to be copied as a concept/look. Never push to it.

## Environment facts
- Blender: `.venv-blender/bin/python` (bpy 5.2.1 = same as Doha's MacBook). Run `npm run model`.
  bpy 5.2.1 has Principled Thin Film (used for anodized titanium) and glTF iridescence export.
- Web: Vite 8 + three r186 + GSAP 3.15 + Lenis 1.3. `npm run dev` (port 5173), `npm run build`.
- Headless Chromium via python playwright; WebGL needs `--use-angle=swiftshader --enable-unsafe-swiftshader`.
  Software GL: pictures are right, fps is NOT meaningful (final fps check on Doha's MacBook).
- Shell cannot reach CDNs; npm/pypi/GitHub work. Container may be reclaimed → commit + push every milestone.
- Doha's MacBook Blender MCP is used only at the finishing stage (GPU render/bake, viewport check, .blend handoff).
- `model/build.py` and `public/assets/kestrel.glb` are still v1 (skeleton-exposed + turbines) and do not match specs v2.1;
  they get rewritten when the v2.1 blockout starts.

## Workflow
- Single agent (no subagents). Render → screenshot → look → fix loop for everything visual.
- Commit + push to `origin main` at every milestone; update `PROGRESS.md` in the same commit.
- When `calc/specs.py` changes, update the numbers in `PLAN.md` in the same commit.
- Share review renders ①②③ with Doha (SendUserFile) and wait for feedback when PLAN says so.
- Commit trailer:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UwYBB3Jad1aokzHmCAYWnn
