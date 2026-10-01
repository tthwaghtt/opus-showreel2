"""HX-01 KESTREL — engineering calculation sheet, v2.1 (2026-09-30).

v2.1 concept: a full-body armored powered suit sized to Doha (1.77 m, wingspan 1.82 m). The pilot stands inside a
dense internal mechanical layer (24 joint actuators, frame, cooling, sensors); 120+ separate armor panels latch onto it.
No flight. Power = the KEEL CORE, a compact aneutronic (p-¹¹B) fusion core behind the sternum keel.

THE ONE ASSUMPTION: the KEEL CORE is fictional future technology (tag "fiction", shown on the page as ASSUMPTION A-01).
Everything else — reaction energy, conversion chain, heat, cooling, structure, actuators — is computed from physics
and real references, starting from that one assumption.

Every engineering number shown on the showreel page comes from this file (calc/specs.json).
Part COUNTS and model envelope sizes come from the Blender model manifest instead (never typed by hand).
Tags: spec = vendor datasheet / published reference, design = chosen value, calc = computed here,
      const = physical constant or textbook value, fiction = the assumed future technology (power core only).
Run:  python3 calc/specs.py      (a failing assert means a design rule is broken: fix the design, not the assert)
"""
import json
import math
import os

g = 9.81
S = {}


def put(key, value, unit, tag, note=""):
    assert tag in ("spec", "design", "calc", "const", "fiction"), tag
    S[key] = {"v": value, "unit": unit, "tag": tag, "note": note}
    return value


def rd(x, n=2):
    return round(x, n)


# ================================================================ general
put("spec_version", "v2.1", "", "design", "2026-09-30 16:30: fictional chest core, Doha's proportions, neck")
m_pilot = put("pilot_mass", 75.0, "kg", "design", "50th-percentile adult male mass")
H = put("pilot_height", 1.77, "m", "design", "Doha's stature (barefoot)")
span = put("pilot_wingspan", 1.82, "m", "design", "Doha's wingspan, fingertip to fingertip (ape index 1.03)")

# ================================================================ actuator classes (24 joints, 3 sizes)
# Real-world anchors: Sarcos Guardian XO (full-body exo, 24 DoF, lifts 90 kg) and the Unitree M107 joint motor
# (360 N·m peak, 1.9 kg -> 189 N·m/kg). Class masses below are chosen to stay BELOW that torque density.
put("ref_guardian_xo_dof", 24, "", "spec", "Sarcos Guardian XO full-body exoskeleton")
put("ref_guardian_xo_lift", 90, "kg", "spec", "Sarcos Guardian XO rated lift")
put("ref_guardian_xo_mass", 68, "kg", "spec", "Sarcos Guardian XO (no armor)")
put("ref_m107_peak_torque", 360, "N·m", "spec", "Unitree M107 (H1 knee), vendor brochure")
put("ref_m107_mass", 1.9, "kg", "spec", "Unitree M107")
put("ref_m107_torque_density", round(360 / 1.9), "N·m/kg", "calc")
ACT = {
    # class: (count, unit mass kg, joints, housing OD mm, housing width mm, reducer)
    "L": (14, 1.40, "hip flex ×2, hip abd ×2, knee ×2, ankle pitch ×2, shoulder flex ×2, shoulder abd ×2, elbow ×2",
          135, 60, "legs: 1-stage planetary 9:1 (QDD: backdrivable, survives landing impacts) · "
                   "arms: strain-wave 100:1 (holds a lifted load without motor heat)"),
    "M": (7, 0.70, "hip rot ×2, ankle roll ×2, shoulder rot ×2, trunk rot ×1", 104, 52,
          "strain-wave 80:1 (ankle roll behind an overload slip clutch)"),
    "S": (3, 0.45, "wrist ×2, neck ×1", 80, 42, "strain-wave 50:1"),
}
n_act = sum(v[0] for v in ACT.values())
assert n_act == 24
put("actuator_count", n_act, "", "calc", "L14 / M7 / S3")
S["actuator_classes"] = {k: {"count": v[0], "kg": v[1], "joints": v[2], "od_mm": v[3], "width_mm": v[4],
                             "reducer": v[5]} for k, v in ACT.items()}
m_act = sum(v[0] * v[1] for v in ACT.values())
Lw, Mw, Sw = (ACT[k][4] / 1000 for k in "LMS")
Lr, Mr, Sr = (ACT[k][3] / 2000 for k in "LMS")
put("actuator_liquid_cooling", "jacket on every housing", "", "design",
    "power is no longer scarce, heat is: liquid jackets raise continuous torque; loop shared with the core")

# ================================================================ geometry layout part 1: pilot + joints
# Blender frame: metres, Z up, suit faces −Y, +X = suit's LEFT (.L). glTF/three: (x, z, −y).
# Pilot proportions after Drillis & Contini (fractions of H), adjusted to Doha: arms from the measured wingspan,
# legs +0.6 % H (Doha asked for slightly longer legs).
foot_plate = put("foot_plate_thickness", 0.020, "m", "design", "exo foot plate under the boot")
boot_sole = put("boot_sole_thickness", 0.025, "m", "design")
z0 = foot_plate + boot_sole
ratio_h = {"ankle": 0.039, "knee": 0.288, "hip": 0.535, "gh": 0.794, "head_top": 1.0}
put("hip_height_ratio", ratio_h["hip"], "H", "design", "Drillis–Contini 0.529 + 0.006 H (longer legs)")
gh_x = put("gh_half_breadth", 0.175, "m", "design", "shoulder joint centre from the midline (biacromial ≈ 0.23 H − 3 cm)")
arm = (span - 2 * gh_x) / 2                 # GH centre -> fingertip
k_arm = arm / (0.163 + 0.146 + 0.108)       # keep the standard upper-arm : forearm : hand proportions
upper_arm, fore_arm, hand = 0.163 * k_arm, 0.146 * k_arm, 0.108 * k_arm
put("arm_length", round(arm * 1000), "mm", "calc", "shoulder joint -> fingertip, from the wingspan")
put("upper_arm_length", round(upper_arm * 1000), "mm", "calc")
put("forearm_length", round(fore_arm * 1000), "mm", "calc")
put("hand_length", round(hand * 1000), "mm", "calc")
z_gh = z0 + ratio_h["gh"] * H
fh = (z_gh - arm - z0) / H
put("fingertip_height", rd(fh, 3), "H", "calc", "standing, arms hanging straight; anthropometric ≈ 0.377 H")
assert 0.36 < fh < 0.40, "arm length out of human range"
abd = math.radians(12)          # rest pose: arms abducted 12°
flex = math.radians(15)         # rest pose: elbows flexed 15° forward


def v3(x, y, z):
    return [round(x, 4), round(y, 4), round(z, 4)]


gh = (gh_x, 0.02, z_gh)
elbow = (gh[0] + upper_arm * math.sin(abd), gh[1], gh[2] - upper_arm * math.cos(abd))
fdir = (math.sin(abd) * math.cos(flex), -math.sin(flex), -math.cos(abd) * math.cos(flex))
wrist = tuple(elbow[i] + fore_arm * fdir[i] for i in range(3))
grip = tuple(wrist[i] + 0.4 * hand * fdir[i] for i in range(3))
J = {  # pilot joint centres and landmarks, LEFT side (mirror x for right)
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
    "jugular": v3(0, -0.07, z0 + 0.818 * H),
    "c7": v3(0, 0.055, z0 + 0.845 * H),
    "chin": v3(0, -0.09, z0 + 0.87 * H),
    "head": v3(0, 0.0, z0 + 0.94 * H),
    "head_top": v3(0, 0.0, z0 + H),
}
fa = [round(c, 4) for c in fdir]
chest_d = put("pilot_chest_half_depth", 0.115, "m", "design", "chest depth ≈ 0.23 m (50th-percentile male)")

# trunk rotation: a curved rail + sector gear BEHIND the lumbar spine (a full ring around the waist would hit the belly)
Zt, Ztp, mt, x_tp, arc_deg = 120, 12, 2.0, 0.30, 35
spine_c = v3(0, 0.045, J["lumbar"][2])      # lumbar rotation axis (vertebral bodies)
R_t = Zt * mt / 2000                        # pitch radius of the sector = rail radius
a_t = (Zt + Ztp) * mt / 2000
# helmet yaw: the ATLAS RING at the top of the neck (C1 level), tilted forward-down to clear the chin
Zc, Zcp, mc, x_cp = 96, 12, 2.25, 0.30
tilt = math.radians(22)
atlas_c = v3(0, 0.010, J["chin"][2] + 0.015)
a_c = (Zc + Zcp) * mc / 2000
n_ax = (0, -math.sin(tilt), math.cos(tilt))                      # ring axis (up and slightly forward)
back_dir = (0, math.cos(tilt), math.sin(tilt))                   # rearmost direction in the ring plane
pin_c = [atlas_c[i] + a_c * back_dir[i] for i in range(3)]
neck_act = v3(*[pin_c[i] - 0.035 * n_ax[i] for i in range(3)])

# exo joints: centre, axis (unit, Blender frame, LEFT side), class. Axes pass through (or near) pilot joints.
X = {
    "hip_abd":      {"c": v3(0.135, 0.150, J["hip"][2] + 0.055), "axis": [0, 1, 0], "cls": "L",
                     "note": "behind the hip on the pelvis frame; 6–7 cm misalignment taken by a passive slider"},
    "hip_flex":     {"c": v3(0.190 + Lw / 2, 0.0, J["hip"][2]), "axis": [1, 0, 0], "cls": "L"},
    "hip_rot":      {"c": None, "axis": "link", "cls": "M",
                     "note": "in-line with the thigh link, 40 % down from the hip actuator (a twist ring)"},
    "knee":         {"c": v3(0.150 + Lw / 2, J["knee"][1], J["knee"][2]), "axis": [1, 0, 0], "cls": "L",
                     "note": "parallel semi-active hydraulic damper on the lateral thigh"},
    "ankle_pitch":  {"c": v3(0.165, 0.060, J["knee"][2] - 2 * Lr - 0.012), "axis": [1, 0, 0], "cls": "L",
                     "joint": v3(0.150, 0.0, J["ankle"][2]),
                     "note": "actuator high on the calf drives the ankle bearing through crank + push rod "
                             "(Achilles linkage): less mass at the foot"},
    "ankle_roll":   {"c": v3(J["ankle"][0], 0.100, 0.085), "axis": [0, 1, 0], "cls": "M", "note": "behind the heel"},
    "trunk_rot":    {"c": v3(0, spine_c[1] + a_t, spine_c[2] - 0.050), "axis": [0, 0, 1], "cls": "M", "side": "C",
                     "arc": {"c": spine_c, "R": R_t, "span_deg": arc_deg, "gear_teeth_full": Zt, "pinion": Ztp,
                             "module": mt},
                     "note": "on the pelvis frame; its pinion drives a sector gear on a curved rail behind the "
                             "lumbar spine, concentric with the spine axis (remote centre)"},
    "neck":         {"c": neck_act, "axis": [round(c, 4) for c in n_ax], "cls": "S", "side": "C",
                     "ring": {"c": atlas_c, "teeth": Zc, "pinion": Zcp, "module": mc, "tilt_deg": 22},
                     "note": "atlas ring at the top of the neck carries the helmet (yaw); passive spring-balanced "
                             "pitch hinges at the ear line; the pilot's neck carries no helmet load"},
    "shoulder_abd": {"c": v3(gh[0], gh[1] + 0.135, gh[2]), "axis": [0, 1, 0], "cls": "L",
                     "note": "behind GH; flex + abd axes intersect at the GH centre (remote centre)"},
    "shoulder_flex": {"c": v3(gh[0] + 0.070 + Lw / 2, gh[1], gh[2]), "axis": [1, 0, 0], "cls": "L"},
    "shoulder_rot": {"c": v3(*[gh[i] + [math.sin(abd), 0, -math.cos(abd)][i] * 0.12 for i in range(3)]),
                     "axis": "upper_arm", "cls": "M", "note": "arc-rail bearing around the upper arm"},
    "elbow":        {"c": v3(*[elbow[i] + 0.085 * [math.cos(abd), 0, math.sin(abd)][i] for i in range(3)]),
                     "axis": [round(math.cos(abd), 4), 0, round(math.sin(abd), 4)], "cls": "L"},
    "wrist":        {"c": v3(*wrist), "axis": fa, "cls": "S", "note": "turns the gauntlet (pronation / supination)"},
}
assert sum(1 if v.get("side") == "C" else 2 for v in X.values()) == 24, "exo joint count must be 24"
_cls_count = {c: sum((1 if v.get("side") == "C" else 2) for v in X.values() if v["cls"] == c) for c in "LMS"}
assert _cls_count == {"L": 14, "M": 7, "S": 3}, _cls_count
_hf, _kn = X["hip_flex"]["c"], X["knee"]["c"]
X["hip_rot"]["c"] = v3(*[_hf[i] + 0.40 * (_kn[i] - _hf[i]) for i in range(3)])
put("neck_visible_height", round((atlas_c[2] - 0.108 * math.sin(tilt) - J["jugular"][2]) * 1000), "mm", "calc",
    "front: jugular notch -> lowest point of the atlas ring (the neck must read as a neck)")
assert atlas_c[2] - 0.108 * math.sin(tilt) < J["chin"][2] - 0.01, "atlas ring hits the chin"

# ================================================================ armor (outer layer)
# (raw values carry through the calculation; rd() is for display only)
bsa = 0.007184 * m_pilot ** 0.425 * (H * 100) ** 0.725
put("pilot_body_surface_area", rd(bsa, 3), "m²", "calc", "Du Bois formula")
k_off = put("armor_area_factor", 1.70, "", "design", "shell sits 6–10 cm outside the skin; limb area grows ~(r+t)/r")
A_arm = bsa * k_off
put("armor_area", rd(A_arm, 3), "m²", "calc", "estimate; the model manifest reports the real area")
t_cf = put("armor_cfrp_thickness", 2.0, "mm", "design", "CFRP [0/±45/90]s skin, clear-coated (graphite look)")
t_ar = put("armor_aramid_thickness", 1.0, "mm", "design", "aramid/epoxy inner liner: catches fragments")
w_lam = t_cf * 1.55 + t_ar * 1.38
put("armor_areal_density_composite", rd(w_lam, 3), "kg/m²", "calc")
t_tip = put("armor_ti_panel_thickness", 1.2, "mm", "design",
            "impact panels (knee / shoulder caps, knuckles) and the helmet shell with its brow, in Ti-6Al-4V: dent instead of shatter")
w_ti = t_tip * 4.43
put("armor_areal_density_ti", rd(w_ti, 3), "kg/m²", "calc")
f_ti = put("armor_ti_area_fraction", 0.15, "", "design", "helmet shell ≈ 0.18 m² (≈ 6%) + caps and knuckles")
hw = put("armor_hardware_factor", 0.15, "", "design", "latches, locating pins, edge trims")
m_armor = A_arm * ((1 - f_ti) * w_lam + f_ti * w_ti) * (1 + hw)
put("armor_mass", rd(m_armor), "kg", "calc")
put("armor_panels_min", 120, "", "design", "target; the real count comes from the model manifest")
put("internal_parts_min", 450, "", "design", "target, fasteners excluded; real count from the manifest")
put("fastener_count_target", 700, "", "design", "≈, M2–M8; real count from the manifest")
put("latch_count_target", 150, "", "design", "≈, over-center latches holding the armor; real count from the manifest")
put("armor_panel_gap", 1.2, "mm", "design", "panel line: tolerance + thermal growth")
put("armor_ballistic", "none", "", "design", "impact / abrasion shell only — NOT ballistic protection")

# ================================================================ power: KEEL CORE  (the ONE fictional assumption)
put("assumption_A01", "a compact aneutronic p-11B fusion core of a few kW exists (future technology)", "", "fiction",
    "the only non-physical assumption on the page; everything below is computed from it")
Q_pb = put("pb11_q_value", 8.68, "MeV", "const", "p + ¹¹B → 3 ⁴He (three alpha particles, no neutron)")
m_fuel_u = 1.007276 + 11.009305                 # proton + boron-11, atomic mass units
e_spec = Q_pb * 1e6 * 1.602177e-19 / (m_fuel_u * 1.660539e-27)     # J/kg
put("pb11_specific_energy", rd(e_spec / 1e12, 1), "TJ/kg", "calc", "E = Q / (m_p + m_B11)")
put("pb11_vs_hydrogen", round(e_spec / 120e6, -3), "×", "calc", "per kg, vs burning hydrogen (120 MJ/kg)")
put("pb11_alpha_energy", rd(Q_pb / 3, 2), "MeV", "calc", "mean energy per alpha particle")
f_ch = put("core_charged_fraction", 0.70, "", "fiction",
           "fusion power leaving as fast alphas; the rest escapes as X-rays (bremsstrahlung) — tamed in the fiction")
eta_tw = put("core_twdec_efficiency", 0.80, "", "fiction",
             "traveling-wave direct energy converter: alpha beam -> RF -> DC (no turbine, no steam)")
eta_xr = put("core_xray_pv_efficiency", 0.20, "", "fiction", "nano-layered X-ray photovoltaic shell around the plasma")
eta_core = f_ch * eta_tw + (1 - f_ch) * eta_xr
put("core_efficiency", rd(eta_core, 3), "", "calc", "fusion -> electricity = f·η_TW + (1−f)·η_X")
P_core = put("core_power_rated", 3000, "W", "fiction", "continuous electric output (set by the radiators, see thermal)")
eta_pc = put("power_conditioning_efficiency", 0.96, "", "design", "RF rectifiers -> 270 V DC bus")
Pf_rated = P_core / eta_core
put("core_fusion_power_rated", round(Pf_rated), "W", "calc")
put("core_heat_rated", round(Pf_rated - P_core), "W", "calc", "to the coolant loop")
V_bus = put("bus_voltage", 270, "V", "spec", "270 V DC: aircraft 'more-electric' standard (MIL-STD-704)")
# pulsed operation: one fuel pellet per pulse -> the core has a HEARTBEAT
m_pel = put("pellet_mass", 1.2, "µg", "fiction", "boron-11 hydride microsphere, Ø ≈ 0.14 mm (a grain of fine sand)")
f_burn = put("pellet_burnup", 0.05, "", "fiction", "fraction fused per pulse")
E_pel = m_pel * 1e-9 * f_burn * e_spec
put("pellet_energy", round(E_pel), "J", "calc", "fusion energy per pulse")
bpm_rated = Pf_rated / E_pel * 60
put("heartbeat_rated", round(bpm_rated), "bpm", "calc", "pulse rate at rated power ≈ a resting human heart")
assert 55 <= bpm_rated <= 80
f_rec = put("fuel_recycle", 0.98, "", "fiction", "unburned fuel recaptured by the converter and re-pelletized")
m_fuel_pulse = m_pel * 1e-9 * (f_burn + (1 - f_burn) * (1 - f_rec))      # kg lost per pulse
mag = put("fuel_magazine", 1.0, "g", "fiction", "spiral magazine of pellets, swapped at service")
put("fuel_magazine_pellets", round(mag * 1e-3 / (m_pel * 1e-9), -3), "", "calc")
core_len, core_d = 250, 76
put("core_vessel", [core_d, core_len], "mm", "design", "vertical spindle Ø × length behind the sternum keel")
put("core_mirror_field", 18, "T", "fiction", "REBCO mirror coils at both throats (magnetic-mirror plasma trap)")
put("core_mirror_ratio", 6, "", "fiction")
put("core_coil_temperature", 50, "K", "design", "REBCO high-temperature superconductor (a real material)")
P_cryo = put("cryocooler_power", 150, "W", "design", "micro pulse-tube cryocooler for the coils")
f_cryo = put("cryocooler_freq", 50, "Hz", "design", "pressure-wave compressor (audible thump)")
t_sh = put("shadow_shield_thickness", 25, "mm", "design",
           "W-Ni-Fe heavy alloy + B₄C, on the PILOT side only (space-reactor 'shadow shield' idea)")
put("core_window", "fibre-optic diagnostic bundle -> keel slit", "", "design",
    "a sample of plasma light reaches the keel through bent fibres; X-rays cannot follow the bends")
put("keel_line_colour", "#B7A6FF", "", "design", "boron-ion (~412 nm) + hydrogen (486 nm) line light, faint")
put("core_scram", "quench-safe: coils dump into resistors, plasma dies in < 1 ms", "", "fiction",
    "a fusion core cannot run away: no fuel inventory in the plasma")
core_parts = [
    ("Vacuum vessel + REBCO mirror coils", 2.40),
    ("Traveling-wave converter stacks ×2 (top and bottom)", 1.20),
    ("X-ray photovoltaic shell", 0.80),
    ("Shadow shield (W alloy + B4C)", 3.20),
    ("Pellet injector + fuel magazine", 0.40),
    ("Pulse-tube cryocooler", 0.90),
    ("RF rectifiers + 270 V conditioning", 1.10),
]
S["core_parts"] = [{"item": k, "kg": v} for k, v in core_parts]
m_core = sum(v for _, v in core_parts)
put("core_system_mass", rd(m_core), "kg", "calc")

# ---- buffer: peaks above the core, regen, pulse smoothing
E_sc = put("buffer_energy", 25, "Wh", "design", "lithium-ion capacitor bank")
P_sc = put("buffer_power", 20000, "W", "design")
m_sc = put("buffer_mass", 1.40, "kg", "design", "≈ 18 Wh/kg incl. packaging")
put("bus_power_peak", round(P_core * eta_pc + P_sc), "W", "calc", "core + buffer")

# ================================================================ thermal (heat, not fuel, now sets the limits)
Q_p = put("pilot_heat_design", 400, "W", "design", "sustained work inside a closed suit (300–500 W)")
put("ref_a7l_lcvg_removal", 590, "W", "spec", "Apollo A7L liquid cooling garment, approx.")
flow = put("lcvg_flow", 1.8, "L/min", "design")
T_in = put("lcvg_inlet_temp", 18, "degC", "design")
mdot = flow * 0.998 / 60
put("lcvg_delta_T", rd(Q_p / (mdot * 4186)), "K", "calc", "Q = ṁ c_p ΔT")
put("lcvg_outlet_temp", rd(T_in + Q_p / (mdot * 4186), 1), "degC", "calc")
put("lcvg_tube", [3.2, 80], "mm, m", "design", "tube OD, total length — quilted into the flight suit")
# loop temperatures: heat only flows downhill, so every hand-off must go from hotter to colder
T_amb = put("ambient_design_temp", 25, "degC", "design", "radiator capacity is quoted for 25 °C outside air")
T_cool = put("coolant_design_temp", 70, "degC", "design",
             "shared loop at the radiator design point (heavy work); the melting wax holds it here")
T_ev = put("chiller_evaporating_temp", 12, "degC", "design", "below the 18 °C garment inlet")
T_cd = put("chiller_condensing_temp", 80, "degC", "design", "above the 70 °C loop it dumps into: the chiller pumps heat uphill")
assert T_ev < T_in, "evaporator must be colder than the cooling-garment water"
assert T_cd >= T_cool + 5, "condenser must be hotter than the coolant loop it rejects into"
COP = put("chiller_cop", 1.5, "", "design", "micro vapour-compression loop lifting 12 °C -> 80 °C")
Te, Tc = T_ev + 273.15, T_cd + 273.15
put("chiller_cop_carnot", rd(Te / (Tc - Te)), "", "calc", "Carnot limit for T_evap 12 °C, T_cond 80 °C")
put("chiller_second_law", rd(COP / (Te / (Tc - Te))), "", "calc", "fraction of Carnot")
assert 0.2 < COP / (Te / (Tc - Te)) < 0.5
P_chill = put("chiller_power", round(Q_p / COP), "W", "calc")
Q_cond = put("condenser_heat", Q_p + round(Q_p / COP), "W", "calc")
rpm_cmp = put("compressor_rpm", 6000, "rpm", "design", "single rolling piston")
put("compressor_freq", rd(rpm_cmp / 60, 1), "Hz", "calc")
rpm_pump = put("pump_rpm", 3600, "rpm", "design", "main coolant loop (core + actuators + condenser)")
z_pump = put("pump_vanes", 5, "", "design")
put("pump_bpf", round(rpm_pump / 60 * z_pump), "Hz", "calc")
# Doha's sketch: two thin tapered panels flush on the back (wide top, rounded narrow bottom).
# Left panel outline in Blender metres (x, z), mirrored for the right; the outline is the single source for its size.
rad_xz = [(0.030, 1.500), (0.105, 1.500), (0.170, 1.410), (0.125, 1.200), (0.085, 1.160), (0.035, 1.180)]
rad_t = 25
rad_xs, rad_zs = [p_[0] for p_ in rad_xz], [p_[1] for p_ in rad_xz]
put("radiator_panel", [round((max(rad_xs) - min(rad_xs)) * 1000), round((max(rad_zs) - min(rad_zs)) * 1000), rad_t], "mm", "calc",
    "each: bounding width × height × thickness of the tapered outline (layout.back_radiators)")
n_fan = put("radiator_fans", 4, "", "design", "2 × 80×25 mm per panel, behind bronze louvers")
d_fan = 0.080
rad_fan_xz = [(0.085, 1.430), (0.085, 1.300)]                # fan centres, left panel


def _inset(p_, a_, b_):
    """signed distance of p inside edge a->b of a clockwise (x, z) outline (> 0 = inside)."""
    ex, ez = b_[0] - a_[0], b_[1] - a_[1]
    return -(ex * (p_[1] - a_[1]) - ez * (p_[0] - a_[0])) / math.hypot(ex, ez)


for fc in rad_fan_xz:                                       # the outline is convex: min inset = clearance to the rim
    assert min(_inset(fc, rad_xz[i], rad_xz[(i + 1) % 6]) for i in range(6)) >= d_fan / 2 + 0.005, "fan does not fit the panel"
assert math.dist(*rad_fan_xz) >= d_fan + 0.010, "fans overlap"
q_air = put("radiator_airflow", 45, "L/s", "design",
            "per panel: 2 fans at 6,000 rpm, ≈33 L/s each in free air, ≈22 L/s against the microchannel core")
dT_air = put("radiator_air_rise", 25, "K", "design", "air 25 °C in -> 50 °C out at the 70 °C design point")
assert T_amb + dT_air < T_cool, "air cannot leave hotter than the coolant that heats it"
C_air = 2 * 1.18 * q_air / 1000 * 1005                      # W/K, both panels
rad_cap = C_air * dT_air
put("radiator_capacity", round(rad_cap), "W", "calc", "2 panels × ρ·V̇·c_p·ΔT of the air stream (25 °C outside air)")
T_pcm = put("pcm_melt_temp", 70, "degC", "design", "paraffin ≈ C32: melts at the radiator design point")
E_pcm = put("pcm_energy", 216, "kJ", "design",
            "1.2 kg paraffin × 180 kJ/kg (conservative), insulated case in the abdomen cavity")
rpm_fan = put("radiator_fan_rpm", 6000, "rpm", "design")
z_fan = put("radiator_fan_blades", 11, "", "design")
z_fs = put("radiator_fan_struts", 3, "", "design", "blade and strut counts coprime: no tonal lock-in")
assert math.gcd(z_fan, z_fs) == 1
put("radiator_fan_bpf", round(rpm_fan / 60 * z_fan), "Hz", "calc")
f_act_heat = put("actuator_heat_fraction", 0.45, "", "design", "share of actuator electrical power that ends up as heat")
m_thermal = 1.2 + 2.5 + 0.9 + 2 * 1.10 + 0.3        # LCVG, chiller+pump+reservoir, coolant, 2 radiators, fans

# ================================================================ power budget + heat budget
prof = {"idle": (0.40, 180), "walk": (0.50, 600), "heavy": (0.10, 2000)}   # (time fraction, actuation W)
assert abs(sum(f for f, _ in prof.values()) - 1) < 1e-9
S["mission_profile"] = [{"mode": k, "time_fraction": f, "actuation_W": w} for k, (f, w) in prof.items()]
P_hud = put("hud_compute_power", 120, "W", "design", "4 cameras, 2 displays, sensors, compute")
P_aux = put("fans_pumps_power", 60, "W", "design", "radiator fans + coolant pump")
P_cont = P_chill + P_hud + P_cryo + P_aux
put("power_continuous_loads", P_cont, "W", "calc", "chiller + HUD + cryocooler + fans/pumps")
P_act_avg = sum(f * w for f, w in prof.values())
P_avg = put("power_mission_average", round(P_act_avg + P_cont), "W", "calc", "on the 270 V bus")
P_heavy = put("power_heavy", prof["heavy"][1] + P_cont, "W", "calc", "heavy work on the 270 V bus")
put("core_power_bus", round(P_core * eta_pc), "W", "calc", "rated core output after conditioning")
assert P_heavy <= P_core * eta_pc, "heavy work must be sustainable by the core alone"


def core_state(P_bus, P_act):
    """fusion power, core heat and total radiator load for a given bus load."""
    P_out = P_bus / eta_pc
    Pf = P_out / eta_core
    heat = (Pf - P_out) + (P_out - P_bus) + f_act_heat * P_act + Q_cond + P_hud + P_cryo + P_aux
    return Pf, heat


Pf_avg, heat_avg = core_state(P_avg, P_act_avg)
Pf_hvy, heat_hvy = core_state(P_heavy, prof["heavy"][1])
put("core_fusion_power_mission", round(Pf_avg), "W", "calc")
put("heartbeat_mission", round(Pf_avg / E_pel * 60), "bpm", "calc", "calm walking pace")
P_sb = put("power_standby", P_hud + P_cryo, "W", "calc", "empty suit in the cradle: sensors + cryocooler keep running")
put("heartbeat_standby", round(P_sb / eta_pc / eta_core / E_pel * 60), "bpm", "calc", "a sleeping pulse")
put("heartbeat_heavy", round(Pf_hvy / E_pel * 60), "bpm", "calc", "heavy work: the core's pulse rises")
put("radiator_load_mission", round(heat_avg), "W", "calc")
put("radiator_load_heavy", round(heat_hvy), "W", "calc")
assert heat_avg <= rad_cap, "radiators cannot carry the mission average"
eps_air = dT_air / (T_cool - T_amb)                       # air-side effectiveness at the design point
T_cool_avg = T_amb + heat_avg / C_air / eps_air           # loop temperature at mission average, fans at full speed
put("coolant_temp_mission", rd(T_cool_avg, 1), "degC", "calc", "same radiator effectiveness at the lower mission load")
assert T_cool_avg < T_pcm - 5, "wax must stay solid at mission average (it is the reserve for heavy work)"
assert T_pcm <= T_cool, "wax must melt before the loop passes the radiator design point"
put("radiator_deficit_heavy", round(heat_hvy - rad_cap), "W", "calc", "heat the wax must absorb during heavy work")
t_burst = E_pcm * 1000 / max(heat_hvy - rad_cap, 1)
put("heavy_work_burst", rd(t_burst / 60, 1), "min", "calc", "melting wax absorbs the heat the radiators cannot")
put("pcm_recharge", rd(E_pcm * 1000 / (rad_cap - heat_avg) / 60, 1), "min", "calc", "wax re-freezes at mission average")
assert t_burst >= 180, "heavy work must last at least 3 minutes"
life_s = mag * 1e-3 / (Pf_avg / E_pel * m_fuel_pulse)
put("fuel_life_mission", round(life_s / 86400), "days", "calc", "continuous at mission-average power")
put("fuel_use_mission", rd(Pf_avg / E_pel * m_fuel_pulse * 3600 * 1e6, 3), "mg/h", "calc")
P_limp = put("power_limp_home", prof["idle"][1] + P_hud, "W", "calc", "after a scram: idle actuation + HUD only")
put("scram_reserve_time", round(E_sc / P_limp * 60, 1), "min", "calc", "buffer alone: kneel, open latches, step out")
put("endurance_limit", "pilot shift & 1,000 h core service interval — not fuel", "", "design")

# ================================================================ mass budget
put("gauntlet_mechanism_mass", 0.90, "kg", "design", "per hand: finger linkage + grip-lock clutch")
d_rod = put("ankle_rod_diameter", 12, "mm", "design", "17-4PH H900, hard-chrome")
_ap = X["ankle_pitch"]
L_rod = math.dist(_ap["c"], _ap["joint"])
put("ankle_rod_length", round(L_rod * 1000), "mm", "calc", "parallelogram: actuator axis -> ankle axis")
m_rodset = math.pi * (d_rod / 2000) ** 2 * L_rod * 7780 + 2 * 0.04 + 2 * 0.05   # rod + 2 rod ends + 2 cranks
budget = [
    ("Joint actuators ×24 (L14 / M7 / S3)", m_act),
    ("Actuator cooling jackets & manifolds ×24", 1.20),
    ("Exo frame: Ti-6Al-4V links & clevises, CFRP spine & pelvis", 14.00),
    ("Trunk arc rail + sector gear", 0.80),
    ("Atlas ring + helmet pitch hinges", 0.55),
    ("Armor panels 120+ (CFRP/aramid, Ti impact panels, latches)", m_armor),
    ("Helmet sensor module (4 cameras, 2 displays, IMU, ANC)", 1.40),
    ("KEEL CORE system (core, shield, cryocooler, conditioning)", m_core),
    ("Buffer bank (lithium-ion capacitors)", m_sc),
    ("Thermal: cooling garment, chiller, coolant, 2 back radiators, fans", m_thermal),
    ("Phase-change heat buffer (paraffin + case)", 1.40),
    ("Knee dampers ×2 (semi-active hydraulic)", 1.20),
    ("Ankle push-rod linkages ×2", 2 * m_rodset),
    ("Gauntlet finger mechanisms ×2", 2 * 0.90),
    ("Fasteners ≈700 (M2–M8, Ti / steel)", 2.10),
    ("Electronics, sensors, 270 V harness", 3.00),
    ("Pilot harness, soft goods", 2.00),
]
S["mass_budget"] = [{"item": k, "kg": rd(v)} for k, v in budget]
m_suit = sum(v for _, v in budget)
m_sys = m_suit + m_pilot
put("suit_mass", rd(m_suit, 1), "kg", "calc", "without pilot")
put("system_mass", rd(m_sys, 1), "kg", "calc", "suit + pilot")

# ================================================================ actuation
Tk = put("knee_torque_design", round(1.5 * m_sys), "N·m", "calc", "1.5 N·m/kg × system mass (stairs, deep squat)")
T_peak = {"L": Tk, "M": 70, "S": 18}
for k in ACT:
    S["actuator_classes"][k]["peak_Nm"] = T_peak[k]
    S["actuator_classes"][k]["density_Nm_per_kg"] = round(T_peak[k] / ACT[k][1])
    assert T_peak[k] / ACT[k][1] < 360 / 1.9, f"class {k} above state-of-the-art torque density"
put("L_torque_density", round(Tk / ACT["L"][1]), "N·m/kg", "calc", "peak; below Unitree M107 189 N·m/kg")
# knee / hip / ankle-pitch reducer: 1-stage planetary
Zs, Zr = 12, 96
Zp = (Zr - Zs) // 2
assert (Zs + Zr) % 3 == 0
put("planetary_sun_teeth", Zs, "", "design")
put("planetary_ring_teeth", Zr, "", "design")
put("planetary_planet_teeth", Zp, "", "calc")
put("planetary_planet_count", 3, "", "design")
ratio = put("planetary_ratio", 1 + Zr / Zs, "", "calc", "ring fixed, sun in, carrier out")
put("planetary_assembly_check", (Zs + Zr) // 3, "", "calc", "(Zs+Zr)/N integer => assemblable")
mod = put("gear_module", 1.0, "mm", "design")
put("sun_planet_centre_distance", mod * (Zs + Zp) / 2, "mm", "calc")
alpha = math.radians(20)
put("pressure_angle", 20, "deg", "const")
put("undercut_limit_teeth", rd(2 / math.sin(alpha) ** 2), "", "calc", "z_min = 2/sin²α for a standard gear (x = 0)")
x_s = put("profile_shift_sun", 0.30, "", "design", "S0 gearing: x_sun + x_planet = 0")
put("profile_shift_planet", -0.30, "", "design")
put("profile_shift_ring", -0.30, "", "design", "internal mesh keeps a = m(Zr−Zp)/2")


def zmin(x):
    return 2 * (1 - x) / math.sin(alpha) ** 2


put("undercut_limit_shifted", rd(zmin(x_s)), "", "calc", "z_min = 2(1−x)/sin²α")
assert Zs >= zmin(x_s), "sun gear would be undercut"
put("ring_planet_centre_distance", mod * (Zr - Zp) / 2, "mm", "calc", "must equal sun–planet distance")
assert mod * (Zr - Zp) / 2 == mod * (Zs + Zp) / 2
Tm = Tk / ratio
put("knee_motor_torque_peak", rd(Tm, 1), "N·m", "calc")
b_face = put("gear_face_width", 20, "mm", "design")
Y12 = 0.245                                           # Lewis form factor, 12T, 20° full depth, x = 0 (conservative)
Ft = Tm * 1000 / (mod * Zs / 2) / 3                   # N per mesh, 3 planets share the load
sb = Ft / (b_face * mod * Y12)
put("sun_tangential_force", round(Ft), "N", "calc", "per planet mesh")
put("sun_bending_stress", round(sb), "MPa", "calc", "Lewis, simplified; x = +0.3 makes the real root thicker")
put("gear_bending_allow", 500, "MPa", "const", "case-hardened 18CrNiMo7-6, approx.")
put("gear_FoS", rd(500 / sb), "", "calc")
assert 500 / sb >= 1.5, "sun gear bending safety factor below 1.5"
pp = put("motor_pole_pairs", 14, "", "design", "28 magnets")
put("stator_slots", 24, "", "design", "24s/28p fractional-slot concentrated winding (q = 2/7)")
# shoulder + elbow reducer: strain wave
Zf, Zcs = 200, 202
put("harmonic_flexspline_teeth", Zf, "", "design")
put("harmonic_circular_teeth", Zcs, "", "design")
put("harmonic_drive_ratio", Zf // (Zcs - Zf), "", "calc", "Zf/(Zc−Zf); shoulders & elbows (hold loads)")
mh = put("harmonic_module", 0.4, "mm", "design")
put("harmonic_flexspline_pd", rd(mh * Zf), "mm", "calc", "pitch diameter (size-32 class)")
put("harmonic_circular_pd", rd(mh * Zcs), "mm", "calc")
put("harmonic_radial_deflection", rd(mh * (Zcs - Zf) / 2), "mm", "calc", "wave generator: w0 = m(Zc−Zf)/2")
w_el = put("elbow_velocity_typ", 3.0, "rad/s", "design", "brisk arm motion")
f_wg = w_el * (Zf // (Zcs - Zf)) / (2 * math.pi)
put("harmonic_vibration_freq", rd(2 * f_wg, 1), "Hz", "calc", "2 × wave-generator rotation (two lobes)")
# ankle pitch: calf-mounted L actuator + parallelogram push rod ("Achilles linkage")
crank = put("ankle_crank_radius", 60, "mm", "design", "both cranks equal -> 1:1")
F_rod = Tk / (crank / 1000)
put("ankle_rod_force", round(F_rod), "N", "calc", "L-class peak / crank")
I_rod = math.pi * d_rod ** 4 / 64
P_cr = math.pi ** 2 * 197000 * I_rod / (L_rod * 1000) ** 2
put("ankle_rod_buckling_load", round(P_cr), "N", "calc", "Euler, pinned–pinned, E 197 GPa")
put("ankle_rod_buckling_FoS", rd(P_cr / F_rod), "", "calc")
assert P_cr / F_rod >= 3.0, "push rod buckling margin below 3"
put("ankle_rod_stress", round(F_rod / (math.pi * d_rod ** 2 / 4)), "MPa", "calc")
z_hip, z_ank, z_act = J["hip"][2], J["ankle"][2], _ap["c"][2]
put("leg_inertia_saving", rd(ACT["L"][1] * ((z_hip - z_ank) ** 2 - (z_hip - z_act) ** 2), 3), "kg·m²", "calc",
    "about the hip, point mass: ankle actuator moved up to the calf")
# trunk sector gear (curved rail behind the lumbar spine) and atlas ring (helmet yaw)
put("trunk_arc_radius", round(R_t * 1000), "mm", "calc", "rail pitch radius around the lumbar spine axis")
put("trunk_arc_span", arc_deg, "deg", "design", "± torso twist")
put("trunk_sector_teeth", math.ceil(Zt * (2 * arc_deg + 10) / 360), "", "calc", "teeth actually cut on the sector")
put("trunk_gear_teeth_full", Zt, "", "design", "equivalent full-circle tooth count, module 2.0")
put("trunk_pinion_teeth", Ztp, "", "design")
put("trunk_ratio", rd(Zt / Ztp), "", "calc")
put("trunk_torque", round(T_peak["M"] * Zt / Ztp), "N·m", "calc", "M-class peak × sector ratio")
assert Ztp >= zmin(x_tp), "trunk pinion would be undercut"
put("atlas_ring_teeth", Zc, "", "design")
put("atlas_pinion_teeth", Zcp, "", "design")
put("atlas_ring_module", mc, "mm", "design")
put("atlas_ring_pd", rd(Zc * mc, 1), "mm", "calc", "pitch diameter")
put("atlas_ratio", rd(Zc / Zcp), "", "calc")
put("atlas_ring_tilt", 22, "deg", "design", "front lower than back: clears the chin")
put("atlas_torque", round(T_peak["S"] * Zc / Zcp), "N·m", "calc", "S-class peak × ring ratio")
assert Zcp >= zmin(x_cp), "atlas pinion would be undercut"
put("encoder_bits", 17, "bit", "design", "motor side and output side (dual encoder)")
put("encoder_cpr", 2 ** 17, "counts/rev", "calc")
w_knee = put("knee_peak_velocity", 6.0, "rad/s", "design", "~345 deg/s gait peak")
w_mot = w_knee * ratio
put("knee_motor_rpm_gait", round(w_mot * 60 / (2 * math.pi)), "rpm", "calc")
put("motor_elec_freq_gait", rd(w_mot / (2 * math.pi) * pp, 1), "Hz", "calc")
put("gear_mesh_freq_gait", rd(Zs * (w_mot - w_knee) / (2 * math.pi), 1), "Hz", "calc")
put("ratchet_teeth", 72, "", "design", "torque wrench")
put("ratchet_step", 360 / 72, "deg", "calc")
for k, v in {"loop_current": 20000, "loop_torque": 1000, "loop_gait": 500}.items():
    put(k, v, "Hz", "design")

# ================================================================ lift (90 kg, both arms)
m_lift = put("lift_mass", 90, "kg", "design", "cf. Sarcos Guardian XO 90 kg")
lev = fore_arm + 0.4 * hand
put("lift_lever", rd(lev, 4), "m", "calc", "elbow axis -> grip centre (forearm + 0.4 × hand)")
M_el = m_lift / 2 * g * lev
put("lift_elbow_moment", rd(M_el, 1), "N·m", "calc", "per arm, elbow at 90°")
put("lift_elbow_fraction", rd(M_el / Tk), "", "calc", "of the L-class peak")
assert M_el < 0.8 * Tk
m_fa = put("forearm_assembly_mass", 3.5, "kg", "design", "forearm armor + wrist actuator + gauntlet")
put("lift_shoulder_moment", rd(M_el + m_fa * g * 0.15, 1), "N·m", "calc", "forearm level, its CoM 0.15 m out")
put("grip_lock", "ratchet clutch per finger group", "", "design",
    "the gauntlet holds the load, not the pilot's fingers")

# ================================================================ landing: 1.5 m drop
h = put("drop_height", 1.5, "m", "design", "design-limit drop with the dampers armed")
v = math.sqrt(2 * g * h)
put("impact_velocity", rd(v), "m/s", "calc")
s = put("landing_stroke", 0.50, "m", "design", "CoM travel: ankle + knee + hip flexion into a deep squat")
n_g = put("landing_load_factor", rd(1 + h / s), "g", "calc", "ground force / weight = 1 + h/s")
put("landing_decel", rd(v ** 2 / (2 * s) / g), "g", "calc", "net deceleration")
F_g = n_g * m_sys * g
F_leg = F_g / 2
t_land = 2 * s / v
put("landing_force", round(F_g), "N", "calc", "total ground reaction")
put("landing_force_per_leg", round(F_leg), "N", "calc", "symmetric landing")
put("landing_time", rd(t_land, 3), "s", "calc", "constant deceleration")
lev_k = put("knee_lever_landing", 0.18, "m", "design", "knee axis to the ground-reaction line, deep squat")
M_kl = F_leg * lev_k
put("knee_moment_landing", round(M_kl), "N·m", "calc")
T_d = put("damper_torque", 400, "N·m", "design", "semi-active hydraulic, parallel to the knee actuator")
put("knee_capacity_landing", Tk + T_d, "N·m", "calc", "actuator peak + damper")
assert Tk + T_d >= M_kl, "knee cannot hold the 1.5 m landing"
put("knee_landing_margin", rd((Tk + T_d) / M_kl), "", "calc")
lev_d = put("damper_lever", 45, "mm", "design")
F_d = T_d / (lev_d / 1000)
put("damper_force", round(F_d), "N", "calc")
bore = put("damper_bore", 22, "mm", "design")
p_d = F_d / (math.pi * bore ** 2 / 4) * 10
put("damper_pressure", round(p_d), "bar", "calc")
p_rated = put("damper_pressure_rated", 400, "bar", "design")
assert p_d < p_rated
put("damper_stroke", round(lev_d * math.radians(60)), "mm", "calc", "60° knee flexion during the landing")
E_land = m_sys * g * (h + s)
put("landing_energy", round(E_land), "J", "calc", "= m g (h + s) = ground force × stroke")
f_knee = put("landing_knee_share", 0.60, "", "design", "knee-dominant soft landing")
E_d = E_land * f_knee / 2 * T_d / (Tk + T_d)
put("damper_energy", round(E_d), "J", "calc", "per knee damper")
m_oil = put("damper_oil_mass", 60, "g", "design")
put("damper_oil_temp_rise", rd(E_d / (m_oil / 1000 * 1900), 1), "K", "calc", "per landing, oil only (1.9 kJ/kg·K)")
E_act = E_land - 2 * E_d
E_rg = min(0.70 * E_act, P_sc * t_land)
put("landing_actuator_energy", round(E_act), "J", "calc", "absorbed by the joint actuators")
put("landing_regen", round(E_rg), "J", "calc", "into the capacitor buffer (70 % motor/driver efficiency)")
put("landing_brake_heat", round(E_act - E_rg), "J", "calc", "windings + drivers")
t_ff = put("free_fall_time", rd(math.sqrt(2 * h / g), 3), "s", "calc")
t_det = put("free_fall_detect", 80, "ms", "design", "|a| < 0.3 g for 80 ms -> dampers armed")
t_valve = put("damper_valve_time", 20, "ms", "design")
put("damper_arm_margin", round(t_ff * 1000 - t_det - t_valve), "ms", "calc")
assert t_ff * 1000 - t_det - t_valve > 200
put("landing_freeze", 0.3, "s", "design", "screen freeze at ground contact")

# ================================================================ structure: thigh link
D, d = 34.0, 30.0
I_l = math.pi / 64 * (D ** 4 - d ** 4)
F_link = F_g                   # asymmetric worst case: the whole landing force on one leg
e_l = 60.0
M_l = F_link * e_l
sig = M_l * (D / 2) / I_l
put("link_OD", D, "mm", "design")
put("link_ID", d, "mm", "design")
put("link_I", round(I_l), "mm⁴", "calc")
put("link_load", round(F_link), "N", "calc", "4 g landing force on ONE leg (asymmetric worst case)")
put("link_eccentricity", e_l, "mm", "design")
put("link_moment", round(M_l / 1000), "N·m", "calc")
put("link_stress", round(sig), "MPa", "calc", "σ = M c / I")
put("link_FoS", rd(880 / sig), "", "calc")
assert 880 / sig >= 3.0, "thigh link safety factor below 3"
put("ti_fatigue_limit", 500, "MPa", "const", "approx., 1e7 cycles")
assert sig < 500

# ================================================================ fasteners & latches
As = put("bolt_M6_stress_area", 20.1, "mm²", "const", "ISO 898")
put("bolt_pitch", 1.0, "mm", "const", "M6 coarse")
put("bolt_engagement", 12, "mm", "design", "2.0 × d in the Al housing (DFM guide: ≥ 1.5 × d)")
put("bolt_turns", 12, "rev", "calc", "engagement / pitch")
Fi = 0.75 * 0.9 * 880 * As
put("bolt_preload", round(Fi), "N", "calc", "0.75 × proof (0.9 σy) × As")
put("bolt_torque", rd(0.2 * Fi * 6 / 1000, 1), "N·m", "calc", "T = K F d, K = 0.2 (anti-seize on Ti)")
flange = {"L": 12, "M": 8, "S": 6}
S["flange_bolts"] = flange
put("flange_bolt_total", sum(ACT[k][0] * flange[k] for k in ACT), "", "calc", "actuator output flanges")
put("flange_pcd_L", 96, "mm", "design", "L-class 12-bolt circle")
put("hero_inspection_bolts", 12, "", "design", "left-knee output flange: the hero torque-wrench game")
put("closeup_unscrew_bolts", 48, "", "design", "hip-flex ×2 + knee ×2 flanges, full 12 turns in the exploded view")
assert 4 * flange["L"] == 48
S["bolt_sequence"] = {                                 # cross (star) tightening patterns
    "12": [1, 7, 4, 10, 2, 8, 5, 11, 3, 9, 6, 12],
    "8": [1, 5, 3, 7, 2, 6, 4, 8],
    "6": [1, 4, 2, 5, 3, 6],
}
for k_, seq in S["bolt_sequence"].items():
    assert sorted(seq) == list(range(1, int(k_) + 1))
put("latch_type", "over-center (toggle) latch + locating pins", "", "design", "robot cell operates them")
put("latch_preload", 500, "N", "design", "elastomer seal compressed 1.0 mm (k = 500 N/mm)")
put("latch_overcenter", 4, "deg", "design", "past dead centre -> self-locking; Hall sensor confirms")

# ================================================================ materials
mats = {
    "Ti-6Al-4V":         {"rho": 4.43, "E": 114, "strength": 880, "su": 950, "Tmax": 400,
                          "use": "frame links, clevises, actuator rings (anodized), impact panels"},
    "Al 7075-T6":        {"rho": 2.81, "E": 71.7, "strength": 503, "su": 572, "Tmax": 120,
                          "use": "actuator housings, brackets, radiator cores"},
    "CFRP [0/±45/90]s":  {"rho": 1.55, "E": 50, "strength": 600, "su": 600, "Tmax": 120,
                          "use": "armor skin, spine & pelvis frame"},
    "Aramid/epoxy":      {"rho": 1.38, "E": 30, "strength": 500, "su": 500, "Tmax": 120,
                          "use": "armor inner liner (strong in tension, catches fragments)"},
    "17-4PH H900":       {"rho": 7.78, "E": 197, "strength": 1170, "su": 1310, "Tmax": 300,
                          "use": "damper rods & push rods (hard-chrome), latch hooks, pins"},
    "18CrNiMo7-6":       {"rho": 7.85, "E": 210, "strength": 850, "su": 1200, "Tmax": 150,
                          "use": "gears (case-hardened)"},
}
for m_ in mats.values():
    m_["specific_strength"] = round(m_["strength"] / m_["rho"])     # kN·m/kg; yield for metals, UTS for composites
S["materials"] = mats
S["core_materials"] = [
    {"name": "REBCO tape", "use": "mirror coils (high-temperature superconductor, real)"},
    {"name": "W-Ni-Fe heavy alloy (ρ ≈ 17.6)", "use": "shadow shield, X-rays"},
    {"name": "B4C (ρ ≈ 2.52)", "use": "shadow shield, neutrons"},
    {"name": "Gold MLI (aluminized polyimide)", "use": "thermal insulation between core and chest"},
]
S["cfrp_layup"] = [0, 45, -45, 90]
S["material_note"] = ("CFRP has the highest specific strength, yet the links are Ti-6Al-4V: isotropic and damage / "
                      "fatigue tolerant at clevises and threads. CFRP is used where loads are spread over large, "
                      "simple shapes (armor, spine, pelvis); aramid backs it because it is strong in tension and "
                      "catches fragments.")
# titanium anodizing: interference colour of a thin transparent TiO2 film (no dye, no paint)
k_an = put("anodize_growth", 2.0, "nm/V", "design",
           "anodic TiO2 ≈ 1.5–2.5 nm/V by electrolyte; 2.0 matches a thin-film render against the colour chart")
put("anodize_film_ior", 2.2, "", "const", "anodic TiO2 ≈ 2.1–2.4")
V_au = put("anodize_gold_voltage", 62, "V", "design", "2nd-order gold: the rotation rings")
put("anodize_gold_thickness", round(V_au * k_an), "nm", "calc")
V_br = put("anodize_bronze_voltage", 12.5, "V", "design", "1st-order bronze: radiator louvers")
put("anodize_bronze_thickness", round(V_br * k_an), "nm", "calc")
S["anodize_chart"] = [{"V": V_, "nm": round(V_ * k_an), "name": nm_} for V_, nm_ in (
    (0, "bare Ti"), (7.5, "light straw"), (12.5, "bronze (1st-order gold)"), (17.5, "purple"), (22.5, "blue"),
    (30, "light blue"), (37.5, "pale blue-silver"), (42.5, "silver"), (47.5, "champagne"), (55, "pale gold"),
    (62, "gold (2nd order)"), (70, "copper"), (80, "magenta"), (90, "deep blue (2nd order)"))]
S["anodize_note"] = "colour names from a Cycles thin-film render (Ti base, film IOR 2.2), 2026-09-30; approximate"
# 3D palette (area share of the visible exterior; the model manifest measures the real shares)
S["palette_3d"] = [
    {"name": "graphite", "finish": "CFRP, clear-coat, twill weave", "share": [0.40, 0.50], "where": "armor faces (resting surfaces)"},
    {"name": "gunmetal", "finish": "bead-blasted Ti-6Al-4V", "share": [0.25, 0.32], "where": "frame, housings, impact panels, helmet shell (the brow is part of it)"},
    {"name": "platinum", "finish": "polished Ti keel strips, hard-chrome rods", "share": [0.06, 0.10], "where": "form lines, sternum keel, sliding parts"},
    {"name": "ti_gold", "finish": f"anodized Ti {V_au} V ({round(V_au * k_an)} nm)", "share": [0.09, 0.12], "where": "rotation rings = joint axes, atlas ring, trunk arc rail"},
    {"name": "ti_bronze", "finish": f"anodized Ti {V_br} V ({round(V_br * k_an)} nm)", "share": [0.01, 0.03], "where": "radiator louvers on the back"},
    {"name": "gold", "finish": "gold plating, gold IR film", "share": [0.0, 0.005],
     "where": "contacts, visor tint (point accents; the gold MLI around the core is inside and not counted)"},
]
put("gold_family_share", [0.10, 0.15], "", "design", "ti_gold + ti_bronze + gold, measured on the model")
put("red_share", 0.0, "", "design", "no red anywhere on the suit")
_lo = sum(p_["share"][0] for p_ in S["palette_3d"])
_hi = sum(p_["share"][1] for p_ in S["palette_3d"])
assert _lo <= 1.0 <= _hi, "palette share ranges cannot add up to 100 %"
_gf = [sum(p_["share"][i] for p_ in S["palette_3d"] if p_["name"] in ("ti_gold", "ti_bronze", "gold")) for i in (0, 1)]
assert _gf[0] >= 0.10 - 1e-9 and _gf[1] <= 0.155, f"gold-family sub-ranges {_gf} do not fit 10–15 %"

# ================================================================ sensors & HUD
put("camera_count", 4, "", "design", "2 per eye: forward stereo + temporal wide (raptors have two foveae per eye)")
put("stereo_baseline", 64, "mm", "design", "= pilot IPD, so distances are not distorted")
fps = put("camera_fps", 120, "fps", "design")
t_proc = put("hud_processing_time", 4.0, "ms", "design")
hz = put("display_refresh", 120, "Hz", "design", "2 micro-OLED displays")
lat = 1000 / fps + t_proc + 0.5 * 1000 / hz
put("motion_to_photon", rd(lat, 1), "ms", "calc", "exposure/readout + processing + half a scan-out")
put("motion_to_photon_max", 20, "ms", "design", "comfort limit for camera pass-through")
assert lat <= 20
put("eye_angle", 15, "deg", "design", "upper edge of the eye aperture vs horizontal, seen from the front (sketch had ~27°); review range 12–18°")
put("uv_channel", "near-UV on the temporal cameras", "", "design",
    "nod to kestrels seeing vole scent marks in UV (Viitala et al., 1995)")
put("cuff_force_sensors", 4, "", "design", "6-axis F/T at forearm and shank cuffs (intent estimation)")
put("foot_pressure_insoles", 2, "", "design")
put("face_keel_release", "manual pull handle", "", "design", "direct view if the cameras fail")

# ================================================================ sound physics
S["beam_mode_ratios"] = [1.0, 2.756, 5.404, 8.933]           # free–free beam: metal impacts
S["cantilever_mode_ratios"] = [1.0, 6.267, 17.547, 34.386]   # clamped–free: latch hooks
put("mains_hum", 120, "Hz", "calc", "2 × 60 Hz grid (KR)")
put("hangar_rt60", 2.5, "s", "design")

# ================================================================ geometry layout part 2: core, radiators, robot cell
core_r = core_d / 2000
core_c = v3(0, -(chest_d + 0.005 + t_sh / 1000 + core_r), J["chest"][2] + 0.02)
core_z = [core_c[2] - core_len / 2000, core_c[2] + core_len / 2000]
assert core_z[1] < J["jugular"][2] - 0.005, "core runs into the neck"
keel_front = core_c[1] - core_r - 0.012                      # gap + armor + keel strip
put("keel_protrusion", round(-(keel_front + chest_d) * 1000), "mm", "calc", "keel ridge in front of the pilot's chest")
rad_y = [0.195, 0.195 + rad_t / 1000]                          # outline rad_xz and fans: thermal section
area = 0.5 * abs(sum(rad_xz[i][0] * rad_xz[(i + 1) % 6][1] - rad_xz[(i + 1) % 6][0] * rad_xz[i][1] for i in range(6)))
put("radiator_panel_area", rd(area, 4), "m²", "calc", "frontal area of one tapered panel")


def box(c, size):
    return [[c[i] - size[i] / 2, c[i] + size[i] / 2] for i in range(3)]


def act_box(name):
    v_ = X[name]
    OD_, W_ = ACT[v_["cls"]][3] / 1000, ACT[v_["cls"]][4] / 1000
    ax = v_["axis"]
    ext = [W_ if (isinstance(ax, list) and abs(ax[i]) > 0.9) else OD_ for i in range(3)]
    return box(v_["c"], ext)


def clash(a, b, gap=0.0):
    return all(a[i][0] < b[i][1] + gap and b[i][0] < a[i][1] + gap for i in range(3))


rad_box = [[min(rad_xs), max(rad_xs)], rad_y, [min(rad_zs), max(rad_zs)]]
core_box = box(core_c, [core_d / 1000, core_d / 1000 + t_sh / 1000, core_len / 1000])
chest_box = [[-0.16, 0.16], [-chest_d, chest_d], [J["chest"][2] - 0.2, J["jugular"][2]]]
checks = {
    "core+shield vs pilot chest": clash(core_box, chest_box, -0.004),
    "radiator vs shoulder_abd": clash(rad_box, act_box("shoulder_abd"), 0.008),
    "radiator vs trunk_rot": clash(rad_box, act_box("trunk_rot"), 0.02),
    "radiator vs neck actuator": clash(rad_box, act_box("neck"), 0.02),
}
S["clash_checks_static"] = {k: ("CLASH" if v_ else "clear") for k, v_ in checks.items()}
assert not any(checks.values()), S["clash_checks_static"]
cell = {
    "platform": {"d": 1.40, "height": 0.12, "note": "turntable positioner, top at z = 0"},
    "gantry": {"post_x": 1.60, "post_y": 0.30, "beam_z": 3.00, "note": "Z-hoist lowers the helmet parts from above; the KEEL CORE never leaves the suit"},
    "arms": [{"base": [sx * 1.05, y_, 0.0], "reach": 1.65} for y_ in (-0.55, 0.75) for sx in (1, -1)],
    "racks": {"x": 2.10, "y": [-1.0, 1.0], "depth": 0.60, "height": 2.0, "note": "armor panels in foam fixtures"},
    "cradle": {"post_y": 0.62, "height": 1.60, "clamp_z": 1.45, "note": "holds the empty suit at the back frame"},
}
for a_ in cell["arms"]:
    assert math.dist(a_["base"][:2], (0, 0)) < a_["reach"], "robot arm cannot reach the suit axis"
S["layout"] = {
    "frame": "Blender metres, Z up, front = −Y, +X = suit LEFT; glTF (x, z, −y)",
    "z0_barefoot": rd(z0, 4),
    "pilot": J,
    "exo": X,
    "forearm_dir": fa,
    "keel_core": {"c": core_c, "d": core_d / 1000, "len": core_len / 1000, "axis": [0, 0, 1],
                  "shield_y": [round(-(chest_d + 0.005 + t_sh / 1000), 4), round(-(chest_d + 0.005), 4)],
                  "keel_front_y": round(keel_front, 4)},
    "back_radiators": {"outline_xz": rad_xz, "y": rad_y, "fans_xz": rad_fan_xz, "fan_d": d_fan,
                       "note": "mirror x; flush with the back armor; bronze louvers; magnet guides + latches + dry-break coupling"},
    "trunk_arc": {"c": spine_c, "R": R_t, "span_deg": arc_deg},
    "atlas_ring": {"c": atlas_c, "pd": Zc * mc / 1000, "tilt_deg": 22},
    "cell": cell,
}

# ================================================================ headline values for the page
S["_headline"] = {"suit_mass": rd(m_suit, 1), "system_mass": rd(m_sys, 1), "knee_torque": Tk,
                  "landing_force": round(F_g), "drop_height": h, "lift_mass": m_lift, "core_power": P_core,
                  "fuel_life_days": round(life_s / 86400), "heartbeat_rated": round(bpm_rated)}

root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(root, "specs.json"), "w") as f:
    json.dump(S, f, ensure_ascii=False, indent=1)
# (the web app imports calc/specs.json directly through Vite; no generated JS copy)
for k, v_ in S.items():
    if isinstance(v_, dict) and "v" in v_:
        print(f"{k:32s} {v_['v']!s:>14} {v_['unit']:10s} [{v_['tag']}]")
print("mass budget:", *(f"\n  {b['kg']:6.2f}  {b['item']}" for b in S["mass_budget"]))
print("clash:", S["clash_checks_static"])
