"""HX-01 KESTREL v2.1 concept sketch (exterior + interior). Reads calc/specs.json layout.
Run: python3 sketches/sketch_v21.py  -> sketches/kestrel_sketch_v2.1.png (needs playwright chromium)."""
import json, math, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(f"{R}/calc/specs.json")); L = S["layout"]; J = L["pilot"]; X = L["exo"]
BG, LN, LN2, F1, F2, GUN = "#0A0C0F", "#E3E6E9", "#8B939D", "#171A1F", "#20242B", "#2B3038"
GOLD, PLAT, BRZ, VIO, CY, OR, PH = "#C9A13E", "#CFCBC2", "#A9773F", "#B7A6FF", "#5CC8EE", "#FF6A1A", "#6F7782"
K, PW, PH_ = 300, 470, 700          # px per metre, panel width, panel height
out = []


def spl(pts, closed=True):
    """Catmull-Rom through pts -> cubic Bezier path string (already in px)."""
    n = len(pts); P = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0, p1, p2, p3 = (P[i - 1] if (closed or i) else P[0]), P[i], P[i + 1], P[i + 2]
        if closed: p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        else: p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d + (" Z" if closed else "")


class V:  # one view panel
    def __init__(s, x0, y0, cx, g, k=K): s.x0, s.y0, s.cx, s.g, s.k = x0, y0, cx, g, k
    def p(s, u, z): return (s.x0 + s.cx + u * s.k, s.y0 + s.g - z * s.k)
    def shape(s, pts, fill=F1, stroke=LN, sw=1.3, mirror=False, closed=True, extra=""):
        for m in ((1, -1) if mirror else (1,)):
            q = [s.p(m * u, z) for u, z in pts]
            f = fill if closed else "none"
            out.append(f'<path d="{spl(q, closed)}" fill="{f}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" {extra}/>')
    def sym(s, half, **kw):  # half outline from centre top to centre bottom (u>=0) -> full symmetric shape
        full = half + [(-u, z) for u, z in reversed(half[1:-1])]
        s.shape(full, **kw)
    def line(s, a, b, col=LN, sw=1, mirror=False, dash=""):
        for m in ((1, -1) if mirror else (1,)):
            A, B = s.p(m * a[0], a[1]), s.p(m * b[0], b[1])
            out.append(f'<line x1="{A[0]:.1f}" y1="{A[1]:.1f}" x2="{B[0]:.1f}" y2="{B[1]:.1f}" stroke="{col}" stroke-width="{sw}" '
                       f'stroke-linecap="round" {"stroke-dasharray=%s" % chr(34) + dash + chr(34) if dash else ""}/>')
    def poly(s, pts, fill=F1, stroke=LN, sw=1.2, mirror=False, extra=""):
        for m in ((1, -1) if mirror else (1,)):
            q = " ".join(f"{s.p(m * u, z)[0]:.1f},{s.p(m * u, z)[1]:.1f}" for u, z in pts)
            out.append(f'<polygon points="{q}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" {extra}/>')
    def ell(s, u, z, ru, rz, col=GOLD, fill="#241f15", sw=2.2, mirror=False, rot=0):
        for m in ((1, -1) if mirror else (1,)):
            c = s.p(m * u, z)
            out.append(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{ru * s.k:.1f}" ry="{rz * s.k:.1f}" fill="{fill}" stroke="{col}" '
                       f'stroke-width="{sw}" transform="rotate({m * rot:.1f} {c[0]:.1f} {c[1]:.1f})"/>')
    def ring(s, u, z, r, mirror=False):  # concentric pair: gunmetal inner + gold outer
        s.ell(u, z, r, r, GOLD, "#241f15", 2.4, mirror); s.ell(u, z, r * 0.72, r * 0.72, "#59606A", GUN, 1.2, mirror)
    def edge_ring(s, u, z, r, mirror=True, rot=0):  # ring seen edge-on (axis in the view plane)
        s.ell(u, z, 0.011, r, GOLD, "#241f15", 2.2, mirror, rot)
    def txt(s, u, z, t, size=10, col=LN2, anchor="start", ko=False):
        c = s.p(u, z); fam = "IBM Plex Sans KR" if ko else "IBM Plex Mono"
        out.append(f'<text x="{c[0]:.1f}" y="{c[1]:.1f}" fill="{col}" font-family="{fam}" font-size="{size}" text-anchor="{anchor}">{t}</text>')
    def note(s, a, b, t, col=LN2):  # leader line a -> b, Korean label at b
        s.line(a, b, "#4A525C", 0.8); s.txt(b[0] + (0.008 if b[0] >= a[0] else -0.008), b[1] - 0.004, t, 10.5, col,
                                             "start" if b[0] >= a[0] else "end", True)


def limb(v, p0, p1, w, mirror=True, fill=F1):
    """smooth limb shell from p0 to p1 with half-widths w = (start, bulge, end)."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]; Ln = math.hypot(dx, dz); nx, nz = dz / Ln, -dx / Ln
    ts, ws = (0, 0.38, 1), w
    a = [(p0[0] + dx * t + nx * ww, p0[1] + dz * t + nz * ww) for t, ww in zip(ts, ws)]
    b = [(p0[0] + dx * t - nx * ww, p0[1] + dz * t - nz * ww) for t, ww in zip(ts, ws)]
    v.shape(a + b[::-1], fill=fill, mirror=mirror)


def panel(i, row, title, sub):
    x0, y0 = i * PW, row * PH_
    out.append(f'<rect x="{x0 + 8}" y="{y0 + 8}" width="{PW - 16}" height="{PH_ - 16}" fill="none" stroke="#262C35"/>')
    out.append(f'<text x="{x0 + 22}" y="{y0 + 32}" fill="{LN}" font-family="IBM Plex Mono" font-size="12" letter-spacing="1.5">{title}</text>')
    out.append(f'<text x="{x0 + 22}" y="{y0 + 50}" fill="{LN2}" font-family="IBM Plex Sans KR" font-size="11">{sub}</text>')
    return x0, y0


# ---------------------------------------------------------------- shared outlines (front/back, u = x)
HELM = [(0, 1.862), (0.07, 1.848), (0.108, 1.80), (0.118, 1.745), (0.112, 1.685), (0.098, 1.635), (0.07, 1.598), (0.03, 1.574), (0, 1.568)]
NECK = [(0, 1.60), (0.088, 1.60), (0.082, 1.552), (0.05, 1.51), (0, 1.495)]
TORSO = [(0, 1.497), (0.07, 1.512), (0.14, 1.528), (0.195, 1.505), (0.214, 1.43), (0.21, 1.35), (0.2, 1.27), (0.178, 1.19),
         (0.166, 1.13), (0.172, 1.085), (0.08, 1.07), (0, 1.066)]
PELV = [(0, 1.096), (0.16, 1.10), (0.228, 1.06), (0.258, 0.995), (0.245, 0.925), (0.16, 0.89), (0.06, 0.862), (0, 0.852)]
THIGH = [(0.035, 0.875), (0.16, 0.915), (0.262, 0.935), (0.268, 0.83), (0.242, 0.70), (0.214, 0.615), (0.15, 0.598), (0.083, 0.606),
         (0.058, 0.69), (0.042, 0.79)]
SHIN = [(0.05, 0.512), (0.15, 0.522), (0.206, 0.50), (0.212, 0.42), (0.19, 0.30), (0.166, 0.185), (0.156, 0.135), (0.10, 0.126),
        (0.064, 0.14), (0.05, 0.25), (0.044, 0.40)]
FOOT = [(0.035, 0.0), (0.168, 0.0), (0.17, 0.05), (0.15, 0.092), (0.10, 0.102), (0.05, 0.09), (0.035, 0.05)]
DELT = [(0.168, 1.535), (0.25, 1.548), (0.312, 1.505), (0.328, 1.43), (0.302, 1.368), (0.24, 1.352), (0.188, 1.39)]
KNEECAP = [(0.1, 0.632), (0.142, 0.61), (0.15, 0.56), (0.13, 0.505), (0.1, 0.492), (0.07, 0.505), (0.05, 0.56), (0.058, 0.61)]
fa = L["forearm_dir"]; tip = (J["wrist"][0] + 0.19 * fa[0], J["wrist"][2] + 0.19 * fa[2])


def body(v, back=False):
    v.ell(0, 1.5999, 0.119, 0.044, GOLD, "#241f15", 2.6)                       # atlas ring (22° tilt -> ellipse)
    v.sym(NECK, fill=F2)
    for leg in (THIGH, SHIN, FOOT): v.shape(leg, mirror=True)
    v.sym(PELV)
    v.sym(TORSO)
    limb(v, (0.19, 1.43), (0.238, 1.18), (0.06, 0.068, 0.056))                # upper arm
    limb(v, (0.238, 1.18), (J["wrist"][0], J["wrist"][2]), (0.062, 0.06, 0.044))  # forearm
    limb(v, (J["wrist"][0], J["wrist"][2]), tip, (0.03, 0.034, 0.02), fill=F2)  # gauntlet (edge view)
    v.shape(DELT, mirror=True)
    v.sym(HELM, fill=F1)
    # rotation rings = gold (front/back view: lateral axes seen edge-on)
    v.edge_ring(0.33, 1.45, 0.0675); v.edge_ring(0.352, 1.193, 0.0675, rot=12)
    v.edge_ring(0.262, 0.992, 0.0675); v.edge_ring(0.216, 0.555, 0.0675); v.edge_ring(0.163, 0.114, 0.04)
    v.ell(0.205, 1.333, 0.072, 0.014, mirror=True, rot=-12); v.ell(J["wrist"][0], J["wrist"][2], 0.05, 0.011, mirror=True, rot=-12)
    v.ell(0.215, 0.817, 0.05, 0.011, mirror=True)
    if not back:
        v.shape(KNEECAP, fill=F2, mirror=True)
        v.line((0.1, 0.63), (0.1, 0.495), "#59606A", 1, True)
        for a, b in (((0.03, 1.455), (0.178, 1.416)), ((0.026, 1.205), (0.152, 1.222)), ((0.03, 1.138), (0.148, 1.146)),
                     ((0.06, 0.80), (0.205, 0.84)), ((0.07, 0.30), (0.17, 0.33))):
            v.line(a, b, "#59606A", 1, True)
        v.shape([(0.022, 1.272), (0.10, 1.29), (0.196, 1.345)], closed=False, fill="none", stroke="#6A727D", sw=1.1, mirror=True)
        for a, b in (((0.143, 0.86), (0.152, 0.64)), ((0.106, 0.47), (0.111, 0.17))):
            v.line(a, b, PLAT, 1.6, True)
        # keel: spindle ridge + faint violet line
        v.sym([(0, 1.486), (0.013, 1.45), (0.023, 1.357), (0.013, 1.26), (0, 1.228)], fill="#2E3238", stroke=PLAT, sw=1.6)
        c1, c2 = v.p(0, 1.425), v.p(0, 1.29)
        out.append(f'<line x1="{c1[0]}" y1="{c1[1]}" x2="{c2[0]}" y2="{c2[1]}" stroke="{VIO}" stroke-width="5" opacity="0.25" filter="url(#glow)"/>')
        out.append(f'<line x1="{c1[0]}" y1="{c1[1]}" x2="{c2[0]}" y2="{c2[1]}" stroke="{VIO}" stroke-width="1.4"/>')
        # helmet face: brow fold (same surface), 15° eyes, cameras, cheek grooves, face keel
        v.line((0, 1.862), (0, 1.568), PLAT, 1.5)
        v.shape([(0.004, 1.776), (0.06, 1.782), (0.113, 1.792)], closed=False, fill="none", stroke=PLAT, sw=1.3, mirror=True)
        eye = [(0.016, 1.738), (0.101, 1.761), (0.097, 1.749), (0.022, 1.727)]
        v.poly(eye, "#050607", LN, 1, True)
        for u, z in ((0.035, 1.735), (0.088, 1.753)): v.ell(u, z, 0.006, 0.004, GOLD, "none", 0.9, True)
        v.line((0.07, 1.722), (0.074, 1.655), "#59606A", 1.6, True)
        v.line((0.085, 1.598), (0.026, 1.506), "#59606A", 1.2, True)          # SCM bands
    else:
        rad = L["back_radiators"]["outline_xz"]
        v.poly(rad, "#1d1f22", LN, 1.3, True)
        for u, z in L["back_radiators"]["fans_xz"]: v.ell(u, z, 0.04, 0.04, "#4A525C", "none", 1, True)
        for i in range(7):
            z = 1.205 + i * 0.024; v.line((0.045, z), (0.115, z + 0.01), BRZ, 1.4, True)
        v.ring(0.175, 1.4504, 0.0675, mirror=True)                               # shoulder abduction rings (axis fore-aft)
        v.line((0, 1.50), (0, 1.16), PLAT, 1.6)                                  # spine strip
        v.poly([(-0.069, 1.152), (0.069, 1.152), (0.069, 1.132), (-0.069, 1.132)], "#241f15", GOLD, 2)   # trunk arc rail
        v.poly([(-0.052, 1.118), (0.052, 1.118), (0.052, 1.066), (-0.052, 1.066)], GUN, "#59606A", 1)
        v.shape([(0.02, 1.0), (0.12, 1.02), (0.22, 0.97)], closed=False, fill="none", stroke="#6A727D", sw=1.1, mirror=True)
        v.poly([(0.135, 0.475), (0.195, 0.475), (0.195, 0.34), (0.135, 0.34)], GUN, "#59606A", 1, True)   # ankle pitch L
        v.line((0.165, 0.34), (0.15, 0.13), PLAT, 1.8, True)                    # Achilles push rods
        v.ring(0.09, 0.085, 0.052, mirror=True)                                  # ankle roll (axis fore-aft)
        v.line((0, 1.862), (0, 1.62), PLAT, 1.3)


def side(v):
    Y = lambda pts: [(y, z) for y, z in pts]
    v.shape(Y([(-0.17, 0), (0.125, 0), (0.13, 0.06), (0.08, 0.102), (-0.05, 0.104), (-0.15, 0.062)]), fill=F2)
    v.shape(Y([(-0.082, 0.505), (-0.097, 0.40), (-0.072, 0.20), (-0.056, 0.135), (0.05, 0.128), (0.095, 0.25), (0.142, 0.40), (0.12, 0.495)]))
    v.ring(0.06, 0.4078, 0.0675); v.line((0.12, 0.408), (0.06, 0.114), PLAT, 2)
    v.shape(Y([(-0.112, 0.925), (-0.142, 0.80), (-0.122, 0.66), (-0.088, 0.598), (0.088, 0.598), (0.105, 0.70), (0.142, 0.85), (0.15, 0.93)]))
    v.line((-0.045, 0.64), (-0.035, 0.86), PLAT, 2)                             # damper rod (lateral)
    v.shape(Y([(-0.112, 0.63), (-0.07, 0.62), (-0.062, 0.50), (-0.105, 0.49)]), fill=F2)
    v.ring(0.005, 0.5548, 0.0675); v.ring(0.0, 0.114, 0.04)
    v.shape(Y([(-0.152, 1.10), (-0.162, 1.0), (-0.122, 0.93), (0.0, 0.885), (0.16, 0.905), (0.215, 0.98), (0.245, 1.07), (0.205, 1.115)]))
    v.ring(0.0, 0.992, 0.0675)
    v.shape(Y([(-0.122, 1.50), (-0.172, 1.47), (-0.19, 1.38), (-0.185, 1.28), (-0.17, 1.2), (-0.165, 1.12), (-0.15, 1.075), (0.06, 1.065),
               (0.175, 1.075), (0.232, 1.13), (0.226, 1.30), (0.22, 1.45), (0.172, 1.53), (0.10, 1.55)]))
    v.poly([(-0.18, 1.482), (-0.233, 1.40), (-0.233, 1.31), (-0.18, 1.232)], "#2E3238", PLAT, 1.6)
    v.line((-0.234, 1.42), (-0.234, 1.29), VIO, 1.4)
    v.poly([(0.195, 1.50), (0.22, 1.50), (0.22, 1.16), (0.195, 1.16)], "#1d1f22", LN, 1.1)
    for i in range(6): z = 1.2 + i * 0.05; v.line((0.222, z), (0.232, z - 0.012), BRZ, 1.4)
    v.poly([(0.14, 1.154), (0.168, 1.154), (0.168, 1.13), (0.14, 1.13)], "#241f15", GOLD, 2)
    v.shape(Y([(-0.1, 1.565), (-0.12, 1.50), (-0.05, 1.49), (0.09, 1.53), (0.125, 1.56), (0.112, 1.64), (0.0, 1.605)]), fill=F2)
    a, b = v.p(-0.090, 1.5595), v.p(0.110, 1.640)
    out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{GOLD}" stroke-width="5" stroke-linecap="round"/>')
    v.shape(Y([(-0.128, 1.70), (-0.116, 1.78), (-0.07, 1.845), (0.02, 1.866), (0.10, 1.842), (0.145, 1.77), (0.142, 1.69), (0.112, 1.645),
               (0.03, 1.622), (-0.05, 1.585), (-0.1, 1.582), (-0.132, 1.63)]))
    v.poly([(-0.124, 1.745), (-0.035, 1.766), (-0.042, 1.753), (-0.12, 1.733)], "#050607", LN, 1)
    v.shape([(-0.132, 1.768), (-0.08, 1.775), (-0.02, 1.792), (0.05, 1.82)], closed=False, fill="none", stroke=PLAT, sw=1.2)
    limb(v, (0.02, 1.45), (0.02, 1.18), (0.058, 0.066, 0.055), mirror=False)
    limb(v, (0.02, 1.18), (J["wrist"][1], J["wrist"][2]), (0.058, 0.056, 0.042), mirror=False)
    limb(v, (J["wrist"][1], J["wrist"][2]), (J["wrist"][1] + 0.19 * fa[1], tip[1]), (0.036, 0.04, 0.026), mirror=False, fill=F2)
    v.ring(0.02, 1.4504, 0.0675); v.ring(0.02, 1.187, 0.06)


def phantom(v):  # pilot, ISO 128 two-point chain line
    d = 'stroke-dasharray="9 3 1.5 3 1.5 3"'
    v.shape([(0, 1.815), (0.06, 1.79), (0.078, 1.71), (0.06, 1.63), (0.04, 1.60), (0.045, 1.53), (0.16, 1.50), (0.2, 1.43), (0.215, 1.25),
             (0.27, 0.93), (0.25, 0.92), (0.19, 1.2), (0.155, 1.15), (0.17, 1.0), (0.14, 0.62), (0.125, 0.15), (0.13, 0.06), (0.04, 0.06),
             (0.06, 0.6), (0.02, 0.9), (0, 0.92)], fill="none", stroke=PH, sw=1, mirror=True, extra=d)


svg = ['<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>',
       f'<rect width="100%" height="100%" fill="{BG}"/>']
# ---------------- row 1: exterior
x0, y0 = panel(0, 0, "SK-01  FRONT", "외부 정면 · 곡면 근육 + 곧은 패널선 · 금색 링 = 회전축")
v = V(x0, y0, PW / 2, PH_ - 40); body(v)
v.note((0.0, 1.36), (0.25, 1.62), "용골 + 보랏빛 선 (KEEL CORE)"); v.note((0.0, 1.55), (-0.2, 1.66), "보이는 목 67 mm")
x0, y0 = panel(1, 0, "SK-02  SIDE", "외부 측면 · 앞이 왼쪽 · 용골 118 mm 돌출, 등 방열판 25 mm")
v = V(x0, y0, PW / 2 + 10, PH_ - 40); side(v)
v.note((-0.233, 1.36), (-0.36, 1.25), "가슴 용골"); v.note((0.21, 1.33), (0.3, 1.22), "방열판 (딸깍 결합)")
v.note((0.01, 1.6), (0.22, 1.72), "아틀라스 링 22°"); v.note((0.09, 0.26), (0.22, 0.2), "아킬레스 푸시로드")
x0, y0 = panel(2, 0, "SK-03  BACK", "외부 후면 · 방열판이 어깨 링을 피해 동심 호로 깎임")
v = V(x0, y0, PW / 2, PH_ - 40); body(v, back=True)
v.note((0.09, 1.3), (0.25, 1.62), "팬 80 mm × 2 / 판"); v.note((0.0, 1.142), (-0.26, 1.06), "허리 곡선 레일 ±35°")
x0, y0 = panel(3, 0, "SK-04  HELMET", "헬멧 정면 3배 · 눈 윗변 15°, 눈썹뼈는 셸과 한 몸")
v = V(x0, y0, PW / 2, 1.72 * 900 + 360, 900)
v.ell(0, 1.5999, 0.119, 0.044, GOLD, "#241f15", 3); v.sym(NECK, fill=F2); v.sym(HELM)
v.line((0, 1.862), (0, 1.568), PLAT, 2)
v.shape([(0.004, 1.776), (0.06, 1.782), (0.113, 1.792)], closed=False, fill="none", stroke=PLAT, sw=1.8, mirror=True)
v.poly([(0.016, 1.738), (0.101, 1.761), (0.097, 1.749), (0.022, 1.727)], "#050607", LN, 1.4, True)
for u, z in ((0.035, 1.735), (0.088, 1.753)): v.ell(u, z, 0.0065, 0.0045, GOLD, "none", 1.2, True)
v.line((0.07, 1.722), (0.074, 1.655), "#59606A", 2.4, True); v.line((0.085, 1.598), (0.026, 1.506), "#59606A", 1.6, True)
v.line((0.016, 1.738), (0.13, 1.738), CY, 0.8, dash="3 3"); v.txt(0.135, 1.741, "15°", 12, CY)
v.note((0.06, 1.783), (0.125, 1.84), "눈썹뼈 = 셸 일체"); v.note((0.088, 1.753), (0.125, 1.70), "카메라 2 / 눈")
v.note((0.072, 1.69), (0.125, 1.64), "배수 홈"); v.note((0.0, 1.57), (-0.16, 1.55), "입 슬릿 없음")
# ---------------- row 2: interior
x0, y0 = panel(0, 1, "SK-05  INTERNAL X-RAY", "내부 기계층 정면 투시 · 액추에이터 24개 (계산 시트 좌표)")
v = V(x0, y0, PW / 2, PH_ - 40); phantom(v)
hf, kn, an = X["hip_flex"]["c"], X["knee"]["c"], X["ankle_pitch"]["joint"]
for a, b in (((hf[0], hf[2]), (kn[0], kn[2])), ((kn[0], kn[2]), (an[0], an[2])), ((0.275, 1.45), (0.318, 1.187)),
             ((0.318, 1.187), (J["wrist"][0], J["wrist"][2])), ((0.12, 1.06), (0.22, 0.992))):
    v.line(a, b, "#9AA3AD", 4, True)
v.line((0, 1.06), (0, 1.54), "#3B4250", 6); v.line((-0.17, 1.06), (0.17, 1.06), "#3B4250", 6)
sz = {k: (c["od_mm"] / 2000, c["width_mm"] / 2000) for k, c in S["actuator_classes"].items()}
for name, a in X.items():
    r, w = sz[a["cls"]]; c = a["c"]; ax = a["axis"]
    mir = a.get("side") != "C"
    if isinstance(ax, list) and abs(ax[1]) > 0.9: v.ring(c[0], c[2], r, mirror=mir)
    elif isinstance(ax, list) and abs(ax[0]) > 0.85: v.poly([(c[0] - w, c[2] + r), (c[0] + w, c[2] + r), (c[0] + w, c[2] - r), (c[0] - w, c[2] - r)], GUN, GOLD, 1.4, mir)
    else: v.poly([(c[0] - r, c[2] + w), (c[0] + r, c[2] + w), (c[0] + r, c[2] - w), (c[0] - r, c[2] - w)], GUN, GOLD, 1.4, mir)
kc = L["keel_core"]["c"]
v.sym([(0, kc[2] + 0.125), (0.02, kc[2] + 0.07), (0.038, kc[2]), (0.02, kc[2] - 0.07), (0, kc[2] - 0.125)], fill="#1b1a26", stroke=VIO, sw=1.4)
v.line((0, kc[2] + 0.08), (0, kc[2] - 0.08), VIO, 2)
v.poly([(-0.09, 1.245), (0.09, 1.245), (0.09, 1.16), (-0.09, 1.16)], "#2a1a10", OR, 1.1)
v.poly([(0.10, 1.10), (0.16, 1.10), (0.16, 1.045), (0.10, 1.045)], "#14202a", CY, 1.1, True)
v.poly([(-0.05, 1.40), (0.05, 1.40), (0.05, 1.26), (-0.05, 1.26)], "none", "#59606A", 1, extra='stroke-dasharray="4 3"')
v.note((0.0, 1.30), (0.25, 1.62), "KEEL CORE Ø76 × 250"); v.note((0.07, 1.2), (0.3, 1.25), "왁스 열 버퍼 (배)")
v.note((0.13, 1.07), (0.32, 1.06), "커패시터 25 Wh × 좌우"); v.note((-0.04, 1.38), (-0.25, 1.45), "냉각기 (등 쪽, 뒤에 숨음)")
v.note((-0.18, 0.555), (-0.32, 0.62), "L급 Ø135 (금 테두리)")
x0, y0 = panel(1, 1, "SK-06  SECTION A-A", "중심 단면 · 세 겹 (조종사 / 내부 / 장갑) · 열의 흐름")
v = V(x0, y0, PW / 2 + 10, PH_ - 40)
v.shape([(-0.122, 1.50), (-0.172, 1.47), (-0.19, 1.38), (-0.185, 1.28), (-0.17, 1.2), (-0.165, 1.12), (-0.15, 1.075), (0.06, 1.065),
         (0.175, 1.075), (0.232, 1.13), (0.226, 1.30), (0.22, 1.45), (0.172, 1.53), (0.10, 1.55)], fill="#121418", stroke=LN, sw=1.2)
v.shape([(0, 1.815), (-0.09, 1.72), (-0.07, 1.60), (-0.115, 1.48), (-0.12, 1.30), (-0.1, 1.12), (-0.11, 0.95), (0.12, 0.93), (0.1, 1.12),
         (0.115, 1.35), (0.07, 1.55), (0.08, 1.70)], fill="none", stroke=PH, sw=1, extra='stroke-dasharray="9 3 1.5 3 1.5 3"')
kc = L["keel_core"]; y_c, z_c = kc["c"][1], kc["c"][2]
v.shape([(y_c, z_c + 0.125), (y_c - 0.022, z_c + 0.07), (y_c - 0.038, z_c), (y_c - 0.022, z_c - 0.07), (y_c, z_c - 0.125), (y_c + 0.022, z_c - 0.07),
         (y_c + 0.038, z_c), (y_c + 0.022, z_c + 0.07)], fill="#1b1a26", stroke=VIO, sw=1.3)
v.poly([(-0.145, 1.47), (-0.12, 1.47), (-0.12, 1.24), (-0.145, 1.24)], "#30343c", "#8B939D", 1)
v.poly([(-0.18, 1.482), (-0.233, 1.40), (-0.233, 1.31), (-0.18, 1.232)], "none", PLAT, 1.5)
v.poly([(0.195, 1.50), (0.22, 1.50), (0.22, 1.16), (0.195, 1.16)], "#1d1f22", LN, 1.1)
v.poly([(0.12, 1.40), (0.19, 1.40), (0.19, 1.26), (0.12, 1.26)], "#22262c", "#59606A", 1)
v.poly([(-0.17, 1.245), (-0.13, 1.245), (-0.13, 1.16), (-0.17, 1.16)], "#2a1a10", OR, 1)
v.poly([(0.125, 1.118), (0.229, 1.118), (0.229, 1.066), (0.125, 1.066)], GUN, GOLD, 1.2)
a, b = v.p(-0.090, 1.5595), v.p(0.110, 1.640)
out_ring = f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{GOLD}" stroke-width="5" stroke-linecap="round"/>'
out.append(out_ring)
for p_ in ([(-0.16, 1.36), (-0.05, 1.47), (0.12, 1.47), (0.2, 1.44)], [(-0.15, 1.20), (0.0, 1.10), (0.16, 1.18), (0.2, 1.24)]):
    v.shape(p_, closed=False, fill="none", stroke=OR, sw=1.6, extra='stroke-dasharray="6 4"')
v.note((y_c, z_c + 0.05), (-0.36, 1.62), "코어 (A-01 가정)"); v.note((-0.132, 1.30), (-0.36, 1.15), "그림자 차폐 25 mm")
v.note((0.155, 1.33), (0.30, 1.62), "냉각기 80 °C → 루프 70 °C"); v.note((0.207, 1.22), (0.30, 1.0), "방열판 2,668 W")
v.note((-0.15, 1.2), (-0.36, 1.0), "왁스 70 °C에서 녹음"); v.note((0.18, 1.09), (0.3, 0.92), "몸통 회전 (허리 레일)")
v.txt(-0.36, 0.80, "주황 점선 = 열의 흐름 (코어·조종사 → 등)", 10.5, OR, ko=True)
x0, y0 = panel(2, 1, "SK-07  KEEL CORE", "코어 단면 4배 · 가정은 이것 하나 (A-01)")
v = V(x0, y0, PW / 2 - 20, 1.357 * 1200 + 360, 1200)
zc = 1.357
v.shape([(0, zc + 0.125), (-0.016, zc + 0.10), (-0.038, zc + 0.03), (-0.038, zc - 0.03), (-0.016, zc - 0.10), (0, zc - 0.125), (0.016, zc - 0.10),
         (0.038, zc - 0.03), (0.038, zc + 0.03), (0.016, zc + 0.10)], fill="#16151f", stroke=LN, sw=1.4)
c1, c2 = v.p(0, zc + 0.085), v.p(0, zc - 0.085)
out.append(f'<line x1="{c1[0]}" y1="{c1[1]}" x2="{c2[0]}" y2="{c2[1]}" stroke="{VIO}" stroke-width="10" opacity="0.3" filter="url(#glow)"/>')
out.append(f'<line x1="{c1[0]}" y1="{c1[1]}" x2="{c2[0]}" y2="{c2[1]}" stroke="{VIO}" stroke-width="2"/>')
for zz in (zc + 0.092, zc - 0.092): v.poly([(-0.034, zz + 0.012), (0.034, zz + 0.012), (0.034, zz - 0.012), (-0.034, zz - 0.012)], "#3a2f1f", GOLD, 1.4)
for i in range(5):
    for sgn in (1, -1):
        zz = zc + sgn * (0.108 + i * 0.0035); v.line((-0.012, zz), (0.012, zz), "#9AA3AD", 1.2)
v.poly([(0.042, zc + 0.11), (0.067, zc + 0.11), (0.067, zc - 0.11), (0.042, zc - 0.11)], "#30343c", "#8B939D", 1.2)
v.line((0.04, zc + 0.11), (0.04, zc - 0.11), GOLD, 1.5, dash="2 2")
v.line((-0.038, zc), (-0.075, zc + 0.02), "#9AA3AD", 3); v.ell(-0.085, zc + 0.026, 0.012, 0.012, "#9AA3AD", F2, 1.2)
v.shape([(-0.005, zc + 0.03), (-0.03, zc + 0.05), (-0.055, zc + 0.06), (-0.075, zc + 0.065)], closed=False, fill="none", stroke=VIO, sw=1)
v.note((0.0, zc + 0.04), (0.11, zc + 0.21), "플라즈마: p + ¹¹B → 3 ⁴He")
v.note((0.03, zc + 0.092), (0.11, zc + 0.16), "거울 코일 18 T")
v.note((0.01, zc - 0.11), (0.11, zc - 0.17), "직접 변환 62%")
v.note((0.06, zc + 0.02), (0.11, zc + 0.06), "차폐 (조종사 쪽)")
v.note((0.04, zc - 0.03), (0.11, zc - 0.03), "금색 단열 MLI")
v.note((-0.085, zc + 0.026), (0.11, zc - 0.10), "알갱이 1.2 µg = 박동 1회")
v.note((-0.06, zc + 0.06), (0.11, zc + 0.11), "광섬유 → 용골의 선")
v.txt(-0.13, zc - 0.20, "박동 7 / 28 / 63 / 69 BPM · 3.0 kW · 270 V DC", 11, CY, ko=True)
v.txt(-0.13, zc - 0.22, "ASSUMPTION A-01 — 나머지는 전부 계산", 11, LN2)
x0, y0 = panel(3, 1, "SK-08  LEGEND", "색과 선의 뜻")
items = [(GOLD, "금색 링 = 회전축 (24개 관절의 사슬)"), (PLAT, "백금색 = 용골·형태선·미끄러지는 부품"), (BRZ, "브론즈 = 따뜻한 공기가 나가는 루버"),
         (VIO, "보랏빛 선 = 코어가 살아 있다는 표시 (희미하게)"), (OR, "주황 = 실제 열의 흐름"), (CY, "시안 = 치수·계산값"), (PH, "2점쇄선 = 조종사 (도하 177 / 182 cm)")]
for i, (c, t) in enumerate(items):
    yy = y0 + 110 + i * 40
    out.append(f'<line x1="{x0 + 40}" y1="{yy}" x2="{x0 + 80}" y2="{yy}" stroke="{c}" stroke-width="4"/>')
    out.append(f'<text x="{x0 + 95}" y="{yy + 4}" fill="{LN}" font-family="IBM Plex Sans KR" font-size="12.5">{t}</text>')
notes = ["바뀐 점 (v2 스케치 대비)", "· 직선 상자 → 근육 곡면 + 곧은 패널선", "· 눈 27° → 15°, 눈썹뼈 일체", "· 목이 보임 + 아틀라스 링",
         "· 팔 735 mm (윙스팬 182), 다리 0.535 H", "· 등 수소 팩 → 얇은 방열판 2장", "· 허리 링 → 척추 뒤 곡선 레일", "· 가슴: 원반 없이 용골 + 선 하나"]
for i, t in enumerate(notes):
    out.append(f'<text x="{x0 + 40}" y="{y0 + 430 + i * 24}" fill="{LN if i == 0 else LN2}" font-family="IBM Plex Sans KR" font-size="12.5">{t}</text>')
W, H = PW * 4, PH_ * 2
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(svg + out) + \
      f'<text x="{W - 20}" y="{H - 18}" fill="#48515C" font-family="IBM Plex Mono" font-size="10" text-anchor="end">HX-01 KESTREL · CONCEPT SKETCH v2.1 · DRAWN BY DOHA</text></svg>'
fs = f"{R}/node_modules/@fontsource"
css = "".join(f'<link rel="stylesheet" href="file://{fs}/{f}">' for f in ("ibm-plex-mono/400.css", "ibm-plex-sans-kr/400.css"))
html = f"<html><head>{css}</head><body style='margin:0;background:{BG}'>{svg}</body></html>"
here = os.path.dirname(os.path.abspath(__file__)); open(f"{here}/sketch_v21.html", "w").write(html)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.25)
    pg.goto(f"file://{here}/sketch_v21.html"); pg.wait_for_timeout(800)
    pg.screenshot(path=f"{here}/kestrel_sketch_v2.1.png", full_page=True); b.close()
print("ok", W, H)
