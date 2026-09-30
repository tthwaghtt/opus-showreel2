"""Cross-check PLAN.md numbers against calc/specs.json (v2.1).

Part 1: every listed spec key must appear in PLAN in its display form.
Part 2: every number-with-unit in PLAN sections 0-9 must match some spec value (or a whitelist), else it is printed for review.
"""
import json, re, sys, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(f"{ROOT}/calc/specs.json"))
plan = open(f"{ROOT}/PLAN.md", encoding="utf-8").read()
# only the "current" part of the plan: sections 0..9 (10 = log, 11 = history table, 12 = reference)
cur = plan.split("## 10. 검토 기록")[0]


def v(k):
    x = S[k]
    return x["v"] if isinstance(x, dict) and "v" in x else x


def fmt(x, nd=None):
    if nd is not None:
        x = round(x, nd)
    if isinstance(x, float) and x.is_integer() and nd in (None, 0):
        x = int(x)
    if isinstance(x, int) or (isinstance(x, float) and nd == 0):
        return f"{int(round(x)):,}"
    return f"{x:,.{nd}f}" if nd is not None else f"{x:,}"


# ---- part 1: key -> expected text
expect = {
    "suit_mass": ["92.0 kg"], "system_mass": ["167.0"], "knee_torque_design": ["250 N·m"],
    "gear_FoS": ["1.59"], "sun_bending_stress": ["315 MPa"], "sun_tangential_force": ["1,543 N"],
    "link_stress": ["259 MPa"], "link_FoS": ["3.40"], "link_moment": ["393 N·m"], "link_I": ["25,836 mm⁴"],
    "landing_force": ["6,552 N"], "landing_force_per_leg": ["3,276 N"], "knee_moment_landing": ["590 N·m"],
    "knee_capacity_landing": ["650 N·m"], "knee_landing_margin": ["1.10"], "damper_force": ["8,889 N"],
    "damper_pressure": ["234 bar"], "damper_stroke": ["47 mm"], "landing_energy": ["3,276 J"], "damper_energy": ["605 J"],
    "damper_oil_temp_rise": ["5.3 K"], "landing_actuator_energy": ["2,066 J"], "landing_regen": ["1,446 J"],
    "landing_brake_heat": ["620 J"], "free_fall_time": ["0.553초"], "damper_arm_margin": ["453 ms"],
    "impact_velocity": ["5.42 m/s"], "landing_time": ["0.184초"],
    "lift_elbow_moment": ["147.2 N·m"], "lift_shoulder_moment": ["152.4 N·m"], "lift_lever": ["0.3335 m"],
    "ankle_rod_force": ["4,167 N"], "ankle_rod_stress": ["37 MPa"], "ankle_rod_buckling_FoS": ["5.27"],
    "leg_inertia_saving": ["0.601 kg·m²"], "ankle_rod_length": ["300 mm"],
    "trunk_torque": ["700 N·m"], "trunk_sector_teeth": ["27T"], "trunk_arc_radius": ["120 mm"], "atlas_torque": ["144 N·m"],
    "atlas_ring_pd": ["216 mm"], "atlas_ring_tilt": ["22°"],
    "knee_motor_rpm_gait": ["516 rpm"], "motor_elec_freq_gait": ["120.3 Hz"], "gear_mesh_freq_gait": ["91.7 Hz"],
    "harmonic_vibration_freq": ["95.5 Hz"], "knee_motor_torque_peak": ["27.8 N·m"],
    "armor_area": ["3.262 m²"], "pilot_body_surface_area": ["1.919 m²"], "armor_mass": ["17.3 kg"],
    "pb11_specific_energy": ["69.7 TJ/kg"], "pb11_alpha_energy": ["2.89 MeV"], "pellet_energy": ["4,182 J"],
    "core_fusion_power_rated": ["4,839 W"], "core_heat_rated": ["1,839 W"], "core_efficiency": ["62%"],
    "heartbeat_standby": ["7"], "heartbeat_mission": ["26"], "heartbeat_heavy": ["60"], "heartbeat_rated": ["69"],
    "fuel_magazine_pellets": ["833,000"], "fuel_life_mission": ["328일"], "fuel_use_mission": ["0.127 mg"],
    "bus_power_peak": ["22.9 kW"], "scram_reserve_time": ["5.0분"], "power_standby": ["270 W"],
    "power_continuous_loads": ["490 W"], "power_mission_average": ["1,062 W"],
    "radiator_capacity": ["2,668 W"], "radiator_load_mission": ["1,870 W"], "radiator_load_heavy": ["3,483 W"],
    "heavy_work_burst": ["4.4분"], "pcm_recharge": ["4.5분"], "radiator_fan_bpf": ["1,100 Hz"],
    "lcvg_delta_T": ["3.19 K"], "lcvg_outlet_temp": ["21.2 °C"], "chiller_power": ["160 W"], "condenser_heat": ["560 W"],
    "chiller_cop_carnot": ["7.5"], "chiller_second_law": ["33%"], "pump_bpf": ["300 Hz"], "compressor_freq": ["100 Hz"],
    "motion_to_photon": ["16.5 ms"], "bolt_torque": ["14.3 N·m"], "bolt_preload": ["11,939 N"], "bolt_turns": ["12바퀴"],
    "flange_bolt_total": ["242"], "anodize_gold_thickness": ["124 nm"], "anodize_bronze_thickness": ["25 nm"],
    "arm_length": ["735 mm"], "upper_arm_length": ["287"], "forearm_length": ["257"], "hand_length": ["190"],
    "fingertip_height": ["0.379 H"], "hip_height_ratio": ["0.535 H"], "neck_visible_height": ["67 mm"],
    "keel_protrusion": ["118 mm"], "undercut_limit_teeth": ["17.1T"], "undercut_limit_shifted": ["11.97T"],
    "sun_planet_centre_distance": ["27 mm"], "harmonic_flexspline_pd": ["80.0"], "harmonic_circular_pd": ["80.8 mm"],
    "radiator_panel": ["140 × 340 mm", "25 mm"], "radiator_panel_area": ["0.036 m²"],
    "encoder_cpr": ["131,072"], "mains_hum": ["120 Hz"], "cryocooler_freq": ["50 Hz"],
    "L_torque_density": ["179 N·m/kg"],
}
bad = 0
for k, texts in expect.items():
    if k not in S:
        print("MISSING KEY", k); bad += 1; continue
    for t in texts:
        if t not in cur:
            print(f"NOT IN PLAN  {k:28s} spec={v(k)!s:<18} expected text '{t}'"); bad += 1
print("part 1:", "all present" if not bad else f"{bad} problems")

# sanity: the expected texts themselves agree with the specs (guards against typing the wrong expectation)
chk = {
    "suit_mass": (v("suit_mass"), 92.0), "system_mass": (v("system_mass"), 167.0), "link_FoS": (v("link_FoS"), 3.40),
    "gear_FoS": (v("gear_FoS"), 1.59), "radiator_capacity": (v("radiator_capacity"), 2668), "heavy_work_burst": (v("heavy_work_burst"), 4.4),
    "pellet_energy": (v("pellet_energy"), 4182), "landing_regen": (v("landing_regen"), 1446), "armor_mass": (round(v("armor_mass"), 1), 17.3),
    "bus_power_peak": (round(v("bus_power_peak") / 1000, 1), 22.9), "radiator_panel": (v("radiator_panel"), [140, 340, 25]),
    "knee_landing_margin": (round(v("knee_landing_margin"), 2), 1.10), "chiller_second_law": (round(v("chiller_second_law") * 100), 33),
}
for k, (a, b) in chk.items():
    if a != b:
        print("EXPECTATION WRONG", k, a, "!=", b)

# ---- part 2: numbers with units in the current plan text vs any spec value
vals = []
def walk(x):
    if isinstance(x, dict):
        if "v" in x and not isinstance(x["v"], (dict, list, str)):
            vals.append(float(x["v"]))
        for y in x.values():
            walk(y)
    elif isinstance(x, list):
        for y in x:
            walk(y)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        vals.append(float(x))
walk(S)
units = r"(N·m/kg|N·m|kg·m²|kW|W|kg|mm⁴|mm|m/s|MPa|GPa|bar|Hz|BPM|kJ|J|K|°C|ms|nm|V|A|MeV|TJ/kg|µg|L/s|L/min|rpm|T|m²|m|g|분|초|일|%|°)"
num = r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?" + units + r"(?![\w])"
white = {  # values that are legitimately not in specs (textbook facts, story timing, UI layout, history)
    "초": None, "%": None,
}
seen = set()
unmatched = []
for m in re.finditer(num, cur):
    s, u = m.group(1), m.group(2)
    x = float(s.replace(",", ""))
    key = (s, u)
    if key in seen:
        continue
    seen.add(key)
    cands = [x]
    if u in ("kW",): cands += [x * 1000]
    if u in ("kJ",): cands += [x * 1000]
    if u in ("mm",): cands += [x / 1000]
    if u in ("m",): cands += [x * 1000]
    if u in ("%",): cands += [x / 100]
    if u in ("분",): cands += [x * 60]
    if u in ("ms",): cands += [x / 1000]
    if u in ("g",): cands += [x * 1000, x / 1000]
    ok = any(math.isclose(c, sv, rel_tol=0.006, abs_tol=0.0051) for c in cands for sv in vals)
    if not ok:
        line = cur[:m.start()].count("\n") + 1
        unmatched.append((line, s + " " + u, cur.splitlines()[line - 1].strip()[:110]))
print(f"part 2: {len(seen)} distinct numbers checked, {len(unmatched)} not found in specs (review):")
for line, t, ctx in unmatched:
    print(f"  L{line:<4} {t:>14}   | {ctx}")
