"""HX-01 KESTREL — engineering calculation sheet.
Every number shown on the showreel page comes from this file (specs.json).
Tags: spec = vendor datasheet, design = chosen value, calc = computed here, const = physical constant/textbook.
"""
import json, math

g = 9.81
S = {}

def put(key, value, unit, tag, note=""):
    S[key] = {"v": value, "unit": unit, "tag": tag, "note": note}
    return value

# ---------------------------------------------------------------- general
put("pilot_mass", 75.0, "kg", "design")
put("suit_height", 1960, "mm", "design", "standing, helmet crest to sole")
put("suit_width", 780, "mm", "design", "shoulder actuator to shoulder actuator")
put("suit_depth", 540, "mm", "design", "chest plate to back turbine")

# ---------------------------------------------------------------- propulsion (JetCat P400-PRO-LN datasheet)
T1 = put("turbine_thrust_max", 425.0, "N", "spec")
m_turb = put("turbine_mass", 4.01, "kg", "spec")
put("turbine_rpm_idle", 30000, "rpm", "spec")
rpm_max = put("turbine_rpm_max", 98000, "rpm", "spec")
put("turbine_egt_min", 480, "degC", "spec")
put("turbine_egt_max", 750, "degC", "spec")
ff_ml = put("turbine_fuel_flow_max", 1392, "mL/min", "spec")
put("turbine_diameter", 148.4, "mm", "spec")
put("turbine_length", 390, "mm", "spec")
n_turb = put("turbine_count", 5, "", "design", "2 per arm + 1 back")
rho_fuel = put("fuel_density", 0.80, "kg/L", "const", "Jet A-1 approx.")
fuel_L = put("fuel_volume", 16.0, "L", "design")
fuel_m = put("fuel_mass", fuel_L * rho_fuel, "kg", "calc")
blades = put("compressor_blades", 7, "", "design", "main blades, radial impeller")

# ---------------------------------------------------------------- mass budget
battery_kWh = put("battery_energy", 1.2, "kWh", "design")
pack_Whkg = put("battery_pack_specific_energy", 220, "Wh/kg", "design")
# 24 actuators (24 DoF, cf. Sarcos Guardian XO), three size classes.
# Real-world anchor for torque density: Unitree M107 joint motor (H1 humanoid), 360 N·m peak, 1.9 kg
# -> 189 N·m/kg peak. Class masses below are chosen to stay BELOW that state of the art.
put("ref_m107_peak_torque", 360, "N·m", "spec", "Unitree M107 (H1 knee), vendor brochure")
put("ref_m107_mass", 1.9, "kg", "spec", "Unitree M107")
put("ref_m107_torque_density", round(360 / 1.9), "N·m/kg", "calc")
ACT = {
    # class: (count, unit mass kg, joints, housing OD mm, housing width mm, reducer)
    "L": (10, 1.40, "hip flex ×2, hip abd ×2, knee ×2, shoulder flex ×2, shoulder abd ×2", 135, 78,
          "hip/knee: 1-stage planetary 9:1 (QDD, backdrivable) · shoulder: strain-wave 100:1 (holds thrust load)"),
    "M": (9, 0.70, "hip rot ×2, ankle pitch ×2, shoulder rot ×2, elbow ×2, trunk rot ×1", 104, 62,
          "strain-wave 80:1"),
    "S": (5, 0.45, "ankle roll ×2, wrist ×2, neck (helmet yaw support) ×1", 80, 50, "strain-wave 50:1"),
}
n_act = sum(v[0] for v in ACT.values())
assert n_act == 24
S["actuator_classes"] = {k: {"count": v[0], "kg": v[1], "joints": v[2], "od_mm": v[3], "width_mm": v[4],
                             "reducer": v[5]} for k, v in ACT.items()}
m_act = sum(v[0] * v[1] for v in ACT.values())
budget = [
    ("Turbines ×5 (P400-class)", n_turb * m_turb),
    ("Turbine mounts, nozzles, heat shields", 3.00),
    ("Fuel system hardware (pumps, valves, filters, lines)", 1.80),
    ("Exo structure (Ti-6Al-4V / CFRP)", 14.00),
    ("Joint actuators ×24 (L10 / M9 / S5)", m_act),
    ("Battery 1.2 kWh", battery_kWh * 1000 / pack_Whkg),
    ("Armor panels ×14 (CFRP + aramid)", 6.00),
    ("Fasteners ≈400 (M3–M8, Ti / steel)", 1.60),
    ("Electronics, sensors, harness", 2.50),
    ("Pilot harness / soft goods", 2.00),
]
S["mass_budget"] = [{"item": k, "kg": round(v, 2)} for k, v in budget]
dry = put("suit_dry_mass", round(sum(v for _, v in budget), 2), "kg", "calc")
m_sys = put("system_mass_no_fuel", dry + S["pilot_mass"]["v"], "kg", "calc")
M0 = put("takeoff_mass", round(m_sys + fuel_m, 2), "kg", "calc")
W = put("takeoff_weight", round(M0 * g, 1), "N", "calc")
T = put("thrust_total", n_turb * T1, "N", "calc")
TW = put("thrust_to_weight", round(T / W, 3), "", "calc")
TW_min = put("thrust_to_weight_min", 1.25, "", "design", "attitude-control margin")
assert TW >= TW_min, f"T/W {TW} below control margin {TW_min}"
put("hover_throttle", round(W / T * 100, 1), "%", "calc")
put("arm_thrust", 2 * T1, "N", "calc", "load carried by exo shoulder, not pilot")

tsfc_min = (ff_ml / 1000 * rho_fuel) / T1                    # kg/(N·min)
put("tsfc", round(tsfc_min * 60, 4), "kg/(N·h)", "calc")
reserve = put("fuel_reserve", 0.15, "", "design")
usable = fuel_m * (1 - reserve); m = M0; t = 0.0; dt = 0.001
while usable > 0:
    ff = m * g * tsfc_min; usable -= ff * dt; m -= ff * dt; t += dt
put("hover_endurance", round(t * 60), "s", "calc", "constant-TSFC, 15% reserve")
pen = put("part_throttle_tsfc_penalty", 1.14, "", "design", "TSFC worse at ~70% throttle")
put("hover_endurance_conservative", round(t * 60 / pen), "s", "calc", "hover_endurance / penalty")
put("hover_fuel_flow_initial", round(M0 * g * tsfc_min, 2), "kg/min", "calc")
put("shaft_freq_max", round(rpm_max / 60, 1), "Hz", "calc")
put("blade_pass_freq_max", round(rpm_max / 60 * blades), "Hz", "calc", "inducer BPF: 7 main blades (splitters start downstream)")
put("blade_pass_freq_idle", round(30000 / 60 * blades), "Hz", "calc")
# blade/vane counts of adjacent rows chosen pairwise coprime to avoid resonance
rows = {"compressor_main": 7, "compressor_splitter": 7, "diffuser_vanes": 11, "ngv_vanes": 13, "turbine_blades": 23}
S["turbine_rows"] = rows
for a, b in [("compressor_main", "diffuser_vanes"), ("diffuser_vanes", "ngv_vanes"), ("ngv_vanes", "turbine_blades")]:
    assert math.gcd(rows[a], rows[b]) == 1, (a, b)
put("fuel_injectors", 6, "", "design", "vaporiser sticks in annular combustor")
put("turbine_bearings", 2, "", "spec", "ceramic ball bearings, fuel/oil mist lubricated")
put("fuel_prefilter", 50, "µm", "spec", "external pre-filter required by JetCat")
put("turbine_part_count", 40, "", "design", "modelled parts per engine (approx.)")
put("tank_part_count", 15, "", "design", "modelled parts per fuel tank (approx.)")

# ---------------------------------------------------------------- actuation
put("actuator_count", n_act, "", "calc", "L10 / M9 / S5")
Zs, Zr = 12, 96
Zp = (Zr - Zs) // 2
assert (Zs + Zr) % 3 == 0
put("planetary_sun_teeth", Zs, "", "design")
put("planetary_ring_teeth", Zr, "", "design")
put("planetary_planet_teeth", Zp, "", "calc")
put("planetary_planet_count", 3, "", "design")
ratio = put("planetary_ratio", 1 + Zr / Zs, "", "calc", "ring fixed, sun in, carrier out; hip & knee (L class, QDD)")
put("planetary_assembly_check", (Zs + Zr) // 3, "", "calc", "(Zs+Zr)/N integer => assemblable")
mod = put("gear_module", 1.0, "mm", "design")
put("sun_planet_centre_distance", mod * (Zs + Zp) / 2, "mm", "calc")
# 12 teeth < 17 (standard undercut limit at 20°) -> positive profile shift on the sun, S0 gearing keeps 27 mm
alpha = math.radians(20)
put("pressure_angle", 20, "deg", "const")
put("undercut_limit_teeth", round(2 / math.sin(alpha) ** 2, 2), "", "calc", "z_min = 2/sin²α for a standard gear (x = 0)")
x_s = put("profile_shift_sun", 0.30, "", "design", "S0 gearing: x_sun + x_planet = 0")
put("profile_shift_planet", -0.30, "", "design")
put("profile_shift_ring", -0.30, "", "design", "internal mesh keeps a = m(Zr−Zp)/2")
zmin_shift = 2 * (1 - x_s) / math.sin(alpha) ** 2
put("undercut_limit_shifted", round(zmin_shift, 2), "", "calc", "z_min = 2(1−x)/sin²α")
assert Zs >= zmin_shift, "sun gear would be undercut"
put("ring_planet_centre_distance", mod * (Zr - Zp) / 2, "mm", "calc", "must equal sun–planet distance")
assert mod * (Zr - Zp) / 2 == mod * (Zs + Zp) / 2
Tk = put("knee_torque_design", round(1.5 * m_sys), "N·m", "calc", "1.5 N·m/kg × system mass")
put("L_torque_density", round(Tk / ACT["L"][1]), "N·m/kg", "calc", "peak; below Unitree M107 189 N·m/kg")
assert Tk / ACT["L"][1] < 360 / 1.9
Tm = put("knee_motor_torque_peak", round(Tk / ratio, 1), "N·m", "calc")
# Lewis bending check of the sun gear (simplified, no dynamic factor)
b_face = put("gear_face_width", 20, "mm", "design")
Y12 = 0.245                                              # Lewis form factor, 12T, 20° full depth
Ft = Tm * 1000 / (mod * Zs / 2) / 3                      # N per mesh, 3 planets share load
sb = Ft / (b_face * mod * Y12)
put("sun_tangential_force", round(Ft), "N", "calc", "per planet mesh")
put("sun_bending_stress", round(sb), "MPa", "calc", "Lewis, simplified")
put("gear_bending_allow", 500, "MPa", "const", "case-hardened 18CrNiMo7-6, approx.")
put("gear_FoS", round(500 / sb, 2), "", "calc")
pp = put("motor_pole_pairs", 14, "", "design", "28 magnets")
put("stator_slots", 24, "", "design", "24s/28p fractional-slot concentrated winding (q = 2/7)")
Zf, Zc = 200, 202
put("harmonic_flexspline_teeth", Zf, "", "design")
put("harmonic_circular_teeth", Zc, "", "design")
put("harmonic_drive_ratio", Zf // (Zc - Zf), "", "calc", "Zf/(Zc−Zf); shoulders (L class, holding load)")
mh = put("harmonic_module", 0.4, "mm", "design")
put("harmonic_flexspline_pd", round(mh * Zf, 2), "mm", "calc", "pitch diameter")
put("harmonic_circular_pd", round(mh * Zc, 2), "mm", "calc")
put("harmonic_radial_deflection", round(mh * (Zc - Zf) / 2, 2), "mm", "calc", "wave generator: w0 = m(Zc−Zf)/2")
# shoulder moment when the arm thrust line is steered off the arm axis
th_steer = put("arm_steer_angle", 15, "deg", "design", "max thrust-vector steering by arm angle")
r_thr = put("shoulder_to_thrust_line", 0.45, "m", "design", "shoulder GH centre to arm-pod thrust centre")
put("shoulder_steer_moment", round(2 * T1 * r_thr * math.sin(math.radians(th_steer))), "N·m", "calc",
    "arm thrust × lever × sin(steer); must stay below L-class peak")
assert 2 * T1 * r_thr * math.sin(math.radians(th_steer)) < Tk
put("encoder_bits", 17, "bit", "design", "motor-side and output-side (dual encoder)")
put("encoder_cpr", 2 ** 17, "counts/rev", "calc")
w_knee = put("knee_peak_velocity", 6.0, "rad/s", "design", "~345 deg/s gait peak")
w_mot = w_knee * ratio
put("knee_motor_rpm_gait", round(w_mot * 60 / (2 * math.pi)), "rpm", "calc")
put("motor_elec_freq_gait", round(w_mot / (2 * math.pi) * pp, 1), "Hz", "calc")
put("gear_mesh_freq_gait", round(Zs * (w_mot - w_knee) / (2 * math.pi), 1), "Hz", "calc")
put("ratchet_teeth", 72, "", "design")
put("ratchet_step", 360 / 72, "deg", "calc")
for k, v in {"loop_current": 20000, "loop_torque": 1000, "loop_gait": 500, "loop_flight": 400}.items():
    put(k, v, "Hz", "design")
put("walking_power", 400, "W", "design", "cf. Guardian XO ~500 W peak")
put("walking_endurance", battery_kWh * 1000 / 400, "h", "calc")

# ---------------------------------------------------------------- fasteners
As = put("bolt_M6_stress_area", 20.1, "mm²", "const", "ISO 898")
put("bolt_pitch", 1.0, "mm", "const", "M6 coarse")
put("bolt_engagement", 12, "mm", "design", "2.0 × d in Al housing (DFM guide: ≥1.5 × d)")
put("bolt_turns", 12, "rev", "calc", "engagement / pitch")
Fi = 0.75 * 0.9 * 880 * As
put("bolt_preload", round(Fi), "N", "calc", "0.75 × proof(0.9σy) × As")
put("bolt_torque", round(0.2 * Fi * 6 / 1000, 1), "N·m", "calc", "T = K F d, K=0.2 (anti-seize on Ti)")
put("fastener_count", 400, "", "design", "≈, M3–M8; exact count comes from the model")
put("hero_inspection_bolts", 12, "", "design", "bolts clickable in hero torque-wrench game")
put("closeup_unscrew_bolts", 48, "", "design", "armor-plate bolts shown unscrewing full 12 turns in close-up; the rest of the ≈400 retract fast")
put("bolt_sequence", [1, 4, 2, 5, 3], "", "const", "star pattern")

# ---------------------------------------------------------------- materials
mats = {
    "Ti-6Al-4V":     {"rho": 4.43, "E": 114, "sy": 880,  "su": 950,  "Tmax": 400, "use": "Structural links"},
    "Al 7075-T6":    {"rho": 2.81, "E": 71.7, "sy": 503, "su": 572,  "Tmax": 120, "use": "Brackets, housings"},
    "Inconel 718":   {"rho": 8.19, "E": 200, "sy": 1030, "su": 1240, "Tmax": 650, "use": "Nozzles, heat shields"},
    "CFRP [0/±45/90]": {"rho": 1.55, "E": 50, "sy": 600,  "su": 600,  "Tmax": 120, "use": "Armor skin"},
}
for k, m_ in mats.items():
    m_["specific_strength"] = round(m_["sy"] / m_["rho"])      # kN·m/kg
S["materials"] = mats
S["cfrp_layup"] = [0, 45, -45, 90]
S["material_note"] = ("CFRP has the highest specific strength, but links are Ti-6Al-4V: isotropic, "
                      "damage/fatigue tolerant at clevises and threads, and usable to 400 °C near turbines. "
                      "CFRP is used only for non-structural armor away from exhaust.")
# oxide (temper) colors, approximate: they depend on alloy and exposure time.
# Ti-6Al-4V service limit is 400 °C, so Ti parts may only show straw → bronze.
S["heat_tint_ti"] = [
    {"T": 250, "c": "#c9b27a", "name": "light straw"},
    {"T": 320, "c": "#b08a4a", "name": "dark straw"},
    {"T": 400, "c": "#8a5a32", "name": "bronze (Ti limit)"},
]
S["heat_tint_inconel"] = [   # nozzles, shields, standoffs (service to ~650 °C)
    {"T": 450, "c": "#a8844e", "name": "straw"},
    {"T": 520, "c": "#7a4a38", "name": "brown"},
    {"T": 580, "c": "#5a3c7a", "name": "purple"},
    {"T": 650, "c": "#2f5fa8", "name": "blue"},
    {"T": 750, "c": "#6f7f8c", "name": "grey (exhaust lip)"},
]

# ---------------------------------------------------------------- structure: thigh link
D, d = 32.0, 28.0
I = math.pi / 64 * (D**4 - d**4)
F = 4 * m_sys * g
e = 60.0
M = F * e
sig = M * (D / 2) / I
put("link_OD", D, "mm", "design"); put("link_ID", d, "mm", "design")
put("link_I", round(I), "mm⁴", "calc")
put("landing_load_factor", 4, "g", "design", "asymmetric landing, one leg")
put("landing_force", round(F), "N", "calc")
put("link_eccentricity", e, "mm", "design")
put("link_moment", round(M / 1000), "N·m", "calc")
put("link_stress", round(sig), "MPa", "calc")
put("link_FoS", round(880 / sig, 2), "", "calc")
put("ti_fatigue_limit", 500, "MPa", "const", "approx., 1e7 cycles")

# landing drop
h = put("drop_height", 0.5, "m", "design")
v = math.sqrt(2 * g * h)
put("impact_velocity", round(v, 2), "m/s", "calc")
put("landing_stroke", round(v**2 / (2 * 3 * g) * 1000), "mm", "calc", "4g ground force => 3g net decel")

# ---------------------------------------------------------------- sound physics
S["beam_mode_ratios"] = [1.0, 2.756, 5.404, 8.933]
put("mains_hum", 120, "Hz", "calc", "2 × 60 Hz grid (KR)")
put("hangar_rt60", 2.5, "s", "design")

# ---------------------------------------------------------------- geometry layout (shared by Blender + web)
# Blender frame: metres, Z up, suit faces −Y, +X = suit's LEFT (.L). glTF/three: (x, z, −y).
# Pilot: 50th-percentile adult male, H = 1.75 m barefoot; segment ratios after Drillis & Contini (fractions of H).
H = put("pilot_height", 1.75, "m", "design", "barefoot stature")
foot_plate = put("foot_plate_thickness", 0.020, "m", "design", "exo foot plate under the boot")
boot_sole = put("boot_sole_thickness", 0.025, "m", "design")
z0 = foot_plate + boot_sole
ratio_h = {"ankle": 0.039, "knee": 0.285, "hip": 0.529, "gh": 0.794, "elbow": 0.631, "head_top": 1.0}
upper_arm = 0.163 * H          # GH centre -> elbow axis
fore_arm = 0.146 * H           # elbow -> wrist
abd = math.radians(12)          # rest pose: arms abducted 12°
flex = math.radians(15)         # rest pose: elbows flexed 15° forward

def v3(x, y, z):
    return [round(x, 4), round(y, 4), round(z, 4)]

gh = (0.185, 0.02, z0 + ratio_h["gh"] * H)
elbow = (gh[0] + upper_arm * math.sin(abd), gh[1], gh[2] - upper_arm * math.cos(abd))
fdir = (math.sin(abd) * math.cos(flex), -math.sin(flex), -math.cos(abd) * math.cos(flex))
wrist = tuple(elbow[i] + fore_arm * fdir[i] for i in range(3))
grip = tuple(wrist[i] + 0.075 * fdir[i] for i in range(3))
J = {  # pilot joint centres, LEFT side (mirror x for right)
    "ankle": v3(0.090, 0.000, z0 + ratio_h["ankle"] * H),
    "knee": v3(0.095, 0.005, z0 + ratio_h["knee"] * H),
    "hip": v3(0.085, 0.000, z0 + ratio_h["hip"] * H),
    "gh": v3(*gh),
    "elbow": v3(*elbow),
    "wrist": v3(*wrist),
    "grip": v3(*grip),
    "pelvis": v3(0, 0.0, z0 + 0.57 * H),
    "lumbar": v3(0, 0.03, z0 + 0.62 * H),
    "chest": v3(0, 0.0, z0 + 0.73 * H),
    "c7": v3(0, 0.055, z0 + 0.845 * H),
    "head": v3(0, 0.0, z0 + 0.94 * H),
    "head_top": v3(0, 0.0, z0 + H),
}
fa = [round(c, 4) for c in fdir]
A = S["actuator_classes"]
Lw, Mw, Sw = A["L"]["width_mm"] / 1000, A["M"]["width_mm"] / 1000, A["S"]["width_mm"] / 1000
# exo joints: centre, axis (unit, Blender frame, LEFT side), class. Axes pass through (or near) pilot joints.
X = {
    "hip_abd":      {"c": v3(0.135, 0.150, J["hip"][2] + 0.055), "axis": [0, 1, 0], "cls": "L",
                     "note": "behind hip on pelvis belt; 6–7 cm misalignment taken by a passive slider in the thigh link"},
    "hip_flex":     {"c": v3(0.190 + Lw / 2, 0.0, J["hip"][2]), "axis": [1, 0, 0], "cls": "L"},
    "hip_rot":      {"c": None, "axis": "link", "cls": "M",
                     "note": "in-line with the thigh link, 40 % down from the hip actuator"},
    "knee":         {"c": v3(0.150 + Lw / 2, J["knee"][1], J["knee"][2]), "axis": [1, 0, 0], "cls": "L"},
    "ankle_pitch":  {"c": v3(0.135 + Mw / 2, J["ankle"][1], J["ankle"][2]), "axis": [1, 0, 0], "cls": "M"},
    "ankle_roll":   {"c": v3(J["ankle"][0], 0.095, 0.078), "axis": [0, 1, 0], "cls": "S", "note": "behind the heel"},
    "trunk_rot":    {"c": v3(0, 0.165, J["lumbar"][2]), "axis": [0, 0, 1], "cls": "M", "side": "C"},
    "neck":         {"c": v3(0, 0.125, J["c7"][2] + 0.02), "axis": [0, 0, 1], "cls": "S", "side": "C"},
    "shoulder_abd": {"c": v3(gh[0], gh[1] + 0.135, gh[2]), "axis": [0, 1, 0], "cls": "L",
                     "note": "behind GH; flex + abd axes intersect at the GH centre (remote centre)"},
    "shoulder_flex":{"c": v3(gh[0] + 0.070 + Lw / 2, gh[1], gh[2]), "axis": [1, 0, 0], "cls": "L"},
    "shoulder_rot": {"c": v3(*[gh[i] + [math.sin(abd), 0, -math.cos(abd)][i] * 0.12 for i in range(3)]),
                     "axis": "upper_arm", "cls": "M", "note": "arc-rail bearing around the upper arm"},
    "elbow":        {"c": v3(elbow[0] + 0.075, elbow[1], elbow[2] + 0.075 * math.tan(abd)),
                     "axis": [math.cos(abd), 0, math.sin(abd)], "cls": "M"},
    "wrist":        {"c": v3(*wrist), "axis": fa, "cls": "S", "note": "rotates the throttle grip module"},
}
assert sum(1 if v.get("side") == "C" else 2 for v in X.values()) == 24, "exo joint count must be 24"
_hf, _kn = X["hip_flex"]["c"], X["knee"]["c"]
X["hip_rot"]["c"] = v3(*[_hf[i] + 0.40 * (_kn[i] - _hf[i]) for i in range(3)])
# propulsion & tanks
tr = S["turbine_diameter"]["v"] / 2000
tl = S["turbine_length"]["v"] / 1000
back_turbine = {"c": v3(0, 0.345, J["chest"][2] + 0.04), "axis": [0, 0, -1], "note": "vertical, exhaust down"}
pod_lat = 0.105   # arm-pod turbines: lateral offset from forearm axis
pod_ap = 0.082    # ± fore/aft offset (16 mm gap between the two casings)
pod_along = 0.040  # shifted toward the hand so the intake sits at elbow height
tank_r = 0.080
tank_len = fuel_L / 2 / 1000 / (math.pi * tank_r ** 2) + 2 / 3 * tank_r  # V = πr²Lc + 4/3πr³, total = Lc + 2r
S["layout"] = {
    "frame": "Blender metres, Z up, front = −Y, +X = suit LEFT; glTF (x, z, −y)",
    "z0_barefoot": round(z0, 4),
    "pilot": J,
    "exo": X,
    "forearm_dir": fa,
    "back_turbine": back_turbine,
    "arm_pod": {"lateral": pod_lat, "fore_aft": pod_ap, "along": pod_along, "turbine_r": round(tr, 4), "turbine_len": tl},
    "tanks": {"x": 0.176, "y": 0.300, "zc": J["chest"][2] + 0.02, "r": tank_r,
              "len": round(tank_len, 4), "volume_L_each": fuel_L / 2},
    "battery": {"size": [0.18, 0.07, 0.30], "c": v3(0, 0.22, J["chest"][2] + 0.03),
                "note": "3.78 L pack, ≈317 Wh/L"},
    "stand": {"post_x": 0.46, "post_y": 0.62, "height": 2.15, "clamp_z": J["chest"][2] + 0.10},
}
put("tank_length", round(tank_len * 1000), "mm", "calc", "Ø160 cylinder with hemispherical ends, 8.0 L each")
put("upper_arm_length", round(upper_arm * 1000), "mm", "calc", "0.163 H")
put("forearm_length", round(fore_arm * 1000), "mm", "calc", "0.146 H")

# ---------------------------------------------------------------- specs used on page as headline
S["_headline"] = {
    "dry": dry, "takeoff": M0, "W": W, "T": T, "TW": TW,
}

import os
root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(root, "specs.json"), "w") as f:
    json.dump(S, f, ensure_ascii=False, indent=1)
# (the web app imports calc/specs.json directly through Vite; no generated JS copy)
for k, v in S.items():
    if isinstance(v, dict) and "v" in v:
        print(f"{k:32s} {v['v']!s:>12} {v['unit']:10s} [{v['tag']}]")
