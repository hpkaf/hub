# -*- coding: utf-8 -*-
"""HackerTrip 对标后的新增页面：探索、主办方、匹配、指南。

保持静态站：筛选/匹配全部在浏览器里完成，数据来自 site/data/*.json。
"""
from __future__ import annotations

import html
import json
import urllib.parse

import common
import taxonomy
from site_ui import (ASSET_V, LEVEL_LABEL, SITE_DESC, SITE_NAME, SITE_URL, SRC_LABEL,
                     WEBCAL_URL, esc, fmt_date, foot, head, itemlist_jsonld, render_row)


def _json_script(data) -> str:
    raw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{raw}</script>'


def _facet_group(label: str, group: str, items: list[tuple[str, str, int]]) -> str:
    buttons = [f'<button class="facet active" data-facet="{group}" data-value="all">全部</button>']
    for value, text, count in items:
        if not count:
            continue
        buttons.append(
            f'<button class="facet" data-facet="{group}" data-value="{esc(value)}">'
            f'{esc(text)}<b>{count}</b></button>'
        )
    return f'<div class="facet-group"><span class="facet-label">{esc(label)}</span>{"".join(buttons)}</div>'


def _mode_items(records: list[dict]) -> list[tuple[str, str, int]]:
    out = []
    for key in ("online", "offline", "hybrid"):
        out.append((key, common.MODE_LABEL.get(key, key), sum(1 for r in records if r.get("mode") == key)))
    unknown = sum(1 for r in records if r.get("mode") not in ("online", "offline", "hybrid"))
    if unknown:
        out.append(("none", "待确认", unknown))
    return out


def _status_items(records: list[dict]) -> list[tuple[str, str, int]]:
    return [
        (key, common.STATUS_LABEL[key], sum(1 for r in records if r.get("status") == key))
        for key in ("open", "closing", "upcoming", "unknown", "closed")
    ]


def _window_items(records: list[dict]) -> list[tuple[str, str, int]]:
    current = [r for r in records if r.get("_tab") == "current"]
    out = []
    for days in (3, 7, 14):
        count = sum(
            1 for r in current
            if (common.days_until(r.get("deadline")) is not None
                and 0 <= common.days_until(r.get("deadline")) <= days)
        )
        out.append((str(days), f"{days} 天内", count))
    return out


def _source_items(records: list[dict]) -> list[tuple[str, str, int]]:
    counts = {}
    for rec in records:
        src = rec.get("source") or ""
        counts[src] = counts.get(src, 0) + 1
    items = []
    for src, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        items.append((src or "none", SRC_LABEL.get(src, src or "未知"), count))
    return items


EXPLORE_JS = r"""
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
"""


def render_explore(records: list[dict]) -> str:
    current = [r for r in records if r.get("_tab") == "current"]
    past = [r for r in records if r.get("_tab") == "past"]
    rows = "\n".join(render_row(r, i + 1) for i, r in enumerate(records))
    cities = []
    for rec in records:
        city = (rec.get("city") or "").strip()
        if city and city not in cities:
            cities.append(city)
    city_opts = "".join(
        f'<option value="{esc(c)}">{esc(c)}（{sum(1 for r in records if (r.get("city") or "") == c)}）</option>'
        for c in sorted(cities)
    )
    facets = "".join([
        _facet_group("方向", "dir", taxonomy.direction_counts(records)),
        _facet_group("平台", "source", _source_items(records)),
        _facet_group("AI 级别", "level", [(k, LEVEL_LABEL[k], sum(1 for r in records if (r.get("ai_level") or "") == k)) for k in ("core", "platform", "track", "other")]),
        _facet_group("形式", "mode", _mode_items(records)),
        _facet_group("截止", "window", _window_items(records)),
        _facet_group("状态", "status", _status_items(records)),
    ])
    jsonld = itemlist_jsonld(records, f"{SITE_NAME} 探索")
    return head(f"探索 AI 赛事 · {SITE_NAME}", "按 AI 方向、平台、级别、形式、状态筛选中国 AI 赛事与黑客松；含往届归档。",
                page="explore") + f"""
<div class="crumbs"><a href="index.html">← 首页</a></div>
<section class="explore-hero">
  <div class="kicker">EXPLORE / {len(records)} TRACKED</div>
  <h1 class="display-sm">探索 AI 赛事</h1>
  <p class="sub">不必翻完整个列表：先按方向、平台或级别收窄，再看截止日和报名入口。每条仍保留核验侧栏与官方来源。</p>
  <div class="cta hero-cta">
    <a class="btn primary" href="match.html">用项目方向匹配</a>
    <a class="btn ghost" href="calendar.html">订阅日历</a>
  </div>
</section>

<div class="explore-tabs">
  <button class="tab active" data-tab="current">在架<b>{len(current)}</b></button>
  <button class="tab" data-tab="past">往届<b>{len(past)}</b></button>
</div>

<div class="explore-filters">
  <div class="explore-tools">
    <div class="search"><span class="sl">/</span>
      <input id="eq" type="text" placeholder="搜索赛事、主办方、赛道、简介" autocomplete="off"></div>
    <select class="city-select" id="ecity"><option value="all">全部城市</option>{city_opts}</select>
    <select class="sort-select" id="esort"><option value="deadline">截止优先</option><option value="newest">最新收录</option></select>
    <button class="explore-reset" id="ereset">重置</button>
  </div>
  <div class="facet-groups">{facets}</div>
</div>

<div class="list-head"><span class="explore-count">● 匹配 <b id="ecount">{len(records)}</b> 场</span>
  <span>点开任意一行看详情与核验记录</span></div>
<section class="race-list" id="explore-list">
{rows}
</section>
<div class="match-empty" id="eempty" style="display:none">没有匹配的赛事，试试减少筛选条件。</div>
{jsonld}
<script src="assets/explore.js?v={ASSET_V}"></script>
""" + foot()


def render_organizers_index(orgs: list[dict]) -> str:
    cards = "".join(
        f'<a class="org-card" href="organizer/{esc(o["slug"])}.html" data-hay="{esc(o["name"] + " " + " ".join(o["cities"]) + " " + o["intro"])}">'
        f'<span class="org-logo sm">{esc(o["letter"])}</span>'
        f'<span class="org-card-main"><b>{esc(o["name"])}</b>'
        f'<small>{esc(" · ".join(o["cities"]) or "线上")} · {len(o["records"])} 场 · 在架 {len(o["current"])}</small></span></a>'
        for o in orgs
    )
    return head(f"主办方与社区 · {SITE_NAME}", "按主办方浏览中国 AI 赛事与黑客松：赛事历史、城市、官网与详情。",
                page="organizers") + f"""
<div class="crumbs"><a href="index.html">← 首页</a></div>
<section class="explore-hero">
  <div class="kicker">ORGANIZERS &amp; COMMUNITIES / {len(orgs)}</div>
  <h1 class="display-sm">主办方与社区</h1>
  <p class="sub">从「谁在办」找赛事：同一主办方的往届、在架、城市与官方入口。</p>
  <div class="explore-tools" style="margin-top:22px;max-width:520px">
    <div class="search"><span class="sl">/</span>
      <input id="oq" type="text" placeholder="搜索主办方、城市、方向" autocomplete="off"></div>
  </div>
</section>
<div class="list-head"><span class="explore-count">● <b id="ocount">{len(orgs)}</b> 个主办方</span>
  <span>按在架赛事数排序</span></div>
<div class="org-grid" id="org-grid">{cards}</div>
<div class="match-empty" id="oempty" style="display:none">没有匹配的主办方。</div>
<script>
(function(){{
  var q=document.getElementById('oq'), cards=[].slice.call(document.querySelectorAll('.org-card')),
      empty=document.getElementById('oempty'), cnt=document.getElementById('ocount');
  function apply(){{
    var kw=(q&&q.value||'').trim().toLowerCase(), n=0;
    cards.forEach(function(c){{
      var ok=!kw||(c.dataset.hay||'').toLowerCase().indexOf(kw)!==-1;
      c.style.display=ok?'':'none'; if(ok)n++;
    }});
    if(cnt)cnt.textContent=n; if(empty)empty.style.display=n?'none':'';
  }}
  if(q)q.addEventListener('input',apply); apply();
}})();
</script>
""" + foot()


def render_organizer(org: dict) -> str:
    website = (f'<a class="btn ghost" href="{esc(org["website"])}" target="_blank" rel="noopener">官方网站 ↗</a>'
               if org.get("website") else "")
    current = "\n".join(render_row(r, i + 1, "../") for i, r in enumerate(org["current"]))
    past = "\n".join(render_row(r, i + 1, "../") for i, r in enumerate(org["past"]))
    levels = " / ".join(LEVEL_LABEL.get(k, k) for k in org["levels"])
    modes = " / ".join(common.MODE_LABEL.get(k, k) for k in org["modes"])
    ld_data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": org["name"],
        "description": org["intro"],
    }
    if org.get("website"):
        ld_data["url"] = org["website"]
    if org["cities"]:
        ld_data["address"] = {"@type": "PostalAddress", "addressLocality": "、".join(org["cities"])}
    ld = _json_script(ld_data)
    return head(f"{org['name']} · 主办的 AI 赛事 · {SITE_NAME}", org["intro"][:150], depth=1) + f"""
<div class="crumbs"><a href="../organizers.html">← 全部主办方</a></div>
<header class="org-hero">
  <div class="org-logo">{esc(org["letter"])}</div>
  <div>
    <div class="kicker">ORGANIZER</div>
    <h1>{esc(org["name"])}</h1>
    <div class="org-meta">{esc(" · ".join(org["cities"]) or "线上")} · {len(org["records"])} 场收录 · 在架 {len(org["current"])}</div>
  </div>
  <div style="margin-left:auto">{website}</div>
</header>
<p class="org-intro">{esc(org["intro"])}</p>
<div class="org-stats">
  <span><b>{len(org["records"])}</b>场</span>
  <span><b>{len(org["current"])}</b>在架</span>
  <span><b>{len(org["past"])}</b>往届</span>
  <span>{esc(modes or "形式待确认")}</span>
  <span>{esc(levels or "AI 相关度待确认")}</span>
</div>
{('<section class="race-section"><h2>在架与近期赛事</h2><section class="race-list">' + current + '</section></section>') if current else ''}
{('<section class="race-section"><h2>往届</h2><section class="race-list">' + past + '</section></section>') if past else ''}
<section class="race-section source-box">
  <h2>主办方页说明</h2>
  <p>本页由 {SITE_NAME} 根据公开赛事信息自动聚合；主办方介绍可能来自官方页或公开资料，未收录的字段不猜测。</p>
  <p class="source-actions"><a href="../submit.html?title={urllib.parse.quote(org['name'])}">认领 / 纠错 / 补充主办方信息 →</a></p>
</section>
{ld}
""" + foot(depth=1)


MATCH_JS = r"""
(function(){
  var form = document.getElementById('match-form');
  if (!form) return;
  var results = document.getElementById('mresults');
  var data = null;
  var dirLabels = %DIRLABELS%;

  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function fmtDeadline(v){ return v ? v : '待确认'; }
  function daysTo(v){
    if (!v) return null;
    var d = new Date(v + 'T00:00:00+08:00');
    if (isNaN(d)) return null;
    var now = new Date(); now.setHours(0,0,0,0);
    return Math.round((d - now) / 86400000);
  }
  function score(rec, q, dir, mode, city, windowDays){
    var reasons = [], s = 0;
    var blob = [rec.title, (rec.tracks||[]).join(' '), rec.summary||'', rec.organizer||''].join(' ').toLowerCase();
    if (dir && dir !== 'all' && (rec.directions||[]).indexOf(dir) !== -1) { s += 30; reasons.push('方向：' + (dirLabels[dir]||dir)); }
    var tokens = (q||'').toLowerCase().split(/[\s,，、+]+/).filter(function(x){ return x.length >= 2; });
    var hits = 0;
    tokens.forEach(function(t){ if (blob.indexOf(t) !== -1) hits++; });
    if (hits) { s += Math.min(24, hits * 8); reasons.push('关键词命中 ' + hits + ' 个'); }
    if (mode && mode !== 'all' && rec.mode === mode) { s += 10; reasons.push('形式：' + mode); }
    if (city && city !== 'all' && rec.city === city) { s += 10; reasons.push('城市：' + city); }
    var d = daysTo(rec.deadline);
    if (windowDays && d !== null && d >= 0 && d <= windowDays) { s += 15; reasons.push(d + ' 天内截止'); }
    if (rec.status === 'open' || rec.status === 'closing') { s += 20; reasons.push('还能报名'); }
    if (rec.ai_level === 'core') { s += 5; }
    return {score:s, reasons:reasons};
  }
  function render(rows){
    if (!results) return;
    if (!rows.length) { results.innerHTML = '<div class="match-empty">没有匹配的赛事，换个方向或放宽截止窗口。</div>'; return; }
    results.innerHTML = rows.map(function(x){
      var rec = x.rec, sc = x.score;
      return '<article class="match-card"><div><h3><a href="race/' + esc(rec.id) + '.html">' + esc(rec.title) + '</a></h3>' +
        '<div class="mm">' + esc(rec.organizer || '主办方待确认') + ' · ' + esc(rec.mode || '待确认') +
        (rec.city ? ' · ' + esc(rec.city) : '') + ' · 截止 ' + esc(fmtDeadline(rec.deadline)) + '</div>' +
        '<div class="match-reasons">' + esc(sc.reasons.join(' · ') || '综合匹配') + '</div></div>' +
        '<div class="match-score">' + sc.score + '<small>MATCH</small></div></article>';
    }).join('');
  }
  function run(){
    var q = (document.getElementById('mq')||{}).value || '';
    var dir = (document.getElementById('mdir')||{}).value || 'all';
    var mode = (document.getElementById('mmode')||{}).value || 'all';
    var city = (document.getElementById('mcity')||{}).value || 'all';
    var win = parseInt((document.getElementById('mwindow')||{}).value || '0', 10);
    var only = document.getElementById('monly');
    if (!data) return;
    var rows = data.map(function(rec){ return {rec:rec, score:score(rec, q, dir, mode, city, win)}; })
      .filter(function(x){
        if (only && only.checked && x.rec.status === 'closed') return false;
        if (!q && dir === 'all' && mode === 'all' && city === 'all' && !win) return true;
        return x.score.score > 0;
      })
      .sort(function(a,b){ return b.score.score - a.score.score || (a.rec.deadline||'9999').localeCompare(b.rec.deadline||'9999'); })
      .slice(0, 12);
    render(rows);
  }
  fetch('data/match.json').then(function(r){ return r.json(); }).then(function(rows){
    data = rows || [];
    var mdir = document.getElementById('mdir');
    if (mdir) {
      var dirs = {};
      data.forEach(function(r){ (r.directions||[]).forEach(function(k){ dirs[k]=1; }); });
      Object.keys(dirs).forEach(function(k){
        var o = document.createElement('option'); o.value = k; o.textContent = dirLabels[k] || k; mdir.appendChild(o);
      });
    }
    var mcity = document.getElementById('mcity');
    if (mcity) {
      var cities = {};
      data.forEach(function(r){ if (r.city) cities[r.city]=1; });
      Object.keys(cities).sort().forEach(function(c){
        var o = document.createElement('option'); o.value = c; o.textContent = c; mcity.appendChild(o);
      });
    }
    run();
  });
  form.addEventListener('submit', function(ev){ ev.preventDefault(); run(); });
})();
"""


def render_match(records: list[dict]) -> str:
    dirs = taxonomy.direction_counts(records)
    dir_opts = "".join(f'<option value="{esc(k)}">{esc(label)}</option>' for k, label, _ in dirs)
    dir_labels = {k: label for k, label, _ in dirs}
    js = MATCH_JS.replace("%DIRLABELS%", json.dumps(dir_labels, ensure_ascii=False))
    return head(f"帮我找 AI 赛事 · {SITE_NAME}", "输入项目方向、技能、城市与截止窗口，按规则匹配 AI 赛事并给出命中理由。",
                page="match") + f"""
<div class="crumbs"><a href="index.html">← 首页</a></div>
<section class="match-hero">
  <div class="kicker">MATCH / RULES, NOT MAGIC</div>
  <h1 class="display-sm">帮我找赛事</h1>
  <p class="sub">按方向、形式、城市和截止窗口做加权筛选；每条结果都给出命中理由。这是筛选器，不是录取预测。</p>
  <form class="match-form" id="match-form">
    <div class="match-field" style="grid-column:1/-1">
      <label for="mq">项目方向 / 技能 / 关键词</label>
      <input id="mq" placeholder="例如：智能体、RAG、Python、前端、具身">
    </div>
    <div class="match-field"><label for="mdir">方向</label><select id="mdir"><option value="all">全部方向</option>{dir_opts}</select></div>
    <div class="match-field"><label for="mmode">形式</label>
      <select id="mmode"><option value="all">全部</option><option value="online">线上</option><option value="offline">线下</option><option value="hybrid">混合</option></select></div>
    <div class="match-field"><label for="mcity">城市</label><select id="mcity"><option value="all">全部城市</option></select></div>
    <div class="match-field"><label for="mwindow">截止窗口</label>
      <select id="mwindow"><option value="0">不限</option><option value="7">7 天内</option><option value="30">30 天内</option><option value="90">90 天内</option></select></div>
    <label class="match-check"><input type="checkbox" id="monly" checked> 只看还能报名</label>
    <div class="match-actions"><button class="btn primary" type="submit">开始匹配 →</button>
      <span class="section-note" style="margin:0">在浏览器本地计算，不上传任何内容。</span></div>
  </form>
</section>
<div class="match-results" id="mresults"></div>
<script>{js}</script>
""" + foot()


GUIDE_INDEX_KEYS = [
    ("2026-ai-race-calendar", "AI 赛事日历：还能报名的都在这里", "现在还能报名的赛事、截止分布与筛选方式。"),
    ("first-ai-hackathon", "第一次参加 AI 黑客松", "从选赛、组队到提交材料的可执行清单。"),
    ("online-vs-offline", "线上 vs 线下 AI 赛事", "用真实数据看两种形式的时间、成本与适配人群。"),
]


def render_guides_index() -> str:
    cards = "".join(
        f'<a class="guide-card" href="guides/{slug}.html"><div class="guide-meta">GUIDE</div>'
        f'<h2>{esc(title)}</h2><p>{esc(desc)}</p></a>'
        for slug, title, desc in GUIDE_INDEX_KEYS
    )
    return head(f"指南 · {SITE_NAME}", "AI 赛事与黑客松的选赛、报名、参赛指南。", page="guides") + f"""
<div class="crumbs"><a href="index.html">← 首页</a></div>
<section class="explore-hero">
  <div class="kicker">GUIDES / 3</div>
  <h1 class="display-sm">指南</h1>
  <p class="sub">不写泛泛的「AI 时代来了」：每篇都落到选赛标准、时间节点和本站数据。</p>
</section>
<div class="guide-grid">{cards}</div>
""" + foot()


def render_guide(guide: dict) -> str:
    ld = _json_script({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": guide["title"],
        "description": guide["desc"],
        "dateModified": common.now_iso()[:10],
        "inLanguage": "zh-CN",
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
    })
    return head(f"{guide['title']} · {SITE_NAME}", guide["desc"], depth=1, page="guides") + f"""
<div class="crumbs"><a href="../guides.html">← 指南</a></div>
<article class="guide-article prose">
{guide['body']}
{ld}
</article>
""" + foot(depth=1)


CALENDAR_JS = r"""
(function(){
  var calUrl = __CAL_URL__;
  var webcalUrl = __WEBCAL_URL__;
  var copied = document.getElementById('cal-copied');

  function flash(text){
    if (!copied) return;
    copied.textContent = text;
    window.setTimeout(function(){ copied.textContent = ''; }, 5000);
  }

  function copyText(text){
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function(resolve, reject){
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      ok ? resolve() : reject(new Error('copy failed'));
    });
  }

  document.querySelectorAll('[data-copy]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var text = btn.getAttribute('data-copy');
      copyText(text).then(function(){
        flash(btn.getAttribute('data-copy-label') || '已复制订阅链接，粘贴到日历即可');
      }).catch(function(){
        flash('复制失败，请手动选中上面的链接');
      });
    });
  });

  var form = document.getElementById('cal-email-form');
  if (!form) return;
  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    var input = document.getElementById('cal-email');
    var status = document.getElementById('cal-status');
    var email = (input.value || '').trim();
    if (!email || email.indexOf('@') < 1) {
      status.textContent = '请输入有效的邮箱地址。';
      input.focus();
      return;
    }
    var subject = 'AI 赛事雷达 · 日历订阅链接';
    var body = '这是 AI 赛事雷达的日历订阅地址：\n\n' + calUrl
      + '\n\nApple / iPhone 可直接打开：\n' + webcalUrl
      + '\n\n打开后确认订阅即可，之后每天自动更新。\n\n—— AI 赛事雷达';
    window.location.href = 'mailto:' + encodeURIComponent(email)
      + '?subject=' + encodeURIComponent(subject)
      + '&body=' + encodeURIComponent(body);
    status.textContent = '已打开邮件客户端；发送后即可在邮箱里点链接订阅。';
  });
})();
"""


def render_calendar() -> str:
    cal = f"{SITE_URL}/calendar.ics"
    webcal = WEBCAL_URL
    outlook = ("https://outlook.office.com/owa/?path=%2Fcalendar%2Faction%2Fcompose"
               "&rru=addsubscription&url=" + urllib.parse.quote(webcal, safe="")
               + "&name=" + urllib.parse.quote("AI 赛事雷达"))
    google = "https://calendar.google.com/calendar/r/settings/addbyurl"
    js = (CALENDAR_JS
          .replace("__CAL_URL__", json.dumps(cal, ensure_ascii=False))
          .replace("__WEBCAL_URL__", json.dumps(webcal, ensure_ascii=False)))
    return head(
        f"订阅 AI 赛事日历 · {SITE_NAME}",
        "把 AI 赛事雷达加进 Apple 日历、Outlook 或 Google 日历；一次订阅，每天自动更新。",
        page="calendar",
    ) + f"""
<div class="crumbs"><a href="index.html">← 首页</a><span>/</span><span>日历订阅</span></div>
<section class="calendar-hero">
  <div class="cal-kicker">CALENDAR / LIVE FEED</div>
  <h1>把赛事日历<br>直接加进你常用的日历</h1>
  <p class="sub">一次订阅，之后每天 08:00 自动更新；不用每次下载 .ics 再导入。下面按你用的日历选一个。</p>
  <div class="cal-urlbar">
    <code id="cal-url">{esc(cal)}</code>
    <button class="btn primary" type="button" data-copy="{esc(cal)}">复制订阅链接</button>
  </div>
  <p class="cal-hint" id="cal-copied" role="status" aria-live="polite"></p>
</section>

<div class="cal-grid">
  <article class="cal-card">
    <div class="cal-badge">01 / APPLE</div>
    <div class="cal-card-head"><span class="cal-logo">iOS</span><h2>Apple 日历 / iPhone</h2></div>
    <p>点一下会打开系统日历，确认“订阅”即可；之后自动刷新，不需要再下载。</p>
    <a class="btn primary" href="{esc(webcal)}">在 Apple 日历中订阅 ↗</a>
    <p class="cal-note">没有自动打开？设置 → 日历 → 账户 → 添加账户 → 其他 → 添加已订阅的日历，粘贴上面的链接。</p>
  </article>

  <article class="cal-card">
    <div class="cal-badge">02 / OUTLOOK</div>
    <div class="cal-card-head"><span class="cal-logo">OUT</span><h2>Outlook</h2></div>
    <p>打开 Outlook 网页版并进入“添加日历 → 从 Web 订阅”，订阅地址已经带好。</p>
    <a class="btn primary" href="{esc(outlook)}" target="_blank" rel="noopener">在 Outlook 中订阅 ↗</a>
    <p class="cal-note">桌面版：日历 → 添加日历 → 从 Web 订阅；粘贴上面的链接。</p>
  </article>

  <article class="cal-card">
    <div class="cal-badge">03 / GOOGLE</div>
    <div class="cal-card-head"><span class="cal-logo">G</span><h2>Google 日历</h2></div>
    <p>Google 不支持链接预填。点下面按钮会复制链接并打开“从网址添加”，粘贴一次即可。</p>
    <a class="btn ghost" href="{esc(google)}" target="_blank" rel="noopener"
       data-copy="{esc(cal)}" data-copy-label="已复制；在 Google 日历里粘贴链接">复制并打开 Google 日历 ↗</a>
    <p class="cal-note">其他日历 → 通过网址添加 → 粘贴 → 添加日历。</p>
  </article>
</div>

<section class="cal-section">
  <div class="cal-section-head"><h2>或者，把链接发到邮箱</h2><span class="mono">EMAIL</span></div>
  <div class="cal-email">
    <div>
      <p>输入你的邮箱，会打开你常用的邮件客户端，把订阅链接发给你自己；在手机邮箱里点开就能订阅。</p>
      <p class="cal-note">本站不保存邮箱，也不代发邮件。想要每天的新赛事摘要，请用 <a href="about.html#subscribe">邮件订阅</a>。</p>
    </div>
    <form id="cal-email-form" class="cal-email-form">
      <label for="cal-email">你的邮箱</label>
      <div class="cal-email-row">
        <input id="cal-email" name="email" type="email" inputmode="email" autocomplete="email"
               placeholder="you@example.com" required>
        <button class="btn primary" type="submit">把链接发给我</button>
      </div>
      <p class="cal-status" id="cal-status" role="status" aria-live="polite"></p>
    </form>
  </div>
</section>

<section class="cal-section cal-why">
  <div class="cal-section-head"><h2>订阅后会发生什么</h2><span class="mono">HOW IT WORKS</span></div>
  <div class="cal-why-grid">
    <div><b>01 / 自动同步</b><p>日历服务会定期拉取同一个地址；本站每天 08:00 重建，新增赛事和截止日会自动出现。</p></div>
    <div><b>02 / 只放有日期的</b><p>没有可靠比赛日期的赛事不会伪造日程；报名截止日会单独生成提醒。</p></div>
    <div><b>03 / 随时退订</b><p>在日历里删除这个订阅即可，不会影响其他日程，也不需要本站账号。</p></div>
  </div>
</section>

<section class="cal-section">
  <div class="cal-fallback">
    <div>
      <h2>不想用日历？</h2>
      <p>下载 .ics 单次导入，或订阅 RSS / 每日邮件。</p>
    </div>
    <div class="cal-fallback-links">
      <a class="btn ghost" href="calendar.ics">下载 .ics</a>
      <a class="btn ghost" href="feed.xml">RSS</a>
      <a class="btn ghost" href="about.html#subscribe">每日邮件</a>
    </div>
  </div>
  <p class="cal-footer-note">订阅源：{esc(cal)} · 更新：每天 08:00（北京时间）· 数据许可 CC BY 4.0</p>
</section>
<script>{js}</script>
""" + foot()
