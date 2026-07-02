// ============================================================
// Shridhar Patil Portfolio — core interactions
// ============================================================
document.addEventListener('DOMContentLoaded', () => {

  // ---- Loading screen ----
  const loader = document.getElementById('loading-screen');
  window.addEventListener('load', () => {
    setTimeout(() => loader && loader.classList.add('hidden'), 400);
  });
  // Fallback in case 'load' already fired
  setTimeout(() => loader && loader.classList.add('hidden'), 2500);

  // ---- AOS init ----
  if (window.AOS) {
    AOS.init({ duration: 700, once: true, offset: 60, easing: 'ease-out-cubic' });
  }

  // ---- Theme toggle (dark/light) ----
  const root = document.documentElement;
  const themeToggle = document.getElementById('theme-toggle');
  const savedTheme = localStorageGet('theme') || 'dark';
  root.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = root.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      localStorageSet('theme', next);
      updateThemeIcon(next);
    });
  }

  function updateThemeIcon(theme) {
    if (!themeToggle) return;
    const icon = themeToggle.querySelector('i');
    if (!icon) return;
    icon.className = theme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
  }

  // Safe localStorage wrappers (artifacts/sandboxes may block storage — app itself is fine on real hosting)
  function localStorageSet(key, val) { try { localStorage.setItem(key, val); } catch (e) {} }
  function localStorageGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }

  // ---- Navbar scroll state + active link ----
  const navbar = document.getElementById('navbar');
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  function onScroll() {
    // navbar background
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 40);

    // scroll progress bar
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    const bar = document.getElementById('scroll-progress-bar');
    if (bar) bar.style.width = progress + '%';

    // back to top visibility
    const btt = document.getElementById('back-to-top');
    if (btt) btt.classList.toggle('show', scrollTop > 500);

    // active nav link
    let currentId = '';
    sections.forEach(sec => {
      const top = sec.offsetTop - 120;
      if (scrollTop >= top) currentId = sec.id;
    });
    navLinks.forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === '#' + currentId);
    });
  }
  document.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ---- Back to top ----
  const backToTop = document.getElementById('back-to-top');
  if (backToTop) {
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  // ---- Mobile nav drawer ----
  const burger = document.getElementById('nav-burger');
  const drawer = document.getElementById('nav-drawer');
  const backdrop = document.getElementById('nav-drawer-backdrop');

  function closeDrawer() {
    burger && burger.classList.remove('open');
    drawer && drawer.classList.remove('open');
    backdrop && backdrop.classList.remove('open');
  }
  if (burger) {
    burger.addEventListener('click', () => {
      burger.classList.toggle('open');
      drawer.classList.toggle('open');
      backdrop.classList.toggle('open');
    });
  }
  backdrop && backdrop.addEventListener('click', closeDrawer);
  document.querySelectorAll('.nav-drawer .nav-link').forEach(a => a.addEventListener('click', closeDrawer));

  // ---- Custom cursor ----
  const cursorDot = document.getElementById('cursor-dot');
  const cursorRing = document.getElementById('cursor-ring');
  if (cursorDot && cursorRing && window.matchMedia('(hover: hover)').matches) {
    let ringX = 0, ringY = 0, mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX; mouseY = e.clientY;
      cursorDot.style.left = mouseX + 'px';
      cursorDot.style.top = mouseY + 'px';
    });
    function animateRing() {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      cursorRing.style.left = ringX + 'px';
      cursorRing.style.top = ringY + 'px';
      requestAnimationFrame(animateRing);
    }
    animateRing();

    document.querySelectorAll('a, button, input, textarea, .project-card, .cert-card').forEach(el => {
      el.addEventListener('mouseenter', () => cursorRing.classList.add('cursor-active'));
      el.addEventListener('mouseleave', () => cursorRing.classList.remove('cursor-active'));
    });
  }

  // ---- Animated counters ----
  const counters = document.querySelectorAll('.stat-num[data-count]');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(c => counterObserver.observe(c));

  function animateCounter(el) {
    const target = parseInt(el.getAttribute('data-count'), 10) || 0;
    const duration = 1200;
    const start = performance.now();
    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      el.textContent = Math.floor(progress * target);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    requestAnimationFrame(step);
  }

  // ---- Skill bar fill on scroll into view ----
  const skillBars = document.querySelectorAll('.skill-bar-fill[data-fill]');
  const skillObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target.getAttribute('data-fill');
        entry.target.style.width = fill + '%';
        skillObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  skillBars.forEach(b => skillObserver.observe(b));

  // ---- Flash message auto-dismiss ----
  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.flash-item').remove());
  });
  document.querySelectorAll('.flash-item').forEach(item => {
    setTimeout(() => { item.style.opacity = '0'; setTimeout(() => item.remove(), 400); }, 5000);
  });

  // ---- Footer year ----
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

});
