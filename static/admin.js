/* Admin dashboard. Vanilla JS, schema-driven: each content type is described
   once in MODULES and rendered by the generic list, form and preview engine. */
(function () {
  'use strict';

  var API = document.querySelector('meta[name="api-base"]').content.replace(/\/$/, '');
  var PUBLIC_URL = document.querySelector('meta[name="public-url"]').content;
  var state = { csrf: null, user: null, options: {}, currentView: 'overview', items: [], query: new URLSearchParams() };

  /* ------------------------------------------------------------- utilities */
  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function fmtDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  function busy(on) { document.body.classList.toggle('is-loading', !!on); }

  function toast(message, kind) {
    var el = document.createElement('div');
    el.className = 'toast toast--' + (kind || 'ok');
    el.textContent = message;
    $('#toasts').appendChild(el);
    setTimeout(function () { el.classList.add('is-leaving'); }, 3600);
    setTimeout(function () { el.remove(); }, 4200);
  }

  function ApiError(message, status, errors) {
    this.message = message; this.status = status; this.errors = errors || {};
  }
  ApiError.prototype = Object.create(Error.prototype);

  /* ---------------------------------------------------------------- API */
  function api(method, path, body) {
    var headers = {};
    var payload;
    if (method !== 'GET' && state.csrf) headers['X-CSRF-TOKEN'] = state.csrf;
    if (body instanceof FormData) {
      payload = body;
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    busy(true);
    return fetch(API + path, { method: method, headers: headers, body: payload, credentials: 'include' })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          busy(false);
          if (res.status === 401 && path !== '/api/auth/login') {
            showLogin(path === '/api/auth/me' ? '' : 'Your session has ended. Please sign in again.');
            throw new ApiError(data.error || 'Signed out', 401, {});
          }
          if (!res.ok) throw new ApiError(data.error || 'Something went wrong.', res.status, data.errors);
          return data;
        });
      }, function () {
        busy(false);
        throw new ApiError('Could not reach the API. Check your connection and try again.', 0, {});
      });
  }

  function errorText(err) {
    if (err && err.errors && Object.keys(err.errors).length) {
      return Object.keys(err.errors).map(function (k) { return k + ': ' + err.errors[k]; }).join(' · ');
    }
    return (err && err.message) || 'Something went wrong.';
  }

  function loadOptions(endpoint) {
    return api('GET', '/api/admin/' + endpoint).then(function (data) {
      state.options[endpoint] = data.items || [];
      return state.options[endpoint];
    });
  }

  /* ------------------------------------------------------- module schema */
  var MODES = [{ value: 'python', label: 'Python Software Developer' }, { value: 'data', label: 'Data Analyst' }];
  var SECTIONS = [
    { value: 'about', label: 'About' }, { value: 'projects', label: 'Projects' },
    { value: 'experience', label: 'Experience' }, { value: 'skills', label: 'Skills' },
    { value: 'certifications', label: 'Certifications' }, { value: 'contact', label: 'Contact' }
  ];

  function statusBadge(published) {
    return published ? '<span class="badge badge--ok">Published</span>' : '<span class="badge">Draft</span>';
  }

  var MODULES = {
    projects: {
      title: 'Projects', endpoint: 'projects', noun: 'project', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Title', render: function (r) { return '<strong>' + esc(r.title) + '</strong>' + (r.slug ? '<div class="muted small">/projects/' + esc(r.slug) + '</div>' : ''); } },
        { label: 'Categories', render: function (r) { return (r.category_names || []).length ? esc(r.category_names.join(', ')) : '<span class="gap">Missing</span>'; } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } },
        { label: 'Featured', render: function (r) { return r.featured ? 'Yes' : '—'; } }
      ],
      fields: [
        { name: 'title', label: 'Title', type: 'text', required: true },
        { name: 'slug', label: 'URL slug', type: 'text', help: 'Leave blank to generate from the title. Changing it changes the project link.' },
        { name: 'category_ids', label: 'Categories', type: 'multi', source: 'project-categories', help: 'Tick every category the project belongs to. A project can appear under several filters.' },
        { name: 'summary', label: 'Natural description (card)', type: 'textarea', rows: 3, required: true },
        { name: 'problem', label: 'Problem statement', type: 'textarea', rows: 3, help: 'Left empty when not supplied by the resume. Do not guess.' },
        { name: 'solution', label: 'Solution', type: 'textarea', rows: 3 },
        { name: 'details', label: 'Detailed case study', type: 'textarea', rows: 6, help: 'Optional. Separate paragraphs with a blank line.' },
        { name: 'technologies', label: 'Technology stack', type: 'list', help: 'One per line.' },
        { name: 'features', label: 'Key features', type: 'list', help: 'One per line.' },
        { name: 'outcomes', label: 'Outcomes (as reported)', type: 'list', help: 'One per line. Use only figures the resume supports.' },
        { name: 'github_url', label: 'GitHub repository', type: 'url' },
        { name: 'live_url', label: 'Live demo', type: 'url' },
        { name: 'image_id', label: 'Project image', type: 'media', kind: 'image' },
        { name: 'modes', label: 'Leads in career views', type: 'checks', options: MODES },
        { name: 'featured', label: 'Featured on homepage', type: 'checkbox' },
        { name: 'is_published', label: 'Published', type: 'checkbox', help: 'Drafts are never shown on the public site.' }
      ],
      preview: true,
      defaults: { is_published: false, featured: false, modes: [], category_ids: [] }
    },
    'project-categories': {
      title: 'Project categories', endpoint: 'project-categories', noun: 'category', reorder: true,
      columns: [{ label: 'Name', render: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } }],
      fields: [{ name: 'name', label: 'Name', type: 'text', required: true }]
    },
    skills: {
      title: 'Skills', endpoint: 'skills', noun: 'skill', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Skill', render: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } },
        { label: 'Category', render: function (r) { return esc(optionLabel('skill-categories', r.category_id)); } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } }
      ],
      fields: [
        { name: 'name', label: 'Skill', type: 'text', required: true },
        { name: 'category_id', label: 'Category', type: 'select', source: 'skill-categories', required: true },
        { name: 'is_published', label: 'Published', type: 'checkbox' }
      ],
      defaults: { is_published: true }
    },
    'skill-categories': {
      title: 'Skill categories', endpoint: 'skill-categories', noun: 'category', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Category', render: function (r) { return '<strong>' + esc(r.name) + '</strong>'; } },
        { label: 'Shown in', render: function (r) { return esc((r.modes || []).join(', ')) || '—'; } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } }
      ],
      fields: [
        { name: 'name', label: 'Name', type: 'text', required: true },
        { name: 'modes', label: 'Emphasised in career views', type: 'checks', options: MODES },
        { name: 'is_published', label: 'Published', type: 'checkbox' }
      ],
      defaults: { is_published: true, modes: [] }
    },
    experience: {
      title: 'Experience', endpoint: 'experience', noun: 'role', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Role', render: function (r) { return '<strong>' + esc(r.role) + '</strong><div class="muted small">' + esc(r.organization) + '</div>'; } },
        { label: 'Dates', render: function (r) { return esc(r.start_label) + (r.end_label ? ' – ' + esc(r.end_label) : ''); } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } }
      ],
      fields: [
        { name: 'organization', label: 'Organisation', type: 'text', required: true },
        { name: 'role', label: 'Role', type: 'text', required: true },
        { name: 'location', label: 'Location', type: 'text' },
        { name: 'employment_type', label: 'Type', type: 'text', help: 'For example Internship or Full-time.' },
        { name: 'start_label', label: 'Start', type: 'text', required: true, help: 'For example Aug 2026.' },
        { name: 'end_label', label: 'End', type: 'text', help: 'Leave blank if not applicable. Use Present for current roles.' },
        { name: 'responsibilities', label: 'Responsibilities', type: 'list', help: 'One per line.' },
        { name: 'is_published', label: 'Published', type: 'checkbox' }
      ],
      defaults: { is_published: true }
    },
    education: {
      title: 'Education', endpoint: 'education', noun: 'entry', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Qualification', render: function (r) { return '<strong>' + esc(r.qualification) + '</strong><div class="muted small">' + esc(r.institution) + '</div>'; } },
        { label: 'Period', render: function (r) { return esc(r.period); } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } }
      ],
      fields: [
        { name: 'institution', label: 'Institution', type: 'text', required: true },
        { name: 'qualification', label: 'Qualification', type: 'text', required: true },
        { name: 'location', label: 'Location', type: 'text' },
        { name: 'period', label: 'Period', type: 'text', help: 'For example Expected 2027.' },
        { name: 'details', label: 'Details', type: 'textarea', rows: 3 },
        { name: 'is_published', label: 'Published', type: 'checkbox' }
      ],
      defaults: { is_published: true }
    },
    certifications: {
      title: 'Certifications', endpoint: 'certifications', noun: 'certification', reorder: true, toggle: 'is_published',
      columns: [
        { label: 'Certification', render: function (r) { return '<strong>' + esc(r.name) + '</strong><div class="muted small">' + esc(r.issuer) + '</div>'; } },
        { label: 'Verification', render: function (r) { return r.verification_url ? '<span class="badge badge--ok">Link</span>' : '<span class="gap">Not added</span>'; } },
        { label: 'Status', render: function (r) { return statusBadge(r.is_published); } }
      ],
      fields: [
        { name: 'name', label: 'Certificate name', type: 'text', required: true },
        { name: 'issuer', label: 'Issuing organisation', type: 'text', required: true },
        { name: 'issued_label', label: 'Date', type: 'text', help: 'For example February 2026. Leave blank if unknown.' },
        { name: 'verification_url', label: 'Verification link', type: 'url' },
        { name: 'media_id', label: 'Certificate file (PDF or image)', type: 'media' },
        { name: 'is_published', label: 'Published', type: 'checkbox' }
      ],
      defaults: { is_published: true }
    },
    messages: {
      title: 'Messages', endpoint: 'messages', noun: 'message', search: true, messages: true
    }
  };

  var SINGLETONS = {
    profile: {
      title: 'Profile', endpoint: 'profile', put: '/api/admin/profile',
      fields: [
        { name: 'name', label: 'Name', type: 'text', required: true },
        { name: 'headline', label: 'Professional headline', type: 'text', required: true },
        { name: 'primary_title', label: 'Primary title', type: 'text' },
        { name: 'secondary_title', label: 'Secondary title', type: 'text' },
        { name: 'bio', label: 'Biography', type: 'textarea', rows: 6 },
        { name: 'intro_developer', label: 'Introduction (Python Software Developer view)', type: 'textarea', rows: 3 },
        { name: 'intro_analyst', label: 'Introduction (Data Analyst view)', type: 'textarea', rows: 3 },
        { name: 'email', label: 'Email', type: 'email' },
        { name: 'phone', label: 'Phone', type: 'text' },
        { name: 'location', label: 'Location', type: 'text' },
        { name: 'linkedin_url', label: 'LinkedIn', type: 'url' },
        { name: 'github_url', label: 'GitHub', type: 'url' },
        { name: 'photo_id', label: 'Profile photograph (optional)', type: 'media', kind: 'image' }
      ]
    },
    settings: {
      title: 'Website settings', endpoint: 'settings', put: '/api/admin/settings',
      fields: [
        { name: 'site_title', label: 'Website title', type: 'text' },
        { name: 'meta_description', label: 'Meta description', type: 'textarea', rows: 2 },
        { name: 'seo_keywords', label: 'SEO keywords (comma separated)', type: 'text' },
        { name: 'homepage_headline', label: 'Homepage headline', type: 'text' },
        { name: 'homepage_bio', label: 'Homepage biography', type: 'textarea', rows: 3 },
        { name: 'default_theme', label: 'Default theme', type: 'select', options: [{ value: 'light', label: 'Light' }, { value: 'dark', label: 'Dark' }] },
        { name: 'visible_sections', label: 'Visible sections', type: 'checks', options: SECTIONS }
      ]
    }
  };

  function optionLabel(endpoint, id) {
    var list = state.options[endpoint] || [];
    var hit = list.filter(function (o) { return o.id === id; })[0];
    return hit ? (hit.name || hit.title || hit.label || '') : '';
  }

  /* ------------------------------------------------------------ navigation */
  var NAV = [
    { view: 'overview', label: 'Overview' },
    { view: 'profile', label: 'Profile' },
    { view: 'projects', label: 'Projects' },
    { view: 'project-categories', label: 'Project categories' },
    { view: 'skill-categories', label: 'Skill groups' },
    { view: 'skills', label: 'Skills' },
    { view: 'experience', label: 'Experience' },
    { view: 'education', label: 'Education' },
    { view: 'certifications', label: 'Certifications' },
    { view: 'resumes', label: 'Resumes' },
    { view: 'media', label: 'Media library' },
    { view: 'messages', label: 'Messages' },
    { view: 'settings', label: 'Website settings' }
  ];

  function renderNav() {
    $('#nav').innerHTML = NAV.map(function (item) {
      return '<a href="#' + item.view + '" data-view="' + item.view + '">' + esc(item.label) + '</a>';
    }).join('');
    $('#view-site').href = PUBLIC_URL;
  }

  function setActiveNav(view) {
    $all('#nav a').forEach(function (a) { a.classList.toggle('is-active', a.getAttribute('data-view') === view); });
  }

  function route() {
    if (!state.user) return;
    var raw = window.location.hash.slice(1) || 'overview';
    var parts = raw.split('?');
    var view = parts[0];
    state.query = new URLSearchParams(parts[1] || '');
    state.currentView = view;
    setActiveNav(view);
    var content = $('#content');
    content.innerHTML = '<div id="progress" class="progress" aria-hidden="true"></div>';
    content.focus({ preventScroll: true });

    if (view === 'overview') return renderOverview();
    if (view === 'profile') return renderSingleton('profile');
    if (view === 'settings') return renderSingleton('settings');
    if (view === 'resumes') return renderResumes();
    if (view === 'media') return renderMedia();
    if (MODULES[view]) return renderCollection(view);
    content.insertAdjacentHTML('beforeend', '<p>Section not found.</p>');
  }

  /* ----------------------------------------------------------- overview */
  function renderOverview() {
    var content = $('#content');
    api('GET', '/api/admin/overview').then(function (o) {
      var cards = [
        ['Projects', o.projects.total, o.projects.published + ' published · ' + o.projects.draft + ' draft'],
        ['Skills', o.skills.total, 'Across all groups'],
        ['Certifications', o.certifications.total, o.certifications.published + ' published · ' + o.certifications.draft + ' draft'],
        ['Experience', o.experience.total, o.experience.published + ' published · ' + o.experience.draft + ' draft'],
        ['Media files', o.media, 'Images and PDFs'],
        ['Unread messages', o.unread_messages, '<a href="#messages">Open messages</a>']
      ];
      var recent = (o.recent_updates || []).map(function (r) {
        return '<li><span class="badge">' + esc(r.type) + '</span> ' + esc(r.title) + '<span class="muted small"> · ' + fmtDate(r.updated_at) + '</span></li>';
      }).join('') || '<li class="muted">Nothing has been edited yet.</li>';
      content.insertAdjacentHTML('beforeend',
        '<header class="page-head"><h1>Overview</h1><p class="muted">Changes you publish here appear on the public site within about 30 seconds. Drafts never go live.</p></header>' +
        '<div class="stats">' + cards.map(function (c) {
          return '<div class="stat"><span class="stat__label">' + esc(c[0]) + '</span><strong class="stat__value">' + esc(c[1]) + '</strong><span class="stat__note">' + c[2] + '</span></div>';
        }).join('') + '</div>' +
        '<section class="panel"><h2>Recent updates</h2><ul class="recent">' + recent + '</ul></section>');
    }).catch(function (e) { content.insertAdjacentHTML('beforeend', '<p class="form-error">' + esc(errorText(e)) + '</p>'); });
  }

  /* -------------------------------------------------------- singletons */
  function renderSingleton(key) {
    var mod = SINGLETONS[key];
    var content = $('#content');
    content.insertAdjacentHTML('beforeend', '<header class="page-head"><h1>' + esc(mod.title) + '</h1></header><div id="singleton"></div>');
    api('GET', '/api/admin/' + mod.endpoint).then(function (values) {
      var form = buildForm(mod.fields, values);
      $('#singleton').innerHTML = '<form class="panel form-grid" id="single-form" novalidate>' + form + '<div class="form-actions"><p id="single-error" class="form-error" role="alert" hidden></p><button class="btn btn--primary" type="submit">Save changes</button></div></form>';
      bindMediaPickers($('#single-form'));
      $('#single-form').addEventListener('submit', function (e) {
        e.preventDefault();
        var body = collect(mod.fields, $('#single-form'));
        var button = $('#single-form button[type=submit]');
        setBusy(button, true);
        api('PUT', mod.put, body).then(function () {
          toast(mod.title + ' saved.');
          route();
        }).catch(function (err) {
          setBusy(button, false);
          var box = $('#single-error'); box.hidden = false; box.textContent = errorText(err);
        });
      });
    }).catch(function (e) { content.insertAdjacentHTML('beforeend', '<p class="form-error">' + esc(errorText(e)) + '</p>'); });
  }

  /* --------------------------------------------------------- collections */
  function renderCollection(view) {
    var mod = MODULES[view];
    if (mod.messages) return renderMessages();
    var content = $('#content');
    var requests = [api('GET', '/api/admin/' + mod.endpoint)];
    (mod.fields || []).forEach(function (f) {
      if (f.source && !state.options[f.source]) requests.push(loadOptions(f.source));
    });
    if (view === 'projects' && !state.options['project-categories']) requests.push(loadOptions('project-categories'));
    if (view === 'skills' && !state.options['skill-categories']) requests.push(loadOptions('skill-categories'));
    Promise.all(requests).then(function (res) {
      var items = res[0].items;
      var head = '<header class="page-head page-head--row"><div><h1>' + esc(mod.title) + '</h1><p class="muted">' + items.length + ' ' + esc(mod.noun) + (items.length === 1 ? '' : 's') + '</p></div>' +
        '<button class="btn btn--primary" type="button" data-new>Add ' + esc(mod.noun) + '</button></header>';
      var rows = items.map(function (r, i) {
        var cells = mod.columns.map(function (c) { return '<td>' + c.render(r) + '</td>'; }).join('');
        var actions = '<div class="row-actions">' +
          (mod.reorder ? '<button class="icon-btn" type="button" data-move="up" data-id="' + r.id + '" aria-label="Move up"' + (i === 0 ? ' disabled' : '') + '>↑</button>' +
            '<button class="icon-btn" type="button" data-move="down" data-id="' + r.id + '" aria-label="Move down"' + (i === items.length - 1 ? ' disabled' : '') + '>↓</button>' : '') +
          (mod.toggle ? '<button class="btn btn--small btn--ghost" type="button" data-toggle="' + r.id + '">' + (r[mod.toggle] ? 'Unpublish' : 'Publish') + '</button>' : '') +
          '<button class="btn btn--small btn--ghost" type="button" data-edit="' + r.id + '">Edit</button>' +
          '<button class="btn btn--small btn--danger" type="button" data-delete="' + r.id + '">Delete</button></div>';
        return '<tr>' + cells + '<td class="actions-cell">' + actions + '</td></tr>';
      }).join('');
      var table = items.length
        ? '<div class="table-wrap"><table class="table"><thead><tr>' + mod.columns.map(function (c) { return '<th>' + esc(c.label) + '</th>'; }).join('') + '<th></th></tr></thead><tbody>' + rows + '</tbody></table></div>'
        : '<div class="panel empty"><p>No ' + esc(mod.title.toLowerCase()) + ' yet.</p><button class="btn btn--primary" type="button" data-new>Add the first one</button></div>';
      state.items = items;
      content.insertAdjacentHTML('beforeend', head + table);
    }).catch(function (e) { content.insertAdjacentHTML('beforeend', '<p class="form-error">' + esc(errorText(e)) + '</p>'); });
  }

  // One delegated listener for the whole content area, bound once at start-up.
  function onContentClick(e) {
    var t = e.target.closest('button');
    if (!t) return;
    var view = state.currentView;
    var mod = MODULES[view];
    if (!mod || mod.messages) return;
    var items = state.items || [];
    if (t.hasAttribute('data-new')) { e.preventDefault(); openForm(view, null); }
    else if (t.hasAttribute('data-edit')) openForm(view, findItem(items, t.getAttribute('data-edit')));
    else if (t.hasAttribute('data-toggle')) toggleItem(view, findItem(items, t.getAttribute('data-toggle')), mod.toggle);
    else if (t.hasAttribute('data-delete')) deleteItem(view, findItem(items, t.getAttribute('data-delete')));
    else if (t.hasAttribute('data-move')) moveItem(view, items, t.getAttribute('data-id'), t.getAttribute('data-move'));
  }

  function findItem(items, id) {
    return items.filter(function (i) { return String(i.id) === String(id); })[0] || null;
  }

  // Re-render the current view. Option lists for categories are reloaded lazily.
  function refresh(view) {
    if (view === 'project-categories' || view === 'skill-categories') state.options[view] = null;
    route();
  }

  function toggleItem(view, item, field) {
    var body = {};
    body[field] = !item[field];
    api('PUT', '/api/admin/' + MODULES[view].endpoint + '/' + item.id, body)
      .then(function () { toast(item[field] ? 'Unpublished. It is hidden from the public site.' : 'Published. It is now live.'); refresh(view); })
      .catch(function (e) { toast(errorText(e), 'error'); });
  }

  function deleteItem(view, item) {
    if (!item) return;
    if (!window.confirm('Delete this ' + MODULES[view].noun + '? This cannot be undone.')) return;
    api('DELETE', '/api/admin/' + MODULES[view].endpoint + '/' + item.id)
      .then(function () { toast('Deleted.'); refresh(view); })
      .catch(function (e) { toast(errorText(e), 'error'); });
  }

  function moveItem(view, items, id, direction) {
    var ids = items.map(function (i) { return i.id; });
    var index = ids.indexOf(Number(id));
    var target = direction === 'up' ? index - 1 : index + 1;
    if (index < 0 || target < 0 || target >= ids.length) return;
    ids.splice(target, 0, ids.splice(index, 1)[0]);
    api('POST', '/api/admin/' + MODULES[view].endpoint + '/reorder', { ids: ids })
      .then(function () { refresh(view); })
      .catch(function (e) { toast(errorText(e), 'error'); });
  }

  /* ------------------------------------------------------------- forms */
  function buildForm(fields, values) {
    values = values || {};
    return fields.map(function (f) {
      var v = values[f.name];
      var id = 'f-' + f.name;
      var help = f.help ? '<p class="help">' + esc(f.help) + '</p>' : '';
      var req = f.required ? ' required' : '';
      var label = '<label for="' + id + '">' + esc(f.label) + (f.required ? ' <span class="req">*</span>' : '') + '</label>';
      var html;
      if (f.type === 'checkbox') {
        return '<div class="field field--check"><label><input type="checkbox" id="' + id + '" name="' + f.name + '"' + (v ? ' checked' : '') + '> ' + esc(f.label) + '</label>' + help + '</div>';
      }
      if (f.type === 'checks') {
        var selected = v || [];
        var boxes = (f.options || []).map(function (o) {
          return '<label class="chip-check"><input type="checkbox" name="' + f.name + '" value="' + esc(o.value) + '"' + (selected.indexOf(o.value) > -1 ? ' checked' : '') + '> ' + esc(o.label) + '</label>';
        }).join('');
        return '<fieldset class="field field--wide"><legend>' + esc(f.label) + '</legend><div class="checks">' + boxes + '</div>' + help + '</fieldset>';
      }
      if (f.type === 'multi') {
        var chosen = (v || []).map(String);
        var options = (state.options[f.source] || []).map(function (o) {
          return '<label class="chip-check"><input type="checkbox" name="' + f.name + '" value="' + esc(o.id) + '"' + (chosen.indexOf(String(o.id)) > -1 ? ' checked' : '') + '> ' + esc(o.name) + '</label>';
        }).join('');
        return '<fieldset class="field field--wide"><legend>' + esc(f.label) + '</legend><div class="checks">' + options + '</div>' + help + '</fieldset>';
      }
      if (f.type === 'textarea') {
        html = '<textarea id="' + id + '" name="' + f.name + '" rows="' + (f.rows || 4) + '"' + req + '>' + esc(v) + '</textarea>';
      } else if (f.type === 'list') {
        html = '<textarea id="' + id + '" name="' + f.name + '" rows="4">' + esc((v || []).join('\n')) + '</textarea>';
      } else if (f.type === 'select') {
        var opts = f.options || (state.options[f.source] || []).map(function (o) { return { value: o.id, label: o.name }; });
        html = '<select id="' + id + '" name="' + f.name + '"' + req + '><option value="">— Choose —</option>' +
          opts.map(function (o) { return '<option value="' + esc(o.value) + '"' + (String(o.value) === String(v) ? ' selected' : '') + '>' + esc(o.label) + '</option>'; }).join('') +
          '</select>';
      } else if (f.type === 'media') {
        html = '<div class="media-picker" data-picker data-kind="' + esc(f.kind || '') + '"><select id="' + id + '" name="' + f.name + '" data-media-select><option value="">— None —</option></select>' +
          '<input type="hidden" data-current="' + esc(v || '') + '"></div>';
      } else {
        var inputType = f.type === 'url' ? 'url' : f.type === 'email' ? 'email' : 'text';
        html = '<input id="' + id + '" name="' + f.name + '" type="' + inputType + '" value="' + esc(v) + '"' + req + '>';
      }
      return '<div class="field' + (f.type === 'textarea' || f.type === 'list' ? ' field--wide' : '') + '">' + label + html + help + '</div>';
    }).join('');
  }

  function bindMediaPickers(root) {
    $all('[data-picker]', root).forEach(function (picker) {
      var select = picker.querySelector('[data-media-select]');
      var current = picker.querySelector('[data-current]').value;
      var kind = picker.getAttribute('data-kind');
      loadMediaOptions(kind).then(function (items) {
        select.innerHTML = '<option value="">— None —</option>' + items.map(function (m) {
          return '<option value="' + m.id + '"' + (String(m.id) === String(current) ? ' selected' : '') + '>' + esc(m.original_name) + '</option>';
        }).join('');
      });
    });
  }

  function loadMediaOptions(kind) {
    return api('GET', '/api/admin/media' + (kind ? '?kind=' + kind : '')).then(function (d) { return d.items; });
  }

  function collect(fields, form) {
    var out = {};
    fields.forEach(function (f) {
      if (f.type === 'checkbox') {
        out[f.name] = form.querySelector('[name="' + f.name + '"]').checked;
      } else if (f.type === 'checks' || f.type === 'multi') {
        out[f.name] = $all('[name="' + f.name + '"]:checked', form).map(function (el) { return el.value; });
      } else if (f.type === 'media') {
        var sel = form.querySelector('[name="' + f.name + '"]');
        out[f.name] = sel && sel.value ? Number(sel.value) : null;
      } else {
        var el = form.querySelector('[name="' + f.name + '"]');
        var value = el ? el.value : '';
        if (f.type === 'number') value = value === '' ? null : Number(value);
        out[f.name] = value;
      }
    });
    return out;
  }

  function setBusy(button, on) {
    if (!button) return;
    button.disabled = on;
    button.dataset.label = button.dataset.label || button.textContent;
    button.innerHTML = on ? '<span class="spinner" aria-hidden="true"></span> Saving…' : button.dataset.label;
  }

  function openForm(view, item) {
    var mod = MODULES[view];
    var values = item ? Object.assign({}, item) : Object.assign({}, mod.defaults || {});
    var fields = mod.fields;
    var title = (item ? 'Edit ' : 'New ') + mod.noun;
    var previewBtn = mod.preview ? '<button type="button" class="btn btn--ghost" data-preview>Preview</button>' : '';
    var body = '<form id="item-form" class="form-grid" novalidate>' + buildForm(fields, values) +
      '<div class="form-actions"><p id="item-error" class="form-error" role="alert" hidden></p>' + previewBtn +
      '<button class="btn btn--primary" type="submit">' + (item ? 'Save changes' : 'Create ' + mod.noun) + '</button></div></form>';
    openModal(title, body);
    var form = $('#item-form');
    bindMediaPickers(form);

    var preview = form.querySelector('[data-preview]');
    if (preview) preview.addEventListener('click', function () { showPreview(collect(fields, form)); });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var button = form.querySelector('button[type=submit]');
      var body = collect(fields, form);
      var path = '/api/admin/' + mod.endpoint + (item ? '/' + item.id : '');
      setBusy(button, true);
      api(item ? 'PUT' : 'POST', path, body)
        .then(function () {
          closeModal();
          toast(item ? 'Saved. Changes will appear on the site within about 30 seconds.' : 'Created.');
          if (view === 'project-categories' || view === 'skill-categories') state.options[view] = null;
          refresh(view);
        })
        .catch(function (err) {
          setBusy(button, false);
          var box = $('#item-error');
          box.hidden = false;
          box.textContent = errorText(err);
          markFieldErrors(form, err.errors || {});
        });
    });
  }

  function markFieldErrors(form, errors) {
    $all('.field', form).forEach(function (f) { f.classList.remove('has-error'); });
    Object.keys(errors).forEach(function (name) {
      var el = form.querySelector('[name="' + name + '"]');
      if (el) { var wrap = el.closest('.field'); if (wrap) wrap.classList.add('has-error'); }
    });
  }

  function showPreview(v) {
    var categoryName = (v.category_ids || []).map(function (id) { return optionLabel('project-categories', Number(id)); }).filter(Boolean).join(' · ') || 'Category';
    var lines = function (text) { return String(text || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean); };
    var tech = lines(v.technologies).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
    var feats = lines(v.features).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
    var html = '<div class="preview">' +
      '<p class="preview__note">Preview only. This is not published. Nothing changes until you save and publish.</p>' +
      '<p class="kicker">' + esc(categoryName) + '</p>' +
      '<h3>' + esc(v.title || 'Untitled project') + '</h3>' +
      '<p class="lede">' + esc(v.summary || 'No description yet.') + '</p>' +
      (v.problem ? '<h4>Problem</h4><p>' + esc(v.problem) + '</p>' : '') +
      (v.solution ? '<h4>Solution</h4><p>' + esc(v.solution) + '</p>' : '') +
      (feats ? '<h4>Key features</h4><ul>' + feats + '</ul>' : '') +
      (tech ? '<h4>Technology stack</h4><ul class="chips">' + tech + '</ul>' : '') +
      '</div>';
    openModal('Preview', html, true);
  }

  /* ---------------------------------------------------------------- messages */
  function renderMessages() {
    var content = $('#content');
    var q = state.query.get('q') || '';
    var unread = state.query.get('unread') === '1';
    var query = '/api/admin/messages' + (q || unread ? '?' + [q ? 'q=' + encodeURIComponent(q) : '', unread ? 'unread=1' : ''].filter(Boolean).join('&') : '');
    content.insertAdjacentHTML('beforeend',
      '<header class="page-head page-head--row"><div><h1>Messages</h1><p class="muted">Contact form submissions, newest first.</p></div></header>' +
      '<form class="toolbar" id="msg-search"><input type="search" name="q" placeholder="Search name, email or text" value="' + esc(q) + '" aria-label="Search messages">' +
      '<label class="chip-check"><input type="checkbox" name="unread" ' + (unread ? 'checked' : '') + '> Unread only</label><button class="btn btn--small btn--ghost" type="submit">Search</button></form>' +
      '<div id="msg-list"></div>');
    api('GET', query).then(function (data) {
      var items = data.items;
      var list = items.length ? '<ul class="messages">' + items.map(function (m) {
        return '<li class="message' + (m.is_read ? '' : ' is-unread') + '">' +
          '<div class="message__meta"><strong>' + esc(m.name) + '</strong> <span class="muted small">' + esc(m.email) + ' · ' + fmtDate(m.created_at) + '</span></div>' +
          '<p class="message__text">' + esc(m.message) + '</p>' +
          '<div class="row-actions"><button class="btn btn--small btn--ghost" data-read="' + m.id + '" data-state="' + (m.is_read ? 'false' : 'true') + '">' + (m.is_read ? 'Mark unread' : 'Mark read') + '</button>' +
          '<a class="btn btn--small btn--ghost" href="mailto:' + esc(m.email) + '">Reply</a>' +
          '<button class="btn btn--small btn--danger" data-remove="' + m.id + '">Delete</button></div></li>';
      }).join('') + '</ul>' : '<div class="panel empty"><p>No messages match.</p></div>';
      $('#msg-list').innerHTML = list;
      $('#msg-list').addEventListener('click', function (e) {
        var t = e.target.closest('button');
        if (!t) return;
        if (t.hasAttribute('data-read')) {
          api('PUT', '/api/admin/messages/' + t.getAttribute('data-read'), { is_read: t.getAttribute('data-state') === 'true' })
            .then(function () { route(); }).catch(function (err) { toast(errorText(err), 'error'); });
        } else if (t.hasAttribute('data-remove')) {
          if (!window.confirm('Delete this message?')) return;
          api('DELETE', '/api/admin/messages/' + t.getAttribute('data-remove'))
            .then(function () { toast('Message deleted.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
        }
      });
    }).catch(function (e) { toast(errorText(e), 'error'); });

    $('#msg-search').addEventListener('submit', function (e) {
      e.preventDefault();
      var f = new FormData(e.target);
      var p = new URLSearchParams();
      if (f.get('q')) p.set('q', f.get('q'));
      if (f.get('unread')) p.set('unread', '1');
      var qs = p.toString();
      window.location.hash = 'messages' + (qs ? '?' + qs : '');
    });
  }

  /* ------------------------------------------------------------ media library */
  function renderMedia() {
    var content = $('#content');
    content.insertAdjacentHTML('beforeend',
      '<header class="page-head"><h1>Media library</h1><p class="muted">Profile photographs, project screenshots, certificates and resume files. JPG, PNG, WEBP or PDF, up to 10 MB. Files are checked by content, not by name.</p></header>' +
      '<form class="panel upload" id="media-upload" novalidate><div class="field"><label for="m-file">File</label><input id="m-file" type="file" name="file" accept=".png,.jpg,.jpeg,.webp,.pdf" required></div>' +
      '<div class="field"><label for="m-alt">Alt text (for images)</label><input id="m-alt" type="text" name="alt_text" maxlength="255"></div>' +
      '<div class="form-actions"><p id="m-error" class="form-error" role="alert" hidden></p><button class="btn btn--primary" type="submit">Upload</button></div></form>' +
      '<div id="media-grid"></div>');
    loadMediaGrid();
    $('#media-upload').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var button = form.querySelector('button[type=submit]');
      var data = new FormData(form);
      if (!data.get('file') || !data.get('file').name) { $('#m-error').hidden = false; $('#m-error').textContent = 'Choose a file first.'; return; }
      setBusy(button, true);
      api('POST', '/api/admin/media', data).then(function () {
        toast('Uploaded.'); route();
      }).catch(function (err) {
        setBusy(button, false); $('#m-error').hidden = false; $('#m-error').textContent = errorText(err);
      });
    });
  }

  function loadMediaGrid() {
    loadMediaOptions().then(function (items) {
      var grid = items.length ? '<div class="media-grid">' + items.map(function (m) {
        var preview = m.kind === 'image'
          ? '<img src="' + esc(m.url) + '" alt="' + esc(m.alt_text || m.original_name) + '" loading="lazy">'
          : '<div class="media-doc">PDF</div>';
        return '<figure class="media-item">' + preview +
          '<figcaption><span class="small">' + esc(m.original_name) + '</span>' +
          '<div class="row-actions"><a class="btn btn--small btn--ghost" href="' + esc(m.url) + '" target="_blank" rel="noopener">Open</a>' +
          '<label class="btn btn--small btn--ghost">Replace<input type="file" hidden data-replace="' + m.id + '" accept=".png,.jpg,.jpeg,.webp,.pdf"></label>' +
          '<button class="btn btn--small btn--danger" data-media-delete="' + m.id + '">Delete</button></div></figcaption></figure>';
      }).join('') + '</div>' : '<div class="panel empty"><p>No files yet.</p></div>';
      $('#media-grid').innerHTML = grid;
      $('#media-grid').addEventListener('change', function (e) {
        var input = e.target;
        if (!input.hasAttribute('data-replace') || !input.files[0]) return;
        var data = new FormData();
        data.append('file', input.files[0]);
        api('PUT', '/api/admin/media/' + input.getAttribute('data-replace'), data)
          .then(function () { toast('File replaced.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
      });
      $('#media-grid').addEventListener('click', function (e) {
        var t = e.target.closest('button');
        if (!t || !t.hasAttribute('data-media-delete')) return;
        if (!window.confirm('Delete this file? Anything using it will lose the image or resume.')) return;
        api('DELETE', '/api/admin/media/' + t.getAttribute('data-media-delete'))
          .then(function () { toast('File deleted.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
      });
    }).catch(function (e) { toast(errorText(e), 'error'); });
  }

  /* ----------------------------------------------------------------- resumes */
  function renderResumes() {
    var content = $('#content');
    content.insertAdjacentHTML('beforeend',
      '<header class="page-head"><h1>Resumes</h1><p class="muted">The active resume for each career view is what the public "Download Resume" button serves. Only one is active per view.</p></header>' +
      '<div id="resume-list"></div>' +
      '<form class="panel upload" id="resume-upload" novalidate><h2>Upload a resume</h2>' +
      '<div class="form-grid"><div class="field"><label for="r-track">Career view</label><select id="r-track" name="track" required><option value="python">Python Software Developer</option><option value="data">Data Analyst</option></select></div>' +
      '<div class="field"><label for="r-label">Label</label><input id="r-label" name="label" type="text" maxlength="120" placeholder="e.g. Data Analyst Resume"></div>' +
      '<div class="field field--wide"><label for="r-file">PDF file</label><input id="r-file" type="file" name="file" accept=".pdf" required></div></div>' +
      '<div class="form-actions"><p id="r-error" class="form-error" role="alert" hidden></p><button class="btn btn--primary" type="submit">Upload resume</button></div></form>');
    loadResumes();
    $('#resume-upload').addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target;
      var button = form.querySelector('button[type=submit]');
      setBusy(button, true);
      api('POST', '/api/admin/resumes', new FormData(form)).then(function () {
        toast('Resume uploaded.'); route();
      }).catch(function (err) {
        setBusy(button, false); $('#r-error').hidden = false; $('#r-error').textContent = errorText(err);
      });
    });
  }

  function loadResumes() {
    api('GET', '/api/admin/resumes').then(function (data) {
      var trackName = { python: 'Python Software Developer', data: 'Data Analyst' };
      var rows = data.items.map(function (r) {
        return '<tr><td><strong>' + esc(trackName[r.track]) + '</strong><div class="muted small">' + esc(r.label) + '</div></td>' +
          '<td>' + esc(r.file_name || '') + '</td>' +
          '<td>' + (r.is_active ? '<span class="badge badge--ok">Default</span>' : '<button class="btn btn--small btn--ghost" data-activate="' + r.id + '">Make default</button>') + '</td>' +
          '<td class="actions-cell"><div class="row-actions">' +
          (r.url ? '<a class="btn btn--small btn--ghost" href="' + esc(r.url) + '" target="_blank" rel="noopener">Open</a>' : '') +
          '<label class="btn btn--small btn--ghost">Replace file<input type="file" hidden accept=".pdf" data-resume-replace="' + r.id + '"></label>' +
          '<button class="btn btn--small btn--danger" data-resume-delete="' + r.id + '">Delete</button></div></td></tr>';
      }).join('');
      $('#resume-list').innerHTML = data.items.length
        ? '<div class="table-wrap"><table class="table"><thead><tr><th>Career view</th><th>File</th><th>Status</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>'
        : '<div class="panel empty"><p>No resumes uploaded yet. The Download Resume button stays hidden until one is active.</p></div>';
      var list = $('#resume-list');
      list.addEventListener('click', function (e) {
        var t = e.target.closest('button');
        if (!t) return;
        if (t.hasAttribute('data-activate')) {
          api('PUT', '/api/admin/resumes/' + t.getAttribute('data-activate'), { is_active: true })
            .then(function () { toast('Default updated.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
        } else if (t.hasAttribute('data-resume-delete')) {
          if (!window.confirm('Delete this resume file?')) return;
          api('DELETE', '/api/admin/resumes/' + t.getAttribute('data-resume-delete'))
            .then(function () { toast('Resume deleted.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
        }
      });
      list.addEventListener('change', function (e) {
        var input = e.target;
        if (!input.hasAttribute('data-resume-replace') || !input.files[0]) return;
        var data = new FormData();
        data.append('file', input.files[0]);
        api('PUT', '/api/admin/resumes/' + input.getAttribute('data-resume-replace'), data)
          .then(function () { toast('Resume file replaced.'); route(); }).catch(function (err) { toast(errorText(err), 'error'); });
      });
    }).catch(function (e) { toast(errorText(e), 'error'); });
  }

  /* ------------------------------------------------------------------- modal */
  function openModal(title, html, wide) {
    $('#modal-title').textContent = title;
    $('#modal-body').innerHTML = html;
    var m = $('#modal');
    m.hidden = false;
    m.querySelector('.modal__panel').classList.toggle('modal__panel--wide', !!wide);
    var first = m.querySelector('input, select, textarea, button');
    if (first) first.focus();
  }
  function closeModal() { $('#modal').hidden = true; $('#modal-body').innerHTML = ''; }

  /* ------------------------------------------------------------ auth */
  function showLogin(message) {
    state.user = null; state.csrf = null;
    $('#shell').hidden = true;
    $('#login').hidden = false;
    $('#app-loading').hidden = true;
    var err = $('#login-error');
    err.hidden = !message; err.textContent = message || '';
  }

  function showApp(user) {
    state.user = user;
    $('#login').hidden = true;
    $('#app-loading').hidden = true;
    $('#shell').hidden = false;
    $('#whoami').textContent = user.email;
    renderNav();
    route();
  }

  function bootSession() {
    api('GET', '/api/auth/me').then(function (data) {
      state.csrf = data.csrf_token;
      showApp(data.user);
    }).catch(function () { showLogin(); });
  }

  $('#login-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var email = $('#login-email').value.trim();
    var password = $('#login-password').value;
    var button = $('#login-submit');
    setBusy(button, true);
    api('POST', '/api/auth/login', { email: email, password: password }).then(function (data) {
      state.csrf = data.csrf_token;
      setBusy(button, false);
      $('#login-password').value = '';
      showApp(data.user);
    }).catch(function (err) {
      setBusy(button, false);
      showLogin(errorText(err));
    });
  });

  $('#logout').addEventListener('click', function () {
    api('POST', '/api/auth/logout').catch(function () {}).then(function () {
      state.options = {};
      showLogin('You have signed out.');
    });
  });

  $('#modal').addEventListener('click', function (e) {
    if (e.target.hasAttribute('data-close') || e.target.id === 'modal') closeModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !$('#modal').hidden) closeModal();
  });
  window.addEventListener('hashchange', route);
  $('#content').addEventListener('click', onContentClick);

  bootSession();
})();
