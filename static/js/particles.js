// ============================================================
// Lightweight animated particle network for the hero background
// ============================================================
(function () {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let particles = [];
  let width, height;
  const hero = canvas.closest('.hero');

  function resize() {
    width = canvas.width = hero.offsetWidth;
    height = canvas.height = hero.offsetHeight;
  }

  function isLight() {
    return document.documentElement.getAttribute('data-theme') === 'light';
  }

  function createParticles() {
    const count = Math.min(70, Math.floor((width * height) / 18000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: Math.random() * 1.8 + 0.6,
    }));
  }

  function step() {
    ctx.clearRect(0, 0, width, height);
    const dotColor = isLight() ? 'rgba(80, 90, 160, 0.55)' : 'rgba(180, 200, 255, 0.6)';
    const lineColorBase = isLight() ? '80, 90, 160' : '150, 170, 255';

    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > width) p.vx *= -1;
      if (p.y < 0 || p.y > height) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = dotColor;
      ctx.fill();
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(${lineColorBase}, ${0.14 * (1 - dist / 120)})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }

    if (!prefersReducedMotion) requestAnimationFrame(step);
  }

  resize();
  createParticles();
  step();

  window.addEventListener('resize', () => {
    resize();
    createParticles();
    if (prefersReducedMotion) step();
  });
})();
