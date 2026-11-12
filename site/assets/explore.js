(function(){
  var rows = [].slice.call(document.querySelectorAll('#explore-list .race-row'));
  if (!rows.length) return;
  var tabs = [].slice.call(document.querySelectorAll('.tab[data-tab]'));
  var facets = [].slice.call(document.querySelectorAll('.facet[data-facet]'));
  var q = document.getElementById('eq');
  var city = document.getElementById('ecity');
  var sort = document.getElementById('esort');
  var reset = document.getElementById('ereset');
  var count = document.getElementById('ecount');
  var empty = document.getElementById('eempty');
  var list = document.getElementById('explore-list');
  var state = {tab:'current', q:'', dir:'all', source:'all', level:'all', mode:'all', window:'all', status:'all', city:'all', sort:'deadline'};
  var facetKeys = ['dir','source','level','mode','status'];

  function setActive(){
    tabs.forEach(function(t){ t.classList.toggle('active', t.dataset.tab === state.tab); });
    facets.forEach(function(f){
      var key = f.dataset.facet, val = f.dataset.value;
      f.classList.toggle('active', state[key] === val);
    });
    if (q) q.value = state.q;
    if (city) city.value = state.city;
    if (sort) sort.value = state.sort;
  }
  function matches(row){
    var tab = row.dataset.tab || 'current';
    if (tab !== state.tab) return false;
    if (state.q && (row.dataset.hay || '').toLowerCase().indexOf(state.q) === -1) return false;
    for (var i = 0; i < facetKeys.length; i++) {
      var key = facetKeys[i], want = state[key];
      if (want === 'all') continue;
      var actual = row.dataset[key] || '';
      if (key === 'dir') {
        if ((actual ? actual.split(/\s+/) : []).indexOf(want) === -1) return false;
      } else if (want === 'none') {
        if (actual) return false;
      } else if (actual !== want) return false;
    }
    if (state.city !== 'all' && (row.dataset.city || '') !== state.city) return false;
    if (state.window !== 'all') {
      var d = parseInt(row.dataset.days, 10);
      var max = parseInt(state.window, 10);
      if (isNaN(d) || d < 0 || d > max) return false;
    }
    return true;
  }
  function renumber(){
    var n = 1;
    rows.forEach(function(row){
      if (row.style.display === 'none') return;
      var num = row.querySelector('.idx .num');
      if (num) num.textContent = ('00' + n).slice(-3);
      n++;
    });
  }
  function countFor(key, value){
    var tabRows = rows.filter(function(row){ return (row.dataset.tab || 'current') === state.tab; });
    if (value === 'all') return tabRows.length;
    return tabRows.filter(function(row){
      var actual = row.dataset[key] || '';
      if (key === 'window') {
        var d = parseInt(row.dataset.days, 10);
        return !isNaN(d) && d >= 0 && d <= parseInt(value, 10);
      }
      if (key === 'dir') return (actual ? actual.split(/\s+/) : []).indexOf(value) !== -1;
      if (value === 'none') return !actual;
      return actual === value;
    }).length;
  }
  function updateCounts(){
    facets.forEach(function(f){
      var b = f.querySelector('b');
      if (b) b.textContent = countFor(f.dataset.facet, f.dataset.value);
    });
  }
  function writeURL(){
    var p = new URLSearchParams();
    if (state.tab !== 'current') p.set('tab', state.tab);
    if (state.q) p.set('q', state.q);
    ['dir','source','level','mode','window','status'].forEach(function(k){
      if (state[k] !== 'all') p.set(k, state[k]);
    });
    if (state.city !== 'all') p.set('city', state.city);
    if (state.sort !== 'deadline') p.set('sort', state.sort);
    var qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
  }
  function apply(){
    var n = 0;
    rows.forEach(function(row){
      var ok = matches(row);
      row.style.display = ok ? '' : 'none';
      if (ok) n++;
    });
    renumber();
    updateCounts();
    if (count) count.textContent = n;
    if (empty) empty.style.display = n ? 'none' : '';
    writeURL();
  }
  function dl(row){
    var v = row.dataset.deadline;
    if (v && v !== '9999-12-31') return v;
    v = row.dataset.end || row.dataset.start;
    if (v) return v;
    return (row.dataset.firstseen || '').slice(0, 10);
  }
  function sortRows(){
    rows.sort(function(a, b){
      if (state.sort === 'newest') {
        return (b.dataset.firstseen || '').localeCompare(a.dataset.firstseen || '') ||
               dl(a).localeCompare(dl(b));
      }
      if (state.tab === 'past') {
        return dl(b).localeCompare(dl(a));
      }
      var ac = a.dataset.status === 'closed' ? 1 : 0;
      var bc = b.dataset.status === 'closed' ? 1 : 0;
      return (ac - bc) ||
        (a.dataset.deadline || '9999-12-31').localeCompare(b.dataset.deadline || '9999-12-31');
    });
    if (list) rows.forEach(function(row){ list.appendChild(row); });
  }
  function readURL(){
    var p = new URLSearchParams(location.search);
    state.tab = p.get('tab') === 'past' ? 'past' : 'current';
    state.q = (p.get('q') || '').toLowerCase();
    ['dir','source','level','mode','window','status'].forEach(function(k){
      var v = p.get(k);
      if (v) state[k] = v;
    });
    if (p.get('city')) state.city = p.get('city');
    if (p.get('sort') === 'newest') state.sort = 'newest';
  }
  tabs.forEach(function(t){
    t.addEventListener('click', function(){
      state.tab = t.dataset.tab;
      setActive(); sortRows(); apply();
    });
  });
  facets.forEach(function(f){
    f.addEventListener('click', function(){
      state[f.dataset.facet] = f.dataset.value;
      setActive(); apply();
    });
  });
  if (q) q.addEventListener('input', function(){ state.q = q.value.trim().toLowerCase(); apply(); });
  if (city) city.addEventListener('change', function(){ state.city = city.value; apply(); });
  if (sort) sort.addEventListener('change', function(){ state.sort = sort.value; sortRows(); apply(); });
  if (reset) reset.addEventListener('click', function(){
    state = {tab:'current', q:'', dir:'all', source:'all', level:'all', mode:'all', window:'all', status:'all', city:'all', sort:'deadline'};
    setActive(); sortRows(); apply();
  });
  readURL(); setActive(); sortRows(); apply();
})();
