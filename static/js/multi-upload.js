/* ===========================================================
   Multi-file upload preview
   Turns a plain <input type="file" multiple> into a small
   thumbnail grid with per-image remove buttons.

   Usage:
     <input type="file" id="my-input" name="images" multiple>
     <div id="my-preview"></div>
     <script>initMultiUpload('my-input', 'my-preview');</script>
   =========================================================== */
function initMultiUpload(inputId, previewId) {
  var input = document.getElementById(inputId);
  var preview = document.getElementById(previewId);
  if (!input || !preview) return;

  // Running list of files currently selected, kept in sync with input.files
  var files = [];

  function render() {
    preview.innerHTML = '';

    if (files.length === 0) {
      return;
    }

    files.forEach(function (file, index) {
      var item = document.createElement('div');
      item.className = 'multi-upload-item';

      var img = document.createElement('img');
      img.alt = file.name;
      var reader = new FileReader();
      reader.onload = function (e) {
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);

      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'multi-upload-remove';
      removeBtn.setAttribute('aria-label', 'Remove ' + file.name);
      removeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      removeBtn.addEventListener('click', function () {
        files.splice(index, 1);
        syncInput();
        render();
      });

      var name = document.createElement('span');
      name.className = 'multi-upload-name';
      name.textContent = file.name;

      item.appendChild(img);
      item.appendChild(removeBtn);
      item.appendChild(name);
      preview.appendChild(item);
    });

    var countEl = document.createElement('p');
    countEl.className = 'multi-upload-count';
    countEl.textContent = files.length + (files.length === 1 ? ' file selected' : ' files selected');
    preview.appendChild(countEl);
  }

  function syncInput() {
    // Rebuild input.files from our `files` array so the form submits
    // only what's left after removals (browsers won't let you edit
    // a FileList directly, so we go through DataTransfer).
    var dt = new DataTransfer();
    files.forEach(function (file) {
      dt.items.add(file);
    });
    input.files = dt.files;
  }

  input.addEventListener('change', function () {
    files = Array.prototype.slice.call(input.files);
    render();
  });
}
