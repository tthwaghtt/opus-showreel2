"""HX-01 KESTREL — engineering calculation sheet, v2 (2026-09-30).

v2 concept: a full-body armored powered suit. The pilot stands inside a dense internal mechanical layer
(24 joint actuators, frame, power, cooling, sensors); 120+ separate armor panels latch onto that layer.
No flight (no turbines). Power = hydrogen fuel cell + buffer battery in the back. Chest carries no power source.

Every engineering number shown on the showreel page comes from this file (calc/specs.json).
Part COUNTS and model envelope sizes come from the Blender model manifest instead (never typed by hand).
Tags: spec = vendor datasheet / published reference, design = chosen value, calc = computed here,
      const = physical constant or textbook value.
Run:  python3 calc/specs.py      (a failing assert means a design rule is broken: fix the design, not the assert)
"""
import json
import math
import os

g = 9.81
S = {}


def put(key, value, unit, tag, note=""):
    S[key] = {"v": value, "unit": unit, "tag": tag, "note": note}
    return value


def rd(x, n=2):
    return round(x, n)


# ================================================================ general
put("spec_version", "v2", "", "design", "2026-09-30: full armor, no flight, hydrogen fuel cell")
m_pilot = put("pilot_mass", 75.0, "kg", "design", "50th-percentile adult male")
H = put("pilot_height", 1.75, "m", "design", "barefoot stature")

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

# ================================================================ geometry layout part 1: pilot + joints
# Blender frame: metres, Z up, suit faces −Y, +X = suit's LEFT (.L). glTF/three: (x, z, −y).
# Pilot: H = 1.75 m barefoot; segment ratios after Drillis & Contini (fractions of H).
foot_plate = put("foot_plate_thickness", 0.020, "m", "design", "exo foot plate under the boot")
boot_sole = put("boot_sole_thickness", 0.025, "m", "design")
z0 = foot_plate + boot_sole
ratio_h = {"ankle": 0.039, "knee": 0.285, "hip": 0.529, "gh": 0.794, "elbow": 0.631, "head_top": 1.0}
upper_arm = 0.163 * H          # GH centre -> elbow axis
fore_arm = 0.146 * H           # elbow -> wrist
abd = math.radians(12)         # rest pose: arms abducted 12°
flex = math.radians(15)        # rest pose: elbows flexed 15° forward
put("upper_arm_length", round(upper_arm * 1000), "mm", "calc", "0.163 H")
put("forearm_length", round(fore_arm * 1000), "mm", "calc", "0.146 H")


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

# ring gears that let big joints rotate around the body (turret-style), both driven by a pinion
Zw, Zwp, mw, x_wp = 170, 17, 2.0, 0.10      # waist: trunk rotation
Zc, Zcp, mc, x_cp = 96, 12, 2.25, 0.30      # collar: helmet yaw
waist_c = v3(0, 0.060, J["lumbar"][2])     # on the lumbar spine axis, not behind it (no misalignment)
collar_c = v3(0, 0.010, J["c7"][2] + 0.031)
a_w = (Zw + Zwp) * mw / 2000               # m, pinion centre distance
a_c = (Zc + Zcp) * mc / 2000

# exo joints: centre, axis (unit, Blender frame, LEFT side), class. Axes pass through (or near) pilot joints.
X = {
    "hip_abd":      {"c": v3(0.135, 0.150, J["hip"][2] + 0.055), "axis": [0, 1, 0], "cls": "L",
                     "note": "behind the hip on the pelvis frame; 6–7 cm misalignment taken by a passive slider"},
    "hip_flex":     {"c": v3(0.190 + Lw / 2, 0.0, J["hip"][2]), "axis": [1, 0, 0], "cls": "L"},
    "hip_rot":      {"c": None, "axis": "link", "cls": "M",
                     "note": "in-line with the thigh link, 40 % down from the hip actuator (a twist ring)"},
    "knee":         {"c": v3(0.150 + Lw / 2, J["knee"][1], J["knee"][2]), "axis": [1, 0, 0], "cls": "L",
                     "note": "parallel semi-active hydraulic damper on the lateral thigh"},
    "ankle_pitch":  {"c": v3(0.165, 0.060, 0.395), "axis": [1, 0, 0], "cls": "L",
                     "joint": v3(0.150, 0.0, J["ankle"][2]),
                     "note": "actuator sits high on the calf and drives the ankle bearing through a crank + push rod "
                             "(Achilles linkage): less mass at the foot"},
    "ankle_roll":   {"c": v3(J["ankle"][0], 0.100, 0.085), "axis": [0, 1, 0], "cls": "M", "note": "behind the heel"},
    "trunk_rot":    {"c": v3(0, waist_c[1] + a_w, waist_c[2] - 0.050), "axis": [0, 0, 1], "cls": "M", "side": "C",
                     "ring": {"c": waist_c, "teeth": Zw, "pinion": Zwp, "module": mw},
                     "note": "on the pelvis frame; its pinion drives the waist ring gear (torso turns on the ring)"},
    "neck":         {"c": v3(0, collar_c[1] + a_c, collar_c[2] - 0.041), "axis": [0, 0, 1], "cls": "S", "side": "C",
                     "ring": {"c": collar_c, "teeth": Zc, "pinion": Zcp, "module": mc},
                     "note": "drives the collar ring: the helmet's weight sits on the suit, not on the pilot's neck"},
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
for k, v in X.items():
    assert (2 if v.get("side") != "C" else 1) and v["cls"] in ACT
_cls_count = {c: sum((1 if v.get("side") == "C" else 2) for v in X.values() if v["cls"] == c) for c in "LMS"}
assert _cls_count == {"L": 14, "M": 7, "S": 3}, _cls_count
_hf, _kn = X["hip_flex"]["c"], X["knee"]["c"]
X["hip_rot"]["c"] = v3(*[_hf[i] + 0.40 * (_kn[i] - _hf[i]) for i in range(3)])

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
            "impact panels (knee / shoulder caps, knuckles, helmet brow) in Ti-6Al-4V: dent instead of shatter")
w_ti = t_tip * 4.43
put("armor_areal_density_ti", rd(w_ti, 3), "kg/m²", "calc")
f_ti = put("armor_ti_area_fraction", 0.15, "", "design")
hw = put("armor_hardware_factor", 0.15, "", "design", "latches, locating pins, edge trims")
m_armor = A_arm * ((1 - f_ti) * w_lam + f_ti * w_ti) * (1 + hw)
put("armor_mass", rd(m_armor), "kg", "calc")
put("armor_panels_min", 120, "", "design", "target; the real count comes from the model manifest")
put("internal_parts_min", 450, "", "design", "target, fasteners excluded; real count from the manifest")
put("fastener_count_target", 700, "", "design", "≈, M2–M8; real count from the manifest")
put("latch_count_target", 150, "", "design", "≈, over-center latches holding the armor; real count from the manifest")
put("armor_panel_gap", 1.2, "mm", "design", "panel line: tolerance + thermal growth")
put("armor_ballistic", "none", "", "design", "impact / abrasion shell only — NOT ballistic protection")

# ================================================================ power: hydrogen fuel cell (back)
# Benchmark: Intelligent Energy IE-SOAR 2.4 (air-cooled PEM module used on drones).
P_fc = put("fc_power_continuous", 2400, "W", "spec", "IE-SOAR 2.4-class air-cooled (open-cathode) PEM module")
m_fc = put("fc_module_mass", 4.80, "kg", "spec", "IE-SOAR 2.4 datasheet")
ref_dim = put("fc_ref_dimensions", [128, 442, 233], "mm", "spec", "IE-SOAR 2.4 module envelope")
V_ref = ref_dim[0] * ref_dim[1] * ref_dim[2] / 1e6
put("fc_ref_volume", rd(V_ref, 1), "L", "calc")
fc_dim = put("fc_module_dimensions", [200, 165, 400], "mm", "design", "x × y × z, repackaged upright along the spine")
V_fc = fc_dim[0] * fc_dim[1] * fc_dim[2] / 1e6
put("fc_module_volume", rd(V_fc, 1), "L", "calc")
assert V_fc >= 0.98 * V_ref, "repackaged module must keep the benchmark volume (same kW per litre)"
N_cell = put("fc_cells", 96, "", "design")
V_cell = put("fc_cell_voltage_rated", 0.65, "V", "design", "at rated power")
put("fc_stack_voltage_rated", rd(N_cell * V_cell, 1), "V", "calc")
I_fc = put("fc_current_rated", rd(P_fc / (N_cell * V_cell), 2), "A", "calc")
A_act = put("fc_active_area", 64, "cm²", "design", "8 × 8 cm per cell")
j_fc = put("fc_current_density", rd(I_fc / A_act, 3), "A/cm²", "calc", "0.4–0.7 typical for air-cooled stacks")
assert 0.3 <= j_fc <= 0.8
put("fc_plates", N_cell + 1, "", "calc", "95 bipolar + 2 terminal plates")
put("fc_bipolar_plates", N_cell - 1, "", "calc")
pitch = put("fc_cell_pitch", 2.4, "mm", "design", "open-cathode plate incl. air channels")
put("fc_stack_length", rd(N_cell * pitch + 2 * 15, 1), "mm", "calc", "cells + 2 × 15 mm end plates")
plate = put("fc_plate_size", [100, 130], "mm", "design")
p_clamp = put("fc_clamp_pressure", 1.0, "MPa", "design", "on the gross plate area")
F_clamp = put("fc_clamp_force", round(p_clamp * plate[0] * plate[1]), "N", "calc")
n_rod = put("fc_tie_rods", 8, "", "design", "M5 class 8.8 with disc-spring stacks")
put("fc_tie_rod_force", round(F_clamp / n_rod), "N", "calc")
assert F_clamp / n_rod < 0.75 * 580 * 14.2, "tie rod above 75 % of proof load"
FARADAY = put("faraday", 96485.33, "C/mol", "const")
M_H2 = put("h2_molar_mass", 2.01588, "g/mol", "const")
LHV = put("h2_lhv", 33.33, "kWh/kg", "const", "120 MJ/kg")
E_lhv = put("h2_lhv_cell_voltage", rd(241.8e3 / (2 * FARADAY), 4), "V", "calc", "ΔH_LHV / 2F")
put("fc_stack_efficiency_rated", rd(V_cell / E_lhv, 3), "", "calc", "V_cell / 1.253 V")
put("fc_h2_flow_rated", rd(N_cell * I_fc * M_H2 / (2 * FARADAY) * 3.6, 4), "kg/h", "calc", "N·I / 2F")
eta_sys = put("fc_system_efficiency", 0.50, "", "design", "net, incl. blowers, controller, purge losses (LHV)")
assert eta_sys <= V_cell / E_lhv, "system efficiency cannot beat the stack"
purge_rated = put("fc_purge_interval_rated", 20, "s", "design", "anode purge valve; interval ∝ 1 / current")
rpm_bl = put("fc_blower_rpm_rated", 12000, "rpm", "design", "2 axial blowers")
z_bl = put("fc_blower_blades", 9, "", "design")
z_bs = put("fc_blower_struts", 4, "", "design", "blade and strut counts coprime: no tonal lock-in")
assert math.gcd(z_bl, z_bs) == 1
put("fc_blower_shaft_freq", rd(rpm_bl / 60, 1), "Hz", "calc")
put("fc_blower_bpf", round(rpm_bl / 60 * z_bl), "Hz", "calc", "blade-pass frequency")
put("fc_exhaust_temp", 60, "degC", "design", "warm, humid stack air; leaves through the lower rear louvers")

# ---- hydrogen storage: 2 × type IV cylinders (PA6 liner, T700-class CFRP), netting analysis
p_nwp = put("h2_pressure", 350, "bar", "design", "nominal working pressure")
T_ref = put("h2_temperature", 288.15, "K", "const", "15 °C reference")
Z350 = put("h2_z_350bar", 1.227, "", "const", "compressibility factor, NIST approx.")
rho350 = p_nwp * 1e5 * M_H2 / 1000 / (Z350 * 8.314462 * T_ref)
put("h2_density_350bar", rd(rho350, 2), "g/L", "calc", "ρ = pM / ZRT")
p_res = put("h2_residual_pressure", 15, "bar", "design", "regulator minimum inlet")
rho_res = p_res * 1e5 * M_H2 / 1000 / (1.009 * 8.314462 * T_ref)
put("h2_density_residual", rd(rho_res, 3), "g/L", "calc", "Z ≈ 1.009")
r_i = put("cyl_inner_radius", 75, "mm", "design")
L_cyl = put("cyl_length", 400, "mm", "design", "overall incl. valve boss = power-pack height")
t_liner = put("cyl_liner_thickness", 2.5, "mm", "design", "PA6 liner")
k_burst = put("cyl_burst_ratio", 2.25, "", "const", "carbon-fibre cylinders, EC 79 value (conservative)")
sig_f = put("cyl_fibre_allowable", 2000, "MPa", "design",
            "wound T700-class CFRP, fibre direction, incl. translation efficiency")
alpha_h = math.asin(15 / r_i)                        # polar boss radius 15 mm
put("cyl_helical_angle", rd(math.degrees(alpha_h), 1), "deg", "calc", "sin α = r_boss / r")
Pb = k_burst * p_nwp / 10                            # MPa
t_hel = Pb * r_i / (2 * sig_f * math.cos(alpha_h) ** 2)
t_hoop = Pb * r_i * (2 - math.tan(alpha_h) ** 2) / (2 * sig_f)
put("cyl_cfrp_helical", rd(t_hel), "mm", "calc", "netting theory")
put("cyl_cfrp_hoop", rd(t_hoop), "mm", "calc", "netting theory")
t_cf_cyl = (t_hel + t_hoop) * 1.10
put("cyl_cfrp_thickness", rd(t_cf_cyl), "mm", "calc", "+10 % dome build-up")
t_wall = t_liner + t_cf_cyl
OD = 2 * (r_i + t_wall)
put("cyl_outer_diameter", rd(OD, 1), "mm", "calc")
h_dome = 0.6 * r_i                                   # isotensoid dome, flatter than a hemisphere
L_c = L_cyl - 2 * t_wall - 30 - 2 * h_dome           # 30 mm boss
V_cyl = (math.pi * r_i ** 2 * L_c + 2 * (2 / 3) * math.pi * r_i ** 2 * h_dome) / 1e6
put("cyl_volume", rd(V_cyl), "L", "calc", "internal; dome height 0.6 r")
a_m, c_m = (r_i + t_wall / 2) / 1000, (h_dome + t_wall / 2) / 1000
e_ = math.sqrt(1 - (c_m / a_m) ** 2)
A_domes = 2 * math.pi * a_m ** 2 + math.pi * c_m ** 2 / e_ * math.log((1 + e_) / (1 - e_))   # 2 domes = 1 spheroid
A_shell = 2 * math.pi * a_m * L_c / 1000 + A_domes
m_cyl = A_shell * (t_cf_cyl * 1.550 + t_liner * 1.140) + 0.20 + 0.30
put("cyl_mass", rd(m_cyl), "kg", "calc", "shell + 0.20 kg boss + 0.30 kg in-tank valve")
n_cyl = put("cyl_count", 2, "", "design", "upright, either side of the fuel cell module")
m_h2 = n_cyl * V_cyl * rho350 / 1000
m_h2_use = n_cyl * V_cyl * (rho350 - rho_res) / 1000
put("h2_mass_full", rd(m_h2, 3), "kg", "calc")
put("h2_mass_usable", rd(m_h2_use, 3), "kg", "calc")
put("cyl_gravimetric", rd(V_cyl * rho350 / 1000 / m_cyl * 100, 1), "wt%", "calc", "stored H2 / cylinder mass")
m_reg = put("h2_regulator_mass", 0.315, "kg", "spec", "IE-SOAR pressure regulator")
put("h2_regulator_out", 0.5, "bar(g)", "design", "stack inlet")
put("h2_lfl", 4.0, "%", "const", "lower flammability limit in air")
put("h2_alarm", 1.0, "%", "design", "25 % LFL, sensor at the pack's highest point (H2 rises)")
put("h2_shutdown", 2.0, "%", "design", "50 % LFL: in-tank valves close")
put("h2_swap_time", 3, "min", "design", "quick-disconnect cylinder swap")

# ---- buffer battery: peaks above the fuel cell, regen, reserve
cell_V = put("batt_cell_voltage", 3.6, "V", "design", "high-power 21700 class (4.5 Ah, 45 A, 70 g)")
cell_Ah = put("batt_cell_capacity", 4.5, "Ah", "design")
cell_A = put("batt_cell_current_max", 45, "A", "design", "10C continuous")
cell_g = put("batt_cell_mass", 70, "g", "design")
ns, npar = 16, 2
put("batt_config", "16S2P", "", "design")
n_cells = put("batt_cells", ns * npar, "", "calc")
V_bus = put("bus_voltage_nominal", rd(ns * cell_V, 1), "V", "calc")
E_b = ns * npar * cell_V * cell_Ah / 1000
put("batt_energy", rd(E_b, 3), "kWh", "calc")
m_b = n_cells * cell_g / 1000 / 0.78
put("batt_mass", rd(m_b), "kg", "calc", "cells are 78 % of pack mass")
P_b = put("batt_power_max", round(npar * cell_A * V_bus), "W", "calc")
put("batt_pack_specific_energy", round(E_b * 1000 / m_b), "Wh/kg", "calc")
c_pulse = put("batt_pulse_charge_rate", 5, "C", "design", "short (< 1 s) regen pulses")
P_regen = put("batt_regen_power_max", round(c_pulse * npar * cell_Ah * V_bus), "W", "calc")
put("bus_power_peak", P_fc + P_b, "W", "calc", "fuel cell + battery")
eta_dc = put("dcdc_efficiency", 0.97, "", "design", "fuel cell -> 57.6 V bus")

# ================================================================ thermal
Q_p = put("pilot_heat_design", 400, "W", "design", "sustained work inside a closed suit (300–500 W)")
put("ref_a7l_lcvg_removal", 590, "W", "spec", "Apollo A7L liquid cooling garment, approx.")
flow = put("lcvg_flow", 1.8, "L/min", "design")
T_in = put("lcvg_inlet_temp", 18, "degC", "design")
mdot = flow * 0.998 / 60
put("lcvg_delta_T", rd(Q_p / (mdot * 4186)), "K", "calc", "Q = ṁ c_p ΔT")
put("lcvg_outlet_temp", rd(T_in + Q_p / (mdot * 4186), 1), "degC", "calc")
put("lcvg_tube", [3.2, 80], "mm, m", "design", "tube OD, total length — quilted into the flight suit")
COP = put("chiller_cop", 2.5, "", "design", "micro vapour-compression loop")
Te, Tc = 285.15, 323.15
put("chiller_cop_carnot", rd(Te / (Tc - Te)), "", "calc", "T_evap 12 °C, T_cond 50 °C")
put("chiller_second_law", rd(COP / (Te / (Tc - Te))), "", "calc", "fraction of Carnot")
assert 0.2 < COP / (Te / (Tc - Te)) < 0.5
P_chill = put("chiller_power", round(Q_p / COP), "W", "calc")
put("condenser_heat", Q_p + round(Q_p / COP), "W", "calc")
rpm_cmp = put("compressor_rpm", 6000, "rpm", "design", "single rolling piston")
put("compressor_freq", rd(rpm_cmp / 60, 1), "Hz", "calc")
rpm_pump = put("pump_rpm", 3600, "rpm", "design")
z_pump = put("pump_vanes", 5, "", "design")
put("pump_bpf", round(rpm_pump / 60 * z_pump), "Hz", "calc")
rpm_fan = put("condenser_fan_rpm", 4500, "rpm", "design")
z_fan = put("condenser_fan_blades", 7, "", "design")
z_fs = put("condenser_fan_struts", 3, "", "design")
assert math.gcd(z_fan, z_fs) == 1
put("condenser_fan_bpf", round(rpm_fan / 60 * z_fan), "Hz", "calc")
m_thermal = 1.2 + 2.5 + 0.5                          # LCVG, chiller + pump + reservoir, coolant

# ================================================================ power budget, endurance, trade study
prof = {"idle": (0.40, 180), "walk": (0.50, 600), "heavy": (0.10, 2000)}   # (time fraction, actuation W)
assert abs(sum(f for f, _ in prof.values()) - 1) < 1e-9
S["mission_profile"] = [{"mode": k, "time_fraction": f, "actuation_W": w} for k, (f, w) in prof.items()]
P_hud = put("hud_compute_power", 120, "W", "design", "4 cameras, 2 displays, sensors, compute")
P_cont = P_chill + P_hud
assert prof["heavy"][1] + P_cont <= P_fc * eta_dc, "heavy work must be sustainable by the fuel cell alone"
P_avg = put("power_mission_average", round(sum(f * w for f, w in prof.values()) + P_cont), "W", "calc",
            "actuation (profile) + chiller + HUD")
E_fc = m_h2_use * LHV * eta_sys * eta_dc
put("fc_energy_delivered", rd(E_fc, 3), "kWh", "calc", "usable H2 × LHV × η_system × η_DC-DC")
t_end = E_fc / (P_avg / 1000)
put("endurance_mission", rd(t_end, 1), "h", "calc", "fuel cell only; battery kept as reserve")
assert t_end >= 4.0, "design goal: ≥ 4 h mission endurance"
res = put("batt_reserve_fraction", 0.5, "", "design", "kept for peaks and emergency")
P_limp = put("power_limp_home", prof["idle"][1] + P_cont, "W", "calc", "idle actuation + chiller + HUD")
put("reserve_time", round(E_b * res * 1000 / P_limp * 60), "min", "calc", "battery reserve at limp-home power")
h2_avg = P_avg / 1000 / (eta_sys * eta_dc * LHV)
put("h2_flow_mission", rd(h2_avg, 4), "kg/h", "calc")
put("water_output_mission", rd(h2_avg * 18.015 / M_H2, 3), "kg/h", "calc", "the only exhaust is water vapour")
put("fc_heat_mission", round(P_avg / eta_dc * (1 / eta_sys - 1)), "W", "calc", "carried away by the stack air")
put("fc_purge_interval_mission", round(purge_rated * P_fc / (P_avg / eta_dc)), "s", "calc", "≈ ∝ 1 / load")
e_bo = put("batt_only_specific_energy", 200, "Wh/kg", "design", "energy-type pack, for the comparison only")
dod = put("batt_only_dod", 0.90, "", "design")
m_bo = E_fc / dod / (e_bo / 1000)
put("batt_only_mass", rd(m_bo, 1), "kg", "calc", "same delivered energy, battery only")
m_fc_fixed = m_fc + m_reg + 0.40 + 0.90 + m_b     # module, regulator, lines/valves, DC-DC + BMS, buffer battery
m_fc_sys = m_fc_fixed + n_cyl * m_cyl + m_h2
put("fc_system_mass", rd(m_fc_sys, 1), "kg", "calc", "module, regulator, lines, DC-DC, buffer battery, cylinders, H2")
put("fc_saving_vs_battery", rd(m_bo - m_fc_sys, 1), "kg", "calc")
k_fc = (n_cyl * m_cyl + m_h2) / E_fc              # storage kg per delivered kWh
k_bo = 1 / dod / (e_bo / 1000)
E_x = m_fc_fixed / (k_bo - k_fc)
put("fc_crossover_energy", rd(E_x), "kWh", "calc", "above this the fuel-cell system is lighter than batteries")
put("fc_crossover_time", rd(E_x / (P_avg / 1000), 1), "h", "calc", "at the mission-average power")

# ================================================================ mass budget
put("gauntlet_mechanism_mass", 0.90, "kg", "design", "per hand: finger linkage + grip-lock clutch")
d_rod = put("ankle_rod_diameter", 12, "mm", "design", "17-4PH H900, hard-chrome")
_ap = X["ankle_pitch"]
L_rod = math.dist(_ap["c"], _ap["joint"])
put("ankle_rod_length", round(L_rod * 1000), "mm", "calc", "parallelogram: actuator axis -> ankle axis")
m_rodset = math.pi * (d_rod / 2000) ** 2 * L_rod * 7780 + 2 * 0.04 + 2 * 0.05   # rod + 2 rod ends + 2 cranks
budget = [
    ("Joint actuators ×24 (L14 / M7 / S3)", m_act),
    ("Exo frame: Ti-6Al-4V links & clevises, CFRP spine & pelvis", 14.00),
    ("Waist turret ring (thin-section bearing + ring gear)", 1.40),
    ("Collar ring (helmet yaw bearing + ring gear)", 0.45),
    ("Armor panels 120+ (CFRP/aramid, Ti impact panels, latches)", m_armor),
    ("Helmet sensor module (4 cameras, 2 displays, IMU, ANC)", 1.40),
    ("Fuel cell module (IE-SOAR 2.4-class)", m_fc),
    ("H2 regulator, lines, valves, sensors", m_reg + 0.40),
    ("H2 cylinders ×2 (type IV, 350 bar)", n_cyl * m_cyl),
    ("Hydrogen (full)", m_h2),
    ("Buffer battery 16S2P", m_b),
    ("Power electronics (DC-DC, BMS, bus bars)", 0.90),
    ("Thermal: cooling garment + chiller + coolant", m_thermal),
    ("Knee dampers ×2 (semi-active hydraulic)", 1.20),
    ("Ankle push-rod linkages ×2", 2 * m_rodset),
    ("Gauntlet finger mechanisms ×2", 2 * 0.90),
    ("Fasteners ≈700 (M2–M8, Ti / steel)", 2.10),
    ("Electronics, sensors, cable harness", 3.00),
    ("Pilot harness, soft goods", 2.00),
]
S["mass_budget"] = [{"item": k, "kg": rd(v)} for k, v in budget]
m_suit = sum(v for _, v in budget)
m_sys = m_suit + m_pilot
put("suit_mass", rd(m_suit, 1), "kg", "calc", "fuelled, without pilot")
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
# ring gears (turret style) for trunk rotation and helmet yaw
for name, Z, Zp_, m_, x_ in (("waist", Zw, Zwp, mw, x_wp), ("collar", Zc, Zcp, mc, x_cp)):
    put(f"{name}_ring_teeth", Z, "", "design")
    put(f"{name}_pinion_teeth", Zp_, "", "design")
    put(f"{name}_ring_module", m_, "mm", "design")
    put(f"{name}_ring_pd", rd(Z * m_, 1), "mm", "calc", "pitch diameter")
    put(f"{name}_ratio", rd(Z / Zp_), "", "calc")
    put(f"{name}_pinion_shift", x_, "", "design")
    put(f"{name}_centre_distance", rd((Z + Zp_) * m_ / 2, 1), "mm", "calc")
    assert Zp_ >= zmin(x_), f"{name} pinion would be undercut"
put("waist_ring_torque", round(T_peak["M"] * Zw / Zwp), "N·m", "calc", "M-class peak × ring ratio")
put("collar_ring_torque", round(T_peak["S"] * Zc / Zcp), "N·m", "calc", "S-class peak × ring ratio")
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
lev = fore_arm + 0.075
put("lift_lever", rd(lev, 4), "m", "calc", "elbow axis -> grip centre (0.146 H + 75 mm)")
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
E_rg = min(0.70 * E_act, P_regen * t_land)
put("landing_actuator_energy", round(E_act), "J", "calc", "absorbed by the joint actuators")
put("landing_regen", round(E_rg), "J", "calc", "limited by the battery's pulse-charge power, not by the motors")
put("landing_brake_heat", round(E_act - E_rg), "J", "calc", "brake resistors + windings")
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
                          "use": "actuator housings, brackets, fuel-cell end plates"},
    "CFRP [0/±45/90]s":  {"rho": 1.55, "E": 50, "strength": 600, "su": 600, "Tmax": 120,
                          "use": "armor skin, spine & pelvis frame, H2 cylinder overwrap"},
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
S["cfrp_layup"] = [0, 45, -45, 90]
S["material_note"] = ("CFRP has the highest specific strength, yet the links are Ti-6Al-4V: isotropic and damage / "
                      "fatigue tolerant at clevises and threads. CFRP is used where loads are spread over large, "
                      "simple shapes (armor, spine, pelvis, cylinder overwrap); aramid backs it because it is "
                      "strong in tension and catches fragments.")
# titanium anodizing: interference colour of a thin transparent TiO2 film (no dye, no paint)
k_an = put("anodize_growth", 2.0, "nm/V", "design",
           "anodic TiO2 ≈ 1.5–2.5 nm/V by electrolyte; 2.0 matches a thin-film render against the colour chart")
put("anodize_film_ior", 2.2, "", "const", "anodic TiO2 ≈ 2.1–2.4")
V_au = put("anodize_gold_voltage", 62, "V", "design", "2nd-order gold: the rotation rings")
put("anodize_gold_thickness", round(V_au * k_an), "nm", "calc")
V_br = put("anodize_bronze_voltage", 12.5, "V", "design", "1st-order bronze: back louvers")
put("anodize_bronze_thickness", round(V_br * k_an), "nm", "calc")
S["anodize_chart"] = [{"V": V_, "nm": round(V_ * k_an), "name": nm_} for V_, nm_ in (
    (0, "bare Ti"), (7.5, "light straw"), (12.5, "bronze (1st-order gold)"), (17.5, "purple"), (22.5, "blue"),
    (30, "light blue"), (37.5, "pale blue-silver"), (42.5, "silver"), (47.5, "champagne"), (55, "pale gold"),
    (62, "gold (2nd order)"), (70, "copper"), (80, "magenta"), (90, "deep blue (2nd order)"))]
S["anodize_note"] = "colour names from a Cycles thin-film render (Ti base, film IOR 2.2), 2026-09-30; approximate"
# 3D palette (area share of the visible exterior; the model manifest measures the real shares)
S["palette_3d"] = [
    {"name": "graphite", "finish": "CFRP, clear-coat, twill weave", "share": [0.40, 0.50], "where": "armor faces (resting surfaces)"},
    {"name": "gunmetal", "finish": "bead-blasted Ti-6Al-4V", "share": [0.25, 0.32], "where": "frame, housings, impact panels, helmet brow"},
    {"name": "platinum", "finish": "polished Ti keel strips, hard-chrome rods", "share": [0.06, 0.10], "where": "form lines, sliding parts"},
    {"name": "ti_gold", "finish": f"anodized Ti {V_au} V ({round(V_au * k_an)} nm)", "share": [0.08, 0.11], "where": "rotation rings = joint axes"},
    {"name": "ti_bronze", "finish": f"anodized Ti {V_br} V ({round(V_br * k_an)} nm)", "share": [0.01, 0.03], "where": "back louvers"},
    {"name": "gold", "finish": "gold plating, gold IR film, MLI foil", "share": [0.01, 0.02], "where": "contacts, visor tint, insulation"},
]
put("gold_family_share", [0.10, 0.15], "", "design", "ti_gold + ti_bronze + gold, measured on the model")
put("red_share", 0.0, "", "design", "no red anywhere on the suit")

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

# ================================================================ geometry layout part 2: back modules + robot cell
# Upper power pack rides on the torso (above the waist ring): [cylinder | fuel cell | cylinder], upright.
cyl_r = OD / 2000
pack_z0 = rd(waist_c[2] + 0.015 + 0.025, 3)          # ring half-height 15 mm + 25 mm gap
pack_y0 = 0.230
fc_c = v3(0, pack_y0 + fc_dim[1] / 2000, pack_z0 + fc_dim[2] / 2000)
cyl_x = fc_dim[0] / 2000 + 0.005 + cyl_r
cyl_c = v3(cyl_x, pack_y0 + cyl_r, pack_z0 + L_cyl / 2000)
assert L_cyl / 1000 <= fc_dim[2] / 1000 + 1e-9, "cylinders taller than the pack"
sacral = {"c": v3(0, 0.300, 0.975), "size": [0.36, 0.14, 0.12],
          "holds": "buffer battery 16S2P + chiller (compressor, condenser + fan, evaporator) + pump + reservoir",
          "note": "on the pelvis frame; its cables cross the waist ring through a ±30° twist loop"}
pack = {"fc_module": {"c": fc_c, "size": [d_ / 1000 for d_ in fc_dim]},
        "h2_cylinders": {"c": cyl_c, "axis": [0, 0, 1], "od": rd(OD / 1000, 4), "len": L_cyl / 1000,
                         "note": "mirror x for the right cylinder"},
        "width": rd(2 * (cyl_x + cyl_r), 3), "depth": rd(max(fc_dim[1] / 1000, 2 * cyl_r), 3),
        "z": [pack_z0, rd(pack_z0 + fc_dim[2] / 1000, 3)],
        "air": "intake behind the collar, exhaust through lower rear louvers; never toward the pilot",
        "insulation": "gold MLI (aluminized polyimide) between the pack and the pilot's back"}
put("power_pack_width", round(pack["width"] * 1000), "mm", "calc")
put("power_pack_depth", round(pack["depth"] * 1000), "mm", "calc")


def box(c, size):
    return [[c[i] - size[i] / 2, c[i] + size[i] / 2] for i in range(3)]


def act_box(name, side=1):
    v = X[name]
    c = list(v["c"])
    c[0] *= side
    OD_, W_ = ACT[v["cls"]][3] / 1000, ACT[v["cls"]][4] / 1000
    ax = v["axis"]
    ext = [OD_ if not (isinstance(ax, list) and abs(ax[i]) > 0.99) else W_ for i in range(3)]
    return box(c, ext)


def clash(a, b, gap=0.0):
    return all(a[i][0] < b[i][1] + gap and b[i][0] < a[i][1] + gap for i in range(3))


upper = box([0, pack_y0 + pack["depth"] / 2, pack_z0 + fc_dim[2] / 2000], [pack["width"], pack["depth"], fc_dim[2] / 1000])
lower = box(sacral["c"], sacral["size"])
ring_box = box(waist_c, [2 * (Zw * mw / 2000 + 0.015), 2 * (Zw * mw / 2000 + 0.015), 0.030])
checks = {
    "pack vs shoulder_abd": clash(upper, act_box("shoulder_abd"), 0.03),
    "pack vs neck": clash(upper, act_box("neck"), 0.03),
    "pack vs trunk_rot": clash(upper, act_box("trunk_rot"), 0.02),
    "pack vs waist ring": clash(upper, ring_box, 0.02),
    "sacral vs hip_abd": clash(lower, act_box("hip_abd"), 0.03),
    "sacral vs trunk_rot": clash(lower, act_box("trunk_rot"), 0.015),
}
S["clash_checks_static"] = {k: ("CLASH" if v_ else "clear") for k, v_ in checks.items()}
assert not any(checks.values()), S["clash_checks_static"]
# robot cell (suit-up): platform top = z 0, hangar floor = z −0.12
cell = {
    "platform": {"d": 1.40, "height": 0.12, "note": "turntable positioner, top at z = 0"},
    "gantry": {"post_x": 1.60, "post_y": 0.30, "beam_z": 3.00, "note": "Z-hoist lowers the power pack and the helmet"},
    "arms": [{"base": [sx * 1.05, y_, 0.0], "reach": 1.65} for y_ in (-0.55, 0.75) for sx in (1, -1)],
    "racks": {"x": 2.10, "y": [-1.0, 1.0], "depth": 0.60, "height": 2.0, "note": "armor panels in foam fixtures"},
    "cradle": {"post_y": 0.62, "height": 1.60, "clamp_z": 1.45, "note": "holds the empty suit at the pack hard points"},
}
for a_ in cell["arms"]:
    assert math.dist(a_["base"][:2], (0, 0)) < a_["reach"], "robot arm cannot reach the suit axis"
S["layout"] = {
    "frame": "Blender metres, Z up, front = −Y, +X = suit LEFT; glTF (x, z, −y)",
    "z0_barefoot": rd(z0, 4),
    "pilot": J,
    "exo": X,
    "forearm_dir": fa,
    "power_pack": pack,
    "sacral_module": sacral,
    "waist_ring": {"c": waist_c, "pd": Zw * mw / 1000},
    "collar_ring": {"c": collar_c, "pd": Zc * mc / 1000},
    "cell": cell,
}

# ================================================================ headline values for the page
S["_headline"] = {"suit_mass": m_suit, "system_mass": m_sys, "knee_torque": Tk, "landing_force": F_g,
                  "drop_height": h, "lift_mass": m_lift, "endurance_h": t_end, "fc_power": P_fc}

root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(root, "specs.json"), "w") as f:
    json.dump(S, f, ensure_ascii=False, indent=1)
# (the web app imports calc/specs.json directly through Vite; no generated JS copy)
for k, v_ in S.items():
    if isinstance(v_, dict) and "v" in v_:
        print(f"{k:32s} {v_['v']!s:>14} {v_['unit']:10s} [{v_['tag']}]")
print("mass budget:", *(f"\n  {b['kg']:6.2f}  {b['item']}" for b in S["mass_budget"]))
print("clash:", S["clash_checks_static"])
