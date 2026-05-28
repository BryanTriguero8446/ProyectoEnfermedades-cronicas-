/* ClinicalLens — main.js */

// ── Sidebar toggle ──────────────────────────────────────────────────────────
(function () {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebarToggle');
  if (!sidebar || !toggle) return;

  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', () =>
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar()
  );
  overlay.addEventListener('click', closeSidebar);
})();

// ── Alerts badge ────────────────────────────────────────────────────────────
(function () {
  if (!document.getElementById('alertas-badge')) return;

  function updateAlertasBadge() {
    fetch('/alertas/api/count/')
      .then(r => r.json())
      .then(data => {
        const count = data.count || 0;
        const badge = document.getElementById('alertas-badge');
        const dot   = document.getElementById('alertas-dot');
        if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline-block' : 'none'; }
        if (dot)   { dot.style.display = count > 0 ? 'block' : 'none'; }
      })
      .catch(() => {});
  }

  updateAlertasBadge();
  setInterval(updateAlertasBadge, 60000);
})();

// ── Mark alert as read ──────────────────────────────────────────────────────
function marcarLeida(pk, btn) {
  fetch('/alertas/marcar/' + pk + '/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        const row = btn.closest('.alerta-row') || btn.closest('tr');
        if (row) row.style.opacity = '.45';
        btn.disabled = true;
        btn.textContent = 'Leída';
      }
    });
}

function marcarTodasLeidas() {
  fetch('/alertas/marcar-todas/', {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  }).then(() => window.location.reload());
}

// ── CSRF helper ─────────────────────────────────────────────────────────────
function getCookie(name) {
  let cv = null;
  if (document.cookie) {
    for (const c of document.cookie.split(';')) {
      const t = c.trim();
      if (t.startsWith(name + '=')) { cv = decodeURIComponent(t.slice(name.length + 1)); break; }
    }
  }
  return cv;
}

// ── Auto-dismiss alerts ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.alert.alert-dismissible').forEach(el => {
    setTimeout(() => {
      const inst = bootstrap.Alert.getOrCreateInstance(el);
      if (inst) inst.close();
    }, 6000);
  });

  // Tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el =>
    new bootstrap.Tooltip(el)
  );

  // Auto-expand nav group if it contains the active page link
  document.querySelectorAll('.nav-group').forEach(function (group) {
    if (group.querySelector('.nav-link-item.active')) {
      group.classList.add('open');
    }
  });
});

// ── Desktop sidebar collapse (icon-only mode) ─────────────────────────────
(function () {
  const sidebar     = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('sidebarCollapseBtn');
  const wrapper     = document.getElementById('mainWrapper');
  if (!sidebar || !collapseBtn || !wrapper) return;

  var STORE_KEY = 'sidebarCollapsed';

  function applyCollapse(collapsed) {
    if (collapsed) {
      sidebar.classList.add('collapsed');
      wrapper.classList.add('sidebar-collapsed');
      collapseBtn.title = 'Expandir menú';
      collapseBtn.querySelector('i').className = 'bi bi-layout-sidebar';
    } else {
      sidebar.classList.remove('collapsed');
      wrapper.classList.remove('sidebar-collapsed');
      collapseBtn.title = 'Colapsar menú';
      collapseBtn.querySelector('i').className = 'bi bi-layout-sidebar-reverse';
    }
  }

  // Restore saved state (before paint to avoid layout shift)
  var saved = localStorage.getItem(STORE_KEY);
  if (saved === 'true') applyCollapse(true);

  collapseBtn.addEventListener('click', function () {
    var isCollapsed = sidebar.classList.contains('collapsed');
    applyCollapse(!isCollapsed);
    localStorage.setItem(STORE_KEY, String(!isCollapsed));
  });
})();

// ── Nav group toggle (sub-menu expand/collapse) ───────────────────────────
function toggleNavGroup(id) {
  var group = document.getElementById(id);
  if (!group) return;
  group.classList.toggle('open');
}
