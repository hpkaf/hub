#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点视觉主题：STYLE（CSS）与 APP_JS。

设计语言：夜间雷达室 / Radar Room
  - 近黑绿底 + 单点荧光绿信号色，其余一律灰阶
  - 标题用宋体（Songti SC）做编辑感，数据/标签一律等宽字体
  - 细发丝线、大留白、编号与倒计时像仪表读数
  - 一个克制的雷达扫描动效作为唯一装饰
"""

STYLE = r"""
:root, :root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0b100d; --panel:#121b16; --panel2:#17231c;
  --ink:#edf2ea; --ink2:#c9d2c7; --muted:#94a298; --faint:#7b897e;
  --line:rgba(237,242,234,.11); --line2:rgba(237,242,234,.22);
  --accent:#c9f73f; --accent-rgb:201,247,63;
  --warn:#ffb65c; --warn-rgb:255,182,92;
  --on-accent:#0b100d;
  --header-bg:rgba(11,16,13,.74); --rail-bg:rgba(11,16,13,.90);
  --hover:rgba(255,255,255,.028); --dash:rgba(237,242,234,.10);
  --outline:rgba(237,242,234,.62); --stroke:1px;
  --noise-opacity:.04; --noise-blend:overlay;
  --glow:radial-gradient(1100px 520px at 82% -8%,rgba(var(--accent-rgb),.075),transparent 60%),
         radial-gradient(900px 480px at 4% -6%,rgba(110,255,214,.045),transparent 55%);
  --serif:"Songti SC","Noto Serif SC","Source Han Serif SC",STSong,"SimSun",serif;
  --mono:"JetBrains Mono","SFMono-Regular",ui-monospace,"SF Mono",Menlo,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",sans-serif;
}
/* 浅色：系统偏好浅色时自动启用；点右上角按钮可手动固定 */
@media (prefers-color-scheme: light){
  :root{
    color-scheme:light;
    --bg:#f3f4ec; --panel:#ffffff; --panel2:#f8f9f2;
    --ink:#16201a; --ink2:#33423a; --muted:#55655b; --faint:#65746a;
    --line:rgba(22,32,26,.12); --line2:rgba(22,32,26,.24);
    --accent:#3f6b00; --accent-rgb:63,107,0;
    --warn:#a35a00; --warn-rgb:163,90,0;
    --on-accent:#ffffff;
    --header-bg:rgba(243,244,236,.82); --rail-bg:rgba(243,244,236,.92);
    --hover:rgba(22,32,26,.035); --dash:rgba(22,32,26,.12);
    --outline:rgba(22,32,26,.78); --stroke:1.4px;
    --noise-opacity:.022; --noise-blend:multiply;
    --glow:radial-gradient(1100px 520px at 82% -8%,rgba(63,107,0,.08),transparent 60%),
           radial-gradient(900px 480px at 4% -6%,rgba(20,120,90,.05),transparent 55%);
  }
}
:root[data-theme="light"]{
  color-scheme:light;
  --bg:#f3f4ec; --panel:#ffffff; --panel2:#f8f9f2;
  --ink:#16201a; --ink2:#33423a; --muted:#55655b; --faint:#65746a;
  --line:rgba(22,32,26,.12); --line2:rgba(22,32,26,.24);
  --accent:#3f6b00; --accent-rgb:63,107,0;
  --warn:#a35a00; --warn-rgb:163,90,0;
  --on-accent:#ffffff;
  --header-bg:rgba(243,244,236,.82); --rail-bg:rgba(243,244,236,.92);
  --hover:rgba(22,32,26,.035); --dash:rgba(22,32,26,.12);
  --outline:rgba(22,32,26,.78); --stroke:1.4px;
  --noise-opacity:.022; --noise-blend:multiply;
  --glow:radial-gradient(1100px 520px at 82% -8%,rgba(63,107,0,.08),transparent 60%),
         radial-gradient(900px 480px at 4% -6%,rgba(20,120,90,.05),transparent 55%);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.65;
  background-image:var(--glow);background-repeat:no-repeat}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:5;
  opacity:var(--noise-opacity);mix-blend-mode:var(--noise-blend);
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
::selection{background:var(--accent);color:var(--on-accent)}
a{color:inherit;text-decoration:none}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px}
.mono{font-family:var(--mono)}

/* ---------------- header ---------------- */
header.site{position:sticky;top:0;z-index:30;background:var(--header-bg);
  backdrop-filter:blur(16px) saturate(140%);-webkit-backdrop-filter:blur(16px) saturate(140%);
  border-bottom:1px solid var(--line)}
.hrow{display:flex;align-items:center;gap:26px;height:64px}
.brand{display:flex;align-items:center;gap:10px;min-width:0}
.mark{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 14px rgba(var(--accent-rgb),.75);flex:none}
.bname{font-family:var(--serif);font-weight:700;font-size:17px;letter-spacing:.08em;white-space:nowrap}
.ben{font-family:var(--mono);font-size:9.5px;letter-spacing:.24em;color:var(--faint);white-space:nowrap;margin-left:2px}
nav.top{display:flex;gap:26px;margin-left:auto;font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;color:var(--muted)}
nav.top a{padding:4px 0;border-bottom:1px solid transparent;transition:color .2s,border-color .2s;white-space:nowrap}
nav.top a:hover{color:var(--ink)}
nav.top a.on{color:var(--accent);border-color:var(--accent)}
.live{display:flex;align-items:center;gap:7px;border-left:1px solid var(--line);padding-left:20px;flex:0 0 auto;
  font-family:var(--mono);font-size:10px;letter-spacing:.18em;color:var(--muted);white-space:nowrap}
.live .lk{white-space:nowrap}
.live i{width:5px;height:5px;border-radius:50%;background:var(--accent);animation:blink 2.6s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
.theme-toggle{appearance:none;-webkit-appearance:none;width:30px;height:30px;border-radius:50%;
  border:1px solid var(--line2);background:transparent;color:var(--ink2);cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;margin-left:14px;
  font-family:var(--mono);font-size:13px;line-height:1;transition:color .2s,border-color .2s,background .2s}
.theme-toggle:hover{color:var(--accent);border-color:var(--accent);background:var(--hover)}
.theme-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ---------------- hero ---------------- */
.hero{display:grid;grid-template-columns:minmax(0,1.24fr) minmax(0,.76fr);gap:48px;align-items:center;padding:76px 0 48px}
.kicker{display:flex;align-items:center;gap:12px;font-family:var(--mono);font-size:10.5px;
  letter-spacing:.26em;color:var(--faint);margin-bottom:30px}
.kicker::before{content:"";width:24px;height:1px;background:var(--accent)}
h1.display{font-family:var(--serif);font-weight:600;font-size:clamp(40px,5.4vw,78px);line-height:1.15;
  letter-spacing:.015em;margin:0}
h1.display em{font-style:normal;color:transparent;-webkit-text-stroke-width:var(--stroke);-webkit-text-stroke-color:var(--outline)}
.hero .sub{color:var(--muted);font-size:15px;max-width:30em;margin:28px 0 0;line-height:1.9}
.radar{position:relative;width:min(380px,100%);aspect-ratio:1;margin-left:auto;justify-self:end}
.rings i{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);border:1px solid rgba(var(--accent-rgb),.13);border-radius:50%}
.rings i:nth-child(1){width:100%;height:100%;border-color:rgba(var(--accent-rgb),.20)}
.rings i:nth-child(2){width:74%;height:74%}
.rings i:nth-child(3){width:48%;height:48%}
.rings i:nth-child(4){width:22%;height:22%;border-color:rgba(var(--accent-rgb),.35)}
.radar::before,.radar::after{content:"";position:absolute;background:rgba(var(--accent-rgb),.10)}
.radar::before{left:0;right:0;top:50%;height:1px}
.radar::after{top:0;bottom:0;left:50%;width:1px}
.sweep{position:absolute;inset:0;border-radius:50%;opacity:.6;
  background:conic-gradient(from 0deg,rgba(var(--accent-rgb),.32),rgba(var(--accent-rgb),.04) 68deg,transparent 125deg);
  animation:spin 14s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.blip{position:absolute;width:5px;height:5px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 10px 1px rgba(var(--accent-rgb),.8);left:var(--x);top:var(--y);animation:pulse 3.4s ease-in-out infinite}
.blip.b2{animation-delay:.9s}
.blip.b3{animation-delay:1.8s}
.blip.b4{animation-delay:2.6s;opacity:.7}
@keyframes pulse{0%,100%{opacity:.3;transform:scale(.75)}50%{opacity:1;transform:scale(1.3)}}
.rlabel,.rmeta{position:absolute;bottom:-28px;font-family:var(--mono);font-size:9.5px;letter-spacing:.22em;color:var(--faint)}
.rlabel{left:2px}
.rmeta{right:2px;letter-spacing:.16em}

/* hero right: deadline panel */
.hero-panel{width:min(470px,100%);justify-self:end;align-self:center;
  border-left:1px solid var(--line);padding-left:28px}
.hp-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.hp-head h2{font-family:var(--serif);font-size:29px;line-height:1.25;margin:5px 0 0}
.hp-live{font-family:var(--mono);font-size:9px;letter-spacing:.12em;color:var(--faint);white-space:nowrap;padding-top:4px}
.hp-live i{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--accent);margin-right:6px;vertical-align:1px;box-shadow:0 0 0 3px rgba(var(--accent-rgb),.10)}
.hp-summary{display:flex;align-items:flex-end;gap:12px;padding:17px 0 13px;border-bottom:1px solid var(--line)}
.hp-big{font-family:var(--serif);font-size:54px;line-height:.85;color:var(--accent)}
.hp-unit{font-family:var(--mono);font-size:9.5px;line-height:1.7;color:var(--muted)}
.hp-note{margin-left:auto;font-family:var(--mono);font-size:9px;line-height:1.8;color:var(--faint);text-align:right}
.hp-list{display:grid}
.hp-row{display:grid;grid-template-columns:36px minmax(0,1fr) 14px;gap:10px;align-items:center;
  padding:12px 0;border-bottom:1px solid var(--line);transition:background .2s}
.hp-row:hover{background:var(--panel)}
.hp-days{font-family:var(--mono);font-size:18px;line-height:1;color:var(--accent)}
.hp-days small{display:block;font-size:8px;color:var(--faint);letter-spacing:.1em;margin-top:4px}
.hp-main{min-width:0}
.hp-main b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  font-size:13px;line-height:1.5;font-weight:600;color:var(--ink)}
.hp-main small{display:block;font-family:var(--mono);font-size:9px;line-height:1.6;color:var(--muted);
  margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hp-arrow{font-family:var(--mono);font-size:11px;color:var(--faint)}
.hp-foot{display:flex;justify-content:space-between;gap:12px;padding-top:12px;font-family:var(--mono);font-size:9px;color:var(--faint)}
.hp-foot a{color:var(--accent);white-space:nowrap}
.hp-empty{color:var(--muted);font-size:13px;line-height:1.9;margin:22px 0 0;max-width:32em}

/* ---------------- ledger ---------------- */
.ledger{display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.cell{padding:20px 22px 18px;border-right:1px solid var(--line);transition:background .25s}
.cell:last-child{border-right:0}
.cell:hover{background:var(--hover)}
.cell .k{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--faint);margin-bottom:10px}
.cell .v{font-family:var(--mono);font-size:30px;font-weight:400;letter-spacing:-.02em;line-height:1;color:var(--ink)}
.cell .v small{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-left:5px;letter-spacing:.06em}
.cell .v.acc{color:var(--accent)}

/* ---------------- filter rail ---------------- */
.rail{position:sticky;top:64px;z-index:20;display:flex;align-items:center;gap:32px;padding:16px 0;
  margin-top:16px;border-bottom:1px solid var(--line);background:var(--rail-bg);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.search{flex:1;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line2);padding-bottom:8px;transition:border-color .2s}
.search:focus-within{border-color:var(--accent)}
.search .sl{font-family:var(--mono);color:var(--accent);font-size:13px;line-height:1}
.search input{flex:1;background:transparent;border:0;outline:0;color:var(--ink);
  font-family:var(--mono);font-size:12.5px;letter-spacing:.02em}
.search input::placeholder{color:var(--faint)}
.chips{display:flex;gap:22px;flex-wrap:wrap}
.chip{background:none;border:0;border-bottom:1px solid transparent;padding:3px 0 2px;cursor:pointer;
  font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;color:var(--muted);transition:color .2s,border-color .2s}
.chip:hover{color:var(--ink)}
.chip.active{color:var(--accent);border-color:var(--accent)}
.sortwrap{display:flex;align-items:center;gap:9px;white-space:nowrap}
.sortwrap label{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--faint)}
select{background:transparent;border:0;outline:0;color:var(--ink);font-family:var(--mono);font-size:11.5px;cursor:pointer}
select option{background:var(--panel);color:var(--ink)}
.list-head{display:flex;justify-content:space-between;align-items:center;gap:20px;
  padding:24px 0 12px;font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;color:var(--faint)}
.list-head .cnt{color:var(--accent)}

/* ---------------- race rows ---------------- */
.race-list{border-top:1px solid var(--line);padding-bottom:80px}
.race-row{display:grid;grid-template-columns:64px minmax(0,1fr) 172px 24px;gap:26px;align-items:center;
  padding:22px 6px;border-bottom:1px solid var(--line);position:relative;transition:background .22s}
.race-row::before{content:"";position:absolute;left:0;top:12px;bottom:12px;width:2px;background:var(--accent);
  opacity:0;transition:opacity .2s}
.race-row:hover{background:var(--hover)}
.race-row:hover::before{opacity:1}
.idx{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:11.5px;
  letter-spacing:.06em;color:var(--faint)}
.st{width:5px;height:5px;border-radius:50%;flex:none;background:var(--faint)}
.st.open{background:var(--accent);box-shadow:0 0 8px rgba(var(--accent-rgb),.7)}
.st.closing{background:var(--warn);box-shadow:0 0 8px rgba(var(--warn-rgb),.6)}
.r-title{display:block;font-size:16.5px;font-weight:600;letter-spacing:.01em;line-height:1.45;color:var(--ink);transition:color .2s}
.race-row:hover .r-title{color:var(--accent)}
.r-sub{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:7px;
  font-family:var(--mono);font-size:11px;letter-spacing:.02em;color:var(--muted)}
.r-sub .sep{color:var(--faint)}
.badge{border:1px solid rgba(var(--accent-rgb),.32);color:var(--accent);padding:1px 7px;
  font-size:9.5px;letter-spacing:.1em;border-radius:2px;white-space:nowrap}
.r-deadline{text-align:right}
.dnum{font-family:var(--mono);font-size:25px;line-height:1;letter-spacing:-.02em;color:var(--ink)}
.dnum small{font-size:10px;color:var(--muted);margin-left:3px;letter-spacing:.08em}
.dnum.warn{color:var(--warn)}
.dnum.sm{font-size:12.5px;letter-spacing:.14em;color:var(--muted)}
.ddate{display:block;margin-top:8px;font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--faint)}
.arrow{font-family:var(--mono);color:var(--faint);font-size:14px;transition:transform .2s,color .2s}
.race-row:hover .arrow{transform:translateX(5px);color:var(--accent)}
.empty{border:1px dashed var(--line2);padding:64px 24px;text-align:center;margin-bottom:80px;
  font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--muted)}

/* ---------------- detail ---------------- */
.crumbs{padding:34px 0 0;font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;color:var(--muted)}
.crumbs a:hover{color:var(--accent)}
.race{max-width:1060px;padding:36px 0 96px}
.meta-line{display:flex;flex-wrap:wrap;align-items:center;gap:14px;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;color:var(--muted)}
.pill{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:10.5px;letter-spacing:.14em}
.pill.open{color:var(--accent)}
.pill.closing{color:var(--warn)}
.pill.closed,.pill.unknown{color:var(--muted)}
.race h1{font-family:var(--serif);font-weight:600;font-size:clamp(30px,4.2vw,54px);line-height:1.22;
  letter-spacing:.01em;margin:22px 0 16px}
.race .org{display:flex;flex-wrap:wrap;align-items:center;gap:12px;color:var(--muted);font-size:14px}
.cta{display:flex;flex-wrap:wrap;gap:14px;margin:32px 0 0}
.cta-note{margin-top:12px;font-family:var(--mono);font-size:10.5px;letter-spacing:.04em;color:var(--faint)}
.cta-note a{color:var(--muted);border-bottom:1px solid var(--line2)}
.cta-note a:hover{color:var(--accent)}
.btn{display:inline-flex;align-items:center;gap:10px;font-family:var(--mono);font-size:11.5px;
  letter-spacing:.12em;padding:15px 26px;border-radius:2px;transition:filter .2s,color .2s,border-color .2s;cursor:pointer}
.btn.primary{background:var(--accent);border:1px solid var(--accent);color:var(--on-accent);font-weight:700}
.btn.primary:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;border:1px solid var(--line2);color:var(--ink)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent)}
.race-body{display:grid;grid-template-columns:1.32fr .68fr;gap:64px;align-items:start;
  border-top:1px solid var(--line);margin-top:44px;padding-top:40px}
.kv{margin:0}
.kv .row{display:grid;grid-template-columns:96px 1fr;gap:20px;padding:14px 0;border-bottom:1px dashed var(--dash)}
.kv dt{font-family:var(--mono);font-size:10px;letter-spacing:.18em;color:var(--faint);padding-top:3px}
.kv dd{margin:0;font-size:14px;color:var(--ink2);line-height:1.75}
.verify{position:sticky;top:96px;background:var(--panel);border:1px solid var(--line);padding:24px;border-radius:2px}
.vhead{display:flex;align-items:center;gap:8px;margin-bottom:18px;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.22em;color:var(--accent)}
.vhead::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 8px rgba(var(--accent-rgb),.8)}
.vline{font-family:var(--mono);font-size:10.5px;line-height:2.1;color:var(--muted);word-break:break-word}
.vline b{color:var(--ink2);font-weight:500}
.vnote{margin-top:16px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;color:var(--faint);line-height:1.85}

/* ---------------- prose ---------------- */
.prose{max-width:860px;padding:56px 0 96px}
.prose h1{font-family:var(--serif);font-weight:600;font-size:clamp(32px,4vw,46px);line-height:1.25;margin:0 0 18px}
.prose .lead{font-size:16px;color:var(--ink2);line-height:1.95;margin:0 0 12px}
.prose h2{display:flex;align-items:baseline;gap:14px;font-family:var(--serif);font-weight:600;font-size:24px;
  margin:52px 0 16px;padding-top:24px;border-top:1px solid var(--line)}
.prose h2 span{font-family:var(--mono);font-size:10.5px;letter-spacing:.18em;color:var(--accent)}
.prose p,.prose li{font-size:14.5px;color:var(--ink2);line-height:1.95}
.prose ul{padding-left:20px;margin:12px 0}
.prose li{margin:6px 0}
.prose a{color:var(--accent);border-bottom:1px solid rgba(var(--accent-rgb),.35)}
.prose code{font-family:var(--mono);font-size:.88em;background:var(--panel2);border:1px solid var(--line);
  padding:1px 5px;border-radius:2px;color:var(--ink2);word-break:break-all}
.prose strong{color:var(--ink);font-weight:600}

/* ---------------- form ---------------- */
.form{margin-top:36px;display:grid;gap:26px}
.field{display:grid;gap:9px}
.field label{font-family:var(--mono);font-size:10px;letter-spacing:.18em;color:var(--faint)}
.field label .req{color:var(--accent)}
.field input,.field textarea{background:var(--panel);border:1px solid var(--line);border-radius:2px;
  color:var(--ink);padding:13px 15px;font-family:var(--sans);font-size:14px;outline:0;transition:border-color .2s}
.field input:focus,.field textarea:focus{border-color:var(--accent)}
.field textarea{min-height:120px;resize:vertical;line-height:1.7}
.hint{font-family:var(--mono);font-size:10px;letter-spacing:.04em;color:var(--faint);line-height:1.8}
.form-actions{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.form-msg{font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--accent)}

/* ---------------- footer ---------------- */
footer.site{border-top:1px solid var(--line);padding:56px 0 40px}
.fcols{display:grid;grid-template-columns:2.1fr 1fr 1fr 1fr;gap:40px}
.fmark{font-family:var(--serif);font-size:15px;letter-spacing:.1em;margin-bottom:14px;color:var(--ink)}
.fcol p{font-size:12.5px;color:var(--muted);line-height:1.9;margin:0 0 14px;max-width:26em}
.fmeta{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;color:var(--faint)}
.fhead{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--faint);margin-bottom:14px}
.fcol a{display:block;font-size:12.5px;color:var(--ink2);padding:4px 0;transition:color .2s}
.fcol a:hover{color:var(--accent)}
.fine{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-top:46px;padding-top:20px;
  border-top:1px solid var(--line);font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--faint)}

/* ---------------- explore / organizers / match / guides ---------------- */
.hero-cta{margin-top:30px}
.hero-cta .btn{padding:13px 20px}
.crumb-sep{margin:0 8px;color:var(--faint)}
.display-sm{font-family:var(--serif);font-weight:600;font-size:clamp(32px,4vw,52px);line-height:1.2;margin:8px 0 0}
.explore-hero{padding:54px 0 24px}
.explore-hero .sub{color:var(--muted);max-width:44em;line-height:1.9;margin:16px 0 0}
.explore-tabs{display:flex;gap:30px;border-bottom:1px solid var(--line);margin-top:18px}
.tab{background:none;border:0;border-bottom:2px solid transparent;padding:10px 0;cursor:pointer;
  font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;color:var(--muted);transition:color .2s,border-color .2s}
.tab.active{color:var(--accent);border-color:var(--accent)}
.tab b{font-weight:400;color:var(--faint);margin-left:4px}
.explore-filters{display:grid;gap:14px;padding:20px 0;border-bottom:1px solid var(--line);
  position:sticky;top:64px;z-index:20;background:var(--rail-bg);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.facet-groups{display:grid;gap:10px}
.facet-group{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
.facet-label{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;color:var(--faint);
  width:72px;flex:none;padding-top:6px}
.facet{background:none;border:0;border-bottom:1px solid transparent;padding:4px 0 3px;cursor:pointer;
  font-family:var(--mono);font-size:11px;letter-spacing:.03em;color:var(--muted);transition:color .2s,border-color .2s}
.facet:hover{color:var(--ink)}
.facet.active{color:var(--accent);border-color:var(--accent)}
.facet b{font-weight:400;color:var(--faint);margin-left:4px}
.explore-tools{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.explore-tools .search{flex:1;min-width:220px}
.city-select,.sort-select{background:transparent;border:1px solid var(--line2);padding:8px 10px;
  color:var(--ink2);font-family:var(--mono);font-size:11px;outline:0}
.city-select:focus,.sort-select:focus{border-color:var(--accent)}
.explore-reset{background:none;border:0;color:var(--faint);font-family:var(--mono);font-size:10.5px;cursor:pointer}
.explore-reset:hover{color:var(--accent)}
.explore-count{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;color:var(--faint)}
.explore-count b{color:var(--accent)}
.race-section{max-width:1060px;border-top:1px solid var(--line);margin-top:44px;padding-top:32px}
.race-section h2{font-family:var(--serif);font-size:23px;margin:0 0 18px}
.race-section p{color:var(--ink2);line-height:1.9;font-size:14.5px}
.section-note{font-family:var(--mono);font-size:10px;color:var(--faint);margin-top:14px;line-height:1.8}
.agenda{list-style:none;margin:0;padding:0}
.agenda li{display:grid;grid-template-columns:150px 1fr;gap:20px;padding:14px 0;border-bottom:1px dashed var(--dash)}
.ag-date{font-family:var(--mono);font-size:11px;letter-spacing:.03em;color:var(--faint)}
.ag-title{font-size:14.5px;color:var(--ink)}
.related-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.related-card{border:1px solid var(--line);padding:16px;background:var(--panel);transition:border-color .2s}
.related-card:hover{border-color:var(--accent)}
.rc-title{display:block;font-weight:600;line-height:1.5;margin-bottom:8px}
.rc-meta{font-family:var(--mono);font-size:10px;color:var(--muted);line-height:1.6}
.source-box{background:var(--panel);border:1px solid var(--line);padding:24px;margin-top:44px}
.source-lines{display:grid;gap:8px;font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:16px;word-break:break-all}
.source-actions{margin-top:16px}
.source-actions a{color:var(--accent)}
.source-evidence{font-size:12px!important;color:var(--faint)!important}
.faq details{border-bottom:1px solid var(--line);padding:15px 0}
.faq summary{cursor:pointer;font-weight:600;color:var(--ink);font-size:15px;line-height:1.7}
.faq summary::marker{color:var(--accent)}
.faq p{color:var(--ink2);font-size:14px;margin:10px 0 0}
.kv dd a{border-bottom:1px solid var(--line2)}
.kv dd a:hover{color:var(--accent)}
.org-hero{display:flex;gap:24px;align-items:center;padding:52px 0 28px;border-bottom:1px solid var(--line)}
.org-logo{width:88px;height:88px;border-radius:50%;background:var(--panel);border:1px solid var(--line2);
  display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-size:36px;color:var(--accent);flex:none}
.org-logo.sm{width:44px;height:44px;font-size:18px}
.org-hero h1{font-family:var(--serif);font-size:clamp(28px,3.4vw,44px);line-height:1.25;margin:0}
.org-meta{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;color:var(--muted);margin-top:10px}
.org-intro{max-width:780px;color:var(--ink2);line-height:1.95;margin:24px 0 0;font-size:14.5px}
.org-stats{display:flex;gap:24px;flex-wrap:wrap;border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  padding:16px 0;margin-top:26px;font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.org-stats b{color:var(--ink);font-size:16px;margin-right:4px}
.org-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:28px;padding-bottom:72px}
.org-card{border:1px solid var(--line);background:var(--panel);padding:16px;display:flex;gap:14px;align-items:center;
  transition:border-color .2s,background .2s}
.org-card:hover{border-color:var(--accent);background:var(--panel2)}
.org-card b{display:block;font-size:14px;line-height:1.45}
.org-card small{display:block;font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:5px;line-height:1.6}
.org-card-main{min-width:0}
.match-hero{padding:54px 0 24px}
.match-form{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:16px;border:1px solid var(--line);
  background:var(--panel);padding:22px;margin-top:28px}
.match-field{display:grid;gap:8px}
.match-field label{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;color:var(--faint)}
.match-field input,.match-field select{background:var(--bg);border:1px solid var(--line);padding:11px 12px;
  color:var(--ink);font-family:var(--sans);font-size:14px;outline:0}
.match-field input:focus,.match-field select:focus{border-color:var(--accent)}
.match-check{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:10.5px;color:var(--muted);grid-column:1/-1}
.match-actions{grid-column:1/-1;display:flex;gap:12px;align-items:center}
.match-results{display:grid;gap:14px;margin-top:28px;padding-bottom:72px}
.match-card{border:1px solid var(--line);background:var(--panel);padding:20px;display:grid;grid-template-columns:1fr auto;gap:20px;align-items:start}
.match-card:hover{border-color:var(--accent)}
.match-card h3{font-family:var(--serif);font-size:20px;margin:0 0 8px;line-height:1.4}
.match-card .mm{font-family:var(--mono);font-size:10px;color:var(--muted);line-height:1.8}
.match-score{font-family:var(--mono);font-size:24px;color:var(--accent);text-align:right;white-space:nowrap}
.match-score small{display:block;font-size:9px;color:var(--faint);letter-spacing:.1em;margin-top:4px}
.match-reasons{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:10px;line-height:1.9}
.match-empty{border:1px dashed var(--line2);padding:40px 20px;text-align:center;color:var(--muted);font-family:var(--mono);font-size:11px}
.guide-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:28px;padding-bottom:72px}
.guide-card{border:1px solid var(--line);background:var(--panel);padding:24px;transition:border-color .2s}
.guide-card:hover{border-color:var(--accent)}
.guide-card h2{font-family:var(--serif);font-size:21px;line-height:1.4;margin:8px 0 10px}
.guide-card p{font-size:13px;color:var(--muted);line-height:1.8;margin:0}
.guide-meta{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;color:var(--faint)}
.guide-article{max-width:860px;padding:48px 0 88px}
.guide-article h1{font-family:var(--serif);font-size:clamp(30px,4vw,44px);line-height:1.25;margin:10px 0 16px}
.guide-article .lead{font-size:16px;color:var(--ink2);line-height:1.95}
.guide-article h2{font-family:var(--serif);font-size:24px;margin:40px 0 12px}
.guide-article p,.guide-article li{font-size:14.5px;line-height:1.95;color:var(--ink2)}
.guide-article table{width:100%;border-collapse:collapse;margin:18px 0;font-size:13px}
.guide-article th,.guide-article td{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left}
.guide-article th{font-family:var(--mono);font-size:10px;letter-spacing:.12em;color:var(--faint);font-weight:400}

/* ---------------- responsive ---------------- */
@media(max-width:960px){
  .hero{grid-template-columns:1fr;padding:56px 0 36px}
  .radar{display:none}
  .hero-panel{width:100%;border-left:0;border-top:1px solid var(--line);padding:24px 0 0;margin-top:8px;align-self:start}
  .race-body{grid-template-columns:1fr;gap:36px}
  .verify{position:static}
  .fcols{grid-template-columns:1fr 1fr}
  .r-deadline{text-align:left}
  .explore-filters{position:static}
  .related-grid{grid-template-columns:1fr}
  .org-grid{grid-template-columns:1fr 1fr}
  .guide-grid{grid-template-columns:1fr 1fr}
  .match-form{grid-template-columns:1fr 1fr}
  .match-card{grid-template-columns:1fr}
}
@media(max-width:720px){
  .wrap{padding:0 18px}
  .hrow{height:56px;gap:14px}
  .ben{display:none}
  .live{display:none}
  .theme-toggle{margin-left:0;width:28px;height:28px}
  nav.top{gap:16px;font-size:10.5px}
  h1.display{font-size:clamp(34px,10vw,46px)}
  .hero .sub{font-size:14px;margin-top:22px}
  .ledger{grid-template-columns:1fr 1fr}
  .cell{padding:16px 14px;border-bottom:1px solid var(--line)}
  .cell .v{font-size:24px}
  .rail{top:56px;flex-direction:column;align-items:stretch;gap:14px;padding:14px 0}
  .chips{gap:16px}
  .sortwrap{justify-content:flex-end}
  .race-row{grid-template-columns:36px minmax(0,1fr) 82px;gap:12px;padding:18px 2px}
  .arrow{display:none}
  .r-title{font-size:15px}
  .r-sub{font-size:10px;gap:6px}
  .dnum{font-size:19px}
  .dnum small{font-size:9px}
  .ddate{font-size:9px;margin-top:6px}
  .race h1{font-size:clamp(26px,7vw,34px)}
  .prose{padding:36px 0 72px}
  .race{padding:28px 0 72px}
  .cta .btn{flex:1;justify-content:center}
  .hero-cta{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .hero-cta .btn{width:100%;white-space:nowrap}
  .hero-cta .btn:first-child{grid-column:1/-1}
  .fcols{grid-template-columns:1fr 1fr;gap:26px}
  .fcol p{font-size:12px}
  .org-grid,.guide-grid{grid-template-columns:1fr}
  .org-hero{flex-wrap:wrap;gap:16px;padding-top:36px}
  .org-logo{width:64px;height:64px;font-size:26px}
  .org-intro{font-size:14px}
  .agenda li{grid-template-columns:110px 1fr;gap:12px}
  .facet-label{width:100%;padding-top:0}
  .explore-hero{padding-top:36px}
  .match-form{grid-template-columns:1fr;padding:16px}
  .hero-panel{padding-top:20px}
  .hp-head h2{font-size:25px}
  .hp-big{font-size:46px}
  .hp-note{font-size:8.5px}
  .hp-row{padding:11px 0}
  .match-card{grid-template-columns:1fr;padding:16px}
  .match-score{text-align:left}
  .guide-article{padding:32px 0 64px}
}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important;scroll-behavior:auto!important}
}
"""

APP_JS = r"""
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
"""
