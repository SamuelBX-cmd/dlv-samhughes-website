// samhughes.com.au: header offset, mobile menu, portfolio hover covers.
(function () {
  var root = document.documentElement;
  var header = document.querySelector('.site-header');

  function setHeaderHeight() {
    if (header) root.style.setProperty('--hdr', header.offsetHeight + 'px');
  }
  setHeaderHeight();
  window.addEventListener('resize', setHeaderHeight);

  // Mobile menu
  var toggle = document.querySelector('.menu-toggle');
  var menu = document.getElementById('mobile-menu');
  if (toggle && menu) {
    var label = toggle.querySelector('.sr');
    var closeTimer;
    function setOpen(open) {
      // Motion: fade the menu in and out (motion.css); hide it once the fade has finished
      clearTimeout(closeTimer);
      if (open) {
        menu.hidden = false;
        requestAnimationFrame(function () { requestAnimationFrame(function () { menu.classList.add('m-open'); }); });
      } else {
        menu.classList.remove('m-open');
        var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduce) menu.hidden = true;
        else closeTimer = setTimeout(function () { menu.hidden = true; }, 160);
      }
      toggle.setAttribute('aria-expanded', String(open));
      document.body.classList.toggle('menu-open', open);
      if (label) label.textContent = open ? 'Close Menu' : 'Open Menu';
    }
    toggle.addEventListener('click', function () { setOpen(menu.hidden); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) setOpen(false); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 768 && !menu.hidden) setOpen(false); });
  }

  // Portfolio index: cover image follows the cursor while hovering a title
  var list = document.querySelector('.pf-list');
  var covers = document.querySelector('.pf-covers');
  if (list && covers && window.matchMedia('(hover: hover)').matches) {
    var section = list.closest('.sec');
    // Motion: the cover follows on a spring (M3 expressive default spatial: damping 0.8, stiffness 380),
    // so it keeps its momentum when the cursor changes direction instead of easing to a stop.
    var target = { x: 0, y: 0 }, pos = { x: 0, y: 0 }, vel = { x: 0, y: 0 }, running = false, last = 0;
    var K = 380, C = 2 * 0.8 * Math.sqrt(K);
    function tick(now) {
      now = now || performance.now();
      var dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
      for (var i = 0; i < 4; i++) {
        var h = dt / 4;
        vel.x += (-K * (pos.x - target.x) - C * vel.x) * h; pos.x += vel.x * h;
        vel.y += (-K * (pos.y - target.y) - C * vel.y) * h; pos.y += vel.y * h;
      }
      covers.style.setProperty('--x', pos.x + 'px');
      covers.style.setProperty('--y', pos.y + 'px');
      if (Math.abs(target.x - pos.x) > 0.5 || Math.abs(target.y - pos.y) > 0.5 || Math.abs(vel.x) + Math.abs(vel.y) > 5) requestAnimationFrame(tick);
      else { running = false; last = 0; }
    }
    section.addEventListener('mousemove', function (e) {
      var r = section.getBoundingClientRect();
      target.x = e.clientX - r.left;
      target.y = e.clientY - r.top;
      if (!running) { running = true; requestAnimationFrame(tick); }
    });
    list.querySelectorAll('.pf-item').forEach(function (item) {
      var img = covers.querySelector('img[data-for="' + item.dataset.id + '"]');
      if (!img) return;
      item.addEventListener('mouseenter', function (e) {
        var r = section.getBoundingClientRect();
        if (!running) { pos.x = target.x = e.clientX - r.left; pos.y = target.y = e.clientY - r.top; vel.x = vel.y = 0; tick(); }
        img.classList.add('on');
      });
      item.addEventListener('mouseleave', function () { img.classList.remove('on'); });
    });
  }
})();
