// ============================================================
// Hero typing effect — cycles through titles like a terminal print
// ============================================================
(function () {
  const el = document.getElementById('typed-text');
  if (!el) return;

  const titles = window.PORTFOLIO_TITLES && window.PORTFOLIO_TITLES.length
    ? window.PORTFOLIO_TITLES
    : ['Computer Science Engineering Student', 'Python Developer', 'Data Analyst'];

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let titleIndex = 0;
  let charIndex = 0;
  let deleting = false;

  const TYPE_SPEED = 55;
  const DELETE_SPEED = 30;
  const HOLD_TIME = 1400;

  if (prefersReducedMotion) {
    el.textContent = titles[0];
    return;
  }

  function tick() {
    const current = titles[titleIndex];

    if (!deleting) {
      charIndex++;
      el.textContent = current.slice(0, charIndex);
      if (charIndex === current.length) {
        deleting = true;
        setTimeout(tick, HOLD_TIME);
        return;
      }
      setTimeout(tick, TYPE_SPEED);
    } else {
      charIndex--;
      el.textContent = current.slice(0, charIndex);
      if (charIndex === 0) {
        deleting = false;
        titleIndex = (titleIndex + 1) % titles.length;
        setTimeout(tick, 300);
        return;
      }
      setTimeout(tick, DELETE_SPEED);
    }
  }

  tick();
})();
