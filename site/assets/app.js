(function(){
  var root = document.documentElement;
  var themeToggle = document.getElementById('theme-toggle');

  function effectiveTheme(){
    var explicit = root.getAttribute('data-theme');
    if (explicit === 'light' || explicit === 'dark') return explicit;
    try {
      return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    } catch (e) { return 'dark'; }
  }
  function syncThemeToggle(){
    if (!themeToggle) return;
    var light = effectiveTheme() === 'light';
    themeToggle.setAttribute('aria-pressed', light ? 'true' : 'false');
    themeToggle.setAttribute('title', light ? '切换到深色' : '切换到浅色');
  }
  if (themeToggle) {
    themeToggle.addEventListener('click', function(){
      var next = effectiveTheme() === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('airr-theme', next); } catch (e) {}
      syncThemeToggle();
    });
    syncThemeToggle();
  }
  try {
    var mq = window.matchMedia('(prefers-color-scheme: light)');
    var onSchemeChange = function(){ syncThemeToggle(); };
    if (mq.addEventListener) mq.addEventListener('change', onSchemeChange);
    else if (mq.addListener) mq.addListener(onSchemeChange);
  } catch (e) {}

  // 探索页有独立的筛选逻辑（assets/explore.js），避免两套 apply 互相覆盖
  if (document.getElementById('explore-list')) return;

  var q = document.getElementById('q');
  var rows = Array.prototype.slice.call(document.querySelectorAll('.race-row'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip[data-filter]'));
  var sort = document.getElementById('sort');
  var empty = document.querySelector('.empty');
  var list = document.querySelector('.race-list');
  var state = {mode:'all', status:'all'};

  function visible(row){
    var kw = (q && q.value || '').trim().toLowerCase();
    var okMode = state.mode === 'all' || row.dataset.mode === state.mode;
    var okStatus = state.status === 'all' || row.dataset.status === state.status;
    var okKw = !kw || (row.dataset.hay || '').toLowerCase().indexOf(kw) !== -1;
    return okMode && okStatus && okKw;
  }
  function renumber(){
    var n = 1;
    rows.forEach(function(row){
      var num = row.querySelector('.idx .num');
      if (row.style.display !== 'none') {
        if (num) num.textContent = ('00' + n).slice(-3);
        n++;
      }
    });
  }
  function apply(){
    rows.forEach(function(row){ row.style.display = visible(row) ? '' : 'none'; });
    if (empty) empty.style.display = rows.some(visible) ? 'none' : '';
    renumber();
  }
  chips.forEach(function(chip){
    chip.addEventListener('click', function(){
      var kind = chip.dataset.filter;
      chips.filter(function(c){ return c.dataset.filter === kind; })
           .forEach(function(c){ c.classList.remove('active'); });
      chip.classList.add('active');
      state[kind] = chip.dataset.value;
      apply();
    });
  });
  if (q) q.addEventListener('input', apply);
  if (sort) sort.addEventListener('change', function(){
    var val = sort.value;
    rows.sort(function(a, b){
      if (val === 'deadline') {
        return ((a.dataset.deadline || '9999-12-31') + '').localeCompare(b.dataset.deadline || '9999-12-31');
      }
      return ((b.dataset.firstseen || '') + '').localeCompare(a.dataset.firstseen || '');
    });
    if (list) rows.forEach(function(row){ list.appendChild(row); });
    apply();
  });
  apply();

  /* 投稿表单：有邮箱走 mailto，没有则复制到剪贴板 */
  var form = document.getElementById('submit-form');
  if (!form) return;
  var msg = document.getElementById('form-msg');
  var email = form.dataset.email || '';
  var preId = '', preTitle = '', preUrl = '';
  try {
    var sp = new URLSearchParams(location.search);
    preId = sp.get('id') || '';
    preTitle = sp.get('title') || '';
    preUrl = sp.get('url') || '';
    if (preTitle) { var nameEl = document.getElementById('f-name'); if (nameEl) nameEl.value = preTitle; }
    if (preUrl) { var urlEl = document.getElementById('f-url'); if (urlEl) urlEl.value = preUrl; }
    if (preId && msg) {
      msg.textContent = '正在纠错：' + preId + '（请说明要改的字段）';
      var noteEl = document.getElementById('f-note');
      if (noteEl && !noteEl.value) noteEl.placeholder = '纠错：请说明要修改的字段（标题 / 日期 / 截止 / 奖金 / 链接）';
    }
  } catch (e) {}
  function val(id){ var el = document.getElementById(id); return el ? el.value.trim() : ''; }
  function payload(){
    var lines = ['## 赛事投稿', '', '- 赛事名称：' + (val('f-name') || '（未填）'),
                 '- 官方链接：' + (val('f-url') || '（未填）'),
                 '- 主办方：' + (val('f-org') || '（未填）'),
                 '- 报名截止：' + (val('f-deadline') || '（未填）'),
                 '- 补充说明：' + (val('f-note') || '（无）')];
    if (preId) lines.push('- 条目 ID：' + preId);
    return lines.join('\n');
  }
  function copy(text){
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
    } else {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    }
  }
  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    var title = val('f-name') || '赛事';
    var text = payload();
    if (email) {
      window.location.href = 'mailto:' + email
        + '?subject=' + encodeURIComponent('投稿｜' + title)
        + '&body=' + encodeURIComponent(text);
    } else {
      copy(text);
      if (msg) msg.textContent = '已复制投稿内容，请发给站方（邮箱上线后公布）';
    }
  });
  var copyBtn = document.getElementById('copy-btn');
  if (copyBtn) copyBtn.addEventListener('click', function(){
    copy(payload());
    if (msg) msg.textContent = '已复制，可直接粘贴到微信 / 邮件发送给站方';
  });
})();
