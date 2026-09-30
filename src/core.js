/* HX-01 KESTREL — shared core. Classic script; defines window.KX. Load after specs.js. */
(function () {
  var KX = (window.KX = window.KX || {});

  // ---------------------------------------------------------------- specs
  KX.specs = window.KX_SPECS || {};
  /** value of a scalar spec, e.g. KX.S('thrust_total') -> 2125 */
  KX.S = function (key) {
    var e = KX.specs[key];
    if (!e) { console.warn('[KX] unknown spec', key); return NaN; }
    return e.v !== undefined ? e.v : e;
  };
  /** unit of a scalar spec */
  KX.U = function (key) { var e = KX.specs[key]; return e && e.unit ? e.unit : ''; };

  // ---------------------------------------------------------------- formatting
  /** 12345.6 -> "12,345.6" with fixed digits; tabular output */
  KX.fmt = function (n, digits) {
    digits = digits || 0;
    var s = Number(n).toFixed(digits).split('.');
    s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return s.join('.');
  };

  // ---------------------------------------------------------------- event bus
  var handlers = {};
  KX.bus = {
    on: function (ev, fn) { (handlers[ev] = handlers[ev] || []).push(fn); return function () { KX.bus.off(ev, fn); }; },
    off: function (ev, fn) { var h = handlers[ev]; if (h) handlers[ev] = h.filter(function (f) { return f !== fn; }); },
    emit: function (ev, data) { (handlers[ev] || []).slice().forEach(function (f) { try { f(data); } catch (e) { console.error(e); } }); }
  };

  // ---------------------------------------------------------------- physics springs
  /* Every UI / scene motion uses one of three mass-spring-damper presets.
     x'' = wn^2 (target - x) - 2 zeta wn x'   (semi-implicit Euler, substepped) */
  KX.SPRINGS = {
    SERVO:  { zeta: 0.6, wn: 18 },   // joints, helmet sensor head
    HEAVY:  { zeta: 0.9, wn: 8 },    // big parts, camera
    DETENT: { zeta: 0.4, wn: 40 }    // buttons, knobs, snaps
  };
  KX.spring = function (preset, x0) {
    var p = typeof preset === 'string' ? KX.SPRINGS[preset] : preset;
    var s = { x: x0 || 0, v: 0, target: x0 || 0, zeta: p.zeta, wn: p.wn };
    s.step = function (dt) {
      var n = Math.max(1, Math.ceil(dt / 0.004)), h = dt / n;
      for (var i = 0; i < n; i++) {
        var a = s.wn * s.wn * (s.target - s.x) - 2 * s.zeta * s.wn * s.v;
        s.v += a * h; s.x += s.v * h;
      }
      return s.x;
    };
    s.settled = function (eps) { eps = eps || 1e-3; return Math.abs(s.target - s.x) < eps && Math.abs(s.v) < eps; };
    s.kick = function (dv) { s.v += dv; };
    return s;
  };
  /** closed-form unit step response of a spring preset at time t (for scrubbable timelines) */
  KX.stepResponse = function (preset, t) {
    var p = typeof preset === 'string' ? KX.SPRINGS[preset] : preset, z = p.zeta, w = p.wn;
    if (t <= 0) return 0;
    if (z < 1) {
      var wd = w * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z / Math.sqrt(1 - z * z)) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w * t) * (1 + w * t); // critically damped approx for z>=1
  };

  // ---------------------------------------------------------------- misc
  KX.reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  KX.clamp = function (x, a, b) { return Math.min(b, Math.max(a, x)); };
  KX.lerp = function (a, b, t) { return a + (b - a) * t; };
  /** map p in [a,b] to 0..1, clamped — used for sub-ranges of scroll progress */
  KX.range = function (p, a, b) { return KX.clamp((p - a) / (b - a), 0, 1); };
  KX.smooth = function (t) { return t * t * (3 - 2 * t); };
})();
