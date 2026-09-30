"""Review renders for the Blender model.

    .venv-blender/bin/python model/render.py <tag> [--cycles-samples 64] [--quick]

Writes renders/<tag>_{front,side,34,sil,hero}.png (compose with scripts/sheet.py)
"""
import sys
import os
import math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
import bpy  # noqa: E402

ARGS = sys.argv[1:]
TAG = ARGS[0] if ARGS else "r"
QUICK = "--quick" in ARGS
ONLY_HERO = "--hero" in ARGS
SAMPLES = int(ARGS[ARGS.index("--cycles-samples") + 1]) if "--cycles-samples" in ARGS else 64
OUT = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "kestrel.blend"))
sc = bpy.context.scene
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass


def cam(name):
    sc.camera = bpy.data.objects[name]


def workbench(single=None):
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO" if single is None else "FLAT"
    try:
        sh.studio_light = "studio.sl"
    except TypeError:
        pass
    sh.color_type = "MATERIAL" if single is None else "SINGLE"
    if single is not None:
        sh.single_color = single
    sh.show_cavity = single is None
    sh.cavity_type = "BOTH"
    sh.cavity_ridge_factor = 1.0
    sh.cavity_valley_factor = 1.2
    sh.curvature_ridge_factor = 1.0
    sh.curvature_valley_factor = 1.0
    sh.show_object_outline = single is None
    sh.object_outline_color = (0.0, 0.0, 0.0)
    sh.show_shadows = single is None
    sh.shadow_intensity = 0.35
    sh.show_specular_highlight = True
    sc.display.render_aa = "8"


def render(name, w, h, transparent=False):
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.filepath = os.path.join(OUT, f"{TAG}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("WROTE", sc.render.filepath)


floor = bpy.data.objects.get("GEO-floor")
bpy.context.scene.world.color = (0.03, 0.032, 0.035)

# ---- clay (workbench) views
workbench()
if ONLY_HERO:
    pass
floor.hide_render = True
for c, n in ((("CAM-front", "front"), ("CAM-side", "side"), ("CAM-34", "34")) if not ONLY_HERO else ()):
    cam(c)
    render(n, 720, 1080, transparent=True)
if not ONLY_HERO:
    workbench(single=(0.0, 0.0, 0.0))
    render("sil", 720, 1080, transparent=True)

# ---- cycles hero (hangar lighting)
if not QUICK:
    floor.hide_render = False
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.5
    cam("CAM-hero")
    render("hero", 900, 1200)
print("DONE")
