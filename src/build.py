# -*- coding: utf-8 -*-
"""LLM Wiki → 教學簡報 建置流程（graph 的程式化版本）

  [INGEST]  讀入 SOURCES（第 1 輪＋第 2 輪）
  [WIKI]    讀入 GUIDES / MOBS / ITEMS / RELATIONS，建立索引與雙向關係
  [CHECK]   前置檢查：連結、必填欄位、列舉值、來源、單向連結、孤島、投影片覆蓋率
            → 有 error 就停止（回到 WIKI 修正後重跑），只有 warn 才繼續
  [GENERATE] 產生每個 Wiki 頁面、圖鑑索引、簡報、流程頁
  [POST-CHECK] 掃描所有輸出 HTML 的本地連結是否存在
  每次執行都寫一份 runs/run_NNN.json 作為執行紀錄。
"""
import os, re, sys, json, glob, time, math, html as H
from collections import defaultdict

SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
from data_mobs import MOBS
from data_items import ITEMS
from data_guides import GUIDES, ORE_LEVELS
from data_links import RELATIONS, SOURCES, PAGE_SOURCES, DEFAULT_MOB_SOURCES, DEFAULT_ITEM_SOURCES
from data_slides import SLIDES, CHAPTERS
import icons

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC, "..", "site")
RUNS = os.path.join(SRC, "..", "runs")
NOTE = sys.argv[2] if len(sys.argv) > 2 else ""
os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.join(OUT, "wiki"), exist_ok=True); os.makedirs(RUNS, exist_ok=True)

STAGES = {"early": ("前期", "生存基礎：工具、鐵與金、基礎怪物", "early"), "mid": ("中期", "裝備、農場、村民交易與下界", "mid"),
          "late": ("後期", "終界之眼、要塞、終界龍", "late")}
HUBS = {"early": "前期生存指南", "mid": "中期生存指南", "late": "後期生存指南", "mobs": "生物圖鑑", "items": "物品圖鑑", "process": "作業流程與反思"}
STRENGTH = {1: "無害", 2: "低", 3: "中", 4: "高", 5: "極高／頭目"}
RARITY = ["常見", "普通", "稀少", "稀有", "極稀有"]
KINDS = ["被動", "中立", "敵對", "頭目"]

# ═══════════════ [WIKI] 建立索引 ═══════════════
ENT = {}
for g in GUIDES: g["type"] = "guide"; ENT[g["id"]] = g
for m in MOBS: m["type"] = "mob"; ENT[m["id"]] = m
for i in ITEMS: i["type"] = "item"; ENT[i["id"]] = i
for h, n in HUBS.items(): ENT[h] = dict(id=h, type="hub", name=n)
LINK_RE = re.compile(r"\[\[([a-z0-9_]+)(?:\|([^\]]+))?\]\]")


def texts_of(e):
    """一個條目中所有可能含 [[連結]] 的文字。"""
    out = []
    for k in ("traits", "counter", "spawn", "obtain", "goal"):
        if e.get(k): out.append(e[k])
    for s in e.get("sections", []): out.append(s[1])
    out += e.get("tips", []) + e.get("checklist", [])
    for d in e.get("drops", []): out.append(d[2])
    return out


def links_in(text):
    return [m.group(1) for m in LINK_RE.finditer(text or "")]


# 雙向關係
REL = defaultdict(list)            # id -> [(other, text)]
REL_PAIRS = set()
for a, b, ta, tb in RELATIONS:
    REL[a].append((b, ta)); REL[b].append((a, tb)); REL_PAIRS.add(frozenset((a, b)))
DROPS_BY_ITEM = defaultdict(list)  # item -> [(mob, qty, note)]
for m in MOBS:
    for iid, qty, note in m.get("drops", []):
        if iid: DROPS_BY_ITEM[iid].append((m["id"], qty, note))
USED_IN = defaultdict(list)        # 材料 -> [(產物, 數量)]
for i in ITEMS:
    for iid, q in i.get("recipe", []):
        if iid: USED_IN[iid].append((i["id"], q))
MENTIONS = defaultdict(list)       # 被提到的 id -> [(來源條目, 句子)]
for e in list(GUIDES) + MOBS + ITEMS:
    for t in texts_of(e):
        for sent in re.split(r"(?<=[。！？])|<br>", t):
            for tid in set(links_in(sent)):
                if tid != e["id"]: MENTIONS[tid].append((e["id"], sent.strip()))
SLIDE_REFS = defaultdict(list)     # wiki id -> [slide index]


def slide_links(s):
    ids = list(s.get("wiki", []))
    for k in ("title", "lead", "note", "sub"):
        ids += links_in(s.get(k, ""))
    for b in s.get("bullets", []) + s.get("items", []) + s.get("points", []): ids += links_in(b)
    for st in s.get("steps", []): ids += links_in(st[0]) + links_in(st[1])
    for r in s.get("rows", []):
        for c in r: ids += links_in(c)
    ids += s.get("ids", [])
    return ids


for n, s in enumerate(SLIDES, 1):
    for wid in dict.fromkeys(slide_links(s)):
        SLIDE_REFS[wid].append(n)

# ═══════════════ [CHECK] 前置檢查 ═══════════════
issues = []
def err(code, where, msg): issues.append(dict(level="error", code=code, where=where, msg=msg))
def warn(code, where, msg): issues.append(dict(level="warn", code=code, where=where, msg=msg))

# C1 連結目標存在
for e in list(GUIDES) + MOBS + ITEMS:
    for t in texts_of(e):
        for tid in links_in(t):
            if tid not in ENT: err("C1-斷鏈", e["id"], f"[[{tid}]] 不存在")
for a, b, *_ in RELATIONS:
    for x in (a, b):
        if x not in ENT: err("C1-斷鏈", "RELATIONS", f"{x} 不存在")
# C2 掉落／配方 id
for m in MOBS:
    for iid, *_ in m.get("drops", []):
        if iid and iid not in ENT: err("C2-掉落物不存在", m["id"], iid)
for i in ITEMS:
    for iid, _ in i.get("recipe", []):
        if iid and iid not in ENT: err("C2-配方材料不存在", i["id"], iid)
# C3 必填欄位 ＋ C7 列舉值
for m in MOBS:
    for k in ("name", "kind", "dim", "hp", "dmg", "xp", "spawn", "traits", "counter", "strength"):
        if m.get(k) in (None, ""): err("C3-缺欄位", m["id"], k)
    if m.get("kind") not in KINDS: err("C7-列舉值", m["id"], f"kind={m.get('kind')}")
    if m.get("strength") not in (1, 2, 3, 4, 5): err("C7-列舉值", m["id"], f"strength={m.get('strength')}")
for i in ITEMS:
    for k in ("name", "obtain", "traits", "rarity", "diff", "icon", "cat"):
        if i.get(k) in (None, ""): err("C3-缺欄位", i["id"], k)
    if i.get("rarity") not in RARITY: err("C7-列舉值", i["id"], f"rarity={i.get('rarity')}")
    if i.get("diff") not in (1, 2, 3, 4, 5): err("C7-列舉值", i["id"], f"diff={i.get('diff')}")
    if i.get("icon", ("",))[0] not in icons.T: warn("C7-圖示樣板", i["id"], f"icon={i.get('icon')}")
for g in GUIDES:
    for k in ("name", "stage", "goal", "sections", "sources"):
        if not g.get(k): err("C3-缺欄位", g["id"], k)
# C5 來源
for g in GUIDES:
    for s in g.get("sources", []):
        if s not in SOURCES: err("C5-來源不存在", g["id"], s)
for k, v in PAGE_SOURCES.items():
    if k not in ENT: err("C5-來源對應到不存在的頁面", k, "")
    for s in v:
        if s not in SOURCES: err("C5-來源不存在", k, s)
# C4 單向連結：A 的內文提到 B（都是生物或物品），但 B 沒有任何地方說明與 A 的關係
def covered(a, b):
    if frozenset((a, b)) in REL_PAIRS: return True
    if any(x[0] == a for x in DROPS_BY_ITEM.get(b, [])) or any(x[0] == b for x in DROPS_BY_ITEM.get(a, [])): return True
    if any(x[0] == a for x in USED_IN.get(b, [])) or any(x[0] == b for x in USED_IN.get(a, [])): return True
    return any(b in links_in(t) for t in texts_of(ENT[a])) and any(a in links_in(t) for t in texts_of(ENT[b]))
UNIDIR = []
for e in MOBS + ITEMS:
    for t in texts_of(e):
        for tid in set(links_in(t)):
            if tid in ENT and ENT[tid]["type"] in ("mob", "item") and not covered(e["id"], tid):
                UNIDIR.append((e["id"], tid))
for a, b in sorted(set(UNIDIR)):
    if {ENT[a]["type"], ENT[b]["type"]} == {"mob", "item"}:  # 第 2 次執行起：生物↔物品的單向連結升級為 error
        err("C4-生物物品單向", a, f"{ENT[a]['name']} 提到 {ENT[b]['name']}，但兩邊沒有雙向關係說明（請在 RELATIONS 補上兩段說明）")
    else:
        warn("C4-單向連結", a, f"{ENT[a]['name']} 提到 {ENT[b]['name']}，但 {ENT[b]['name']} 頁面沒有對應說明（將自動產生反向引用）")
# C4b 孤島：生物沒有連到任何物品；物品沒有連到任何生物或攻略
for m in MOBS:
    if not any(ENT.get(o, {}).get("type") == "item" for o, _ in REL[m["id"]]) and not any(d[0] for d in m.get("drops", [])):
        warn("C4-孤島", m["id"], f"{m['name']} 沒有連到任何物品")
for i in ITEMS:
    linked = DROPS_BY_ITEM.get(i["id"]) or REL.get(i["id"]) or any(ENT[s]["type"] == "guide" for s, _ in MENTIONS.get(i["id"], []))
    if not linked: warn("C4-孤島", i["id"], f"{i['name']} 沒有連到任何生物、關係或攻略")
# C6 投影片
for n, s in enumerate(SLIDES, 1):
    refs = slide_links(s)
    if s["layout"] != "cover" and not s.get("wiki"): err("C6-投影片無 Wiki 依據", f"slide {n}", s["title"])
    for r in refs:
        if r not in ENT: err("C6-投影片斷鏈", f"slide {n}", r)
for g in GUIDES:
    if not SLIDE_REFS.get(g["id"]): warn("C6-指南未被簡報涵蓋", g["id"], g["name"])
# C8 重複關係
seen = set()
for a, b, *_ in RELATIONS:
    k = frozenset((a, b))
    if k in seen: warn("C8-重複關係", f"{a}↔{b}", "同一組關係出現兩次")
    seen.add(k)

errors = [x for x in issues if x["level"] == "error"]
warns = [x for x in issues if x["level"] == "warn"]
run_no = len(glob.glob(os.path.join(RUNS, "run_*.json"))) + 1
report = dict(run=run_no, time=time.strftime("%Y-%m-%d %H:%M:%S"), note=NOTE,
              ingest=dict(round1=sum(1 for v in SOURCES.values() if v[2] == 1), round2=sum(1 for v in SOURCES.values() if v[2] == 2)),
              wiki=dict(guides=len(GUIDES), mobs=len(MOBS), items=len(ITEMS), relations=len(RELATIONS),
                        drop_links=sum(len(v) for v in DROPS_BY_ITEM.values()), recipe_links=sum(len(v) for v in USED_IN.values()), slides=len(SLIDES)),
              check=dict(errors=len(errors), warns=len(warns),
                         by_code={c: sum(1 for x in issues if x["code"] == c) for c in sorted({x["code"] for x in issues})},
                         samples=issues[:60]))


def save_report():
    with open(os.path.join(RUNS, f"run_{run_no:03d}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


print(f"[CHECK] run {run_no}: {len(errors)} errors, {len(warns)} warnings")
for x in issues[:400]:
    print(f"  {x['level']:5} {x['code']:14} {x['where']:18} {x['msg']}")
if errors:
    report["result"] = "STOP：前置檢查有 error，未產生頁面（回到 Wiki 修正）"
    save_report(); print(report["result"]); sys.exit(1)

# ═══════════════ [GENERATE] ═══════════════
def href(tid, base):
    p = "" if base == "root" else "../"
    if tid in ("index", "slides", "process"): return f"{p}{tid}.html"
    return f"{'wiki/' if base == 'root' else ''}{tid}.html"


def md(text, base, newtab=False):
    if not text: return ""
    def rep(m):
        tid, label = m.group(1), m.group(2)
        e = ENT.get(tid)
        label = label or (e["name"] if e else tid)
        tgt = ' target="_blank"' if newtab else ""
        return f'<a class="wl wl-{e["type"] if e else "x"}" href="{href(tid, base)}"{tgt}>{label}</a>'
    t = LINK_RE.sub(rep, text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)


def plain(text):
    t = LINK_RE.sub(lambda m: m.group(2) or ENT.get(m.group(1), {}).get("name", m.group(1)), text or "")
    return re.sub(r"<[^>]+>|\*\*", "", t)


def item_icon(iid, size=36):
    i = ENT[iid]; tpl, col = i["icon"]
    return icons.svg(tpl, col, size, i["name"])


def slot(iid, base, n="", newtab=False):
    tgt = ' target="_blank"' if newtab else ""
    return f'<a class="slot" href="{href(iid, base)}" title="{ENT[iid]["name"]}"{tgt}>{item_icon(iid)}<span class="n">{n}</span></a>'


def hpnum(hp):
    m = re.search(r"\d+", str(hp)); return int(m.group()) if m else 0


def hearts(hp, cap=10):
    n = hpnum(hp); h = n / 2; out = []
    full = int(min(h, cap)); half = (h - int(h)) >= .5 and h < cap
    out += [icons.heart("full")] * full
    if half: out.append(icons.heart("half"))
    extra = f' <span style="font-size:13px">×{h/cap:.0f}</span>' if h > cap else ""
    return f'<span class="hearts">{"".join(out)}{extra}</span>'


def picks(n, total=5, size=18):
    on = icons.svg("pickaxe", "#9aa3ad", size)
    off = on.replace('class="px"', 'class="px off" style="opacity:.25"')
    return f'<span class="picks" title="取得難度 {n}/5">{on * n}{off * (total - n)}</span>'


def stars(n, total=5):
    return f'<span class="stars">{"★" * n}<span class="off">{"★" * (total - n)}</span></span>'


def avatar(m, big=False):
    dim = m["dim"]; dd = "mix" if "／" in dim else dim
    return f'<span class="avatar av-{m["kind"]}{" big" if big else ""}" title="{m["name"]}">{m["name"][0]}<span class="dimdot dd-{dd}"></span></span>'


def mob_card(m, base, newtab=False, compact=False):
    tgt = ' target="_blank"' if newtab else ""
    drops = "".join(item_icon(d[0], 20) for d in m["drops"] if d[0])
    extra = "" if compact else f'<div class="d">{plain(m["traits"])[:46]}…</div>'
    return (f'<a class="card mob-card" href="{href(m["id"], base)}"{tgt} data-dim="{m["dim"]}" data-kind="{m["kind"]}" data-s="{m["strength"]}">{avatar(m)}'
            f'<div><div class="t">{m["name"]} <span class="tag k-{m["kind"]}">{m["kind"]}</span></div>'
            f'<div class="d">{stars(m["strength"])}</div><div class="d" style="white-space:nowrap">❤ {hpnum(m["hp"])}　<span class="xp">XP {m["xp"].split("（")[0].split("；")[0]}</span></div>'
            f'<div>{drops}</div>{extra}</div></a>')


def item_card(i, base, newtab=False):
    tgt = ' target="_blank"' if newtab else ""
    return (f'<a class="card item-card" href="{href(i["id"], base)}"{tgt} data-cat="{i["cat"]}" data-r="{i["rarity"]}">'
            f'<span class="slot">{item_icon(i["id"])}</span><div><div class="t">{i["name"]}</div>'
            f'<div><span class="tag r-{i["rarity"]}">{i["rarity"]}</span> {picks(i["diff"], size=16)}</div>'
            f'<div class="d">{plain(i["traits"])[:40]}…</div></div></a>')


NAV = [("index", "首頁"), ("slides", "教學簡報"), ("early", "前期"), ("mid", "中期"), ("late", "後期"), ("mobs", "生物圖鑑"), ("items", "物品圖鑑"), ("process", "流程與反思")]


def page(title, body, base, theme="home", active=None, js=""):
    p = "" if base == "root" else "../"
    nav = "".join(f'<a class="navbtn{" on" if k == active else ""}" href="{href(k, base)}">{n}</a>' for k, n in NAV)
    logo = icons.svg("block", "#5d9b3a", 26)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}｜Minecraft 生存指南 Wiki</title><link rel="stylesheet" href="{p}assets/style.css"></head>
<body class="t-{theme}"><header class="topbar"><div class="in"><a class="brand" href="{href('index', base)}">{logo}生存指南 Wiki</a>{nav}
<div class="search"><input id="q" placeholder="搜尋生物、物品…" autocomplete="off"><div class="res" id="qres"></div></div></div></header>
<main class="wrap">{body}</main>
<a class="mcbtn backtoslide" id="back2slide" href="{p}slides.html">◀ 回到簡報</a>
<script>window.MC_BASE="{p}";</script><script src="{p}assets/site.js"></script>{js}</body></html>"""


def sources_block(ids, base):
    li = "".join(f'<li><span class="round-tag">第{SOURCES[s][2]}輪</span><a href="{SOURCES[s][1]}" target="_blank" rel="noopener">[{s}] {SOURCES[s][0]}</a></li>' for s in ids)
    return f'<div class="panel"><h3>資料來源</h3><ul class="src">{li}</ul><p style="font-size:13px;color:#aaa">數值以 Java 版 26.x、普通難度為準；Bedrock 版與舊版本可能不同。</p></div>'


def slide_refs_block(eid, base):
    refs = SLIDE_REFS.get(eid, [])
    if not refs: return ""
    p = "" if base == "root" else "../"
    a = "".join(f'<a href="{p}slides.html#s{n}">第 {n} 頁：{plain(SLIDES[n-1]["title"])}</a>' for n in refs)
    return f'<div class="panel purple slideref"><h3>對應的簡報頁</h3>{a}</div>'


def rel_block(eid, base):
    rows = []
    for o, t in REL.get(eid, []):
        oe = ENT[o]
        ic = avatar(oe) if oe["type"] == "mob" else (f'<span class="slot">{item_icon(o)}</span>' if oe["type"] == "item" else "")
        kind = {"mob": "生物圖鑑", "item": "物品圖鑑", "guide": "生存指南"}.get(oe["type"], "")
        rows.append(f'<div class="rel">{ic}<div><div class="rk">{kind} ↔</div><div class="rt"><a href="{href(o, base)}">{oe["name"]}</a></div><p>{md(t, base)}</p></div></div>')
    if not rows: return ""
    return f'<div class="panel gold"><h2 style="margin-top:0">與其他條目的關係</h2><p style="color:#bbb;font-size:14px">每一組關係在雙方頁面都有各自的說明，點名稱可以跳到對方頁面。</p>{"".join(rows)}</div>'


def backlinks_block(eid, base):
    """其他生物／物品頁提到這裡（自動反向引用，處理 C4 單向連結）"""
    rows, seen = [], set()
    for src, sent in MENTIONS.get(eid, []):
        se = ENT[src]
        if se["type"] not in ("mob", "item") or src in seen: continue
        if frozenset((src, eid)) in REL_PAIRS: continue
        if any(x[0] == src for x in DROPS_BY_ITEM.get(eid, [])) or any(x[0] == eid for x in DROPS_BY_ITEM.get(src, [])): continue  # 已在掉落表
        if any(x[0] == src for x in USED_IN.get(eid, [])) or any(x[0] == eid for x in USED_IN.get(src, [])): continue  # 已在配方
        seen.add(src)
        rows.append(f'<li><a href="{href(src, base)}">{se["name"]}</a>：「{plain(sent)[:90]}」</li>')
    if not rows: return ""
    return f'<div class="panel"><h3>其他圖鑑頁提到這裡</h3><ul>{"".join(rows)}</ul></div>'


def guides_block(eid, base):
    gs = list(dict.fromkeys(s for s, _ in MENTIONS.get(eid, []) if ENT[s]["type"] == "guide"))
    if not gs: return ""
    a = "".join(f'<a class="card" href="{href(g, base)}"><span class="tag s-{ENT[g]["stage"]}">{STAGES[ENT[g]["stage"]][0]}</span><div class="t" style="font-size:16px">{ENT[g]["name"]}</div></a>' for g in gs)
    return f'<div class="panel green"><h3>出現在這些生存指南</h3><div class="grid g3">{a}</div></div>'


def tips_block(e, base):
    if not e.get("tips"): return ""
    return '<div class="panel"><h3>小技巧</h3><ul>' + "".join(f"<li>{md(t, base)}</li>" for t in e["tips"]) + "</ul></div>"


# ───── 共用圖解（Wiki 與簡報都用同一份，確保內容一致） ─────
def ore_chart(base, newtab=False, gap=92, bw=74, Hh=400):
    lo, hi = -64, 320
    y = lambda v: (hi - v) / (hi - lo) * Hh
    marks = "".join(f'<div class="yl" style="top:{y(v):.0f}px">Y {v}</div>' for v in (320, 232, 128, 63, 16, -59))
    bars = []
    for k, (nm, iid, col, a, b, peaks, note) in enumerate(ORE_LEVELS):
        x = 20 + k * gap
        lab = f'<a href="{href(iid, base)}"{" target=_blank" if newtab else ""}>{nm}</a>' if iid else nm
        pk = "".join(f'<div class="peak" style="top:{y(p) - y(b):.0f}px" title="高峰 Y={p}"></div>' for p in peaks)
        bars.append(f'<div class="bar" style="left:{x}px;width:{bw}px;top:{y(b):.0f}px;height:{y(a) - y(b):.0f}px;background:{col}" title="{nm} Y {a}~{b} {note}"><span class="lab">{lab}</span>{pk}</div>')
    return f'<div class="ore" style="height:{Hh}px">{marks}{"".join(bars)}</div><p style="font-size:13px;color:#ccc">白色橫條＝最常見高度。海平面 Y=63。</p>'


def portal_diagram():
    cells = []
    for r in range(5):
        for c in range(4):
            corner = (r in (0, 4)) and (c in (0, 3))
            frame = r in (0, 4) or c in (0, 3)
            cls = "corner" if corner else ("obs" if frame else "fire")
            cells.append(f'<div class="pc {cls}"></div>')
    return f'<div class="portal-grid">{"".join(cells)}</div>'


def altar_diagram():
    cells = []
    eyes = {(0, 1), (1, 4), (4, 2), (3, 0)}
    for r in range(5):
        for c in range(5):
            corner = (r in (0, 4)) and (c in (0, 4))
            ring = (r in (0, 4) or c in (0, 4)) and not corner
            cls = "air" if corner else ("frame" + (" eye" if (r, c) in eyes else "") if ring else "lava")
            cells.append(f'<div class="ac {cls}"></div>')
    return f'<div class="altar-grid">{"".join(cells)}</div>'


def pillars_svg():
    out = ['<svg viewBox="0 0 300 300" width="300" height="300" class="pillars">', '<circle cx="150" cy="150" r="140" fill="#dcdca0" stroke="#000" stroke-width="3"/>',
           '<rect x="135" y="135" width="30" height="30" fill="#222" stroke="#000"/><text x="150" y="190" text-anchor="middle" font-size="11" fill="#333">出口傳送門</text>']
    for k in range(10):
        a = k / 10 * 2 * math.pi; x = 150 + 100 * math.cos(a); y = 150 + 100 * math.sin(a); r = 10 + (k * 7 % 5) * 2
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#2a1740" stroke="#000" stroke-width="2"/><circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="#ff7af0"/>')
        if k in (2, 6): out.append(f'<rect x="{x - r - 3:.0f}" y="{y - r - 3:.0f}" width="{2 * r + 6}" height="{2 * r + 6}" fill="none" stroke="#bbb" stroke-width="2" stroke-dasharray="3 2"/>')
    out.append("</svg>")
    return "".join(out)


DIAGRAM_CSS = """
.portal-grid{display:grid;grid-template-columns:repeat(4,46px);gap:0;border:0}
.pc{width:46px;height:46px;border:1px solid rgba(0,0,0,.4)}
.pc.obs{background:url(TEX/tex_obsidian.png);background-size:46px}
.pc.corner{background:repeating-linear-gradient(45deg,#2a1740 0 4px,transparent 4px 9px);opacity:.55;border:2px dashed #aaa}
.pc.fire{background:linear-gradient(135deg,#7b2fbf,#c15cff,#5a1c99);animation:pf 1.4s infinite alternate}
@keyframes pf{to{filter:brightness(1.3)}}
.altar-grid{display:grid;grid-template-columns:repeat(5,46px)}
.ac{width:46px;height:46px;border:1px solid rgba(0,0,0,.5)}
.ac.frame{background:#2f6b57;box-shadow:inset 0 0 0 6px #d8d4a8}
.ac.frame.eye::after{content:"";display:block;margin:13px;width:20px;height:20px;background:#3fb58f;border:2px solid #0f3b2e}
.ac.lava{background:linear-gradient(135deg,#ff7a00,#ffb400,#e04a00)}
.ac.air{background:transparent}
"""


# ───── Guide 頁 ─────
STAGE_ICON = {"early": ("block", "#5d9b3a"), "mid": ("pickaxe", "#d8d8d8"), "late": ("eye", "#3fb58f")}


def render_guide(g):
    base = "wiki"; st = g["stage"]
    same = [x for x in GUIDES if x["stage"] == st]; k = same.index(g)
    secs = "".join(f'<div class="panel"><h2 style="margin-top:0">{h}</h2><p>{md(t, base)}</p></div>' for h, t in g["sections"])
    special = ""
    if g["id"] == "e3_mining": special = f'<div class="panel"><h2 style="margin-top:0">礦石高度圖</h2>{ore_chart(base)}</div>'
    if g["id"] == "m4_portal": special = f'<div class="panel purple"><h2 style="margin-top:0">傳送門框示意（外框 4×5）</h2><div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">{portal_diagram()}<p>深紫色＝黑曜石（10 塊）；虛線角落＝可省略；中間 2×3 為傳送門。<br>用[[flint_and_steel|打火石]]點燃內側即可啟動。</p></div></div>'
    if g["id"] == "l2_stronghold": special = f'<div class="panel purple"><h2 style="margin-top:0">終界傳送門（俯視圖）</h2><div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">{altar_diagram()}<p>12 個框架圍住 3×3 的岩漿池。<br>綠色方塊＝已放入終界之眼。<br>全部放滿就會啟動。</p></div></div>'
    if g["id"] == "l4_dragon": special = f'<div class="panel purple"><h2 style="margin-top:0">終界主島俯視</h2><div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">{pillars_svg()}<p>10 根黑曜石柱，粉紅點＝終界水晶；<br>虛線方框＝被鐵欄杆包住的 2 顆。</p></div></div>'
    special = md(special, base)
    chk = "".join(f'<li><input type="checkbox" data-k="{g["id"]}-{n}"><span>{md(c, base)}</span></li>' for n, c in enumerate(g.get("checklist", [])))
    linked = list(dict.fromkeys(t for s in g["sections"] for t in links_in(s[1])))
    mobs = "".join(mob_card(ENT[x], base, compact=True) for x in linked if ENT.get(x, {}).get("type") == "mob")
    items = "".join(f'<span style="display:inline-block;margin:3px">{slot(x, base)}</span>' for x in linked if ENT.get(x, {}).get("type") == "item")
    prev = f'<a class="mcbtn" href="{href(same[k-1]["id"], base)}">◀ {same[k-1]["name"]}</a>' if k > 0 else f'<a class="mcbtn" href="{href(st, base)}">◀ {STAGES[st][0]}目錄</a>'
    nxt_stage = {"early": "mid", "mid": "late", "late": "mobs"}[st]
    nxt = f'<a class="mcbtn" href="{href(same[k+1]["id"], base)}">{same[k+1]["name"]} ▶</a>' if k < len(same) - 1 else f'<a class="mcbtn" href="{href(nxt_stage, base)}">前往 {ENT[nxt_stage]["name"]} ▶</a>'
    tpl, col = STAGE_ICON[st]
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › <a href="{href(st, base)}">{HUBS[st]}</a> › {g['name']}</div>
<div class="panel green"><div class="hero"><div class="big-icon">{icons.svg(tpl, col, 96)}</div><div>
<span class="tag s-{st}">{STAGES[st][0]} {k+1}/{len(same)}</span><span class="tag cat">{g['en']}</span><h1>{g['name']}</h1>
<div class="goal"><span class="xp">學習目標</span>｜{md(g['goal'], base)}</div></div></div></div>
{secs}{special}
<div class="grid g2"><div class="gui"><h3>過關清單（勾選會記在這台電腦）</h3><ul class="check">{chk}</ul></div>
<div class="panel"><h3>本篇提到的生物</h3><div class="grid g2">{mobs or '<p style="color:#aaa">—</p>'}</div><h3>本篇提到的物品</h3><div>{items}</div></div></div>
{slide_refs_block(g['id'], base)}{sources_block(g['sources'], base)}
<div class="grid g2">{prev}{nxt}</div>"""
    return page(g["name"], body, base, theme=st, active=st)


# ───── 生物頁 ─────
def render_mob(m):
    base = "wiki"
    def drow(i, q, n):
        if i:
            return f'<tr><td>{slot(i, base)}</td><td><a href="{href(i, base)}">{ENT[i]["name"]}</a></td><td>{q}</td><td>{md(n, base)}</td></tr>'
        return f'<tr><td></td><td>{q}</td><td></td><td>{md(n, base)}</td></tr>'
    drops = "".join(drow(*d) for d in m["drops"])
    drops_t = f'<table class="mc"><tr><th style="width:70px"></th><th>掉落物</th><th>數量</th><th>備註</th></tr>{drops}</table>' if m["drops"] else '<p>不會掉落物品。</p>'
    srcs = PAGE_SOURCES.get(m["id"], DEFAULT_MOB_SOURCES)
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › <a href="{href('mobs', base)}">生物圖鑑</a> › {m['name']}</div>
<div class="panel red"><div class="hero">{avatar(m, big=True)}<div><h1>{m['name']} <span style="font-size:20px;color:#bbb">{m['en']}</span></h1>
<span class="tag k-{m['kind']}">{m['kind']}生物</span><span class="tag dim">{m['dim']}</span>
<div style="margin-top:6px">威脅等級 {stars(m['strength'])} <span style="color:#ddd">{STRENGTH[m['strength']]}</span></div></div></div>
<div class="stats"><div class="stat"><div class="k">生命值</div><div class="v">{m['hp']}</div>{hearts(m['hp'])}</div>
<div class="stat"><div class="k">攻擊傷害（簡單／普通／困難）</div><div class="v" style="font-size:15px">{m['dmg']}</div></div>
<div class="stat"><div class="k">經驗值</div><div class="v xp">{m['xp']}</div></div>
<div class="stat"><div class="k">威脅等級</div><div class="v">{m['strength']} / 5</div></div></div>
<div class="stat"><div class="k">在哪裡生成</div><div>{md(m['spawn'], base)}</div></div></div>
<div class="grid g2"><div class="panel"><h2 style="margin-top:0">特性</h2><p>{md(m['traits'], base)}</p></div>
<div class="panel green"><h2 style="margin-top:0">應對方式</h2><p>{md(m['counter'], base)}</p></div></div>
<div class="panel"><h2 style="margin-top:0">掉落物</h2>{drops_t}</div>
{rel_block(m['id'], base)}{backlinks_block(m['id'], base)}{guides_block(m['id'], base)}{tips_block(m, base)}
{slide_refs_block(m['id'], base)}{sources_block(srcs, base)}"""
    return page(m["name"], body, base, theme="mob", active="mobs")


# ───── 物品頁 ─────
def render_item(i):
    base = "wiki"
    recipe = ""
    if i.get("recipe"):
        ing = "".join(slot(x, base, q) for x, q in i["recipe"] if x)
        recipe = f'<div class="panel"><h3>合成材料</h3><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">{ing}<span style="font-size:28px">➜</span><span class="slot">{item_icon(i["id"])}</span></div><p style="font-size:14px;color:#bbb">完整配方見「如何取得」的說明（圖中只列出 Wiki 內有頁面的材料）。</p></div>'
    used = USED_IN.get(i["id"], [])
    used_b = f'<div class="panel gold"><h3>可以用來製作</h3><div class="grid g3">{"".join(item_card(ENT[p], base) for p, _ in used)}</div></div>' if used else ""
    src_m = DROPS_BY_ITEM.get(i["id"], [])
    drop_b = ""
    if src_m:
        rows = "".join(f'<tr><td>{avatar(ENT[mid])}</td><td><a href="{href(mid, base)}">{ENT[mid]["name"]}</a><br><span class="tag k-{ENT[mid]["kind"]}">{ENT[mid]["kind"]}</span> {stars(ENT[mid]["strength"])}</td><td>{q}</td><td>{md(n, base)}</td></tr>' for mid, q, n in src_m)
        drop_b = f'<div class="panel red"><h3>掉落來源（生物圖鑑）</h3><table class="mc"><tr><th style="width:74px"></th><th>生物</th><th>數量</th><th>備註</th></tr>{rows}</table></div>'
    srcs = PAGE_SOURCES.get(i["id"], DEFAULT_ITEM_SOURCES)
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › <a href="{href('items', base)}">物品圖鑑</a> › {i['name']}</div>
<div class="panel gold"><div class="hero"><div class="big-icon">{icons.svg(i['icon'][0], i['icon'][1], 96)}</div><div>
<h1>{i['name']} <span style="font-size:20px;color:#bbb">{i['en']}</span></h1><span class="tag cat">{i['cat']}</span><span class="tag r-{i['rarity']}">{i['rarity']}</span></div></div>
<div class="stats"><div class="stat"><div class="k">稀缺程度</div><div class="v">{i['rarity']}（{RARITY.index(i['rarity'])+1}/5）</div></div>
<div class="stat"><div class="k">取得難度</div><div class="v">{picks(i['diff'], size=24)} {i['diff']}/5</div></div>
<div class="stat"><div class="k">分類</div><div class="v">{i['cat']}</div></div></div></div>
<div class="grid g2"><div class="panel"><h2 style="margin-top:0">如何取得</h2><p>{md(i['obtain'], base)}</p></div>
<div class="panel green"><h2 style="margin-top:0">特性與用途</h2><p>{md(i['traits'], base)}</p></div></div>
{recipe}{used_b}{drop_b}{rel_block(i['id'], base)}{backlinks_block(i['id'], base)}{guides_block(i['id'], base)}{tips_block(i, base)}
{slide_refs_block(i['id'], base)}{sources_block(srcs, base)}"""
    return page(i["name"], body, base, theme="item", active="items")


# ───── 索引頁 ─────
def render_stage_hub(st):
    base = "wiki"; gs = [g for g in GUIDES if g["stage"] == st]
    cards = "".join(f'<a class="card" href="{href(g["id"], base)}"><span class="slot" style="flex:none"><span style="font-size:24px;color:#fff;text-shadow:2px 2px 0 #3f3f3f">{n}</span></span><div><div class="t">{g["name"]}</div><div class="d">{plain(g["goal"])}</div></div></a>' for n, g in enumerate(gs, 1))
    intro = {"early": "以生存基礎為主：製作工具、取得鐵礦與黃金、應對殭屍與苦力怕等基礎怪物。完成這一階段，你就能穩定活過每個夜晚。",
             "mid": "提升裝備與生活品質：附魔、農場、村民交易，然後準備並進入「下界」——學會蓋傳送門、應對下界怪物，以及遇到突發狀況時如何自保。",
             "late": "準備進入「終界」：收集烈焰桿與終界珍珠做出終界之眼，找到要塞裡的終界祭壇，帶齊裝備後擊敗終界龍。"}[st]
    tpl, col = STAGE_ICON[st]
    nxt = {"early": "mid", "mid": "late", "late": "mobs"}[st]
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › {HUBS[st]}</div>
<div class="panel green"><div class="hero"><div class="big-icon">{icons.svg(tpl, col, 96)}</div><div><h1>{HUBS[st]}</h1><p>{intro}</p></div></div></div>
<div class="grid g2">{cards}</div><br>{slide_refs_block(st, base)}<a class="mcbtn" href="{href(nxt, base)}">下一部分：{HUBS[nxt]} ▶</a>"""
    return page(HUBS[st], body, base, theme=st, active=st)


def render_mob_hub():
    base = "wiki"
    ms = sorted(MOBS, key=lambda m: (m["strength"], hpnum(m["hp"])))
    cards = "".join(mob_card(m, base) for m in ms)
    legend = "".join(f'<span class="tag k-{k}">{k}</span>' for k in KINDS)
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › 生物圖鑑</div>
<div class="panel red"><h1>生物圖鑑</h1><p>共 {len(MOBS)} 種生物。每張卡片顯示：行為類型、威脅等級 ★1–5、生命值、經驗值與掉落物（點掉落物圖示可跳到物品圖鑑）。</p>
<p>類型：{legend}　頭像右下角色塊＝出現維度（綠：主世界、紅：下界、黃：終界）</p>
<p>威脅等級：{"　".join(f"{stars(k)} {v}" for k, v in STRENGTH.items())}</p></div>
<div class="filters" data-for="mob"><button class="on" data-f="all">全部</button><button data-f="dim:主世界">主世界</button><button data-f="dim:下界">下界</button><button data-f="dim:終界">終界</button>
<button data-f="kind:被動">被動</button><button data-f="kind:中立">中立</button><button data-f="kind:敵對">敵對</button><button data-f="kind:頭目">頭目</button></div>
<div class="grid g3" id="flist">{cards}</div>{slide_refs_block('mobs', base)}"""
    return page("生物圖鑑", body, base, theme="mob", active="mobs")


def render_item_hub():
    base = "wiki"
    cats = list(dict.fromkeys(i["cat"] for i in ITEMS))
    cards = "".join(item_card(i, base) for i in ITEMS)
    fb = "".join(f'<button data-f="cat:{c}">{c}</button>' for c in cats) + "".join(f'<button data-f="r:{r}">{r}</button>' for r in RARITY)
    body = f"""<div class="crumb"><a href="{href('index', base)}">首頁</a> › 物品圖鑑</div>
<div class="panel gold"><h1>物品圖鑑</h1><p>共 {len(ITEMS)} 種物品。每個物品標示<strong>稀缺程度</strong>（常見 → 極稀有）與<strong>取得難度</strong>（{picks(3, 3, 16)} 1–5 把鎬），頁面內有取得方式、可製作的東西、掉落來源生物與相關關係。</p>
<p>稀缺度：{"".join(f'<span class="tag r-{r}">{r}</span>' for r in RARITY)}</p></div>
<div class="filters" data-for="item"><button class="on" data-f="all">全部</button>{fb}</div>
<div class="grid g3" id="flist">{cards}</div>{slide_refs_block('items', base)}"""
    return page("物品圖鑑", body, base, theme="item", active="items")


def render_index():
    base = "root"
    demo_e = next(t for o, t in REL["emerald"] if o == "villager"); demo_v = next(t for o, t in REL["villager"] if o == "emerald")
    body = f"""<div class="panel green" style="text-align:center;padding:34px 20px">
<h1 style="font-size:clamp(34px,6vw,64px);color:#fff">Minecraft 生存指南</h1>
<p style="font-size:20px">LLM Wiki × 教學 HTML 簡報｜從第一天活下來，到擊敗終界龍</p>
<p style="color:#ccc">{len(GUIDES)} 篇生存指南・{len(MOBS)} 種生物・{len(ITEMS)} 種物品・{len(RELATIONS)} 組雙向關係・{len(SOURCES)} 個來源</p></div>
<div class="grid g3" style="max-width:980px;margin:0 auto 18px">
<a class="mcbtn" style="grid-column:1/-1;font-size:26px;padding:18px" href="slides.html">▶ 開始教學簡報<small>{len(SLIDES)} 頁・方向鍵翻頁・數字鍵 1–5 跳章節</small></a>
<a class="mcbtn" href="{href('early', base)}">{icons.svg('block', '#5d9b3a', 30)} 前期<small>工具・礦物・基礎怪物</small></a>
<a class="mcbtn" href="{href('mid', base)}">{icons.svg('pickaxe', '#d8d8d8', 30)} 中期<small>裝備・農場・下界</small></a>
<a class="mcbtn" href="{href('late', base)}">{icons.svg('eye', '#3fb58f', 30)} 後期<small>終界・終界龍</small></a>
<a class="mcbtn" href="{href('mobs', base)}">{icons.svg('sword', '#d8483b', 30)} 生物圖鑑<small>{len(MOBS)} 種・強度・掉落</small></a>
<a class="mcbtn" href="{href('items', base)}">{icons.svg('gem', '#4fd9e0', 30)} 物品圖鑑<small>{len(ITEMS)} 種・稀缺度・用途</small></a>
<a class="mcbtn" href="process.html">{icons.svg('book', '#8b4513', 30)} 流程與反思<small>loop / graph・執行紀錄</small></a></div>
<div class="panel gold" style="max-width:980px;margin:0 auto 18px"><h2 style="margin-top:0">Wiki 的「雙向關係」是什麼？</h2>
<p>每個生物與物品都不是孤立的頁面。例如：</p>
<div class="grid g2"><div class="rel"><span class="slot">{item_icon('emerald')}</span><div><div class="rk">在「綠寶石」頁</div><div class="rt"><a href="{href('emerald', base)}">綠寶石</a> → <a href="{href('villager', base)}">村民</a></div><p>{md(demo_e, base)}</p></div></div>
<div class="rel">{avatar(ENT['villager'])}<div><div class="rk">在「村民」頁</div><div class="rt"><a href="{href('villager', base)}">村民</a> → <a href="{href('emerald', base)}">綠寶石</a></div><p>{md(demo_v, base)}</p></div></div></div>
<p style="font-size:14px;color:#bbb">另外，生物的掉落物會自動出現在物品頁的「掉落來源」，物品的合成材料會自動出現在材料頁的「可以用來製作」。</p></div>
<div class="panel" style="max-width:980px;margin:0 auto"><h3>使用方式</h3><ul><li>電腦：簡報用 ← → 翻頁，按 1–5 直接跳到 前期／中期／後期／生物圖鑑／物品圖鑑。</li>
<li>簡報每一頁下方都有「📖 對應 Wiki」按鈕，點了會開啟該頁內容的 Wiki 來源頁；Wiki 頁右下角有「回到簡報」。</li>
<li>右上角搜尋框可以直接找任何生物或物品。</li></ul></div>"""
    return page("首頁", body, base, theme="home", active="index")


# ───── 搜尋索引與共用 JS ─────
def write_site_js():
    idx = [[e["id"], e["name"], e.get("en", ""), {"guide": "指南", "mob": "生物", "item": "物品", "hub": "目錄"}[e["type"]], href(e["id"], "root")] for e in ENT.values()]
    js = "window.MC_IDX=" + json.dumps(idx, ensure_ascii=False) + ";\n" + r"""
(function(){
 var q=document.getElementById('q'),r=document.getElementById('qres');
 if(q){q.addEventListener('input',function(){var v=q.value.trim().toLowerCase();if(!v){r.style.display='none';return;}
  var hit=MC_IDX.filter(function(e){return (e[1]+e[2]+e[0]).toLowerCase().indexOf(v)>=0;}).slice(0,12);
  r.innerHTML=hit.map(function(e){return '<a href="'+MC_BASE+e[4]+'">'+e[1]+' <small>'+e[3]+'</small></a>';}).join('')||'<a>找不到</a>';r.style.display='block';});
  document.addEventListener('click',function(ev){if(!ev.target.closest('.search'))r.style.display='none';});}
 // 從簡報點進來時，顯示「回到簡報第 N 頁」
 var m=location.hash.match(/from-s(\d+)/),b=document.getElementById('back2slide');
 try{ if(m){sessionStorage.setItem('mcFrom',m[1]);} var f=m?m[1]:sessionStorage.getItem('mcFrom');
  if(f&&b){b.href=MC_BASE+'slides.html#s'+f;b.textContent='◀ 回到簡報第 '+f+' 頁';b.style.display='flex';} }catch(e){ if(m&&b){b.href=MC_BASE+'slides.html#s'+m[1];b.style.display='flex';} }
 // 勾選清單
 document.querySelectorAll('.check input').forEach(function(c){try{c.checked=localStorage.getItem('mc-'+c.dataset.k)==='1';}catch(e){}
  c.addEventListener('change',function(){try{localStorage.setItem('mc-'+c.dataset.k,c.checked?'1':'0');}catch(e){}});});
 // 圖鑑篩選
 document.querySelectorAll('.filters button').forEach(function(btn){btn.addEventListener('click',function(){
  document.querySelectorAll('.filters button').forEach(function(x){x.classList.remove('on')});btn.classList.add('on');
  var f=btn.dataset.f;document.querySelectorAll('#flist .card').forEach(function(c){
   if(f==='all'){c.style.display='';return;} var p=f.split(':'),v=c.dataset[p[0]]||'';c.style.display=(v.indexOf(p[1])>=0)?'':'none';});});});
})();
"""
    with open(os.path.join(OUT, "assets", "site.js"), "w", encoding="utf-8") as f: f.write(js)


# ═══════════════ 簡報 ═══════════════
from slides_render import render_slides  # noqa: E402

pages = {}
for g in GUIDES: pages[f"wiki/{g['id']}.html"] = render_guide(g)
for m in MOBS: pages[f"wiki/{m['id']}.html"] = render_mob(m)
for i in ITEMS: pages[f"wiki/{i['id']}.html"] = render_item(i)
for st in STAGES: pages[f"wiki/{st}.html"] = render_stage_hub(st)
pages["wiki/mobs.html"] = render_mob_hub()
pages["wiki/items.html"] = render_item_hub()
pages["index.html"] = render_index()
G = dict(ENT=ENT, MOBS=MOBS, ITEMS=ITEMS, GUIDES=GUIDES, SLIDES=SLIDES, CHAPTERS=CHAPTERS, REL=REL, RELATIONS=RELATIONS, DROPS_BY_ITEM=DROPS_BY_ITEM,
         USED_IN=USED_IN, ORE_LEVELS=ORE_LEVELS, md=md, plain=plain, href=href, item_icon=item_icon, slot=slot, avatar=avatar, stars=stars, hearts=hearts,
         hpnum=hpnum, picks=picks, mob_card=mob_card, item_card=item_card, ore_chart=ore_chart, portal_diagram=portal_diagram, altar_diagram=altar_diagram,
         pillars_svg=pillars_svg, DIAGRAM_CSS=DIAGRAM_CSS, STRENGTH=STRENGTH, RARITY=RARITY, links_in=links_in, slide_links=slide_links, icons=icons)
pages["slides.html"] = render_slides(G)
DIAG = DIAGRAM_CSS.replace("TEX/", "../assets/")
for k in list(pages):
    if k.startswith("wiki/") and ("portal-grid" in pages[k] or "altar-grid" in pages[k]):
        pages[k] = pages[k].replace("</head>", f"<style>{DIAG}</style></head>")
from process_render import render_process  # noqa: E402

pages["process.html"] = "<!-- placeholder -->"
os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
write_site_js()


def post_check(pages):
    bad = []
    for path, htm in pages.items():
        d = os.path.dirname(path)
        for m in re.finditer(r'(?:href|src)="([^"#:]+?)(?:#[^"]*)?"', htm):
            u = m.group(1)
            if u.startswith(("http", "data:", "mailto")) or not u: continue
            tgt = os.path.normpath(os.path.join(d, u))
            if tgt not in pages and not os.path.exists(os.path.join(OUT, tgt)): bad.append((path, u))
        for m in re.finditer(r"url\(([^)]+)\)", htm):
            u = m.group(1).strip("'\"")
            if u.startswith(("http", "data:", "#")): continue  # url(#id) 是 SVG 內部參照，不是檔案
            tgt = os.path.normpath(os.path.join(d, u))
            if not os.path.exists(os.path.join(OUT, tgt)): bad.append((path, u))
    return bad


bad = post_check(pages)
for n in G.get("EMPTY_SLIDES", []): bad.append((f"slides.html#s{n}", "空白投影片（版面未實作）"))
report["generate"] = dict(pages=len(pages), wiki_pages=sum(1 for k in pages if k.startswith("wiki/")))
report["post_check"] = dict(broken_links=len(bad), samples=bad[:20])
report["result"] = "OK" if not bad else "POST-CHECK 失敗：有斷掉的本地連結"
pages["process.html"] = render_process(G, report, RUNS, SOURCES, href, page)
bad = post_check(pages) + [(f"slides.html#s{n}", "空白投影片（版面未實作）") for n in G.get("EMPTY_SLIDES", [])]; report["post_check"] = dict(broken_links=len(bad), samples=bad[:20])
report["result"] = "OK" if not bad else "POST-CHECK 失敗：有斷掉的本地連結或空白投影片"
for path, htm in pages.items():
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f: f.write(htm)
save_report()
print(f"[GENERATE] {len(pages)} pages → {OUT}")
print(f"[POST-CHECK] broken local links: {len(bad)}", bad[:10])
