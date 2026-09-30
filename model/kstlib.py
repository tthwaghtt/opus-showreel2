"""HX-01 KESTREL — Blender helper library (bpy 5.2.1).

Conventions (BLENDER_METHOD.md, CONTRACT.md):
  * metres, Z up, suit faces −Y, +X = suit LEFT (.L)
  * object names  GEO-kst_* (mesh), HLP-kst_* (empties: joints, sockets), MAT-kst_* (materials)
  * joint empties: origin on the joint axis, local +Z = rotation axis (→ glTF local +Y)
  * every part carries custom props (exported as glTF extras): part_no, material, mass_kg, ...
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion

# ------------------------------------------------------------------ scene / collections

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


_ACTIVE = {"col": None}


def set_collection(col):
    _ACTIVE["col"] = col


def link(obj):
    (_ACTIVE["col"] or bpy.context.scene.collection).objects.link(obj)
    return obj


# ------------------------------------------------------------------ math helpers

def V(*a):
    if len(a) == 1:
        return Vector(a[0])
    return Vector(a)


def mirror(v, s):
    """mirror a LEFT-side vector to side s (+1 left, −1 right)"""
    v = Vector(v)
    return Vector((v.x * s, v.y, v.z))


def basis_z(axis, up_hint=(0, 0, 1)):
    """rotation matrix whose local Z = axis"""
    z = Vector(axis).normalized()
    hint = Vector(up_hint)
    if abs(z.dot(hint.normalized())) > 0.95:
        hint = Vector((0, 1, 0)) if abs(z.y) < 0.9 else Vector((1, 0, 0))
    x = hint.cross(z).normalized()
    y = z.cross(x).normalized()
    m = Matrix((x, y, z)).transposed()
    return m.to_4x4()


def frame(loc, axis=(0, 0, 1), up_hint=(0, 0, 1)):
    m = basis_z(axis, up_hint)
    m.translation = Vector(loc)
    return m


# ------------------------------------------------------------------ object creation

def mesh_object(name, bm, matrix=None, mat=None, parent=None, smooth=True, sharp_angle=30.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    link(obj)
    if mat is not None:
        mats = mat if isinstance(mat, (list, tuple)) else [mat]
        for m in mats:
            me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
        try:
            me.set_sharp_from_angle(angle=math.radians(sharp_angle))
        except Exception:
            pass
    if matrix is not None:
        obj.matrix_world = matrix
    if parent is not None:
        parent_keep(obj, parent)
    return obj


def empty(name, matrix, parent=None, disp_size=0.05, disp_kind="ARROWS", **props):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = disp_kind
    obj.empty_display_size = disp_size
    link(obj)
    obj.matrix_world = matrix
    if parent is not None:
        parent_keep(obj, parent)
    for k, v in props.items():
        obj[k] = v
    return obj


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    child.matrix_world = mw


def props(obj, **kw):
    for k, v in kw.items():
        obj[k] = v
    return obj


# ------------------------------------------------------------------ modifiers

def bevel(obj, width=0.0015, segments=2, angle=30.0, profile=0.5, clamp=True, harden=False):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.profile = profile
    m.use_clamp_overlap = clamp
    m.harden_normals = harden
    return m


def weighted_normal(obj):
    m = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    m.keep_sharp = True
    m.weight = 50
    return m


def subsurf(obj, levels=2, render=None):
    m = obj.modifiers.new("Subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = render if render is not None else levels
    return m


def solidify(obj, t, offset=-1.0):
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = t
    m.offset = offset
    m.use_even_offset = True
    return m


def hard_surface(obj, width=0.0015, segments=2, angle=30.0):
    bevel(obj, width=width, segments=segments, angle=angle)
    weighted_normal(obj)
    return obj


# ------------------------------------------------------------------ bmesh primitives (built around the origin)

def bm_cylinder(r, depth, segments=48, r2=None, caps=True, z0=None):
    """cylinder/cone along local Z; by default centred on the origin"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segments,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth,
                          calc_uvs=True)
    if z0 is not None:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, z0 + depth / 2))
    return bm


def bm_box(sx, sy, sz, center=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=center)
    return bm


def bm_uvsphere(r, u=48, v=24, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r, calc_uvs=True)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    return bm


def bm_lathe(profile, segments=64, angle=2 * math.pi):
    """profile: list of (r, z) from bottom to top, revolved around local Z"""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    closed = abs(angle - 2 * math.pi) < 1e-6
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=angle, steps=segments, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_torus(R, r, seg=64, ring=16, arc=2 * math.pi, rect=None):
    """torus in the XY plane around Z. rect=(w, h) gives a rectangular cross-section."""
    if rect:
        w, h = rect
        prof = [(R - w / 2, -h / 2), (R + w / 2, -h / 2), (R + w / 2, h / 2), (R - w / 2, h / 2), (R - w / 2, -h / 2)]
    else:
        prof = [(R + r * math.cos(a), r * math.sin(a))
                for a in [2 * math.pi * i / ring for i in range(ring + 1)]]
    return bm_lathe(prof, segments=seg, angle=arc)


def bm_tube_between(p0, p1, r, segments=24, r1=None):
    """solid round bar from p0 to p1 (world coords baked in)"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bm_cylinder(r, d.length, segments=segments, r2=r1)
    m = basis_z(d)
    m.translation = (p0 + p1) / 2
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm


def bm_extrude_outline(pts, thickness, center_z=0.0):
    """closed 2D outline (XY) extruded along Z"""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, center_z - thickness / 2)) for x, y in pts]
    f = bm.faces.new(vs)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, thickness))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_merge(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_tmp")
        b.to_mesh(me)
        b.free()
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
    return out


def bm_transform(bm, matrix):
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    return bm


# ------------------------------------------------------------------ skin-modifier bodies (pilot mannequin)

def skin_object(name, verts, edges, radii, mat=None, parent=None, root=0, sub_levels=2, matrix=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    obj = bpy.data.objects.new(name, me)
    link(obj)
    sk = obj.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sv = me.skin_vertices[0].data
    for i, r in enumerate(radii):
        sv[i].radius = r if isinstance(r, (tuple, list)) else (r, r)
    sv[root].use_root = True
    subsurf(obj, sub_levels)
    if mat is not None:
        me.materials.append(mat)
    if matrix is not None:
        obj.matrix_world = matrix
    if parent is not None:
        parent_keep(obj, parent)
    for p in me.polygons:
        p.use_smooth = True
    return obj


# ------------------------------------------------------------------ materials

def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip("#")
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def material(name, base, metallic=0.0, rough=0.5, coat=0.0, coat_rough=0.05, emission=None,
             emission_strength=0.0, transmission=0.0, aniso=0.0, viewport=None, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    col = tuple(base) + (1.0,)
    p.inputs["Base Color"].default_value = col
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = coat_rough
    if emission is not None:
        p.inputs["Emission Color"].default_value = tuple(emission) + (1.0,)
        p.inputs["Emission Strength"].default_value = emission_strength
    if transmission:
        p.inputs["Transmission Weight"].default_value = transmission
    if aniso:
        p.inputs["Anisotropic"].default_value = aniso
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
    # viewport / workbench display
    vc = viewport or base
    m.diffuse_color = tuple(vc) + (1.0,)
    m.metallic = min(metallic, 0.25)   # workbench/clay review only (render uses the node tree)
    m.roughness = max(rough, 0.35)
    return m


def make_materials():
    """Physically based base colours (linear sRGB) from physicallybased.info where applicable."""
    M = {}
    ti = (0.441, 0.400, 0.361)
    M["ti_blast"] = material("MAT-kst_ti_blast", ti, 1.0, 0.46, viewport=(0.52, 0.52, 0.50))
    M["ti_machined"] = material("MAT-kst_ti_machined", tuple(c * 1.08 for c in ti), 1.0, 0.24, aniso=0.5, viewport=(0.66, 0.66, 0.64))
    M["al_dark"] = material("MAT-kst_al_anodized_dark", (0.018, 0.019, 0.021), 1.0, 0.36, viewport=(0.15, 0.16, 0.18))
    M["al_bare"] = material("MAT-kst_al_bare", (0.916, 0.923, 0.924), 1.0, 0.30, viewport=(0.62, 0.63, 0.64))
    M["inconel"] = material("MAT-kst_inconel", (0.697, 0.641, 0.563), 1.0, 0.34, viewport=(0.56, 0.52, 0.46))
    M["steel"] = material("MAT-kst_steel", (0.669, 0.639, 0.598), 1.0, 0.28, viewport=(0.58, 0.57, 0.55))
    M["steel_dark"] = material("MAT-kst_steel_dark", (0.10, 0.10, 0.105), 1.0, 0.38)
    M["copper"] = material("MAT-kst_copper", (0.932, 0.623, 0.522), 1.0, 0.30)
    M["cfrp"] = material("MAT-kst_cfrp", (0.016, 0.017, 0.019), 0.0, 0.30, coat=1.0, coat_rough=0.06, viewport=(0.085, 0.09, 0.10))
    M["fabric"] = material("MAT-kst_fabric_aramid", hex_lin("2b3036"), 0.0, 0.92, viewport=(0.30, 0.31, 0.29))
    M["fabric_dark"] = material("MAT-kst_fabric_webbing", hex_lin("16181b"), 0.0, 0.85)
    M["rubber"] = material("MAT-kst_rubber", (0.012, 0.012, 0.013), 0.0, 0.78)
    M["visor"] = material("MAT-kst_visor", (0.004, 0.005, 0.006), 0.0, 0.04, coat=1.0, coat_rough=0.02, viewport=(0.02, 0.025, 0.03))
    M["glass"] = material("MAT-kst_glass", (0.9, 0.92, 0.95), 0.0, 0.02, transmission=1.0, alpha=0.3)
    M["paint_caution"] = material("MAT-kst_paint_caution", hex_lin("e8c14a"), 0.0, 0.5)
    M["stand"] = material("MAT-kst_stand_paint", hex_lin("2b2f35"), 0.0, 0.55, viewport=(0.12, 0.13, 0.14))
    M["led"] = material("MAT-kst_led", (0.02, 0.2, 0.3), 0.0, 0.3, emission=hex_lin("5cc8ee"), emission_strength=6.0)
    return M


# ------------------------------------------------------------------ bookkeeping

def tri_count(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    try:
        me = ev.to_mesh()
    except RuntimeError:
        return 0
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def to_gltf(v):
    """Blender (x, y, z) → glTF (x, z, −y)"""
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]
