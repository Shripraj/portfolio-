(function () {
  'use strict';
  var root = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- theme toggle ---------- */
  var themeBtn = document.querySelector('[data-theme-toggle]');
  function syncThemeButton() {
    if (!themeBtn) return;
    var dark = root.getAttribute('data-theme') === 'dark';
    themeBtn.setAttribute('aria-pressed', dark ? 'true' : 'false');
  }
  if (themeBtn) {
    syncThemeButton();
    themeBtn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) { /* ignore */ }
      syncThemeButton();
    });
  }

  /* ---------- mobile menu ---------- */
  var menuBtn = document.querySelector('[data-menu-toggle]');
  var nav = document.getElementById('site-nav');
  function setMenu(open) {
    if (!menuBtn || !nav) return;
    nav.classList.toggle('is-open', open);
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      setMenu(!nav.classList.contains('is-open'));
    });
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setMenu(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setMenu(false);
    });
  }

  /* ---------- header shadow line and back-to-top ---------- */
  var header = document.querySelector('[data-site-header]');
  var toTop = document.querySelector('[data-to-top]');
  var ticking = false;
  function onScroll() {
    var y = window.scrollY || window.pageYOffset;
    if (header) header.classList.toggle('is-scrolled', y > 8);
    if (toTop) toTop.classList.toggle('is-visible', y > 600);
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { window.requestAnimationFrame(onScroll); ticking = true; }
  }, { passive: true });
  onScroll();
  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }

  /* ---------- project filters ---------- */
  var filterButtons = document.querySelectorAll('[data-filter]');
  var tiles = document.querySelectorAll('[data-project-grid] .tile');
  var emptyMsg = document.querySelector('[data-empty]');
  filterButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var wanted = button.getAttribute('data-filter');
      var visible = 0;
      filterButtons.forEach(function (b) {
        var active = b === button;
        b.classList.toggle('is-active', active);
        b.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      tiles.forEach(function (tile) {
        var slugs = (tile.getAttribute('data-categories') || '').split(' ');
        var match = wanted === 'all' || slugs.indexOf(wanted) > -1;
        tile.hidden = !match;
        if (match) visible += 1;
      });
      if (emptyMsg) emptyMsg.hidden = visible > 0;
    });
  });

  /* ---------- scroll reveals (content is visible without JS) ---------- */
  var revealItems = document.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach(function (el) { el.classList.add('is-visible'); });
  } else {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    revealItems.forEach(function (el) { observer.observe(el); });
  }

  /* ---------- contact notice: move focus so screen readers announce it ---------- */
  var notice = document.querySelector('[data-notice]');
  if (notice) {
    notice.setAttribute('tabindex', '-1');
    notice.focus({ preventScroll: true });
  }
})();
