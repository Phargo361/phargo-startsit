"""Multi-league start/sit positional board for all of Phargo's leagues.

Inputs (scratchpad): sleeper_input.json (leagues+rosters+Sleeper proj+meta),
features.json (nflverse model projections per scoring + 2025 usage signals).
Output: phargo_startsit.html — one page, a tab per league.

Data sources: model projection + signals = nflverse (our wrxp model, 2025 game
logs). Sleeper API supplies only rosters, league config, and its own projection.
"""
import json, os, re, html

SCRATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(SCRATCH, "sleeper_input.json")))
F = json.load(open(os.path.join(SCRATCH, "features.json")))
MODEL, SIG = F["model"], F["signals"]
PROJ, META = S["sleeper_proj"], S["meta"]

def norm(s): return re.sub(r"[^a-z]", "", str(s).lower())

# Sleeper draft position colors (QB rose, RB teal, WR blue, TE orange, DEF tan);
# FLEX keeps its own yellow and SUPER_FLEX its own violet (Sleeper has no such color).
COL_COLOR = {"QB": "#fc2b6d", "RB": "#00ceb8", "WR": "#58a7ff", "TE": "#ffae58",
             "FLEX": "#f2c200", "SF": "#a78bfa", "DEF": "#be9b72"}

def text_on(hexc):
    """Black or white chip text depending on the accent's brightness."""
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#141414" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#fff"

# ---------- per-league lineup + card data ----------------------------------
def build_league(lg):
    scoring = lg["scoring"]           # 'half' | 'standard' | 'ppr'
    players = []
    for pid in lg["players"]:
        m = META.get(pid, {})
        pos = m.get("pos")
        if pos == "DB" or pos is None:
            continue
        nm = m.get("name", pid)
        k = norm(nm)
        model = (MODEL.get(k) or {}).get(scoring)
        sl = (PROJ.get(str(pid)) or {}).get(scoring)
        vals = [v for v in (model, sl) if isinstance(v, (int, float))]
        blend = round(sum(vals) / len(vals), 1) if vals else 0.0
        players.append({
            "id": pid, "name": nm, "pos": pos, "team": m.get("team", "FA"),
            "age": m.get("age"), "model": model, "sleeper": sl, "blend": blend,
            "startable": isinstance(sl, (int, float)) and sl > 0,
            "sig": SIG.get(k), "inj": m.get("inj"), "inj_part": m.get("inj_part"),
            "depth": m.get("depth"),
        })

    # slot counts from roster_positions
    rp = lg["roster_positions"]
    n = {s: rp.count(s) for s in set(rp)}
    slots = {"QB": n.get("QB", 0), "RB": n.get("RB", 0), "WR": n.get("WR", 0),
             "TE": n.get("TE", 0), "DEF": n.get("DEF", 0)}
    n_flex = n.get("FLEX", 0) + n.get("REC_FLEX", 0) + n.get("WRRB_FLEX", 0)
    n_sf = n.get("SUPER_FLEX", 0)

    chip = {}
    used = set()
    def pool(elig): return sorted([p for p in players if p["pos"] in elig and p["startable"]
                                   and p["id"] not in used], key=lambda x: -x["blend"])
    # fixed position slots
    for pos in ("QB", "RB", "WR", "TE", "DEF"):
        for i, p in enumerate(pool({pos})[:slots[pos]], 1):
            chip[p["id"]] = pos if slots[pos] == 1 else f"{pos}{i}"
            used.add(p["id"])
    # FLEX (RB/WR/TE)
    for i, p in enumerate(pool({"RB", "WR", "TE"})[:n_flex], 1):
        chip[p["id"]] = f"FLEX{i}" if n_flex > 1 else "FLEX"
        used.add(p["id"])
    # SUPER_FLEX (QB/RB/WR/TE)
    for i, p in enumerate(pool({"QB", "RB", "WR", "TE"})[:n_sf], 1):
        chip[p["id"]] = f"SF{i}" if n_sf > 1 else "SF"
        used.add(p["id"])

    total = round(sum(p["blend"] for p in players if chip.get(p["id"])), 1)
    return players, chip, n_flex, n_sf, total

# ---------- card rendering --------------------------------------------------
def slot_color(slot):
    if not slot: return None
    base = "SF" if slot.startswith("SF") else ("FLEX" if slot.startswith("FLEX")
            else slot.rstrip("0123456789"))
    return COL_COLOR.get(base)

def form_flag(sig):
    if not sig: return None
    l3, sea = sig.get("l3"), sig.get("sea")
    if l3 is None or sea in (None, 0): return None
    r = l3 / sea
    if r >= 1.20: return ("hot", f"heating up: L3 {l3:.1f} vs {sea:.1f}")
    if r <= 0.80: return ("cold", f"cooling: L3 {l3:.1f} vs {sea:.1f}")
    return None

SEP = "<span class='sep'>&middot;</span>"

def sig_inline(p):
    """One dot-separated usage line (bold values) for the strip layout."""
    s, pos = p["sig"], p["pos"]
    if not s:
        return "<span class='muted'>no 2025 usage on file</span>"
    parts = []
    if pos == "QB":
        parts = [f"<b>{s.get('att_pg','?')}</b> att", f"<b>{s.get('pyd_pg','?')}</b> pyd",
                 f"<b>{s.get('ptd','?')}</b> pTD", f"<b>{s.get('rush_pg','?')}</b> rush yd"]
    else:
        if s.get("snap") is not None:
            parts.append(f"<b>{s['snap']}%</b>")
        if pos in ("WR", "TE"):
            parts += [f"<b>{s.get('tgt_pg','?')}</b> tgt", f"<b>{s.get('ryd_pg','?')}</b> yd",
                      f"<b>{s.get('td','?')}</b> TD/{s.get('gp','?')}g"]
        else:
            parts += [f"<b>{s.get('car_pg','?')}</b> car", f"<b>{s.get('tgt_pg','?')}</b> tgt",
                      f"<b>{s.get('rush_pg','?')}</b> yd", f"<b>{s.get('td','?')}</b> TD"]
    return SEP.join(parts)

def card(p, chip, outline):
    slot = chip.get(p["id"])
    starter = slot is not None
    cls = "card starter" if starter else ("card bench na" if not p["startable"] else "card bench")
    ostyle = (f" style='border-color:{outline};box-shadow:0 0 0 1px {outline} inset'"
              if starter and outline else "")
    cstyle = f" style='background:{outline};color:{text_on(outline)}'" if slot and outline else ""
    chip_html = f"<div class='chip'{cstyle}>{slot}</div>" if slot else ""
    age = f" &middot; {p['age']}y" if p.get("age") else ""
    m, s = p["model"], p["sleeper"]
    mt = f"{m:.1f}" if isinstance(m, (int, float)) else "&mdash;"
    st = f"{s:.1f}" if isinstance(s, (int, float)) else "&mdash;"
    proj = (f"<div class='proj'><span class='pm' title='our nflverse model'>{mt}</span>"
            f"<span class='ps' title='Sleeper'>{st}</span>"
            f"<span class='pb' title='blend (ranks the card)'>{p['blend']:.1f}</span></div>")
    badges = ""
    fl = form_flag(p["sig"])
    if fl:
        badges += f"<span class='badge {fl[0]}' title='{html.escape(fl[1])}'>{'&#9650; hot' if fl[0]=='hot' else '&#9660; cold'}</span>"
    if p.get("inj"):
        part = f" &middot; {html.escape(str(p['inj_part']))}" if p.get("inj_part") else ""
        badges += f"<span class='badge inj' title='{html.escape(str(p['inj']))}{part}'>&#10010; {html.escape(str(p['inj']))}</span>"
    if isinstance(p.get("depth"), int) and p["depth"] >= 2 and p["pos"] in ("RB", "WR", "TE"):
        badges += f"<span class='badge depth' title='depth chart slot'>DC{p['depth']}</span>"
    if not p["startable"]:
        why = "Sleeper 0" if isinstance(p["sleeper"], (int, float)) else "no NFL team / not projected"
        badges += f"<span class='badge na' title='Sleeper has no projection ({why}) &mdash; not startable'>&#8709; no Sleeper</span>"
    # V2 strip: line 1 = who (name+meta) + projections; line 2 = inline usage + badges
    who = (f"<div class='who'><span class='name'>{html.escape(p['name'])}</span>"
           f"<span class='meta'>{html.escape(p.get('team','FA') or 'FA')}{age}</span></div>")
    sigrow = f"<div class='sigrow'><span class='sig'>{sig_inline(p)}</span>{badges}</div>"
    return (f"<div class='{cls}'{ostyle}>{chip_html}"
            f"<div class='r1'>{who}{proj}</div>{sigrow}</div>")

def league_board(lg, idx):
    if not lg["drafted"]:
        return (f"<section class='board' id='lg{idx}' hidden><div class='awaiting'>"
                f"<div class='aw-badge'>{'&#9203;'}</div>"
                f"<h2>Awaiting draft</h2><p>{html.escape(lg['name'])} is a redraft league and "
                f"hasn't drafted for 2026 yet (status: {lg['status']}). The board fills in "
                f"automatically once Phargo has a roster.</p></div></section>")
    players, chip, n_flex, n_sf, total = build_league(lg)
    cols = ["QB", "RB", "WR", "TE", "FLEX"] + (["SF"] if n_sf else []) + ["DEF"]
    label = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "FLEX": "FLEX",
             "SF": "SUPERFLEX", "DEF": "DEF"}
    colmap = {c: [] for c in cols}
    for p in players:
        native = p["pos"] if p["pos"] in colmap else None
        if native: colmap[native].append(p)
        if p["pos"] in ("RB", "WR", "TE"): colmap["FLEX"].append(p)
        if n_sf and p["pos"] in ("QB", "RB", "WR", "TE"): colmap["SF"].append(p)
    html_cols = ""
    for c in cols:
        lst = sorted(colmap[c], key=lambda p: (chip.get(p["id"]) is None, -p["blend"]))
        n_in = sum(1 for p in lst if chip.get(p["id"]))
        cards = "".join(card(p, chip, slot_color(chip.get(p["id"]))) for p in lst) or "<div class='empty'>&mdash;</div>"
        extra = " flexcol" if c == "FLEX" else (" sfcol" if c == "SF" else "")
        html_cols += (f"<div class='column{extra}' style='--accent:{COL_COLOR[c]}'>"
                      f"<div class='colhead'><span class='cname'>{label[c]}</span>"
                      f"<span class='cslots'>{n_in} in lineup</span></div>"
                      f"<div class='cards'>{cards}</div></div>")
    fmt = ("Superflex" if lg["superflex"] else "1-QB") + " &middot; " + \
          {"half": "Half PPR", "standard": "Standard", "ppr": "Full PPR"}[lg["scoring"]]
    sub = (f"<div class='lgsub'>{fmt} &middot; projected starting total (blend): "
           f"<b>{total:.1f}</b> pts/wk &middot; ranked by model+Sleeper blend</div>")
    return f"<section class='board' id='lg{idx}' hidden>{sub}<div class='grid'>{html_cols}</div></section>"

# ---------- assemble page ---------------------------------------------------
tabs, boards = "", ""
for i, lg in enumerate(S["leagues"]):
    badge = ("SF" if lg["superflex"] else "1QB")
    state = "" if lg["drafted"] else " pre"
    tabs += (f"<button class='tab{state}' data-i='{i}' onclick='pick({i})'>"
             f"<span class='tname'>{html.escape(lg['name'])}</span>"
             f"<span class='tbadge'>{badge} &middot; {'Half' if lg['scoring']=='half' else ('PPR' if lg['scoring']=='ppr' else 'Std')}"
             f"{'' if lg['drafted'] else ' &middot; pre-draft'}</span></button>")
    boards += league_board(lg, i)

CSS = open(os.path.join(os.path.dirname(__file__), "board.css")).read()
cols_btns = "".join(f"<button data-c='{c}'>{c}</button>" for c in range(2, 8))
cols_ctrl = (f"<div class='cols-ctrl'>Columns in view:<div class='cols-btns'>{cols_btns}</div>"
             f"<span class='cols-hint'>(saved on this device)</span></div>")
JS = ("function pick(i){document.querySelectorAll('.board').forEach((b,n)=>b.hidden=(n!=i));"
      "document.querySelectorAll('.tab').forEach((t,n)=>t.setAttribute('aria-current',n==i?'true':'false'));"
      "document.querySelectorAll('.grid').forEach(g=>g.scrollLeft=0);}"
      "function setCols(n){document.documentElement.style.setProperty('--cols',n);"
      "try{localStorage.setItem('ss_cols',n)}catch(e){}"
      "document.querySelectorAll('.cols-btns button').forEach(b=>b.setAttribute('aria-current',b.dataset.c==n?'true':'false'));}"
      "document.addEventListener('DOMContentLoaded',()=>{"
      "document.querySelectorAll('.cols-btns button').forEach(b=>b.addEventListener('click',()=>setCols(b.dataset.c)));"
      "var s=null;try{s=localStorage.getItem('ss_cols')}catch(e){}if(s)setCols(s);"
      "var f=Array.from(document.querySelectorAll('.tab')).findIndex(t=>!t.classList.contains('pre'));"
      "pick(f<0?0:f);});")

OUT = os.path.join(SCRATCH, "index.html")
page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Phargo &mdash; Start/Sit, all leagues</title>\n<style>{CSS}</style></head><body>\n"
        f"<div class='wrap'><h1>Phargo &mdash; <span class='hl'>start / sit board</span>"
        f"<span class='yr'>2026 &middot; all leagues</span></h1>"
        f"<div class='legend'><b class='pm'>model</b> our nflverse model &middot; "
        f"<b class='ps'>slpr</b> Sleeper &middot; <b class='pb'>blend</b> ranks the card &nbsp;|&nbsp; "
        f"chip = lineup slot &middot; &#9650;/&#9660; hot/cold (L3 vs season) &middot; &#10010; injury &middot; "
        f"&#8709; pink = Sleeper says not startable</div>"
        f"{cols_ctrl}"
        f"<div class='tabs'>{tabs}</div>{boards}</div>\n<script>{JS}</script></body></html>")
open(OUT, "w", encoding="utf-8").write(page)
print("wrote", OUT, len(page), "bytes")
for lg in S["leagues"]:
    if lg["drafted"]:
        pl, chip, nf, nsf, tot = build_league(lg)
        starters = [(chip[p['id']], p['name'], p['blend']) for p in pl if chip.get(p['id'])]
        starters.sort(key=lambda x: x[0])
        print(f"\n{lg['name']} ({lg['scoring']}, sf={lg['superflex']}) total={tot}")
        for s in starters: print(f"  {s[0]:6} {s[1]:22} {s[2]}")
