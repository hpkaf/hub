# -*- coding: utf-8 -*-
"""三篇数据驱动的指南。内容在构建时生成，数字来自当前 races.json。"""
from __future__ import annotations

import html

import common


def _e(value) -> str:
    return html.escape(str(value or ""), quote=True)


def build(records: list[dict], index_records: list[dict]) -> list[dict]:
    total = len(records)
    current = len(index_records)
    past = total - current
    online = sum(1 for r in records if r.get("mode") == "online")
    offline = sum(1 for r in records if r.get("mode") == "offline")
    hybrid = sum(1 for r in records if r.get("mode") == "hybrid")
    openable = sum(1 for r in index_records if r.get("status") in ("open", "closing"))
    no_deadline = sum(1 for r in index_records if not r.get("deadline"))
    cities = sorted({r.get("city") for r in records if r.get("city")})
    upcoming = sorted(
        [r for r in index_records if r.get("status") in ("open", "closing", "upcoming")],
        key=lambda r: (r.get("deadline") or "9999-12-31", r.get("title") or ""),
    )[:8]
    upcoming_html = "".join(
        f'<li><a href="../race/{_e(r["id"])}.html">{_e(r.get("title"))}</a>'
        f'<span class="guide-meta"> · {_e(common.MODE_LABEL.get(r.get("mode") or "", "待确认"))}'
        f' · 截止 {_e(r.get("deadline") or "待确认")}</span></li>'
        for r in upcoming
    ) or "<li>当前窗口暂时没有可报名的赛事，可先看往届或订阅日历。</li>"
    city_html = "、".join(_e(c) for c in cities) or "线上"

    g1 = f"""
<div class="guide-meta">GUIDE 01 · 数据更新 {_e(common.now_iso()[:10])}</div>
<h1>AI 赛事日历：还能报名的都在这里</h1>
<p class="lead">这份日历不追求「全网最全」，只回答一个问题：<strong>现在点开还能报名、日期对得上的 AI 赛事有哪些。</strong>
所有数字来自本站当前收录，完整列表在 <a href="../explore.html">探索页</a>。</p>

<h2>先看数字</h2>
<table>
<tr><th>指标</th><th>当前</th></tr>
<tr><td>收录（含近 90 天往届）</td><td>{total} 场</td></tr>
<tr><td>首页在架（在架 + 近 14 天结束）</td><td>{current} 场</td></tr>
<tr><td>还能报名（报名中 + 即将截止）</td><td>{openable} 场</td></tr>
<tr><td>线上 / 线下 / 混合（含往届）</td><td>{online} / {offline} / {hybrid}</td></tr>
<tr><td>截止日待确认（在架）</td><td>{no_deadline} 场</td></tr>
<tr><td>覆盖城市（线下）</td><td>{city_html}</td></tr>
</table>

<h2>现在可以优先看的 8 场</h2>
<ul class="guide-list">{upcoming_html}</ul>
<p class="section-note">按报名截止日排序；每条详情页都有链接核验时间、来源页和官方报名入口。</p>

<h2>怎么用这份日历</h2>
<ol>
<li>先按「线上 / 线下 / 混合」排除无法参加的形式；本站线上赛占多数。</li>
<li>再看截止日：7 天内截止的标「即将截止」，不要等到最后一天。</li>
<li>报名状态以官方页为准；本站的「已确认」只代表链接能打开，不代表主办方信息永不变化。</li>
<li>想按方向找，用 <a href="../match.html">帮我找赛事</a>；想按平台/级别筛，用 <a href="../explore.html">探索页</a>。</li>
</ol>

<h2>常见问题</h2>
<p><strong>为什么只有这些赛事？</strong> 只收 AI 相关、且有公开可访问官方链接的赛事；私域扫码、只有截图的线索不进公开列表。</p>
<p><strong>截止日为什么有「待确认」？</strong> 官方页没写清楚，或页面动态渲染拿不到可靠字段；我们不猜日期。</p>
<p><strong>往届在哪里？</strong> 探索页切到「往届」，或在详情页查看 90 天内存档。</p>
<p><strong>怎么订阅？</strong> 打开 <a href="../calendar.html">日历订阅页</a>，按你的日历点一下即可；也可看 <a href="../about.html#subscribe">订阅与接入</a>。</p>
"""

    g2 = f"""
<div class="guide-meta">GUIDE 02 · 适合第一次参赛</div>
<h1>第一次参加 AI 黑客松：从选赛到提交</h1>
<p class="lead">第一次参赛最容易犯的错，不是技术不够，而是<strong>选错赛、错过截止、提交材料不齐</strong>。下面是一份可以照着做的清单。</p>

<h2>1. 先选「能完成」的赛，而不是「看起来最酷」的赛</h2>
<ul>
<li><strong>时间</strong>：48 小时线下赛和 4 周线上赛是两种运动；先看自己能不能在截止前留出完整时间。</li>
<li><strong>形式</strong>：线上赛省通勤，线下赛更容易组队和拿反馈；本站当前收录 {online} 场线上、{offline} 场线下、{hybrid} 场混合。</li>
<li><strong>方向</strong>：智能体、大模型应用、具身、算法/AIGC 的评审标准不同；用 <a href="../match.html">匹配页</a> 按方向筛，不要盲投。</li>
<li><strong>资格</strong>：学生/高校/企业/地区限制在官方页，别只看海报。</li>
</ul>

<h2>2. 报名前核对四件事</h2>
<ol>
<li>官方报名页能打开，且截止日没写「已结束」；</li>
<li>组队要求（个人/2–4 人/必须跨校）和年龄/身份限制；</li>
<li>提交物：Demo、GitHub 仓库、Pitch deck、视频、现场路演，哪些必须；</li>
<li>奖金/差旅/住宿规则，尤其是「税前」「代金券」「股权投资」这类口径。</li>
</ol>

<h2>3. 48 小时怎么排</h2>
<table>
<tr><th>时间</th><th>动作</th></tr>
<tr><td>前 2 小时</td><td>定一个能演示的最小问题；确定技术栈与分工</td></tr>
<tr><td>第 1 天</td><td>跑通端到端 Demo，先有可演示的「丑版本」</td></tr>
<tr><td>第 2 天上午</td><td>补关键功能、写 README、录 Demo 视频</td></tr>
<tr><td>最后 3 小时</td><td>只做提交材料与路演稿，不再加新功能</td></tr>
</table>

<h2>4. 提交材料清单</h2>
<ul>
<li>项目名 + 一句话介绍 + 目标用户；</li>
<li>Demo 链接 / 视频（确保评委不用登录也能看）；</li>
<li>代码仓库（公开或按赛事要求）；</li>
<li>技术栈、使用到的模型/API、数据来源；</li>
<li>团队成员与分工；</li>
<li>若使用开源项目/数据集，写清许可与出处。</li>
</ul>

<h2>5. 去哪里找下一场</h2>
<p>用 <a href="../explore.html">探索页</a> 按方向/形式/截止筛，或打开 <a href="../calendar.html">日历订阅页</a>。
本站只做信息整理，报名与资格以主办方官方页为准。</p>
"""

    g3 = f"""
<div class="guide-meta">GUIDE 03 · 数据视角</div>
<h1>线上 vs 线下 AI 赛事：怎么选</h1>
<p class="lead">同一场 AI 黑客松，线上和线下是两种完全不同的体验。用本站当前数据看：
<strong>线上 {online} 场、线下 {offline} 场、混合 {hybrid} 场</strong>——线上是绝对主力。</p>

<h2>一张表看清差别</h2>
<table>
<tr><th>维度</th><th>线上</th><th>线下</th></tr>
<tr><td>时间成本</td><td>低，适合异步/跨城</td><td>高，通常 24–48 小时驻场</td></tr>
<tr><td>组队</td><td>靠社群/私信，弱连接</td><td>现场碰撞，强连接</td></tr>
<tr><td>评审反馈</td><td>多为录屏/仓库评审</td><td>现场路演，即时问答</td></tr>
<tr><td>差旅/住宿</td><td>无</td><td>可能需要，先看主办方是否补贴</td></tr>
<tr><td>适合谁</td><td>有全职工作/课业、想快速试水</td><td>想深度组队、拿现场资源/offer</td></tr>
</table>

<h2>怎么判断一场线下赛值不值得去</h2>
<ol>
<li>看奖金/资源是否覆盖差旅；没有补贴的异地赛，先算成本。</li>
<li>看场地与日程：是否提供住宿、餐饮、设备；48 小时赛的「不能睡觉」不是荣誉。</li>
<li>看评审与资源：是否有目标公司/投资人/社区在场。</li>
<li>看资格：学生赛/高校赛/企业赛的限制。</li>
</ol>

<h2>线上赛怎么避免「交了没人看」</h2>
<ul>
<li>Demo 视频前 30 秒必须讲清「解决什么问题」；</li>
<li>README 写运行方式、依赖、数据来源；</li>
<li>仓库保持可复现，别把密钥/隐私数据提交上去；</li>
<li>按赛事要求提交，不要只发一个网盘链接。</li>
</ul>

<h2>按形式筛赛事</h2>
<p><a href="../explore.html?mode=online">只看线上</a> ·
<a href="../explore.html?mode=offline">只看线下</a> ·
<a href="../explore.html?mode=hybrid">只看混合</a></p>
<p>线下城市当前覆盖：{city_html}。城市样本还少，我们不会为了筛选项硬凑城市页。</p>
"""

    return [
        {"slug": "2026-ai-race-calendar", "title": "AI 赛事日历：还能报名的都在这里",
         "desc": "用当前收录数据看还能报名的 AI 赛事、截止分布与筛选方式。", "body": g1},
        {"slug": "first-ai-hackathon", "title": "第一次参加 AI 黑客松：从选赛到提交",
         "desc": "第一次参加 AI 黑客松的选赛、报名、48 小时排期与提交材料清单。", "body": g2},
        {"slug": "online-vs-offline", "title": "线上 vs 线下 AI 赛事：怎么选",
         "desc": "用真实收录数据比较线上、线下、混合 AI 赛事的时间、成本与适配人群。", "body": g3},
    ]
