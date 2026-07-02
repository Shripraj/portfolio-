// ============================================================
// Admin panel — small UX helpers
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.flash-item').remove());
  });
  document.querySelectorAll('.flash-item').forEach(item => {
    setTimeout(() => { item.style.opacity = '0'; setTimeout(() => item.remove(), 400); }, 5000);
  });
});
