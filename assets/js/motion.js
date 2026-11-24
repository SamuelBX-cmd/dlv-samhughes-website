// samhughes.com.au: motion layer. Changes how the site moves, never how it looks at rest:
// every effect ends exactly on the original layout, and split headlines are restored to
// their original markup once they have landed.
// The head script only adds .motion when JS runs and reduced motion is off.
(function () {
  var root = document.documentElement;
  window.__motion = true;
  if (!root.classList.contains('motion')) return;

  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  /* ---------- Smooth, inertial scrolling (desktop mouse and trackpad only) ---------- */
  var lenis = null;
  if (fine && window.Lenis) {
    lenis = new window.Lenis({ lerp: 0.11, wheelMultiplier: 1, anchors: { offset: -80 }, autoRaf: true });
    // pause while the mobile menu is open
    new MutationObserver(function () {
      if (document.body.classList.contains('menu-open')) lenis.stop(); else lenis.start();
    }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }
  var scrollY = function () { return window.scrollY; };

  /* ---------- Headlines: words slide up from behind a mask, line by line ---------- */
  var heads = [];
  document.querySelectorAll('main .display, main .lead').forEach(function (h) {
    var original = h.innerHTML;
    (function wrap(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 1 && n.tagName !== 'BR') return wrap(n);
        if (n.nodeType !== 3 || !n.textContent.trim()) return;
        var frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach(function (part) {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
          var w = document.createElement('span'); w.className = 'm-w';
          var i = document.createElement('span'); i.className = 'm-wi'; i.textContent = part;
          w.appendChild(i); frag.appendChild(w);
        });
        node.replaceChild(frag, n);
      });
    })(h);
    // stagger by line: group words by their vertical position
    var tops = [], words = h.querySelectorAll('.m-w');
    words.forEach(function (w) {
      var t = Math.round(w.offsetTop);
      if (tops.indexOf(t) < 0) tops.push(t);
      w.firstChild.style.setProperty('--l', (tops.indexOf(t) * 80) + 'ms');
    });
    h.classList.add('m-split');
    heads.push({ el: h, original: original, lines: tops.length });
  });
  function restore(hd) {
    // after the last line lands, put the original markup back: identical rendering at rest
    setTimeout(function () { hd.el.innerHTML = hd.original; hd.el.classList.add('m-done'); }, 900 + hd.lines * 80);
  }

  /* ---------- Reveal targets, grouped so each group staggers on its own ---------- */
  var groups = [];
  document.querySelectorAll('main .row, .site-footer .foot').forEach(function (row) {
    var items = [];
    Array.prototype.forEach.call(row.children, function (c) {
      if (c.matches('.label, .article-side')) items.push(c);
      else if (c.matches('.content')) {
        Array.prototype.forEach.call(c.children, function (k) {
          if (k.matches('.numbered')) items.push.apply(items, k.children);
          else items.push(k);
        });
      } else if (row.matches('.foot')) items.push(c);
    });
    groups.push(items);
  });
  var base = document.querySelector('.site-footer .foot-base');
  if (base) groups.push([base]);

  var all = [];
  groups.forEach(function (items) {
    var writing = items.length && items[0].parentElement && items[0].parentElement.classList.contains('writing');
    items.forEach(function (el, i) {
      var step = writing ? (i % 2) : Math.min(i, 6);
      el.style.setProperty('--d', (step * 70) + 'ms');
      all.push(el);
    });
  });

  function markDone(el) {
    el.addEventListener('transitionend', function f(e) {
      if (e.target !== el || e.propertyName !== 'translate') return;
      el.classList.add('m-done');
      el.removeEventListener('transitionend', f);
    });
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      var el = en.target;
      markDone(el);
      el.classList.add('m-in');
      heads.forEach(function (hd) { if (hd.el === el) restore(hd); });
      io.unobserve(el);
    });
  }, { rootMargin: '0px', threshold: 0 });
  all.forEach(function (el) { io.observe(el); });
  window.addEventListener('beforeprint', function () {
    all.forEach(function (el) { el.classList.add('m-in', 'm-done'); });
    heads.forEach(function (hd) { hd.el.innerHTML = hd.original; });
  });

  /* ---------- Hero: drifts up and softens as you scroll away (back to normal at the top) ---------- */
  var hero = document.querySelector('main .row.hero:not(.article-head) .content');
  var heroH = hero ? hero.closest('.row').offsetHeight : 0;

  /* ---------- Header: steps aside while reading down, returns on any scroll up ---------- */
  var header = document.querySelector('.site-header');
  var lastY = scrollY(), ticking = false;
  function onScroll() {
    var y = scrollY();
    if (hero) {
      var p = Math.min(Math.max(y / heroH, 0), 1);
      hero.style.translate = p ? '0 ' + (p * heroH * 0.22).toFixed(1) + 'px' : '';
      hero.style.opacity = p ? (1 - p * 0.65).toFixed(3) : '';
    }
    if (header) {
      var dy = y - lastY;
      var menuOpen = document.body.classList.contains('menu-open');
      if (menuOpen || header.contains(document.activeElement) || y < header.offsetHeight * 3) header.classList.remove('m-hide');
      else if (dy > 6) header.classList.add('m-hide');
      else if (dy < -6) header.classList.remove('m-hide');
      if (Math.abs(dy) > 6) lastY = y;
    }
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  window.addEventListener('resize', function () { if (hero) heroH = hero.closest('.row').offsetHeight; });
  if (header) header.addEventListener('focusin', function () { header.classList.remove('m-hide'); });

  /* ---------- Magnetic call to action: the button leans toward the cursor ---------- */
  if (fine) {
    document.querySelectorAll('.btn-soft').forEach(function (btn) {
      // spring: M3 expressive fast spatial (damping 0.6, stiffness 800)
      var K = 800, C = 2 * 0.6 * Math.sqrt(K), pos = { x: 0, y: 0 }, vel = { x: 0, y: 0 }, tgt = { x: 0, y: 0 }, raf = 0, last = 0;
      function step(now) {
        var dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
        for (var i = 0; i < 4; i++) {
          var h = dt / 4;
          vel.x += (-K * (pos.x - tgt.x) - C * vel.x) * h; pos.x += vel.x * h;
          vel.y += (-K * (pos.y - tgt.y) - C * vel.y) * h; pos.y += vel.y * h;
        }
        var settled = Math.abs(pos.x - tgt.x) < 0.05 && Math.abs(pos.y - tgt.y) < 0.05 && Math.abs(vel.x) + Math.abs(vel.y) < 0.5;
        if (settled) { pos.x = tgt.x; pos.y = tgt.y; }
        btn.style.translate = (pos.x || pos.y) ? pos.x.toFixed(2) + 'px ' + pos.y.toFixed(2) + 'px' : '';
        if (settled) { raf = 0; last = 0; } else raf = requestAnimationFrame(step);
      }
      function go() { if (!raf) raf = requestAnimationFrame(step); }
      btn.addEventListener('pointermove', function (e) {
        var r = btn.getBoundingClientRect();
        tgt.x = (e.clientX - (r.left + r.width / 2)) * 0.18;
        tgt.y = (e.clientY - (r.top + r.height / 2)) * 0.25;
        go();
      });
      btn.addEventListener('pointerleave', function () { tgt.x = 0; tgt.y = 0; go(); });
    });
  }
})();
