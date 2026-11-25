/* Custom cursor.
   States: dot (free, 16px) · grow (over buttons and links: +50%, inverting them) ·
   beam (text) · read (a circle that says Read over article tiles).
   Size, position and corners each run on their own spring (M3 expressive values). */
(function () {
  'use strict';
  var root = document.documentElement;
  if (!matchMedia('(hover: hover) and (pointer: fine)').matches || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  root.classList.add('cx');

  var body = document.createElement('div'), read = document.createElement('div');
  body.className = 'cur-body out'; read.className = 'cur-read out';
  body.setAttribute('aria-hidden', 'true'); read.setAttribute('aria-hidden', 'true');
  read.innerHTML = '<span>Read<i></i></span>';
  document.body.appendChild(body); document.body.appendChild(read);
  var label = read.firstChild;
  var cur = { classList: { remove: function (c) { body.classList.remove(c); read.classList.remove(c); }, add: function (c) { body.classList.add(c); read.classList.add(c); },
    toggle: function (c, v) { body.classList.toggle(c, v); read.classList.toggle(c, v); } } };

  function S(v, k, z) { return { x: v, v: 0, t: v, k: k, c: 2 * z * Math.sqrt(k) }; }
  // position: expressive fast (0.6/800) when free, steadier while wrapping
  var X = S(-50, 900, .75), Y = S(-50, 900, .75);
  var W = S(16, 520, .62), H = S(16, 520, .62), R = S(8, 520, .62);
  var RD = S(0, 520, .62);           // read circle diameter, springs in with a little overshoot
  var P = S(1, 800, .6);             // press scale
  var mx = -50, my = -50, lx = -50, ly = -50, vx = 0, vy = 0;
  var el = null, mode = 'dot';

  var WRAP = 'a, button, [role="button"], summary, label[for]';
  var TEXT = 'p, h1, h2, h3, h4, li, blockquote, figcaption, .status';

  function resolve(t) {
    if (!t || !t.closest) return ['dot', null];
    var tile = t.closest('.wcard, .pager-link');
    if (tile) return ['read', tile];
    var w = t.closest(WRAP);
    if (w) return ['wrap', w];
    var tx = t.closest(TEXT);
    if (tx && tx.textContent.trim()) return ['beam', tx];
    return ['dot', null];
  }

  addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'mouse') return;
    mx = e.clientX; my = e.clientY;
    cur.classList.remove('out');
    var r = resolve(e.target);
    if (r[0] !== mode || r[1] !== el) {
      mode = r[0]; el = r[1];
      cur.classList.toggle('tile', mode === 'read');
      cur.classList.toggle('ext', mode === 'read' && el.target === '_blank');
      if (mode === 'read') label.firstChild.nodeValue = el.classList.contains('work') ? 'View' : el.classList.contains('pager-link') ? 'Next' : 'Read';
    }
  }, { passive: true });
  document.addEventListener('mouseleave', function () { cur.classList.add('out'); });
  document.addEventListener('mouseenter', function () { cur.classList.remove('out'); });
  addEventListener('pointerdown', function () { P.t = .88; });
  addEventListener('pointerup', function () { P.t = 1; });
  // after a scroll the element under a still pointer changes
  addEventListener('scroll', function () {
    var t = document.elementFromPoint(mx, my), r = resolve(t);
    if (r[0] !== mode || r[1] !== el) { mode = r[0]; el = r[1]; cur.classList.toggle('tile', mode === 'read'); }
  }, { passive: true });

  var last = performance.now();
  function step(s, dt) { for (var j = 0; j < 4; j++) { s.v += (-s.k * (s.x - s.t) - s.c * s.v) * dt; s.x += s.v * dt; } }
  (function tick(now) {
    var dt = Math.min(.032, (now - last) / 1000) / 4; last = now;
    vx = vx * .7 + (mx - lx) * .3; vy = vy * .7 + (my - ly) * .3; lx = mx; ly = my;

    var cx = mx, cy = my, w = 16, h = 16, r = 8, op = 1;
    if (mode === 'wrap') {
      // over buttons and links the circle grows by 50% (16px to 24px) and inverts what it covers
      w = 24; h = 24; r = 12;
    } else if (mode === 'beam' && el.isConnected) {
      var fs = parseFloat(getComputedStyle(el).fontSize) || 16;
      w = 2; h = Math.round(fs * 1.15); r = 1;
    } else if (mode === 'read') {
      w = 0; h = 0; r = 0; op = 0;
    } else {
      // free dot stretches a little along its direction of travel
      var sp = Math.min(1, Math.hypot(vx, vy) / 40);
      w = 16 + sp * 10; h = 16 - sp * 4; r = h / 2;
    }
    X.t = cx; Y.t = cy; W.t = w; H.t = h; R.t = r; RD.t = mode === 'read' ? 92 : 0;
    [X, Y, W, H, R, RD, P].forEach(function (s) { step(s, dt); });

    var ang = mode === 'dot' && Math.hypot(vx, vy) > 2 ? Math.atan2(vy, vx) * 180 / Math.PI : 0;
    var bw = Math.max(0, W.x) * P.x, bh = Math.max(0, H.x) * P.x;
    body.style.cssText = 'width:' + bw.toFixed(1) + 'px;height:' + bh.toFixed(1) + 'px;border-radius:' + Math.max(0, R.x * P.x).toFixed(1) + 'px;' +
      'translate:' + (X.x - bw / 2).toFixed(1) + 'px ' + (Y.x - bh / 2).toFixed(1) + 'px;rotate:' + ang.toFixed(1) + 'deg;opacity:' + op;
    var d = Math.max(0, RD.x) * P.x;
    read.style.cssText = 'width:' + d.toFixed(1) + 'px;height:' + d.toFixed(1) + 'px;translate:' + (X.x - d / 2).toFixed(1) + 'px ' + (Y.x - d / 2).toFixed(1) + 'px;opacity:' + (d > 1 ? 1 : 0);
    requestAnimationFrame(tick);
  })(last);
})();
