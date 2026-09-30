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
# 24 actuators (24 DoF, cf. Sarcos Guardian XO), three size classes
ACT = {
    # class: (count, unit mass kg, joints)
    "L": (10, 1.10, "hip flex ×2, hip abd ×2, knee ×2, shoulder flex ×2, shoulder abd ×2"),
    "M": (9, 0.70, "hip rot ×2, ankle pitch ×2, shoulder rot ×2, elbow ×2, trunk rot ×1"),
    "S": (5, 0.45, "ankle roll ×2, wrist ×2, neck ×1"),
}
n_act = sum(c for c, _, _ in ACT.values())
assert n_act == 24
S["actuator_classes"] = {k: {"count": c, "kg": m, "joints": j} for k, (c, m, j) in ACT.items()}
m_act = sum(c * m for c, m, _ in ACT.values())
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
Tk = put("knee_torque_design", round(1.5 * m_sys), "N·m", "calc", "1.5 N·m/kg × system mass")
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

# ---------------------------------------------------------------- specs used on page as headline
S["_headline"] = {
    "dry": dry, "takeoff": M0, "W": W, "T": T, "TW": TW,
}

import os
root = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(root, "specs.json"), "w") as f:
    json.dump(S, f, ensure_ascii=False, indent=1)
with open(os.path.join(root, "..", "src", "specs.js"), "w") as f:
    f.write("window.KX_SPECS = " + json.dumps(S, ensure_ascii=False) + ";\n")
for k, v in S.items():
    if isinstance(v, dict) and "v" in v:
        print(f"{k:32s} {v['v']!s:>12} {v['unit']:10s} [{v['tag']}]")
