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
    function setOpen(open) {
      menu.hidden = !open;
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
    var target = { x: 0, y: 0 }, pos = { x: 0, y: 0 }, running = false;
    function tick() {
      pos.x += (target.x - pos.x) * 0.1;
      pos.y += (target.y - pos.y) * 0.1;
      covers.style.setProperty('--x', pos.x + 'px');
      covers.style.setProperty('--y', pos.y + 'px');
      if (Math.abs(target.x - pos.x) > 0.5 || Math.abs(target.y - pos.y) > 0.5) requestAnimationFrame(tick);
      else running = false;
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
        if (!running) { pos.x = target.x = e.clientX - r.left; pos.y = target.y = e.clientY - r.top; tick(); }
        img.classList.add('on');
      });
      item.addEventListener('mouseleave', function () { img.classList.remove('on'); });
    });
  }
})();
