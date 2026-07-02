// ============================================================
// Contact form — submits via fetch without a full page reload
// ============================================================
(function () {
  const form = document.getElementById('contact-form');
  if (!form) return;
  const status = document.getElementById('form-status');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    status.textContent = '';
    status.className = 'form-status';

    try {
      const formData = new FormData(form);
      const res = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData,
      });
      const data = await res.json();

      if (data.success) {
        status.textContent = data.message || 'Message sent successfully!';
        status.classList.add('ok');
        form.reset();
      } else {
        status.textContent = (data.errors && data.errors.join(' ')) || 'Something went wrong.';
        status.classList.add('err');
      }
    } catch (err) {
      status.textContent = 'Network error — please try again.';
      status.classList.add('err');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalHTML;
    }
  });
})();
