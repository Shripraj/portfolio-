/* ===========================================================
   Glass View Modal
   Any element with `data-modal-view` opens its image inside the
   glass modal instead of navigating away / opening a new tab.

   data-modal-type: "image" | "pdf"   (defaults to "image")
   data-modal-title: optional label shown in the modal header
   data-modal-src: preferred source url; falls back to href
   href:            works too, for plain <a> triggers

   Gallery support: if the trigger sits inside a container that
   also holds a `<script type="application/json" class="gallery-data">`
   containing an array of image URLs, the modal shows prev/next
   arrows and a counter to page through all of them.
   =========================================================== */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var backdrop = document.getElementById('glass-modal-backdrop');
    var body = document.getElementById('glass-modal-body');
    var titleEl = document.getElementById('glass-modal-title');
    var closeBtn = document.getElementById('glass-modal-close');

    if (!backdrop || !body || !closeBtn) return;

    var lastFocused = null;
    var currentGallery = [];
    var currentIndex = 0;
    var currentTitle = '';

    function showLoader() {
      body.innerHTML = '<div class="glass-modal-loader"><i class="fa-solid fa-spinner fa-spin"></i></div>';
    }

    function renderImage(src, title) {
      showLoader();
      var img = new Image();
      img.className = 'glass-modal-img';
      img.alt = title || '';
      img.onload = function () {
        body.innerHTML = '';
        body.appendChild(img);
        if (currentGallery.length > 1) {
          appendNav();
        }
      };
      img.onerror = function () {
        body.innerHTML = '<p class="glass-modal-error">Couldn\'t load this file.</p>';
      };
      img.src = src;
    }

    function appendNav() {
      var prevBtn = document.createElement('button');
      prevBtn.type = 'button';
      prevBtn.className = 'glass-modal-nav glass-modal-nav-prev';
      prevBtn.setAttribute('aria-label', 'Previous photo');
      prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
      prevBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        step(-1);
      });

      var nextBtn = document.createElement('button');
      nextBtn.type = 'button';
      nextBtn.className = 'glass-modal-nav glass-modal-nav-next';
      nextBtn.setAttribute('aria-label', 'Next photo');
      nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
      nextBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        step(1);
      });

      var counter = document.createElement('span');
      counter.className = 'glass-modal-counter';
      counter.textContent = (currentIndex + 1) + ' / ' + currentGallery.length;

      body.appendChild(prevBtn);
      body.appendChild(nextBtn);
      body.appendChild(counter);
    }

    function step(delta) {
      currentIndex = (currentIndex + delta + currentGallery.length) % currentGallery.length;
      renderImage(currentGallery[currentIndex], currentTitle);
    }

    function findGallery(trigger) {
      var container = trigger.closest('.cert-card, .project-thumb, .project-card');
      if (!container) return [];
      var dataEl = container.querySelector('script.gallery-data');
      if (!dataEl) return [];
      try {
        var parsed = JSON.parse(dataEl.textContent);
        return Array.isArray(parsed) ? parsed : [];
      } catch (err) {
        return [];
      }
    }

    function openModal(type, src, title, gallery) {
      if (!src && (!gallery || gallery.length === 0)) return;

      currentTitle = title || '';
      titleEl.textContent = currentTitle;
      showLoader();

      lastFocused = document.activeElement;
      backdrop.classList.add('active');
      document.body.classList.add('modal-open');
      closeBtn.focus();

      if (type === 'pdf') {
        currentGallery = [];
        var iframe = document.createElement('iframe');
        iframe.className = 'glass-modal-iframe';
        iframe.src = src;
        iframe.title = title || 'Document preview';
        body.innerHTML = '';
        body.appendChild(iframe);
      } else {
        currentGallery = gallery && gallery.length > 0 ? gallery : [src];
        currentIndex = Math.max(0, currentGallery.indexOf(src));
        renderImage(currentGallery[currentIndex], title);
      }
    }

    function closeModal() {
      backdrop.classList.remove('active');
      document.body.classList.remove('modal-open');
      setTimeout(function () {
        body.innerHTML = '';
      }, 250);
      if (lastFocused && typeof lastFocused.focus === 'function') {
        lastFocused.focus();
      }
    }

    document.addEventListener('click', function (e) {
      var trigger = e.target.closest('[data-modal-view]');
      if (!trigger) return;
      e.preventDefault();
      var type = trigger.getAttribute('data-modal-type') || 'image';
      var src = trigger.getAttribute('data-modal-src') || trigger.getAttribute('href');
      var title = trigger.getAttribute('data-modal-title') || '';
      var gallery = type === 'pdf' ? [] : findGallery(trigger);
      openModal(type, src, title, gallery);
    });

    closeBtn.addEventListener('click', closeModal);

    backdrop.addEventListener('click', function (e) {
      if (e.target === backdrop) closeModal();
    });

    document.addEventListener('keydown', function (e) {
      if (!backdrop.classList.contains('active')) return;
      if (e.key === 'Escape') closeModal();
      if (e.key === 'ArrowLeft' && currentGallery.length > 1) step(-1);
      if (e.key === 'ArrowRight' && currentGallery.length > 1) step(1);
    });
  });
})();
