# -*- coding: utf-8 -*-
"""教學簡報產生器：所有數字、卡片、圖解都直接取自 Wiki 資料（與 Wiki 頁面共用同一份函式）。"""
import math


def render_slides(G):
    E, md, plain, href = G["ENT"], G["md"], G["plain"], G["href"]
    icons = G["icons"]
    CH = {c[0]: c for c in G["CHAPTERS"]}
    CH_ORDER = [c[0] for c in G["CHAPTERS"]]
    CH_ICON = {"early": ("block", "#5d9b3a"), "mid": ("pickaxe", "#d8d8d8"), "late": ("eye", "#3fb58f"), "mobs": ("sword", "#d8483b"), "items": ("gem", "#4fd9e0")}
    B = "root"
    S = G["SLIDES"]
    first = {}
    for n, s in enumerate(S, 1):
        if s["ch"] and s["ch"] not in first: first[s["ch"]] = n
    M = lambda t: md(t, B)

    def foot(s, n):
        ids = list(dict.fromkeys(s.get("wiki", [])))
        if not ids: return ""
        chips = "".join(f'<a class="chip" href="{href(i, B)}">{E[i]["name"]}</a>' for i in ids if i in E)
        return f'<div class="sl-foot"><span>📖 對應 Wiki：</span>{chips}</div>'

    def head(s, n):
        ch = s["ch"]
        tag = f'<span class="chtag c-{ch}">{CH[ch][1]}</span>' if ch else ""
        return f'<div class="sl-head">{tag}<h2>{M(s["title"])}</h2><span class="pg">{n}</span></div>'

    def lead(s):
        return f'<p class="lead">{M(s["lead"])}</p>' if s.get("lead") else ""

    def body(s, n):
        L = s["layout"]
        if L == "cover":
            btns = "".join(f'<a class="cbtn" href="#s{first[c]}">{icons.svg(*CH_ICON[c], 44)}<b>{CH[c][1]}</b><small>{CH[c][2]}</small></a>' for c in CH_ORDER)
            return (f'<div class="cover"><div class="ctitle">{s["title"]}</div><div class="csub">{s["sub"]}</div>'
                    f'<div class="cbtns">{btns}</div><div class="hint">按 → 或 空白鍵 開始｜按 1–5 跳到章節｜每頁下方可開啟對應的 Wiki 頁面</div>'
                    f'<a class="wikilink" href="index.html">🏠 Wiki 首頁</a></div>')
        if L == "chapter":
            ch = s["ch"]; k = CH_ORDER.index(ch) + 1
            pts = "".join(f'<li>{icons.svg(*CH_ICON[ch], 26)}<span>{M(p)}</span></li>' for p in s["points"])
            return (f'<div class="chap"><div class="chnum">CH.{k}<div class="chicon">{icons.svg(*CH_ICON[ch], 150)}</div></div>'
                    f'<div><div class="chtitle">{s["title"]}</div><div class="chsub">{M(s["sub"])}</div><div class="learn">這一章你會學到</div><ul class="pts">{pts}</ul></div></div>')
        if L == "bullets":
            li = "".join(f"<li>{M(b)}</li>" for b in s["bullets"])
            note = f'<div class="note">{M(s["note"])}</div>' if s.get("note") else ""
            ids = [i for i in dict.fromkeys(x for b in s["bullets"] + [s.get("lead", ""), s.get("note", "")] for x in G["links_in"](b)) if E[i]["type"] in ("mob", "item")][:8]
            side = ""
            if ids:
                cells = "".join(f'<a class="sidec" href="{href(i, B)}">' + (G["avatar"](E[i]) if E[i]["type"] == "mob" else f'<span class="slot">{G["item_icon"](i)}</span>') + f'<span>{E[i]["name"]}</span></a>' for i in ids)
                side = f'<div class="side"><div class="sideh">本頁提到的圖鑑</div><div class="sideg">{cells}</div></div>'
            return f'{lead(s)}<div class="bwrap"><div><ul class="bl">{li}</ul>{note}</div>{side}</div>'
        if L == "check":
            li = "".join(f'<li><input type="checkbox" data-k="slide{n}-{k}"><span>{M(x)}</span></li>' for k, x in enumerate(s["items"]))
            return f'<p class="lead">在進入下一章之前，確認你已經做到這些（可以直接勾選）：</p><div class="gui chk"><ul class="check">{li}</ul></div>'
        if L == "flow":
            st = '<div class="arrow">➜</div>'.join(f'<div class="step"><div class="sn">{k}</div><div class="st">{M(a)}</div><div class="sd">{M(b)}</div></div>' for k, (a, b) in enumerate(s["steps"], 1))
            ch = ""
            if s.get("chain"):
                ch = '<span class="carr">➜</span>'.join(f'<div class="ci">{G["slot"](i, B)}<span>{E[i]["name"]}</span></div>' for i in s["chain"])
                ch = f'<div class="chain"><div class="chl">實際例子（點圖示看 Wiki）</div><div class="chr">{ch}</div></div>'
            return f'{lead(s)}<div class="flow">{st}</div>{ch}'
        if L == "table":
            th = "".join(f"<th>{h}</th>" for h in s["head"])
            tr = "".join("<tr>" + "".join(f"<td>{M(c)}</td>" for c in r) + "</tr>" for r in s["rows"])
            return f'{lead(s)}<table class="mc big">{"<tr>" + th + "</tr>"}{tr}</table>'
        if L == "cards":
            many = len(s["ids"]) > 6
            cls = "g4" if many else ("g2" if len(s["ids"]) <= 4 else "g3")
            cards = "".join(G["mob_card"](E[i], B, compact=many) for i in s["ids"])
            return f'{lead(s)}<div class="grid {cls}">{cards}</div>'
        if L == "cards_item":
            return f'{lead(s)}<div class="grid g4">{"".join(G["item_card"](E[i], B) for i in s["ids"])}</div>'
        if L == "pack":
            sl = "".join(f'<div class="pk">{G["slot"](i, B)}<span>{E[i]["name"]}</span></div>' for i in s["ids"])
            return f'<div class="gui inv"><div class="invt">背包</div><div class="pack">{sl}</div></div>{lead(s)}'
        if L == "ore_chart":
            return f'{lead(s)}<div class="orewrap">{G["ore_chart"](B, gap=142, bw=104, Hh=440)}</div>'
        if L == "econ":
            sell = [("stick", "32", "製箭師"), ("rotten_flesh", "32", "神職人員"), ("wheat", "20", "農夫")]
            buy = [("diamond_gear", "", "鐵匠類村民"), ("book", "", "圖書管理員（附魔書）"), ("ender_pearl", "", "神職人員（5 顆換 1）")]
            L1 = "".join(f'<div class="ek">{G["slot"](i, B, q)}<span>→ {who}</span></div>' for i, q, who in sell)
            R1 = "".join(f'<div class="ek"><span>{who} →</span>{G["slot"](i, B)}</div>' for i, q, who in buy)
            te = next(t for o, t in G["REL"]["emerald"] if o == "villager")
            return (f'{lead(s)}<div class="econ"><div class="ecol"><div class="eh">賣給村民</div>{L1}</div>'
                    f'<div class="ecen">{G["slot"]("emerald", B)}<div><a href="{href("emerald", B)}">綠寶石</a></div><div class="sm">村民交易的貨幣</div></div>'
                    f'<div class="ecol"><div class="eh">向村民購買</div>{R1}</div></div><div class="note">Wiki 綠寶石頁：{M(te)}</div>')
        if L == "portal":
            steps = ["收集 10 塊[[obsidian|黑曜石]]（需[[diamond_gear|鑽石鎬]]，或用水＋岩漿澆注）", "排成外框 4×5 的長方形，四個角可省略",
                     "用[[flint_and_steel|打火石]]點燃框內底部", "走進紫色傳送門，等待約 4 秒",
                     "抵達後：記座標、用[[cobblestone|圓石]]包住傳送門"]
            li = "".join(f"<li>{M(x)}</li>" for x in steps)
            return f'<div class="two"><div>{G["portal_diagram"]()}<p class="sm">深紫＝黑曜石｜虛線角＝可省略</p></div><ol class="bl">{li}</ol></div>'
        if L == "altar":
            steps = ["沿著[[eye_of_ender|終界之眼]]的方向找到要塞，往下挖進去", "找到有岩漿池與樓梯的房間：這就是終界祭壇",
                     "先拆掉樓梯上的[[silverfish|蠹魚]]生怪籠", "用方塊蓋住岩漿池，避免掉下去",
                     "把終界之眼放進 12 個框架（有些可能已經有了）", "⚠ 跳進去前先在附近睡床、檢查裝備"]
            li = "".join(f"<li>{M(x)}</li>" for x in steps)
            return f'<div class="two"><div>{G["altar_diagram"]()}<p class="sm">俯視圖｜綠色＝已放入終界之眼｜中央＝岩漿</p></div><ol class="bl">{li}</ol></div>'
        if L == "dragon":
            ph = [("① 拆水晶", "用[[bow|弓]]射掉柱頂的[[end_crystal|終界水晶]]；2 顆在鐵籠中，要搭方塊上去打。水晶不拆完，龍會一直回血。"),
                  ("② 空中輸出", "龍盤旋時用弓箭射擊。被撞飛就喝[[slow_falling|緩降藥水]]或放水桶落地。"),
                  ("③ 停棲近戰", "龍停在中央傳送門上時，Java 版**箭無效**，改用劍砍頭；避開紫色龍息。")]
            cols = "".join(f'<div class="ph"><div class="pht">{a}</div><p>{M(b)}</p></div>' for a, b in ph)
            m = E["ender_dragon"]
            return (f'<div class="two" style="grid-template-columns:1fr 430px"><div><div class="phs">{cols}</div>'
                    f'<p class="sm">{G["avatar"](m)} 終界龍：生命 {m["hp"]}（100 顆心）｜經驗 {m["xp"]}</p></div><div>{G["pillars_svg"]()}<p class="sm">10 根黑曜石柱，虛線＝鐵籠</p></div></div>')
        if L == "scale":
            ex = {1: "cow", 2: "zombie", 3: "creeper", 4: "blaze", 5: "ender_dragon"}
            rows = "".join(f'<tr><td style="white-space:nowrap">{G["stars"](k)}</td><td style="white-space:nowrap">{G["STRENGTH"][k]}</td><td style="white-space:nowrap">例：<a href="{href(v, B)}">{E[v]["name"]}</a></td></tr>' for k, v in ex.items())
            kinds = [("被動", "不會攻擊，被打只會逃（牛、羊、村民）"), ("中立", "被挑釁才攻擊（終界使者、豬布林、鐵魔像）"), ("敵對", "看到就攻擊（殭屍、苦力怕、烈焰使者）"), ("頭目", "Boss 等級（終界龍）")]
            kt = "".join(f'<li><span class="tag k-{k}">{k}</span> {d}</li>' for k, d in kinds)
            return (f'<div class="two"><div><h3>4 種行為類型</h3><ul class="bl">{kt}</ul><h3>卡片怎麼看</h3>{G["mob_card"](E["creeper"], B, compact=True)}'
                    f'<p class="sm">頭像顏色＝類型｜右下色塊＝維度｜★＝威脅｜❤＝生命｜XP＝經驗｜下方圖示＝掉落物</p></div>'
                    f'<div><h3>★ 新手威脅量表</h3><table class="mc">{rows}</table><p class="sm">威脅等級由本 Wiki 依「傷害、生命、特殊能力、新手常見死因」綜合評定。</p></div></div>')
        if L == "rank":
            ms = sorted([m for m in G["MOBS"] if m["kind"] != "被動"], key=lambda m: (-m["strength"], -G["hpnum"](m["hp"])))[:11]
            mx = math.log(500)
            rows = "".join(f'<div class="rk"><span class="rn">{G["avatar"](m)}<a href="{href(m["id"], B)}">{m["name"]}</a></span>'
                           f'<span class="rb"><span style="width:{max(4, math.log(max(2, G["hpnum"](m["hp"]))) / mx * 100):.0f}%;background:{["#3f8f3a", "#3f8f3a", "#c08a1c", "#d8483b", "#b8312a", "#6c2bb5"][m["strength"]]}"></span><em>❤ {G["hpnum"](m["hp"])}</em></span>'
                           f'<span>{G["stars"](m["strength"])}</span></div>' for m in ms)
            return f'<p class="lead">長條＝生命值（對數尺度）｜★＝威脅等級。生命值高不一定最危險：苦力怕只有 20，卻能一次炸掉大半血量。</p><div class="rank">{rows}</div>'
        if L == "matrix":
            R = G["RARITY"]
            cells = '<div></div>' + "".join(f'<div class="mx-x"><span class="tag r-{r}">{r}</span></div>' for r in R)
            for d in range(5, 0, -1):
                cells += f'<div class="mx-y">難度 {d}</div>'
                for r in R:
                    its = "".join(f'<a href="{href(i["id"], B)}" title="{i["name"]}">{G["item_icon"](i["id"], 28)}</a>' for i in G["ITEMS"] if i["diff"] == d and i["rarity"] == r)
                    cells += f'<div class="mx-c">{its}</div>'
            return f'<p class="lead">橫軸＝稀缺程度，縱軸＝取得難度；越往右上越是終局物品（點圖示開啟物品頁）。</p><div class="matrix">{cells}</div>'
        if L == "graph":
            ids = s["wiki"]; W, Hh, R = 1100, 460, 180
            pos = dict(s["pos"]) if s.get("pos") else {}
            for k, i in enumerate(ids):
                a = -math.pi / 2 + k / len(ids) * 2 * math.pi
                pos.setdefault(i, (W / 2 + R * 2.6 * math.cos(a), Hh / 2 + 10 + R * math.sin(a)))
            edges = []
            for a, b, *_ in G["RELATIONS"]:
                if a in pos and b in pos:
                    lab = "交易" if "villager" in (a, b) else ("以物易物" if "piglin" in (a, b) else "相關")
                    edges.append((a, b, lab))
            for it, lst in G["DROPS_BY_ITEM"].items():
                for mob, *_ in lst:
                    if it in pos and mob in pos: edges.append((mob, it, "掉落"))
            for mat, lst in G["USED_IN"].items():
                for prod, _ in lst:
                    if mat in pos and prod in pos: edges.append((mat, prod, "合成"))
            svg = "".join(f'<line x1="{pos[a][0]:.0f}" y1="{pos[a][1]:.0f}" x2="{pos[b][0]:.0f}" y2="{pos[b][1]:.0f}" stroke="#ffd23f" stroke-width="4" stroke-dasharray="{"0" if l != "相關" else "6 4"}"/>'
                          f'<text x="{(pos[a][0] + pos[b][0]) / 2:.0f}" y="{(pos[a][1] + pos[b][1]) / 2 - 4:.0f}" text-anchor="middle" class="el">{l}</text>' for a, b, l in edges)
            nodes = ""
            for i, (x, y) in pos.items():
                e = E[i]
                ic = G["avatar"](e) if e["type"] == "mob" else f'<span class="slot">{G["item_icon"](i)}</span>'
                nodes += f'<a class="gn" style="left:{x - 60:.0f}px;top:{y - 40:.0f}px" href="{href(i, B)}">{ic}<span>{e["name"]}</span></a>'
            return f'{lead(s)}<div class="graph"><svg width="{W}" height="{Hh}">{svg}</svg>{nodes}</div>'
        if L == "road":
            ms = [("early", [("e1_first_day", "床與基地", "bed", "#c0392b"), ("e2_tools", "石器", "pickaxe", "#7f7f7f"), ("e3_mining", "鐵器", "ingot", "#d8d8d8"), ("e5_mobs", "盾牌", "shield", "#9a6b3a")]),
                  ("mid", [("m1_gear", "鑽石＋附魔", "gem", "#4fd9e0"), ("m3_trading", "交易站", "gem", "#2ecc71"), ("m4_portal", "下界傳送門", "block", "#2a1740"), ("m5_nether_mobs", "烈焰桿", "rod", "#f2a51a")]),
                  ("late", [("l1_eyes", "終界之眼", "eye", "#3fb58f"), ("l2_stronghold", "要塞", "block", "#8a8a8a"), ("l4_dragon", "終界龍", "crystal", "#d06bd0"), ("l5_after", "鞘翅", "wings", "#8f8fb8")])]
            rows = ""
            for st, lst in ms:
                nodes = '<span class="rarr">➜</span>'.join(f'<a class="rd" href="{href(g, B)}"><span class="slot">{icons.svg(t, c, 44)}</span><b>{nm}</b></a>' for g, nm, t, c in lst)
                rows += f'<div class="rrow"><a class="rst c-{st}" href="{href(st, B)}">{ {"early": "前期", "mid": "中期", "late": "後期"}[st]}</a>{nodes}</div>'
            return f'<p class="lead">前期把「活下來」變成習慣，中期把資源變成能力，後期把能力帶到終界。每個里程碑都可以點進對應的生存指南。</p><div class="road">{rows}</div>'
        if L == "end":
            flow = ["取得資料（ingest 33 個來源）", "整理成 Wiki 條目＋雙向關係", "前置檢查（8 類規則）", "從 Wiki 生成簡報與頁面", "後置檢查（本地連結）"]
            f = '<span class="arrow">➜</span>'.join(f'<span class="pn">{x}</span>' for x in flow)
            return (f'<p class="lead">{s["sub"]}</p><div class="pipe">{f}</div>'
                    f'<div class="two" style="margin-top:26px"><a class="bigbtn" href="process.html">📜 查看完整流程、執行紀錄與反思</a><a class="bigbtn" href="index.html">🏠 回到 Wiki 首頁</a></div>'
                    f'<p class="thanks">感謝觀看！祝你屠龍成功。</p>')
        return ""

    secs = []
    G["EMPTY_SLIDES"] = [n for n, s in enumerate(S, 1) if not body(s, n).strip()]
    for n, s in enumerate(S, 1):
        ch = s["ch"] or "cover"
        cls = f'slide ch-{ch} L-{s["layout"]}'
        inner = body(s, n) if s["layout"] in ("cover",) else head(s, n) + f'<div class="sl-body">{body(s, n)}</div>' + foot(s, n)
        if s["layout"] == "chapter": inner = f'<div class="sl-body">{body(s, n)}</div>' + foot(s, n)
        secs.append(f'<section class="{cls}" id="s{n}" data-ch="{s["ch"] or ""}" aria-label="第 {n} 頁">{inner}</section>')

    hot = [("cover", 1, "封面", ("block", "#5d9b3a"))] + [(c, first[c], CH[c][1], CH_ICON[c]) for c in CH_ORDER]
    hb = "".join(f'<a class="hs" data-ch="{c}" href="#s{n}" title="{nm}（{k}）">{icons.svg(*ic, 34)}<span class="hk">{k}</span></a>' for k, (c, n, nm, ic) in enumerate(hot))
    hb += f'<a class="hs" href="index.html" title="Wiki 首頁">{icons.svg("book", "#8b4513", 34)}</a><a class="hs" href="process.html" title="流程與反思">{icons.svg("dust", "#d42a2a", 34)}</a><a class="hs" id="fs" href="#" title="全螢幕（F）">{icons.svg("template", "#8a8a8a", 34)}</a>'
    css = SLIDE_CSS + G["DIAGRAM_CSS"].replace("TEX/", "assets/")
    return f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Minecraft 生存指南｜教學簡報</title><link rel="stylesheet" href="assets/style.css"><style>{css}</style></head>
<body class="deck"><div id="vp"><div id="stage">{''.join(secs)}</div></div>
<div id="hud"><button id="prev" class="nb" aria-label="上一頁">◀</button><div class="hudc"><div class="xpwrap"><div class="xpbar"><i id="xpfill"></i></div><span id="lvl">1</span></div>
<nav class="hotbar">{hb}</nav></div><button id="next" class="nb" aria-label="下一頁">▶</button></div>
<script>{SLIDE_JS}
document.querySelectorAll('.check input').forEach(function(c){{try{{c.checked=localStorage.getItem('mc-'+c.dataset.k)==='1';}}catch(e){{}}c.addEventListener('change',function(){{try{{localStorage.setItem('mc-'+c.dataset.k,c.checked?'1':'0');}}catch(e){{}}}});}});</script></body></html>"""


SLIDE_CSS = r"""
html,body.deck{height:100%;overflow:hidden;background:#111}
#vp{position:fixed;inset:0 0 92px 0;display:grid;place-items:center}
#stage{width:1280px;height:720px;position:relative;transform-origin:center center}
.slide{position:absolute;inset:0;display:none;flex-direction:column;padding:34px 48px 20px;background:#1b1b1b url(assets/tex_deep.png);background-size:64px;border:4px solid #000;box-shadow:0 0 0 3px #3a3a3a;overflow:hidden}
.slide::before{content:"";position:absolute;inset:0;background:rgba(0,0,0,.58);pointer-events:none}
.slide>*{position:relative}
.slide.on{display:flex;animation:fi .25s}
@keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
.ch-early{background-image:url(assets/tex_grass.png)}.ch-mid{background-image:url(assets/tex_stone.png)}.ch-late{background-image:url(assets/tex_end.png)}
.ch-late::before{background:rgba(14,4,24,.78)}.ch-mobs{background-image:url(assets/tex_nether.png)}.ch-items{background-image:url(assets/tex_plank.png)}.ch-cover{background-image:url(assets/tex_grass.png)}
.ch-cover::before{background:linear-gradient(rgba(0,0,0,.25),rgba(0,0,0,.7))}
.sl-head{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.sl-head h2{margin:0;font-size:38px;color:#fff;text-shadow:3px 3px 0 #3f3f3f}
.sl-head .pg{margin-left:auto;color:#80ff20;font-size:22px;text-shadow:2px 2px 0 #1f3f00}
.chtag{padding:2px 12px;border:3px solid #000;font-size:18px;color:#fff;text-shadow:2px 2px 0 #000}
.c-early{background:#4b7a2f}.c-mid{background:#5d6670}.c-late{background:#6c2bb5}.c-mobs{background:#b8312a}.c-items{background:#b88a1c}
.sl-body{flex:1;min-height:0;font-size:25px;line-height:1.6}
.sl-body .lead{font-size:25px;color:#ffe9a8;margin:0 0 12px;text-shadow:2px 2px 0 #000}
.sl-foot{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:15px;color:#ddd;border-top:2px dashed rgba(255,255,255,.25);padding-top:8px;margin-top:6px}
.chip{padding:1px 10px;background:#2d0a63;border:2px solid #000;color:#fff;font-size:15px}
.chip:hover{background:#4c1aa0;color:#ffffa0;text-decoration:none}
ul.bl,ol.bl{margin:6px 0;padding-left:0;list-style:none}
ul.bl li,ol.bl li{position:relative;padding:9px 0 9px 44px;font-size:27px;text-shadow:2px 2px 0 #000}
ul.bl li::before{content:"";position:absolute;left:6px;top:21px;width:16px;height:16px;background:#80ff20;border:3px solid #000;box-shadow:inset -3px -3px 0 #3f8f10}
ol.bl{counter-reset:k}ol.bl li{counter-increment:k}
ol.bl li::before{content:counter(k);position:absolute;left:0;top:12px;width:30px;height:30px;line-height:26px;text-align:center;background:#5a5a5a;border:3px solid #000;font-size:18px;color:#fff}
.note{margin-top:10px;padding:10px 16px;background:rgba(120,20,20,.75);border:3px solid #000;font-size:19px}
.flow{display:flex;align-items:stretch;gap:10px;margin-top:22px}
.step{flex:1;background:rgba(16,0,16,.88);border:3px solid #000;box-shadow:inset 0 0 0 3px #2d0a63;padding:18px 14px;text-align:center}
.step .sn{display:inline-block;width:40px;height:40px;line-height:36px;background:#80ff20;color:#1f3f00;border:3px solid #000;font-size:22px;margin-bottom:8px;text-shadow:none}
.step .st{font-size:26px;color:#fff;text-shadow:2px 2px 0 #000}.step .sd{font-size:18px;color:#ccc;margin-top:6px}
.flow{margin-top:40px}
.flow .arrow{align-self:center;font-size:40px;color:#ffd23f;text-shadow:3px 3px 0 #000}
table.mc.big th,table.mc.big td{font-size:25px;padding:15px 18px}
.grid.g4{grid-template-columns:repeat(4,1fr)}.grid.g2{grid-template-columns:repeat(2,1fr)}
.slide .card .t{font-size:22px}.slide .card .d{font-size:17px}.slide .grid{gap:16px}
.slide .grid.g2 .card,.slide .grid.g3 .card{padding:16px}.slide .grid.g2 .avatar,.slide .grid.g3 .avatar{width:74px;height:74px;font-size:38px}
.L-portal .portal-grid{grid-template-columns:repeat(4,78px)}.L-portal .pc{width:78px;height:78px}
.L-altar .altar-grid{grid-template-columns:repeat(5,74px)}.L-altar .ac{width:74px;height:74px}.L-altar .ac.frame.eye::after{margin:22px;width:28px;height:28px}
.L-dragon svg.pillars{width:420px;height:420px}.L-dragon .ph p{font-size:21px}.L-dragon .phs{gap:16px}.L-dragon .ph{padding:16px}
.L-econ .ek{font-size:22px;margin:14px 0}.L-econ .ecol{padding:18px 20px}.L-econ .ecen .slot{width:150px;height:150px}.L-econ .ecen .slot svg{width:110px;height:110px}
.L-flow .step{padding:30px 16px}.L-flow .step .st{font-size:30px}.L-flow .step .sd{font-size:21px}
.slide .mob-card{padding:9px}
.cover{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.ctitle{font-size:96px;color:#fff;text-shadow:5px 5px 0 #3f3f3f,0 0 30px rgba(0,0,0,.6);line-height:1.1}
.csub{font-size:26px;color:#ffe066;text-shadow:3px 3px 0 #000;margin:14px 0 30px}
.cbtns{display:flex;gap:14px}
.cbtn{width:180px;padding:14px 8px;display:flex;flex-direction:column;align-items:center;gap:6px;background:#6f6f6f url(assets/tex_stone.png);background-size:48px;border:3px solid #000;box-shadow:inset 3px 3px 0 rgba(255,255,255,.4),inset -3px -3px 0 rgba(0,0,0,.45);color:#fff;text-shadow:2px 2px 0 #3f3f3f}
.cbtn b{font-weight:normal;font-size:24px}.cbtn small{font-size:14px;color:#eee}
.cbtn:hover{outline:3px solid #fff;outline-offset:-3px;text-decoration:none;color:#ffffa0}
.hint{margin-top:26px;color:#ddd;font-size:17px;text-shadow:2px 2px 0 #000}
.wikilink{position:absolute;right:0;top:0;font-size:18px}
.chap{flex:1;display:grid;grid-template-columns:330px 1fr;gap:40px;align-items:center}
.chnum{font-size:70px;color:#80ff20;text-shadow:4px 4px 0 #1f3f00;text-align:center}
.chicon{margin-top:10px;display:grid;place-items:center;width:230px;height:230px;margin-inline:auto;background:#8b8b8b;border:4px solid #000;box-shadow:inset 5px 5px 0 #fff,inset -5px -5px 0 #373737}
.chtitle{font-size:62px;color:#fff;text-shadow:4px 4px 0 #3f3f3f;line-height:1.2}
.chsub{font-size:24px;color:#ffe066;margin:8px 0 22px;text-shadow:2px 2px 0 #000}
.learn{font-size:18px;color:#aaa}
.pts{list-style:none;padding:0;margin:6px 0}.pts li{display:flex;gap:12px;align-items:center;font-size:26px;padding:8px 0;text-shadow:2px 2px 0 #000}
.inv{display:inline-block;margin:6px 0 16px;padding:14px 20px}.invt{font-size:20px;margin-bottom:6px}
.pack{display:grid;grid-template-columns:repeat(5,200px);gap:16px 12px}
.pk{display:flex;flex-direction:column;align-items:center;font-size:20px;text-align:center;line-height:1.3}
.pk .slot{width:96px;height:96px}.pk .slot svg{width:70px;height:70px}.L-pack .lead{margin-top:6px}
.orewrap .ore{height:400px;margin-top:34px}
.econ{display:grid;grid-template-columns:1fr 240px 1fr;gap:20px;align-items:center;margin:10px 0}
.ecol{background:rgba(16,0,16,.85);border:3px solid #000;padding:12px 16px}
.eh{color:#ffe066;font-size:20px;margin-bottom:6px}
.ek{display:flex;align-items:center;gap:12px;margin:8px 0;font-size:19px}
.ecen{text-align:center;font-size:24px}.ecen .slot{width:120px;height:120px}.ecen .slot svg{width:90px;height:90px}
.sm{font-size:15px;color:#ccc}
.two{display:grid;grid-template-columns:auto 1fr;gap:40px;align-items:start}
.two h3{margin:0 0 6px}
.phs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.ph{background:rgba(16,0,16,.88);border:3px solid #000;box-shadow:inset 0 0 0 3px #5b2a96;padding:12px 14px}
.ph p{font-size:18px;margin:4px 0}.pht{font-size:26px;color:#ff9cf5;text-shadow:2px 2px 0 #000}
.rank{display:grid;gap:4px}.rk{display:grid;grid-template-columns:240px 1fr 140px;gap:12px;align-items:center;font-size:20px}
.rk .avatar{width:34px;height:34px;font-size:17px;margin-right:8px}.rk .rn{display:flex;align-items:center}
.rb{position:relative;height:24px;background:rgba(0,0,0,.6);border:2px solid #000}.rb span{display:block;height:100%}
.rb em{position:absolute;right:6px;top:-3px;font-style:normal;font-size:15px}
.matrix{display:grid;grid-template-columns:90px repeat(5,1fr);gap:4px}.L-scale table.mc td{padding:6px 10px;font-size:20px}.L-scale .mob-card{max-width:440px}
.mx-c{min-height:60px;background:rgba(0,0,0,.6);border:2px solid #000;padding:4px;display:flex;flex-wrap:wrap;gap:3px;align-content:flex-start}
.mx-y{display:grid;place-items:center;font-size:18px;color:#ffe066}.mx-x{text-align:center}
.graph{position:relative;width:1100px;height:460px;margin:0 auto}
.graph svg{position:absolute;inset:0}.graph .el{fill:#ffe9a8;font-size:15px;paint-order:stroke;stroke:#000;stroke-width:4px}
.gn{position:absolute;width:100px;display:flex;flex-direction:column;align-items:center;gap:2px;color:#fff;font-size:16px;text-shadow:2px 2px 0 #000}
.road{display:grid;gap:18px;margin-top:16px}
.rrow{display:flex;align-items:center;gap:14px;background:rgba(0,0,0,.45);border:3px solid #000;padding:10px 16px}
.rst{width:110px;text-align:center;padding:12px 0;border:3px solid #000;color:#fff;font-size:26px;text-shadow:2px 2px 0 #000}
.rd{display:flex;flex-direction:column;align-items:center;width:150px;color:#fff;text-shadow:2px 2px 0 #000}
.rd .slot{width:76px;height:76px}.rd .slot svg{width:54px;height:54px}
.rd b{font-weight:normal;font-size:21px}.rarr{color:#ffd23f;font-size:30px;text-shadow:2px 2px 0 #000}
.chain{margin-top:34px;background:rgba(0,0,0,.5);border:3px solid #000;padding:14px 18px}.chl{font-size:18px;color:#aaa;margin-bottom:6px}
.chr{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ci{display:flex;flex-direction:column;align-items:center;font-size:16px;width:100px;text-align:center}
.ci .slot{width:64px;height:64px}.ci .slot svg{width:46px;height:46px}.carr{color:#ffd23f;font-size:24px}
.bwrap{display:grid;grid-template-columns:1fr 330px;gap:26px;align-items:start}
.side{background:rgba(0,0,0,.55);border:3px solid #000;box-shadow:inset 0 0 0 2px #3a3a3a;padding:12px 14px}.sideh{font-size:17px;color:#aaa;margin-bottom:8px}
.sideg{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.sidec{display:flex;flex-direction:column;align-items:center;gap:3px;color:#fff;font-size:16px;text-align:center;line-height:1.25;text-shadow:2px 2px 0 #000}
.sidec .slot{width:68px;height:68px}.sidec .slot svg{width:48px;height:48px}.sidec .avatar{width:68px;height:68px;font-size:34px}
.L-check .chk{padding:22px 30px}.L-check .check li{font-size:28px;padding:12px 10px}.L-check .check input{width:34px;height:34px}
.L-chapter .sl-body{display:flex}.chap{align-self:center;width:100%}
.gn .slot{width:64px;height:64px}.gn .slot svg{width:46px;height:46px}.gn .avatar{width:64px;height:64px;font-size:32px}.gn{width:120px;font-size:19px}
.graph .el{font-size:18px}
.pipe{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:20px}
.pn{padding:10px 14px;background:rgba(16,0,16,.88);border:3px solid #000;box-shadow:inset 0 0 0 3px #2d0a63}
.pipe .arrow{color:#ffd23f;font-size:28px}
.bigbtn{display:block;padding:20px;text-align:center;font-size:24px;background:#6f6f6f url(assets/tex_stone.png);background-size:48px;border:3px solid #000;box-shadow:inset 3px 3px 0 rgba(255,255,255,.4),inset -3px -3px 0 rgba(0,0,0,.45);color:#fff;text-shadow:2px 2px 0 #3f3f3f}
.bigbtn:hover{outline:3px solid #fff;outline-offset:-3px;text-decoration:none}
.thanks{text-align:center;font-size:34px;color:#80ff20;text-shadow:3px 3px 0 #1f3f00;margin-top:30px}
#hud{position:fixed;left:0;right:0;bottom:0;height:92px;display:flex;align-items:center;justify-content:center;gap:16px;background:linear-gradient(transparent,rgba(0,0,0,.6))}
.hudc{display:flex;flex-direction:column;align-items:center;gap:4px}
.xpwrap{position:relative;width:560px}
.xpbar{height:10px;background:#1a1a1a;border:2px solid #000}.xpbar i{display:block;height:100%;width:0;background:linear-gradient(#b8ff60,#5cc416);transition:width .25s}
#lvl{position:absolute;left:50%;top:-22px;transform:translateX(-50%);color:#80ff20;font-size:20px;text-shadow:2px 2px 0 #000,-2px -2px 0 #000,2px -2px 0 #000,-2px 2px 0 #000}
.hotbar{display:flex;background:rgba(0,0,0,.55);border:3px solid #000;padding:2px}
.hs{width:60px;height:60px;display:grid;place-items:center;border:3px solid #6b6b6b;margin:-1px;position:relative;background:rgba(80,80,80,.4)}
.hs:hover{background:rgba(255,255,255,.18)}
.hs.on{border-color:#fff;box-shadow:0 0 0 3px #000,inset 0 0 0 2px #000;z-index:2}
.hk{position:absolute;right:3px;bottom:-2px;font-size:13px;color:#fff;text-shadow:2px 2px 0 #3f3f3f}
.nb{font-family:inherit;font-size:24px;width:56px;height:56px;color:#fff;background:#6f6f6f url(assets/tex_stone.png);background-size:48px;border:3px solid #000;box-shadow:inset 3px 3px 0 rgba(255,255,255,.4),inset -3px -3px 0 rgba(0,0,0,.45);text-shadow:2px 2px 0 #3f3f3f;cursor:var(--cursor-hover)}
.nb:hover{outline:3px solid #fff;outline-offset:-3px}
@media(max-width:700px){.xpwrap{width:300px}.hs{width:40px;height:40px}.hs svg{width:24px;height:24px}.nb{width:40px;height:40px}}
"""

SLIDE_JS = r"""
(function(){
 var S=[].slice.call(document.querySelectorAll('.slide')),N=S.length,cur=1,stage=document.getElementById('stage');
 function fit(){var w=innerWidth,h=innerHeight-92,k=Math.min(w/1280,h/720)*0.98;stage.style.transform='scale('+k+')';}
 addEventListener('resize',fit);fit();
 function go(n,push){n=Math.max(1,Math.min(N,n));S[cur-1].classList.remove('on');cur=n;var s=S[n-1];s.classList.add('on');
  document.getElementById('xpfill').style.width=((n-1)/(N-1)*100)+'%';document.getElementById('lvl').textContent=n+' / '+N;
  var ch=s.dataset.ch||'cover';document.querySelectorAll('.hs').forEach(function(h){h.classList.toggle('on',h.dataset.ch===ch)});
  if(push!==false){try{history.replaceState(null,'','#s'+n)}catch(e){location.hash='s'+n}}}
 function fromHash(){var m=location.hash.match(/s(\d+)/);go(m?+m[1]:1,false);}
 addEventListener('hashchange',fromHash);fromHash();
 document.getElementById('next').onclick=function(){go(cur+1)};document.getElementById('prev').onclick=function(){go(cur-1)};
 var chFirst={};S.forEach(function(s,i){var c=s.dataset.ch;if(c&&!chFirst[c])chFirst[c]=i+1;});
 var order=['early','mid','late','mobs','items'];
 addEventListener('keydown',function(e){if(e.target.tagName==='INPUT')return;var k=e.key;
  if(k==='ArrowRight'||k==='PageDown'||k===' '){e.preventDefault();go(cur+1)}else if(k==='ArrowLeft'||k==='PageUp'){e.preventDefault();go(cur-1)}
  else if(k==='Home')go(1);else if(k==='End')go(N);else if(/^[1-5]$/.test(k))go(chFirst[order[+k-1]]);else if(k==='0')go(1);else if(k==='f'||k==='F')fs();});
 document.querySelectorAll('.hs[href^="#s"],.cbtn').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();go(+a.getAttribute('href').slice(2))})});
 function fs(){try{if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}catch(e){}}
 document.getElementById('fs').onclick=function(e){e.preventDefault();fs()};
 // 點進 Wiki 時帶上目前頁碼，Wiki 頁會顯示「回到簡報第 N 頁」
 document.addEventListener('click',function(e){var a=e.target.closest('a');if(!a)return;var h=a.getAttribute('href')||'';
  if(/^wiki\/|^index\.html|^process\.html/.test(h)&&h.indexOf('#')<0){a.setAttribute('href',h+'#from-s'+cur);}});
 var x0=null;addEventListener('touchstart',function(e){x0=e.touches[0].clientX},{passive:true});
 addEventListener('touchend',function(e){if(x0===null)return;var dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>50)go(cur+(dx<0?1:-1));x0=null});
})();
"""
