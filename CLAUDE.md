# opus-showreel2 — HX-01 KESTREL (read me first, every session, and after every context compaction)

DOHA's scroll-driven engineering showreel: an ORIGINAL full-body armored powered suit (HX-01 KESTREL) presented as a
12-sheet engineering drawing package, ~94 s of scroll motion graphics + free 3D inspection mode + synthesized sound.
Concept v2 (2026-09-30): the pilot stands inside a dense internal mechanical layer; 120+ separate armor panels latch onto it.
No flight. Power = hydrogen fuel cell + buffer battery in the back.

## Source of truth (read in this order)
1. `PROGRESS.md` — what is done, what is next, open issues. **Update it at every milestone.**
2. `PLAN.md` — every decision (sections 0–12). Section 10 = contradiction log (v2 from #31), section 11 = v1 → v2 table.
3. `CONTRACT.md` — build rules (files, constraints, visual/motion/number rules, testing).
4. `BLENDER_METHOD.md` — how 3D is made (Blender = shape & surface, code = numbers & motion, sockets, armor panels, MakeHuman pilot).
5. `calc/specs.py` → `calc/specs.json` — ALL engineering numbers. Never hardcode a number that is in specs.
   Part COUNTS and model envelope sizes come from the Blender model manifest, never typed by hand.

## Gate
- **Do not start production (modeling, rendering, web code) until Doha says "시작".** As of 2026-09-30 13:56 the plan v2 is
  written and awaiting Doha's review; Doha said to only finish the plan documents.

## Non-negotiables (user = Doha, first-year mechanical engineering student; reply in casual Korean prose)
- Heavy, metallic, detailed but never cluttered (70/30 rule). Precision is the aesthetic. Nothing stuck on the outside.
- Three layers: pilot / dense internal mechanical layer / 120+ separate armor panels on over-center latches.
- Joints: exposed concentric rings (gold ring = rotation axis), clearance cuts, single sliding caps. NEVER overlapping scales.
- Original design only: must not resemble any film/comic armor. No red, no red-and-gold scheme, no all-gold, no gold faceplate,
  no chest reactor / chest emitter, no mouth slit, no glowing eyes, no external turbines, no forearm tool bay (Doha dropped it).
- Palette (3D materials): graphite CFRP, gunmetal titanium, platinum-tone polish, anodized titanium-gold, gold.
  Gold family 10–15% of the visible exterior (measured from the model), red 0%. Gold comes from physics (Ti anodizing thin film).
- Helmet: kestrel eyes but NOT round — narrow, swept, angular apertures under a heavy brow; 4 cameras; no glow.
- Pilot: no skin/face visible — flame-resistant flight suit with cooling-garment quilting, thin fabric balaclava, gloves, boots;
  MakeHuman CC0 body with subtle motion (not a mannequin).
- Suit-up: a robot cell assembles parts onto the pilot in our own choreography (load-path order). Never copy film choreography.
- NO big decorative title text anywhere. Name only small in the title block ("DRAWN BY DOHA").
- UI colors carry meaning: cyan = measured values, orange = real heat (UI), green = approved, yellow = torque paint / caution.
- Every motion is physical (springs SERVO/HEAVY/DETENT), scrubbable as a pure function of scroll progress p.
- Sound is mandatory, synthesized, frequencies computed from the design (motor, gear mesh, strain wave, fuel-cell blower, chiller, latches).
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
- `model/build.py` and `public/assets/kestrel.glb` are still v1 (skeleton-exposed + turbines) and do not match specs v2;
  they get rewritten when the v2 blockout starts.

## Workflow
- Single agent (no subagents). Render → screenshot → look → fix loop for everything visual.
- Commit + push to `origin main` at every milestone; update `PROGRESS.md` in the same commit.
- When `calc/specs.py` changes, update the numbers in `PLAN.md` in the same commit.
- Share review renders ①②③ with Doha (SendUserFile) and wait for feedback when PLAN says so.
- Commit trailer:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UwYBB3Jad1aokzHmCAYWnn
