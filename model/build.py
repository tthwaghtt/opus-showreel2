"""HX-01 KESTREL — procedural Blender build (bpy 5.2.1).

    .venv-blender/bin/python model/build.py [--stage blockout] [--no-export]

Reads every dimension from calc/specs.json (layout section). Writes
  model/kestrel.blend, public/assets/kestrel.glb, public/assets/kestrel_manifest.json
Blender = shape & surface; code (three.js) = counted/precise/moving parts, attached at HLP-kst_socket_* empties.
"""
import sys
import os
import json
import math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
from kstlib import (reset_scene, collection, set_collection, V, mirror, basis_z, frame, mesh_object, empty,  # noqa: E402
                    parent_keep, props, bevel, weighted_normal, subsurf, solidify, hard_surface, bm_cylinder,
                    bm_box, bm_uvsphere, bm_lathe, bm_torus, bm_tube_between, bm_merge, bm_transform,
                    skin_object, make_materials, tri_count, to_gltf)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
STAGE = ARGS[ARGS.index("--stage") + 1] if "--stage" in ARGS else "blockout"
EXPORT = "--no-export" not in ARGS

SPEC = json.load(open(os.path.join(ROOT, "calc", "specs.json")))
LAY = SPEC["layout"]
P = {k: Vector(v) for k, v in LAY["pilot"].items()}
X = LAY["exo"]
AC = SPEC["actuator_classes"]


def sv(k):
    return SPEC[k]["v"]


def axis_side(a, s):
    """rotation axes are pseudo-vectors: mirror x→−x maps (ax, ay, az) → (ax, −ay, −az)"""
    a = Vector(a)
    return a if s > 0 else Vector((a.x, -a.y, -a.z))


def sfx(s):
    return ".L" if s > 0 else ".R"


# ============================================================================ setup
reset_scene()
M = make_materials()
COL = collection("CH-kst")
COL_RENDER = collection("LG-kst_studio")
COL_CAM = collection("CA-kst")
set_collection(COL)

ROOT_E = empty("HLP-kst_root", Matrix.Identity(4), disp_size=0.2, disp_kind="PLAIN_AXES",
               asset="HX-01 KESTREL", frame=LAY["frame"], stage=STAGE)
JN = {}          # joint empties by name
PARTS = []       # every mesh part (for the manifest)


def joint(name, center, axis, parent, up_hint=(0, 0, 1), **kw):
    e = empty("HLP-kst_j_" + name, frame(center, axis, up_hint), parent=parent, disp_size=0.06,
              joint=name, axis_local_gltf=[0, 1, 0], **kw)
    JN[name] = e
    return e


def part(obj, **kw):
    props(obj, **kw)
    PARTS.append(obj)
    return obj


def socket(name, matrix, parent, **kw):
    return empty("HLP-kst_socket_" + name, matrix, parent=parent, disp_size=0.03, disp_kind="SINGLE_ARROW", socket=name, **kw)


BOLT = {"L": ("M5", 12), "M": ("M4", 10), "S": ("M3", 8)}


def actuator(name, cls, center, axis_rot, out_dir, parent, stator_mat=None):
    """drum housing (stator side, parented to the previous segment) + bolt-circle socket on the outer face.
    Blockout: plain drum + output flange ring."""
    c = AC[cls]
    od, w = c["od_mm"] / 1000, c["width_mm"] / 1000
    m = frame(center, out_dir)
    bm = bm_cylinder(od / 2, w, segments=64)
    bm = bm_merge(bm, bm_cylinder(od * 0.42, 0.010, segments=48, z0=-w / 2 - 0.010))   # output flange (inner side)
    bm = bm_merge(bm, bm_cylinder(od * 0.30, 0.006, segments=48, z0=w / 2))            # end cap (outer side)
    obj = mesh_object("GEO-kst_act_" + name, bm, matrix=m, mat=stator_mat or M["al_dark"], parent=parent)
    hard_surface(obj, 0.0025, 2)
    size, count = BOLT[cls]
    socket("bolts_act_" + name, frame(Vector(center) + Vector(out_dir).normalized() * (w / 2), out_dir), obj,
           size=size, count=count, pcd_mm=round(od * 820), kind="bolt_circle")
    socket("drive_" + name, frame(center, out_dir), obj, kind="drive",
           reducer=("planetary" if (cls == "L" and ("hip" in name or "knee" in name)) else "strain_wave"),
           axis_rot=list(axis_rot))
    return part(obj, part_no=f"HX01-{cls}-{name.upper().replace('.', '')}", cls=cls, mass_kg=c["kg"],
                material="Al 7075-T6 housing / Ti output", kind="actuator", od_mm=c["od_mm"], width_mm=c["width_mm"])


def bar(name, pts, r, parent, mat=None, **kw):
    """polyline of round bars (link tubes). pts in world coords."""
    bms = [bm_tube_between(pts[i], pts[i + 1], r, segments=20) for i in range(len(pts) - 1)]
    for p in pts[1:-1]:
        s = bm_uvsphere(r * 1.08, 20, 10)
        bm_transform(s, Matrix.Translation(p))
        bms.append(s)
    obj = mesh_object("GEO-kst_" + name, bm_merge(*bms), mat=mat or M["ti_blast"], parent=parent)
    return part(obj, kind="link", material="Ti-6Al-4V", **kw)


def block(name, size, matrix, parent, mat=None, bev=0.003, **kw):
    obj = mesh_object("GEO-kst_" + name, bm_box(*size), matrix=matrix, mat=mat or M["ti_blast"], parent=parent)
    hard_surface(obj, bev, 2)
    return part(obj, **kw)


def shell(name, a, b, radius, mid_dir, arc_deg, thick, parent, facets=5, lsegs=1, r_end=None, mat=None, **kw):
    """faceted armor shell: a cylinder/cone segment around the line a→b, centred on mid_dir."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    u = (Vector(mid_dir) - ax * Vector(mid_dir).dot(ax)).normalized()
    v = ax.cross(u)
    r_end = radius if r_end is None else r_end
    bm = bmesh.new()
    rows = []
    for j in range(lsegs + 1):
        t = j / lsegs
        base = a.lerp(b, t)
        r = radius + (r_end - radius) * t
        row = []
        for i in range(facets + 1):
            ang = math.radians(-arc_deg / 2 + arc_deg * i / facets)
            row.append(bm.verts.new(base + (u * math.cos(ang) + v * math.sin(ang)) * r))
        rows.append(row)
    for j in range(lsegs):
        for i in range(facets):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # make normals point outward (away from the axis)
    f0 = bm.faces[0]
    cen = f0.calc_center_median()
    radial = cen - a - ax * (cen - a).dot(ax)
    if f0.normal.dot(radial) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    obj = mesh_object("GEO-kst_armor_" + name, bm, mat=mat or M["cfrp"], parent=parent, smooth=False)
    solidify(obj, thick, offset=-1.0)
    bevel(obj, width=0.0012, segments=2, angle=25)
    weighted_normal(obj)
    return part(obj, kind="armor", material="CFRP [0/±45/90] + aramid", **kw)


# ============================================================================ pelvis & trunk
pel = joint("pelvis", P["pelvis"], (0, 0, 1), ROOT_E)
tr = X["trunk_rot"]
trunk = joint("trunk_rot", tr["c"], tr["axis"], pel)
actuator("trunk_rot", "M", tr["c"], tr["axis"], (0, 0, 1), pel)

# pelvis belt: elliptical band (Ti frame + CFRP), buckle at the front
belt_z = P["pelvis"].z + 0.035
bm = bm_torus(0.200, 0, seg=72, rect=(0.022, 0.055))
bm_transform(bm, Matrix.Diagonal((1.0, 0.74, 1.0, 1.0)))
obj = mesh_object("GEO-kst_pelvis_belt", bm, matrix=Matrix.Translation((0, 0.0, belt_z)), mat=M["ti_blast"], parent=pel)
hard_surface(obj, 0.002, 2)
part(obj, kind="frame", material="Ti-6Al-4V", part_no="HX01-FR-001", mass_kg=1.1)

# back frame: machined Ti spine plate from the trunk actuator to the shoulder yoke
back_c = Vector((0, 0.170, 1.345))
block("spine_plate", (0.24, 0.020, 0.40), Matrix.Translation(back_c), trunk, part_no="HX01-FR-010", kind="frame",
      material="Ti-6Al-4V", mass_kg=1.4)
yoke_z = 1.525
block("shoulder_yoke", (0.46, 0.030, 0.040), Matrix.Translation((0, 0.185, yoke_z)), trunk,
      part_no="HX01-FR-011", kind="frame", material="Ti-6Al-4V", mass_kg=0.6)

# neck actuator (helmet yaw support) sits on the yoke
nk = X["neck"]
neck = joint("neck", nk["c"], nk["axis"], trunk)
actuator("neck", "S", nk["c"], nk["axis"], (0, 0, 1), trunk)

# ============================================================================ legs


def build_leg(s):
    x = sfx(s)

    def c(k):
        return mirror(X[k]["c"], s)

    def ax(k):
        return axis_side(X[k]["axis"], s)

    out_lat = Vector((s, 0, 0))
    out_back = Vector((0, 1, 0))
    # hip abduction (axis Y, behind hip on the belt)
    j_abd = joint("hip_abd" + x, c("hip_abd"), ax("hip_abd"), pel, up_hint=(0, 0, 1))
    actuator("hip_abd" + x, "L", c("hip_abd"), ax("hip_abd"), out_back, pel)
    # hip flexion (lateral)
    j_flex = joint("hip_flex" + x, c("hip_flex"), ax("hip_flex"), j_abd)
    # abd → flex bracket (moves with abduction)
    ha, hf = c("hip_abd"), c("hip_flex")
    bar("bracket_hip" + x, [ha + Vector((0, -0.045, -0.03)), Vector((hf.x, ha.y - 0.06, hf.z + 0.09)),
                             hf + Vector((0, 0.0, 0.07))], 0.014, j_abd, part_no="HX01-BR-HIP" + x, mass_kg=0.25)
    actuator("hip_flex" + x, "L", c("hip_flex"), ax("hip_flex"), out_lat, j_abd)
    # thigh link with in-line hip rotation actuator
    kn = c("knee")
    thigh_dir = (kn - hf).normalized()
    hr = c("hip_rot")
    j_rot = joint("hip_rot" + x, hr, thigh_dir, j_flex, up_hint=(0, -1, 0))
    AL = AC["L"]["od_mm"] / 2000
    AM = AC["M"]["width_mm"] / 2000
    bar("thigh_link_upper" + x, [hf + thigh_dir * (AL * 0.85), hr - thigh_dir * AM], 0.016, j_flex,
        part_no="HX01-LK-TH1" + x, mass_kg=0.35)
    actuator("hip_rot" + x, "M", hr, thigh_dir, thigh_dir, j_flex)
    j_knee = joint("knee" + x, kn, ax("knee"), j_rot)
    bar("thigh_link_lower" + x, [hr + thigh_dir * AM, kn - thigh_dir * (AL * 0.85)], 0.016, j_rot,
        part_no="HX01-LK-TH2" + x, mass_kg=0.35, od_mm=32, id_mm=28)
    actuator("knee" + x, "L", kn, ax("knee"), out_lat, j_rot)
    # shank link → ankle pitch
    ap = c("ankle_pitch")
    j_ap = joint("ankle_pitch" + x, ap, ax("ankle_pitch"), j_knee)
    shank_dir = (ap - kn).normalized()
    bar("shank_link" + x, [kn + shank_dir * (AL * 0.85), ap - shank_dir * (AC["M"]["od_mm"] / 2000 * 0.85)], 0.016,
        j_knee, part_no="HX01-LK-SH" + x, mass_kg=0.40, od_mm=32, id_mm=28)
    actuator("ankle_pitch" + x, "M", ap, ax("ankle_pitch"), out_lat, j_knee)
    # stirrup: ankle pitch output → behind the heel → ankle roll
    ar = c("ankle_roll")
    j_ar = joint("ankle_roll" + x, ar, ax("ankle_roll"), j_ap)
    bar("stirrup" + x, [ap + Vector((0, 0.035, -0.035)), Vector((ap.x, ar.y + 0.02, ar.z + 0.035)),
                         Vector((ar.x + s * 0.045, ar.y + 0.02, ar.z + 0.035))], 0.011, j_ap,
        part_no="HX01-BR-ST" + x, mass_kg=0.2)
    actuator("ankle_roll" + x, "S", ar, ax("ankle_roll"), out_back, j_ap)
    # foot plate (carries the suit to the ground) + heel upright to the roll actuator
    ank = mirror(P["ankle"], s)
    fp_len, fp_w, fp_t = 0.305, 0.118, sv("foot_plate_thickness")
    fp_c = Vector((ank.x, -0.080, fp_t / 2))
    block("foot_plate" + x, (fp_w, fp_len, fp_t), Matrix.Translation(fp_c), j_ar, part_no="HX01-FT-001" + x,
          kind="frame", material="Ti-6Al-4V + load cell", mass_kg=0.55)
    block("heel_upright" + x, (0.05, 0.018, ar.z - fp_t + 0.02), Matrix.Translation((ar.x, ar.y - 0.03,
          (ar.z + fp_t) / 2)), j_ar, kind="frame", material="Ti-6Al-4V", mass_kg=0.08)
    sole = mesh_object("GEO-kst_sole" + x, bm_box(fp_w * 0.96, fp_len * 0.98, 0.008),
                       matrix=Matrix.Translation((ank.x, -0.080, -0.004 + 0.008)), mat=M["rubber"], parent=j_ar)
    part(sole, kind="sole", material="rubber tread")
    return j_abd, j_flex, j_rot, j_knee, j_ap, j_ar


LEG = {s: build_leg(s) for s in (1, -1)}

# ============================================================================ arms
fdir = Vector(LAY["forearm_dir"]).normalized()


def build_arm(s):
    x = sfx(s)

    def c(k):
        return mirror(X[k]["c"], s)

    def ax(k):
        return axis_side(X[k]["axis"], s)

    gh, el, wr, gp = (mirror(P[k], s) for k in ("gh", "elbow", "wrist", "grip"))
    ua_dir = (el - gh).normalized()
    fd = mirror(fdir, s)
    out_lat = Vector((s, 0, 0))
    # shoulder abduction (axis Y, behind GH), stator on the yoke
    sa = c("shoulder_abd")
    j_sa = joint("shoulder_abd" + x, sa, ax("shoulder_abd"), trunk)
    actuator("shoulder_abd" + x, "L", sa, ax("shoulder_abd"), Vector((0, 1, 0)), trunk)
    bar("yoke_drop" + x, [Vector((sa.x, 0.19, yoke_z - 0.02)), sa + Vector((0, 0.045, 0.06))], 0.013, trunk,
        mass_kg=0.1)
    # arc bracket over the shoulder to the flexion actuator
    sf = c("shoulder_flex")
    j_sf = joint("shoulder_flex" + x, sf, ax("shoulder_flex"), j_sa)
    bar("shoulder_arc" + x, [sa + Vector((0, -0.045, 0.04)), Vector((sa.x + s * 0.01, sa.y - 0.07, sa.z + 0.10)),
                              Vector((sf.x, sf.y + 0.05, sf.z + 0.10)), sf + Vector((0, 0, 0.068))], 0.014, j_sa,
        part_no="HX01-BR-SA" + x, mass_kg=0.3)
    actuator("shoulder_flex" + x, "L", sf, ax("shoulder_flex"), out_lat, j_sa)
    # shoulder rotation: arc rail around the upper arm
    sr = c("shoulder_rot")
    j_sr = joint("shoulder_rot" + x, sr, ua_dir, j_sf, up_hint=(0, -1, 0))
    rail = bm_torus(0.078, 0, seg=40, rect=(0.018, 0.030), arc=math.radians(200))
    rm = basis_z(ua_dir, up_hint=(0, -1, 0)) @ Matrix.Rotation(math.radians(-100 if s > 0 else 80), 4, "Z")
    rm.translation = sr
    ro = mesh_object("GEO-kst_act_shoulder_rot" + x, rail, matrix=rm, mat=M["al_dark"], parent=j_sf)
    hard_surface(ro, 0.002, 2)
    part(ro, kind="actuator", cls="M", mass_kg=AC["M"]["kg"], part_no=f"HX01-M-SHOULDER_ROT{x}",
         material="Al 7075-T6 arc rail + crossed-roller carriage")
    socket("drive_shoulder_rot" + x, frame(sr, ua_dir), ro, kind="drive", reducer="arc_rail")
    bar("upper_arm_link_top" + x, [sf + Vector((0, 0, -0.06)), Vector((sf.x - s * 0.005, sf.y, sr.z + 0.02))],
        0.015, j_sf, mass_kg=0.15)
    # upper arm link → elbow
    ea = c("elbow")
    j_el = joint("elbow" + x, ea, ax("elbow"), j_sr)
    bar("upper_arm_link" + x, [Vector((sf.x - s * 0.005, sf.y, sr.z - 0.02)), ea + Vector((0, 0, 0.055))],
        0.015, j_sr, part_no="HX01-LK-UA" + x, mass_kg=0.3, od_mm=30, id_mm=26)
    actuator("elbow" + x, "M", ea, ax("elbow"), mirror(Vector(X["elbow"]["axis"]), s), j_sr)
    # forearm pod: 2 turbines lateral to the forearm, clamped by two Ti bands
    lat = fd.cross(Vector((0, 1, 0))).normalized()
    if lat.x * s < 0:
        lat = -lat
    aft = lat.cross(fd).normalized()
    if aft.y < 0:
        aft = -aft
    mid = (el + wr) / 2
    ap_ = LAY["arm_pod"]
    tl, trr = ap_["turbine_len"], ap_["turbine_r"]
    pod = []
    for i, sgn in enumerate((-1, 1)):
        tc = mid + fd * ap_["along"] + lat * ap_["lateral"] + aft * (sgn * ap_["fore_aft"])
        nm = f"turbine_arm{x}{i + 1}"
        build_turbine(nm, tc, fd, j_el, f"HX01-TB-{'L' if s > 0 else 'R'}{i + 1}")
        pod.append(tc)
    pc = (pod[0] + pod[1]) / 2
    for k, t in enumerate((-0.10, 0.10)):
        m = Matrix((lat, aft, fd)).transposed().to_4x4()
        m.translation = pc + fd * t + lat * 0.0
        o = mesh_object(f"GEO-kst_pod_band{x}{k}", bm_box(0.022, 0.36, 0.018), matrix=m, mat=M["ti_blast"], parent=j_el)
        hard_surface(o, 0.002, 2)
        part(o, kind="frame", material="Ti-6Al-4V", mass_kg=0.12)
    bar("pod_spine" + x, [ea + fd * 0.03, pc - fd * 0.12, pc + fd * 0.12], 0.013, j_el, mass_kg=0.25)
    # wrist ring actuator (rotates the throttle grip)
    j_wr = joint("wrist" + x, wr, fd, j_el, up_hint=(0, -1, 0))
    ring = bm_torus(0.035, 0, seg=48, rect=(0.012, AC["S"]["width_mm"] / 1000))
    wo = mesh_object("GEO-kst_act_wrist" + x, ring, matrix=frame(wr, fd), mat=M["al_dark"], parent=j_el)
    hard_surface(wo, 0.0015, 2)
    part(wo, kind="actuator", cls="S", mass_kg=AC["S"]["kg"], part_no=f"HX01-S-WRIST{x}",
         material="hollow-shaft torque motor")
    # throttle grip (hand closes around it)
    grip = bm_tube_between(gp - aft * 0.06, gp + aft * 0.06, 0.016, segments=20)
    go = mesh_object("GEO-kst_grip" + x, grip, mat=M["rubber"], parent=j_wr)
    part(go, kind="control", material="rubber over Al", part_no="HX01-GR-001" + x)
    bar("grip_arm" + x, [gp + aft * 0.06, gp + aft * 0.07 + lat * 0.06, pc + aft * 0.02 + fd * 0.12], 0.009, j_wr)
    return j_sa, j_sf, j_sr, j_el, j_wr


def build_turbine(name, center, axis, parent, part_no):
    """P400-class turbojet, blockout: bellmouth + casing + nozzle. axis points to the exhaust."""
    r = LAY["arm_pod"]["turbine_r"]
    L = LAY["arm_pod"]["turbine_len"]
    prof = [(0.0, -L / 2 + 0.004), (r * 0.62, -L / 2), (r * 0.98, -L / 2 + 0.02), (r, -L / 2 + 0.05),
            (r, L / 2 - 0.10), (r * 0.93, L / 2 - 0.06), (r * 0.66, L / 2), (0.0, L / 2)]
    bm = bm_lathe(prof, segments=48)
    obj = mesh_object("GEO-kst_" + name, bm, matrix=frame(center, axis), mat=M["steel"], parent=parent)
    hard_surface(obj, 0.0015, 2)
    part(obj, kind="turbine", material="Inconel 718 / Ti casing", mass_kg=sv("turbine_mass"), part_no=part_no,
         thrust_N=sv("turbine_thrust_max"))
    socket("rotor_" + name, frame(center, axis), obj, kind="turbine_rotor", rows=SPEC["turbine_rows"])
    return obj


ARM = {s: build_arm(s) for s in (1, -1)}

# ============================================================================ backpack
bp = empty("HLP-kst_backpack", Matrix.Translation((0, 0.25, 1.35)), parent=trunk, disp_size=0.05)
bat = LAY["battery"]
block("battery", tuple(bat["size"][i] for i in (0, 1, 2)), Matrix.Translation(bat["c"]), bp, mat=M["al_dark"],
      part_no="HX01-PW-001", kind="battery", material="Li-ion 1.2 kWh, Al case",
      mass_kg=round(sv("battery_energy") * 1000 / sv("battery_pack_specific_energy"), 2))
tk = LAY["tanks"]
for s in (1, -1):
    r, L = tk["r"], tk["len"]
    prof = [(0.0, -L / 2)]
    for i in range(1, 9):
        a = math.pi / 2 * i / 8
        prof.append((r * math.sin(a), -L / 2 + r - r * math.cos(a)))
    prof += [(r, L / 2 - r)]
    for i in range(1, 9):
        a = math.pi / 2 * i / 8
        prof.append((r * math.cos(a), L / 2 - r + r * math.sin(a)))
    obj = mesh_object("GEO-kst_tank" + sfx(s), bm_lathe(prof, 48), matrix=Matrix.Translation((s * tk["x"], tk["y"],
                      tk["zc"])), mat=M["al_bare"], parent=bp)
    part(obj, kind="tank", material="Al 6061 liner + CFRP overwrap", volume_L=tk["volume_L_each"],
         part_no="HX01-FU-00" + ("1" if s > 0 else "2"), mass_kg=0.9)
    socket("tank" + sfx(s), frame((s * tk["x"], tk["y"], tk["zc"]), (0, 0, 1)), obj, kind="tank")
    # side rail (stand hard point)
    bar("pack_rail" + sfx(s), [Vector((s * 0.272, 0.30, 1.12)), Vector((s * 0.272, 0.30, 1.585))], 0.0125, bp,
        part_no="HX01-FR-02" + ("1" if s > 0 else "2"), mass_kg=0.2)
for z in (1.14, 1.575):
    bar(f"pack_cross_{int(z * 1000)}", [Vector((-0.272, 0.30, z)), Vector((0, 0.24, z)), Vector((0.272, 0.30, z))],
        0.011, bp, mass_kg=0.15)
bt = LAY["back_turbine"]
gimbal = joint("gimbal_back", bt["c"], (1, 0, 0), bp)
gr = mesh_object("GEO-kst_gimbal_ring", bm_torus(0.089, 0, seg=64, rect=(0.010, 0.026)),
                 matrix=Matrix.Translation(bt["c"]), mat=M["ti_machined"], parent=bp)
hard_surface(gr, 0.0015, 2)
part(gr, kind="gimbal", material="Ti-6Al-4V", mass_kg=0.3)
build_turbine("turbine_back", Vector(bt["c"]), Vector(bt["axis"]), gimbal, "HX01-TB-05")
hs = mesh_object("GEO-kst_heat_shield_back", bm_cylinder(0.105, 0.004, segments=48),
                 matrix=Matrix.Translation(Vector(bt["c"]) + Vector((0, -0.10, -0.26))), mat=M["inconel"], parent=bp)
part(hs, kind="heat_shield", material="Inconel 718 + aerogel blanket")

# ============================================================================ helmet & head
hc = Vector((0, -0.006, P["head"].z + 0.015))
bm = bm_uvsphere(1.0, 64, 32, scale=(0.132, 0.150, 0.158))
bm_transform(bm, Matrix.Translation(hc))
cut_z = P["c7"].z + 0.055
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, cut_z),
                       plane_no=(0, 0, 1), clear_inner=True)
visor_faces = [f for f in bm.faces if f.calc_center_median().y < -0.07 and hc.z - 0.07 < f.calc_center_median().z < hc.z + 0.035]
for f in visor_faces:
    f.material_index = 1
helm = mesh_object("GEO-kst_helmet", bm, mat=[M["cfrp"], M["visor"]], parent=neck)
solidify(helm, 0.006, offset=-1)
part(helm, kind="helmet", material="CFRP shell, polycarbonate visor", part_no="HX01-HM-001", mass_kg=1.6)
sen = joint("sensor_head", (0, -0.03, hc.z + 0.158 + 0.012), (0, 0, 1), neck)
block("sensor_pod", (0.07, 0.085, 0.032), Matrix.Translation((0, -0.04, hc.z + 0.158 + 0.03)), sen,
      mat=M["al_dark"], part_no="HX01-SN-001", kind="sensor", material="stereo camera + lidar")
collar = mesh_object("GEO-kst_collar", bm_torus(0.085, 0, seg=48, rect=(0.018, 0.030)),
                     matrix=Matrix.Translation((0, 0.01, cut_z - 0.005)), mat=M["ti_blast"], parent=neck)
hard_surface(collar, 0.0015, 2)
part(collar, kind="frame", material="Ti-6Al-4V", part_no="HX01-HM-010")

# ============================================================================ pilot (flight suit mannequin, rigid segments)
FAB = M["fabric"]


EASE = 0.009   # flight suits are cut loose: ~9 mm of fabric ease over the body


def pilot_seg(name, verts, radii, parent, edges=None, ease=EASE):
    edges = edges or [(i, i + 1) for i in range(len(verts) - 1)]
    radii = [(r[0] + ease, r[1] + ease) for r in radii]
    obj = skin_object("GEO-kst_pilot_" + name, verts, edges, radii, mat=FAB, parent=parent)
    return part(obj, kind="pilot", material="Nomex/aramid flight suit")


pz = P["pelvis"].z
pilot_seg("pelvis", [V(0, 0.005, P["hip"].z - 0.07), V(0, 0.0, pz), V(0, 0.02, P["lumbar"].z)],
          [(0.13, 0.095), (0.165, 0.11), (0.145, 0.10)], pel)
pilot_seg("torso", [V(0, 0.02, P["lumbar"].z), V(0, 0.0, P["chest"].z), V(0, 0.012, 1.425), V(0, 0.035, P["c7"].z),
                    V(0.165, 0.02, 1.445), V(-0.165, 0.02, 1.445)],
          [(0.145, 0.10), (0.162, 0.115), (0.168, 0.105), (0.058, 0.055), (0.062, 0.062), (0.062, 0.062)], trunk,
          edges=[(0, 1), (1, 2), (2, 3), (2, 4), (2, 5)])
pilot_seg("neck", [V(0, 0.035, P["c7"].z), V(0, 0.01, P["head"].z - 0.07)], [(0.056, 0.055), (0.055, 0.058)], neck)
head = mesh_object("GEO-kst_pilot_head", bm_uvsphere(1.0, 32, 16, scale=(0.078, 0.098, 0.113)),
                   matrix=Matrix.Translation((0, 0.0, P["head"].z)), mat=FAB, parent=neck)
part(head, kind="pilot", material="balaclava (thin aramid knit)")
for s in (1, -1):
    x = sfx(s)
    hip, kn, an = (mirror(P[k], s) for k in ("hip", "knee", "ankle"))
    j_abd, j_flex, j_rot, j_knee, j_ap, j_ar = LEG[s]
    pilot_seg("thigh" + x, [hip, hip.lerp(kn, 0.5) + V(0, -0.005, 0), kn + V(0, 0, 0.01)],
              [(0.082, 0.085), (0.072, 0.074), (0.054, 0.056)], j_rot)
    pilot_seg("shank" + x, [kn, kn.lerp(an, 0.3) + V(0, 0.012, 0), an + V(0, 0, 0.03)],
              [(0.053, 0.055), (0.052, 0.060), (0.036, 0.038)], j_knee)
    ank = mirror(P["ankle"], s)
    zb = sv("foot_plate_thickness")
    pilot_seg("boot" + x, [ank + V(0, 0.0, 0.14), ank + V(0, 0.0, 0.0), V(ank.x, 0.035, zb + 0.050),
                           V(ank.x, -0.08, zb + 0.045), V(ank.x, -0.19, zb + 0.040)],
              [(0.052, 0.056), (0.050, 0.060), (0.050, 0.045), (0.054, 0.042), (0.048, 0.034)], j_ar)
    gh, el, wr, gp = (mirror(P[k], s) for k in ("gh", "elbow", "wrist", "grip"))
    j_sa, j_sf, j_sr, j_el, j_wr = ARM[s]
    pilot_seg("upper_arm" + x, [gh, gh.lerp(el, 0.45), el], [(0.058, 0.058), (0.052, 0.055), (0.043, 0.044)], j_sr)
    pilot_seg("forearm" + x, [el, el.lerp(wr, 0.35), wr], [(0.043, 0.044), (0.042, 0.040), (0.030, 0.024)], j_el)
    pilot_seg("glove" + x, [wr, wr.lerp(gp, 0.55), gp + (gp - wr).normalized() * 0.02],
              [(0.030, 0.024), (0.043, 0.036), (0.040, 0.036)], j_wr)

# ============================================================================ armor (14 plates, blockout shells)
fwd = Vector((0, -1, 0))
shell("chest", (0, 0.0, 1.235), (0, 0.0, 1.455), 0.185, fwd, 150, 0.006, trunk, facets=6, lsegs=2,
      r_end=0.175, part_no="HX01-AR-01", mass_kg=0.7)
shell("back_cowl", (0, 0.16, 1.47), (0, 0.16, 1.60), 0.22, Vector((0, 1, 0.4)), 130, 0.005, bp, facets=5,
      r_end=0.17, part_no="HX01-AR-02", mass_kg=0.45)
for s in (1, -1):
    x = sfx(s)
    hip, kn, an = (mirror(P[k], s) for k in ("hip", "knee", "ankle"))
    j_abd, j_flex, j_rot, j_knee, j_ap, j_ar = LEG[s]
    shell("thigh" + x, hip.lerp(kn, 0.28), hip.lerp(kn, 0.88), 0.098, Vector((s * 0.35, -1, 0)), 140, 0.005, j_rot,
          r_end=0.080, part_no="HX01-AR-TH" + x, mass_kg=0.35)
    shell("shin" + x, kn.lerp(an, 0.12), kn.lerp(an, 0.80), 0.070, Vector((s * 0.2, -1, 0)), 140, 0.005, j_knee,
          r_end=0.058, part_no="HX01-AR-SH" + x, mass_kg=0.3)
    shell("hip" + x, V(s * 0.0, 0.0, 0.985), V(s * 0.0, 0.0, 1.11), 0.235, Vector((s, 0.25, 0)), 44, 0.005, pel,
          facets=3, r_end=0.215, part_no="HX01-AR-HP" + x, mass_kg=0.2)
    gh, el, wr = (mirror(P[k], s) for k in ("gh", "elbow", "wrist"))
    j_sa, j_sf, j_sr, j_el, j_wr = ARM[s]
    shell("upper_arm" + x, gh.lerp(el, 0.45), gh.lerp(el, 0.90), 0.070, Vector((s * 0.2, -1, 0)), 130, 0.004, j_sr,
          r_end=0.062, part_no="HX01-AR-UA" + x, mass_kg=0.18)
    shell("forearm" + x, el.lerp(wr, 0.15), el.lerp(wr, 0.80), 0.058, Vector((-s * 0.6, -1, 0.2)), 120, 0.004, j_el,
          r_end=0.047, part_no="HX01-AR-FA" + x, mass_kg=0.15)
    shell("shoulder_cap" + x, gh + V(0, 0, 0.02), gh + V(s * 0.04, 0, -0.07), 0.118, Vector((s * 0.6, -0.1, 1)), 150,
          0.005, j_sf, facets=5, r_end=0.105, part_no="HX01-AR-SC" + x, mass_kg=0.22)

# ============================================================================ maintenance stand (gantry)
st = LAY["stand"]
stand = empty("HLP-kst_stand", Matrix.Translation((0, st["post_y"], 0)), parent=ROOT_E, disp_size=0.1)
block("stand_base", (1.22, 0.62, 0.035), Matrix.Translation((0, st["post_y"], 0.0175)), stand, mat=M["stand"],
      part_no="HX01-GS-001", kind="stand", material="S355 steel, powder coat")
for sx in (1, -1):
    stripe = block(f"stand_stripe{sx}", (0.035, 0.62, 0.037), Matrix.Translation((sx * 0.595, st["post_y"], 0.0185)),
                   stand, mat=M["paint_caution"], kind="stand", bev=0.001)
    block(f"stand_post{sx}", (0.08, 0.08, st["height"]), Matrix.Translation((sx * st["post_x"], st["post_y"],
          st["height"] / 2 + 0.035)), stand, mat=M["stand"], kind="stand", material="S355 box section 80×80×5")
    arm_y0, arm_y1 = st["post_y"], 0.315
    block(f"stand_arm{sx}", (0.06, arm_y0 - arm_y1, 0.07), Matrix.Translation((sx * st["post_x"],
          (arm_y0 + arm_y1) / 2, st["clamp_z"])), stand, mat=M["stand"], kind="stand")
    block(f"stand_clampbar{sx}", (st["post_x"] - 0.29, 0.06, 0.06), Matrix.Translation((sx * (st["post_x"] + 0.29) / 2,
          0.30, st["clamp_z"])), stand, mat=M["stand"], kind="stand")
    pin = mesh_object(f"GEO-kst_clamp_pin{sfx(sx)}", bm_cylinder(0.011, 0.07, 24),
                      matrix=frame((sx * 0.285, 0.30, st["clamp_z"]), (sx, 0, 0)), mat=M["steel"], parent=stand)
    part(pin, kind="clamp_pin", material="17-4PH steel, hydraulic", part_no="HX01-GS-PIN" + sfx(sx))
block("stand_top", (2 * st["post_x"] + 0.08, 0.08, 0.08), Matrix.Translation((0, st["post_y"], st["height"])),
      stand, mat=M["stand"], kind="stand")

# ============================================================================ render set (not exported)
set_collection(COL_RENDER)
floor = mesh_object("GEO-floor", bm_box(14, 14, 0.02, center=(0, 0, -0.01)),
                    mat=__import__("kstlib").material("MAT-floor_concrete", (0.055, 0.055, 0.058), 0.0, 0.62))


def area(name, loc, target, size, energy, color=(1, 1, 1), shape="RECTANGLE", size_y=None):
    d = bpy.data.lights.new(name, "AREA")
    d.shape = shape
    d.size = size
    if size_y:
        d.size_y = size_y
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    from kstlib import link
    link(o)
    o.location = loc
    dirv = Vector(target) - Vector(loc)
    o.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
    return o


area("LGT-key_strip", (-1.9, -2.4, 3.1), (0, 0, 1.2), 0.35, 260, (1.0, 0.96, 0.9), size_y=2.4)
area("LGT-rim_strip", (2.2, 1.9, 2.6), (0, 0.2, 1.3), 0.25, 320, (0.8, 0.88, 1.0), size_y=2.2)
area("LGT-top_strip", (0.0, -0.4, 3.6), (0, 0, 1.0), 0.3, 120, (1, 1, 1), size_y=3.0)
area("LGT-rim_left", (-2.4, 1.6, 2.0), (0, 0.1, 1.2), 0.2, 180, (1.0, 0.92, 0.85), size_y=2.0)
area("LGT-fill", (2.6, -3.0, 1.0), (0, 0, 1.0), 2.0, 18, (0.9, 0.95, 1.0))
world = bpy.data.worlds.new("WLD-kst_hangar")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.0045, 0.005, 1)
bpy.context.scene.world = world

set_collection(COL_CAM)


def camera(name, loc, target, lens=70, ortho=None):
    d = bpy.data.cameras.new(name)
    if ortho:
        d.type = "ORTHO"
        d.ortho_scale = ortho
    else:
        d.lens = lens
    o = bpy.data.objects.new(name, d)
    from kstlib import link
    link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


camera("CAM-front", (0, -6, 1.0), (0, 0, 1.0), ortho=2.35)
camera("CAM-side", (6, 0.2, 1.0), (0, 0.2, 1.0), ortho=2.35)
camera("CAM-34", (2.35, -3.7, 1.45), (0.0, 0.08, 0.98), lens=62)
camera("CAM-hero", (-1.55, -3.05, 1.05), (0.02, 0.05, 1.08), lens=58)

# ============================================================================ checks, manifest, export
bpy.context.view_layer.update()
set_collection(COL)
report = {"stage": STAGE, "objects": 0, "tris": 0, "joints": len(JN), "actuators": 0, "sockets": 0}
manifest = {"asset": "HX-01 KESTREL", "stage": STAGE, "frame": "glTF (x, z, −y) of Blender", "parts": [],
            "joints": [], "sockets": []}
def conv(v):
    if hasattr(v, "to_dict"):
        return v.to_dict()
    if hasattr(v, "to_list"):
        return v.to_list()
    return v


for o in COL.all_objects:
    report["objects"] += 1
    wp = o.matrix_world.translation
    if o.type == "MESH":
        t = tri_count(o)
        report["tris"] += t
        if o.get("kind") == "actuator":
            report["actuators"] += 1
        manifest["parts"].append({"name": o.name, "parent": o.parent.name if o.parent else None, "tris": t,
                                  "pivot": to_gltf(wp), **{k: conv(o[k]) for k in o.keys() if not k.startswith("_")}})
    elif o.name.startswith("HLP-kst_j_"):
        ax = o.matrix_world.to_3x3() @ Vector((0, 0, 1))
        manifest["joints"].append({"name": o.name, "parent": o.parent.name if o.parent else None,
                                   "pivot": to_gltf(wp), "axis_world": to_gltf(ax)})
    elif o.name.startswith("HLP-kst_socket_"):
        report["sockets"] += 1
        manifest["sockets"].append({"name": o.name, "parent": o.parent.name if o.parent else None,
                                    "pivot": to_gltf(wp), **{k: conv(o[k]) for k in o.keys() if not k.startswith("_")}})

# bounding box of the suit (without stand) for the envelope dimensions
mins, maxs = Vector((9, 9, 9)), Vector((-9, -9, -9))
_deps = bpy.context.evaluated_depsgraph_get()
for o in COL.all_objects:
    if o.type != "MESH" or o.get("kind") == "stand" or o.name.startswith("GEO-kst_stand") or "clamp_pin" in o.name:
        continue
    ev = o.evaluated_get(_deps)
    me = ev.to_mesh()
    mw = o.matrix_world
    for vtx in me.vertices:
        w = mw @ vtx.co
        mins = Vector(map(min, mins, w))
        maxs = Vector(map(max, maxs, w))
    ev.to_mesh_clear()
env = maxs - mins
report["envelope_mm"] = {"width_x": round(env.x * 1000), "depth_y": round(env.y * 1000), "height_z": round(maxs.z * 1000)}
report["actuator_count_check"] = report["actuators"] == 24
manifest["report"] = report
print("REPORT", json.dumps(report))

os.makedirs(os.path.join(ROOT, "public", "assets"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "kestrel.blend"))
if EXPORT:
    lc = bpy.context.view_layer.layer_collection.children["CH-kst"]
    bpy.context.view_layer.active_layer_collection = lc
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "public", "assets", "kestrel.glb"), export_format="GLB",
                              use_active_collection=True, use_active_collection_with_nested=True,
                              export_apply=True, export_extras=True, export_yup=True, export_cameras=False,
                              export_lights=False, export_tangents=True, export_draco_mesh_compression_enable=False)
    with open(os.path.join(ROOT, "public", "assets", "kestrel_manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
print("DONE")
