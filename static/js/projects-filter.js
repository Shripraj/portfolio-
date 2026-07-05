// ============================================================
// Projects section — filter cards by category, no page reload
// ============================================================
(function () {
  const tabs = document.querySelectorAll('.filter-tab');
  const cards = document.querySelectorAll('.project-card');
  const emptyState = document.getElementById('project-empty-state');
  if (!tabs.length || !cards.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const filter = tab.getAttribute('data-filter');
      let visibleCount = 0;

      cards.forEach(card => {
        const matches = filter === 'all' || card.getAttribute('data-category') === filter;
        card.classList.toggle('filtered-out', !matches);
        if (matches) visibleCount++;
      });

      if (emptyState) emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
    });
  });
})();