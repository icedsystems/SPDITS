/* ============================================================
   ICED SPDITS — Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // Sidebar toggle
  const menuToggle = document.getElementById('menu-toggle');
  const wrapper = document.getElementById('wrapper');
  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      wrapper.classList.toggle('toggled');
    });
  }

  // Mark active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.list-group-item-action').forEach(link => {
    if (link.getAttribute('href') && currentPath.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/dashboard/') {
      link.classList.add('active');
    } else if (link.getAttribute('href') === '/dashboard/' && currentPath === '/dashboard/') {
      link.classList.add('active');
    }
  });

  // DataTables init on any table with class datatable
  if (typeof $ !== 'undefined' && $.fn.DataTable) {
    $('.datatable').each(function () {
      $(this).DataTable({
        pageLength: 25,
        responsive: true,
        language: { search: '', searchPlaceholder: 'Search...' },
        dom: '<"row"<"col-sm-6"l><"col-sm-6"f>>rt<"row"<"col-sm-6"i><"col-sm-6"p>>',
      });
    });
  }

  // Drag-and-drop file upload zone
  const zone = document.getElementById('upload-zone');
  if (zone) {
    const input = document.getElementById('id_file');
    zone.addEventListener('click', () => input && input.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files.length && input) {
        input.files = e.dataTransfer.files;
        updateFileLabel(e.dataTransfer.files[0]);
      }
    });
    if (input) {
      input.addEventListener('change', () => {
        if (input.files[0]) updateFileLabel(input.files[0]);
      });
    }
  }

  function updateFileLabel(file) {
    const label = document.getElementById('file-label');
    if (label) label.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
    const zone = document.getElementById('upload-zone');
    if (zone) zone.classList.add('border-primary', 'bg-primary-subtle');
  }

  // Bulk select table rows
  const selectAll = document.getElementById('select-all');
  if (selectAll) {
    selectAll.addEventListener('change', function () {
      document.querySelectorAll('.row-check').forEach(cb => cb.checked = this.checked);
      updateBulkActionBar();
    });
    document.querySelectorAll('.row-check').forEach(cb => {
      cb.addEventListener('change', updateBulkActionBar);
    });
  }

  function updateBulkActionBar() {
    const checked = document.querySelectorAll('.row-check:checked').length;
    const bar = document.getElementById('bulk-action-bar');
    const countEl = document.getElementById('selected-count');
    if (bar) bar.style.display = checked > 0 ? 'flex' : 'none';
    if (countEl) countEl.textContent = checked;
    // Collect selected IDs into hidden input
    const ids = Array.from(document.querySelectorAll('.row-check:checked')).map(cb => cb.value);
    document.querySelectorAll('.selected-ids-input').forEach(inp => inp.value = ids.join(','));
  }

  // Session timeout countdown (if element present)
  const countdown = document.getElementById('session-countdown');
  if (countdown) {
    let secs = parseInt(countdown.dataset.seconds || '300');
    const interval = setInterval(() => {
      secs--;
      const m = Math.floor(secs / 60);
      const s = secs % 60;
      countdown.textContent = `${m}:${s.toString().padStart(2, '0')}`;
      if (secs <= 0) {
        clearInterval(interval);
        window.location.href = '/accounts/login/?timeout=1';
      }
    }, 1000);
  }

  // HTMX: show toast on after-swap
  document.body.addEventListener('htmx:afterSwap', function (evt) {
    initToasts();
  });

  function initToasts() {
    document.querySelectorAll('.toast:not(.initialized)').forEach(el => {
      el.classList.add('initialized');
      const t = new bootstrap.Toast(el, { delay: 4000 });
      t.show();
    });
  }

  // Auto-dismiss alerts after 5s
  setTimeout(() => {
    document.querySelectorAll('.alert-dismissible').forEach(el => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    });
  }, 5000);

  // Confirm dangerous actions
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  });

  // Re-identification auto-hide timer
  const reidentifyBox = document.getElementById('reidentify-box');
  if (reidentifyBox) {
    let remaining = 60;
    const timerEl = document.getElementById('reidentify-timer');
    const timer = setInterval(() => {
      remaining--;
      if (timerEl) timerEl.textContent = remaining;
      if (remaining <= 0) {
        clearInterval(timer);
        reidentifyBox.innerHTML = '<div class="alert alert-danger">Session expired. Data hidden for security.</div>';
      }
    }, 1000);
  }

});
