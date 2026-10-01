"""Cross-check the plan documents against calc/specs.json.

Run:  python3 calc/check_plan.py      (after python calc/specs.py)

Part 1: every listed spec value must appear in PLAN sections 0-9 in its display form.
        The expected text is built from the CURRENT spec value, so a changed calc sheet
        immediately shows which PLAN lines are stale.
Part 2: every number-with-unit in PLAN sections 0-9 must match some spec value; the rest is printed
        for a human to review (story timing, physical constants, history are expected there).
Part 3: CLAUDE.md carries the current heartbeat numbers.
"""
import json, re, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(ROOT, "calc", "specs.json")))
plan = open(os.path.join(ROOT, "PLAN.md"), encoding="utf-8").read()
cur = plan.split("## 10. 검토 기록")[0]          # sections 0-9 = the current design (10 = log, 11 = history)


def v(k):
    x = S[k]
    return x["v"] if isinstance(x, dict) and "v" in x else x


def f(template, x):
    if isinstance(x, float) and x.is_integer() and ("{:," in template or "{:d}" in template):
        x = int(x)
    return template.format(x)


# key -> list of templates (or (template, transform))
T = {
    "suit_mass": ["{:.1f} kg"], "system_mass": ["{:.1f}"], "knee_torque_design": ["{:,} N·m"], "L_torque_density": ["{} N·m/kg"],
    "gear_FoS": ["{:.2f}"], "sun_bending_stress": ["{:,} MPa"], "sun_tangential_force": ["{:,} N"],
    "link_stress": ["{:,} MPa"], "link_FoS": ["{:.2f}"], "link_moment": ["{:,} N·m"], "link_I": ["{:,} mm⁴"],
    "landing_force": ["{:,} N"], "landing_force_per_leg": ["{:,} N"], "knee_moment_landing": ["{:,} N·m"],
    "knee_capacity_landing": ["{:,} N·m"], "knee_landing_margin": ["{:.2f}"], "damper_force": ["{:,} N"],
    "damper_pressure": ["{:,} bar"], "damper_stroke": ["{:,} mm"], "landing_energy": ["{:,} J"], "damper_energy": ["{:,} J"],
    "damper_oil_temp_rise": ["{:.1f} K"], "landing_actuator_energy": ["{:,} J"], "landing_regen": ["{:,} J"],
    "landing_brake_heat": ["{:,} J"], "free_fall_time": ["{:.3f}초"], "damper_arm_margin": ["{:,} ms"],
    "impact_velocity": ["{:.2f} m/s"], "landing_time": ["{:.3f}초"], "landing_freeze": ["{}초"],
    "lift_elbow_moment": ["{:.1f} N·m"], "lift_shoulder_moment": ["{:.1f} N·m"], "lift_lever": ["{:.4f} m"],
    "ankle_rod_force": ["{:,} N"], "ankle_rod_stress": ["{:,} MPa"], "ankle_rod_buckling_FoS": ["{:.2f}"],
    "leg_inertia_saving": ["{:.3f} kg·m²"], "ankle_rod_length": ["{:,} mm"],
    "trunk_torque": ["{:,} N·m"], "trunk_sector_teeth": ["{}T"], "trunk_arc_radius": ["{} mm"], "trunk_arc_span": ["±{}°"],
    "atlas_torque": ["{:,} N·m"], "atlas_ring_pd": ["{:.0f} mm"], "atlas_ring_tilt": ["{}°"],
    "knee_motor_rpm_gait": ["{:,} rpm"], "motor_elec_freq_gait": ["{:.1f} Hz"], "gear_mesh_freq_gait": ["{:.1f} Hz"],
    "harmonic_vibration_freq": ["{:.1f} Hz"], "knee_motor_torque_peak": ["{:.1f} N·m"],
    "armor_area": ["{:.3f} m²"], "pilot_body_surface_area": ["{:.3f} m²"], "armor_mass": ["{:.1f} kg"],
    "pb11_specific_energy": ["{:.1f} TJ/kg"], "pb11_alpha_energy": ["{:.2f} MeV"], "pellet_energy": ["{:,} J"],
    "core_fusion_power_rated": ["{:,} W"], "core_heat_rated": ["{:,} W"], "core_efficiency": ["{:.0%}"],
    "core_vessel": [("Ø{} × {} mm", lambda x: tuple(x))],
    "heartbeat_standby": ["대기 {}"], "heartbeat_mission": ["보행 {}"], "heartbeat_heavy": ["중작업 {}"], "heartbeat_rated": ["정격 {} BPM"],
    "fuel_magazine_pellets": ["{:,.0f}"], "fuel_life_mission": ["약 {}일"], "fuel_use_mission": ["{} mg"],
    "bus_power_peak": [("{:.1f} kW", lambda x: x / 1000)], "buffer_energy": ["{} Wh"], "buffer_power": [("{:.0f} kW", lambda x: x / 1000)],
    "scram_reserve_time": ["{:.1f}분"], "power_standby": ["{:,} W"],
    "power_continuous_loads": ["{:,} W"], "power_mission_average": ["{:,} W"], "power_heavy": ["{:,} W"], "core_power_bus": ["{:,} W"],
    "radiator_capacity": ["{:,} W"], "radiator_load_mission": ["{:,} W"], "radiator_load_heavy": ["{:,} W"],
    "radiator_deficit_heavy": ["{:,} W"], "heavy_work_burst": ["{:.1f}분"], "pcm_recharge": ["{:.1f}분"], "radiator_fan_bpf": ["{:,} Hz"],
    "radiator_panel": [("{} × {} mm", lambda x: (x[0], x[1])), ("{} mm", lambda x: x[2])], "radiator_panel_area": ["{:.3f} m²"],
    "lcvg_delta_T": ["{:.2f} K"], "lcvg_outlet_temp": ["{:.1f} °C"], "chiller_power": ["{:,} W"], "condenser_heat": ["{:,} W"],
    "chiller_cop": ["COP {}"], "chiller_cop_carnot": ["{}"], "chiller_second_law": ["{:.0%}"],
    "pump_bpf": ["{:,} Hz"], "compressor_freq": ["{:.0f} Hz"],
    "ambient_design_temp": ["바깥 공기 {} °C"], "coolant_design_temp": ["루프 {}"], "chiller_condensing_temp": ["응축 {}"],
    "chiller_evaporating_temp": ["증발 {}"], "pcm_melt_temp": ["{} °C에서 녹음"], "coolant_temp_mission": ["{:.1f} °C"],
    "motion_to_photon": ["{:.1f} ms"], "bolt_torque": ["{:.1f} N·m"], "bolt_preload": ["{:,} N"], "bolt_turns": ["{}바퀴"],
    "flange_bolt_total": ["{}"], "anodize_gold_thickness": ["{} nm"], "anodize_bronze_thickness": ["{} nm"],
    "arm_length": ["{} mm"], "upper_arm_length": ["{}"], "forearm_length": ["{}"], "hand_length": ["{}"],
    "fingertip_height": ["{} H"], "hip_height_ratio": ["{} H"], "neck_visible_height": ["{} mm"], "keel_protrusion": ["{} mm"],
    "eye_angle": ["{}°"], "undercut_limit_teeth": ["{}T"], "undercut_limit_shifted": ["{}T"],
    "sun_planet_centre_distance": ["{:.0f} mm"], "harmonic_flexspline_pd": ["{:.1f}"], "harmonic_circular_pd": ["{:.1f} mm"],
    "encoder_cpr": ["{:,}"], "mains_hum": ["{} Hz"], "cryocooler_freq": ["{} Hz"],
}
bad = 0
for k, temps in T.items():
    if k not in S:
        print("MISSING KEY", k); bad += 1; continue
    for t in temps:
        tpl, tf = (t if isinstance(t, tuple) else (t, None))
        x = v(k) if tf is None else tf(v(k))
        txt = tpl.format(*x) if isinstance(x, tuple) else f(tpl, x)
        if txt not in cur:
            print(f"NOT IN PLAN  {k:28s} spec={v(k)!s:<16} expected '{txt}'"); bad += 1
hb4 = f"{v('heartbeat_standby')} / {v('heartbeat_mission')} / {v('heartbeat_heavy')} / {v('heartbeat_rated')} BPM"
if hb4 not in cur:
    print(f"NOT IN PLAN  heartbeat summary          expected '{hb4}'"); bad += 1
print("part 1:", f"all {sum(len(t) for t in T.values()) + 1} expected texts present" if not bad else f"{bad} problems")

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
seen, unmatched = set(), []
for m in re.finditer(num, cur):
    s, u = m.group(1), m.group(2)
    if (s, u) in seen:
        continue
    seen.add((s, u))
    x = float(s.replace(",", ""))
    cands = [x] + {"kW": [x * 1000], "kJ": [x * 1000], "mm": [x / 1000], "m": [x * 1000], "%": [x / 100],
                   "분": [x * 60], "ms": [x / 1000], "g": [x * 1000, x / 1000]}.get(u, [])
    if not any(math.isclose(c, sv, rel_tol=0.006, abs_tol=0.0051) for c in cands for sv in vals):
        line = cur[:m.start()].count("\n") + 1
        unmatched.append((line, s + " " + u, cur.splitlines()[line - 1].strip()[:110]))
print(f"part 2: {len(seen)} distinct numbers checked, {len(unmatched)} not found in specs (review):")
for line, t, ctx in unmatched:
    print(f"  L{line:<4} {t:>14}   | {ctx}")

# ---- part 3: CLAUDE.md heartbeat line
claude = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
hb = f"standby {v('heartbeat_standby')} / walk {v('heartbeat_mission')} / heavy {v('heartbeat_heavy')} / rated {v('heartbeat_rated')} BPM"
print("part 3:", "CLAUDE.md heartbeat line OK" if hb in claude else f"CLAUDE.md is missing '{hb}'")
