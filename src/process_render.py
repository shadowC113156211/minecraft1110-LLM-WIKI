# -*- coding: utf-8 -*-
"""作業說明頁：主題介紹、Wiki／簡報連結、loop/graph、執行紀錄（讀 runs/*.json）、反思。"""
import os, json, glob
from data_report import DISCUSSION, LOOP_TEXT, REFLECTION, MANUAL_LOG


def graph_svg():
    N = {  # id: (x, y, w, h, 文字, 類型)
        "A": (20, 30, 170, 64, "① 需求討論<br>（先討論）", "p"),
        "B": (240, 30, 170, 64, "② 取得資料<br>Ingest 來源", "p"),
        "C": (460, 30, 170, 64, "③ 整理 Wiki 條目<br>指南／生物／物品", "p"),
        "D": (680, 30, 170, 64, "④ 建立雙向關係<br>RELATIONS", "p"),
        "E": (860, 145, 236, 100, "⑤ 前置檢查<br>CHECK（8 類規則）", "c"),
        "F": (640, 300, 200, 64, "⑥ 從 Wiki 生成<br>Wiki 頁＋簡報", "p"),
        "G": (380, 290, 200, 92, "⑦ 後置檢查<br>本地連結", "c"),
        "H": (130, 290, 200, 92, "⑧ 人工檢視<br>截圖看版面", "c"),
        "I": (20, 450, 170, 56, "⑨ 輸出交付", "o"),
    }
    def box(k):
        x, y, w, h, t, ty = N[k]
        fill = {"p": "#1f3a14", "c": "#4a3a06", "o": "#2d0a63"}[ty]
        stroke = {"p": "#6aab44", "c": "#fcd34d", "o": "#b07ce8"}[ty]
        lines = t.split("<br>")
        tx = "".join(f'<tspan x="{x + w / 2}" dy="{0 if i == 0 else 22}">{l}</tspan>' for i, l in enumerate(lines))
        shape = (f'<polygon points="{x + w / 2},{y} {x + w},{y + h / 2} {x + w / 2},{y + h} {x},{y + h / 2}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>' if ty == "c"
                 else f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
        return f'{shape}<text x="{x + w / 2}" y="{y + h / 2 - (len(lines) - 1) * 11 + 6}" text-anchor="middle" font-size="16" fill="#fff">{tx}</text>'
    def c(k, side):
        x, y, w, h, *_ = N[k]
        return {"r": (x + w, y + h / 2), "l": (x, y + h / 2), "t": (x + w / 2, y), "b": (x + w / 2, y + h)}[side]
    E = [("A", "r", "B", "l", "", "#ddd", ""), ("B", "r", "C", "l", "", "#ddd", ""), ("C", "r", "D", "l", "", "#ddd", ""),
         ("D", "r", "E", "t", "", "#ddd", ""), ("E", "b", "F", "r", "通過（只剩 warn）", "#80ff20", ""),
         ("F", "l", "G", "r", "", "#ddd", ""), ("G", "l", "H", "r", "0 斷鏈", "#80ff20", ""), ("H", "b", "I", "r", "OK", "#80ff20", "")]
    out = ['<svg viewBox="0 0 1100 520" width="100%" style="max-width:1100px;background:rgba(0,0,0,.45);border:3px solid #000">',
           '<defs><marker id="ar" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ddd"/></marker>'
           '<marker id="ag" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#80ff20"/></marker>'
           '<marker id="ae" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ff6b6b"/></marker></defs>']
    for a, sa, b, sb, lab, col, _ in E:
        (x1, y1), (x2, y2) = c(a, sa), c(b, sb)
        mk = "ag" if col == "#80ff20" else "ar"
        if sa in "rl" and sb in "tb":
            d = f"M{x1},{y1} L{x2},{y1} L{x2},{y2}"
        elif sa in "tb" and sb in "rl":
            d = f"M{x1},{y1} L{x1},{y2} L{x2},{y2}"
        else:
            d = f"M{x1},{y1} L{x2},{y2}"
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3" marker-end="url(#{mk})"/>')
        if lab: out.append(f'<text x="{(x1 + x2) / 2 + 6}" y="{(y1 + y2) / 2 - 8}" font-size="14" fill="{col}">{lab}</text>')
    loops = [  # 紅色回圈
        ("M980,150 L980,120 L545,120 L545,94", "error → 修正條目（重跑 ③④⑤）", 690, 114),
        ("M1080,196 L1095,196 L1095,10 L325,10 L325,30", "缺數值／來源 → 補 ingest", 640, 26),
        ("M480,382 L480,420 L740,420 L740,364", "斷鏈 → 局部重新生成", 520, 440),
        ("M230,290 L230,250 L560,250 L560,94", "版面／內容問題 → 回到條目或模板", 250, 244),
    ]
    for d, lab, lx, ly in loops:
        out.append(f'<path d="{d}" fill="none" stroke="#ff6b6b" stroke-width="3" stroke-dasharray="8 5" marker-end="url(#ae)"/>'
                   f'<text x="{lx}" y="{ly}" font-size="14" fill="#ff9b9b">{lab}</text>')
    out += [box(k) for k in N]
    out.append('<g font-size="13" fill="#ccc"><rect x="640" y="460" width="18" height="12" fill="#1f3a14" stroke="#6aab44"/><text x="664" y="471">處理節點</text>'
               '<rect x="740" y="460" width="18" height="12" fill="#4a3a06" stroke="#fcd34d"/><text x="764" y="471">檢查節點</text>'
               '<line x1="840" y1="466" x2="870" y2="466" stroke="#ff6b6b" stroke-width="3" stroke-dasharray="6 4"/><text x="876" y="471">失敗時的回圈</text></g></svg>')
    return "".join(out)


def render_process(G, report, runs_dir, SOURCES, href, page):
    B = "root"; md = lambda t: G["md"](t, B)
    runs = []
    for f in sorted(glob.glob(os.path.join(runs_dir, "run_*.json"))):
        with open(f, encoding="utf-8") as fh: runs.append(json.load(fh))
    if not runs or runs[-1]["run"] != report["run"]: runs.append(report)
    rows = ""
    for r in runs:
        ck = r.get("check", {}); pc = r.get("post_check", {})
        codes = "<br>".join(f"{k}：{v}" for k, v in ck.get("by_code", {}).items()) or "—"
        res = r.get("result", "")
        color = "#80ff20" if res.startswith("OK") else "#ff8080"
        rows += (f'<tr><td>#{r["run"]}</td><td style="font-size:13px">{r.get("time","")}</td><td style="font-size:14px">{r.get("note","")}</td>'
                 f'<td>{ck.get("errors","")}</td><td>{ck.get("warns","")}</td><td style="font-size:13px">{codes}</td>'
                 f'<td>{pc.get("broken_links","—") if pc else "—"}</td><td style="color:{color};font-size:14px">{res}</td></tr>')
    first_fail = next((r for r in runs if r.get("check", {}).get("errors")), None)
    sample = ""
    if first_fail:
        li = "".join(f'<li><code>{x["level"]}</code> {x["code"]}｜{x["where"]}｜{x["msg"]}</li>' for x in first_fail["check"]["samples"][:18])
        sample = f'<h3>第 #{first_fail["run"]} 次執行被擋下時的檢查輸出（節錄）</h3><ul style="font-size:14px">{li}</ul>'
    last = runs[-1]
    li_last = "".join(f'<li>{x["code"]}｜{x["where"]}｜{x["msg"]}</li>' for x in last.get("check", {}).get("samples", [])[:14])
    src_rows = "".join(f'<tr><td>{k}</td><td>第 {v[2]} 輪</td><td><a href="{v[1]}" target="_blank" rel="noopener">{v[0]}</a></td></tr>' for k, v in sorted(SOURCES.items()))
    disc = "".join(f"<tr><td>{a}</td><td>{md(b)}</td></tr>" for a, b in DISCUSSION)
    man = "".join(f"<tr><td>{a}</td><td>{md(b)}</td><td>{md(c)}</td></tr>" for a, b, c in MANUAL_LOG)
    W = report["wiki"]
    refl = "".join(f'<h3>{q}</h3><p>{md(a)}</p>' for q, a in REFLECTION)
    loop = "".join(f'<h3>{q}</h3><p>{md(a)}</p>' for q, a in LOOP_TEXT)
    body = f"""<div class="crumb"><a href="index.html">首頁</a> › 作業流程與反思</div>
<div class="panel green"><h1>作業說明：用 LLM Wiki 做一份教學 HTML 簡報</h1><p>主題：<strong>Minecraft 生存指南 Wiki ＋ 生物圖鑑 ＋ 物品圖鑑</strong></p></div>

<div class="panel"><h2 style="margin-top:0">1. LLM Wiki 主題與簡短介紹</h2>
<p>這是一份給「完全沒玩過生存模式」的人看的 Minecraft 知識庫。內容分成五大項：<strong>前期</strong>（工具、鐵與金、基礎怪物）、<strong>中期</strong>（裝備、農場、村民交易、下界）、<strong>後期</strong>（終界之眼、要塞、終界龍）、<strong>生物圖鑑</strong>（強度、掉落、經驗、生成地點、應對）、<strong>物品圖鑑</strong>（特性、可製作、取得難度、稀缺度）。</p>
<p>最大的特色是<strong>條目之間的雙向關係</strong>：例如「綠寶石」頁說明它是村民交易的貨幣、並連到「村民」；「村民」頁則說明交易全以綠寶石計價、並連回「綠寶石」。生物的掉落物會自動出現在物品頁，物品的材料也會自動連到它能做出的東西。</p></div>

<div class="panel gold"><h2 style="margin-top:0">2. LLM Wiki 成果</h2>
<div class="stats"><div class="stat"><div class="k">生存指南</div><div class="v">{W['guides']} 篇</div></div><div class="stat"><div class="k">生物圖鑑</div><div class="v">{W['mobs']} 種</div></div>
<div class="stat"><div class="k">物品圖鑑</div><div class="v">{W['items']} 種</div></div><div class="stat"><div class="k">手寫雙向關係</div><div class="v">{W['relations']} 組</div></div>
<div class="stat"><div class="k">自動關係（掉落＋合成）</div><div class="v">{W['drop_links'] + W['recipe_links']} 條</div></div><div class="stat"><div class="k">Ingest 來源</div><div class="v">{report['ingest']['round1'] + report['ingest']['round2']} 個</div></div></div>
<div class="grid g3"><a class="mcbtn" href="index.html">Wiki 首頁</a><a class="mcbtn" href="{href('early', B)}">前期</a><a class="mcbtn" href="{href('mid', B)}">中期</a>
<a class="mcbtn" href="{href('late', B)}">後期</a><a class="mcbtn" href="{href('mobs', B)}">生物圖鑑</a><a class="mcbtn" href="{href('items', B)}">物品圖鑑</a></div>
<p style="font-size:14px;color:#bbb">每個條目都是獨立的 HTML 頁面（共 {report.get('generate', {}).get('wiki_pages', '')} 個 Wiki 頁），不是 Markdown 檔。</p></div>

<div class="panel purple"><h2 style="margin-top:0">3. 教學 HTML 簡報</h2><p>{W['slides']} 頁，五個章節對應 Wiki 五大項。每一頁的內容都從 Wiki 資料產生，下方有「📖 對應 Wiki」按鈕可跳到來源頁。</p>
<a class="mcbtn" style="max-width:420px" href="slides.html">▶ 開啟教學簡報</a></div>

<div class="panel"><h2 style="margin-top:0">「先討論、後生成」：需求討論紀錄</h2><p>在生成任何內容之前，先把需求轉成資料結構的決定：</p>
<table class="mc"><tr><th style="width:34%">討論到的需求</th><th>轉成的設計決定</th></tr>{disc}</table></div>

<div class="panel"><h2 style="margin-top:0">4. Loop / Graph 設計</h2>{graph_svg()}{loop}</div>

<div class="panel"><h2 style="margin-top:0">5. 實際執行結果與檢查紀錄</h2>
<p>下表由建置程式自動寫入（<code>runs/run_NNN.json</code>），每次執行一列。前置檢查有 <strong>error</strong> 時流程會停止、不產生任何頁面。</p>
<table class="mc" style="font-size:15px"><tr><th>次</th><th>時間</th><th>這次改了什麼</th><th>error</th><th>warn</th><th>問題分類</th><th>斷鏈</th><th>結果</th></tr>{rows}</table>
{sample}
<h3>最後一次執行仍保留的 warn（節錄）</h3><ul style="font-size:14px">{li_last}</ul>
<h3>人工檢視（截圖）發現的問題</h3><table class="mc"><tr><th>發現於</th><th>問題</th><th>處理方式</th></tr>{man}</table>
<h3>Ingest 紀錄（共 {len(SOURCES)} 個來源）</h3><p style="font-size:14px">第 1 輪＝前一版半成品已整理的 Minecraft Wiki 頁面；第 2 輪＝本次為了補齊生物／物品數值與 26.x 版本差異所新增的來源。</p>
<table class="mc" style="font-size:14px"><tr><th>編號</th><th>輪次</th><th>來源</th></tr>{src_rows}</table></div>

<div class="panel gold"><h2 style="margin-top:0">6. 反思</h2>{refl}</div>"""
    return page("作業流程與反思", body, B, theme="home", active="process")
