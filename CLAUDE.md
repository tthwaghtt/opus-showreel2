# opus-showreel2 — HX-01 KESTREL (read me first, every session, and after every context compaction)

DOHA's scroll-driven engineering showreel: an ORIGINAL powered exosuit (HX-01 KESTREL) presented as a 12-sheet
engineering drawing package, ~92 s of scroll motion graphics + free 3D inspection mode + synthesized sound.

## Source of truth (read in this order)
1. `PROGRESS.md` — what is done, what is next, open issues. **Update it at every milestone.**
2. `PLAN.md` — every decision (sections 1–12). Section 10 = contradiction log, section 12 = reference review.
3. `CONTRACT.md` — build rules (files, constraints, visual/motion/number rules, testing).
4. `BLENDER_METHOD.md` — how 3D is made (Blender = shape & surface, code = numbers & motion, sockets).
5. `calc/specs.py` → `calc/specs.json` — ALL engineering numbers. Never hardcode a number that is in specs.

## Non-negotiables (user = Doha, first-year mechanical engineering student; reply in casual Korean prose)
- Heavy, metallic, detailed but never cluttered (70/30 rule). Precision is the aesthetic.
- Original design only: must not resemble any film/comic armor (no red/gold, no chest reactor, no franchise faceplate).
- Pilot: no skin/face visible — flame-resistant flight suit, thin fabric balaclava, gloves, boots.
- NO big decorative title text anywhere. Name only small in the title block ("DRAWN BY DOHA").
- Colors carry meaning: cyan = measured values, orange = real heat (UI), green = approved, yellow = torque paint.
- Every motion is physical (springs SERVO/HEAVY/DETENT), scrubbable as a pure function of scroll progress p.
- Sound is mandatory, synthesized, frequencies computed from the design (motor, gear mesh, turbine blade-pass).
- The reference repo (tthwaghtt/making-assbitch-cool, branch claude/sleepy-franklin-801eu8) is for techniques only,
  not to be copied as a concept/look.

## Environment facts
- Blender: `.venv-blender/bin/python` (bpy 5.2.1 = same as Doha's MacBook). Run `npm run model`.
- Web: Vite 8 + three r186 + GSAP 3.15 + Lenis 1.3. `npm run dev` (port 5173), `npm run build`.
- Headless Chromium via python playwright; WebGL needs `--use-angle=swiftshader --enable-unsafe-swiftshader`.
  Software GL: pictures are right, fps is NOT meaningful (final fps check on Doha's MacBook).
- Shell cannot reach CDNs; npm/pypi/GitHub work. Container may be reclaimed → commit + push every milestone.
- Doha's MacBook Blender MCP is used only at the finishing stage (GPU render/bake, viewport check, .blend handoff).

## Workflow
- Single agent (no subagents). Render → screenshot → look → fix loop for everything visual.
- Commit + push to `origin main` at every milestone; update `PROGRESS.md` in the same commit.
- Share review renders ①②③ with Doha (SendUserFile) and wait for feedback when PLAN says so.
- Commit trailer:
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UwYBB3Jad1aokzHmCAYWnn
