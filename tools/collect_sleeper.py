"""Pull the Sleeper side for all of Phargo's leagues -> sleeper_input.json.

Portable / CI-friendly: player metadata is fetched live from Sleeper's public
players endpoint (so injury status is current), with no dependency on a local
file. Rosters, league config, and Sleeper's own projections come from the API.
No auth required.
"""
import json, urllib.request as U, os

API1 = "https://api.sleeper.app/v1"
APIP = "https://api.sleeper.com"
PUID = "325677742303494144"                      # Phargo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tab order on the board. Leagues Sleeper returns that are not named here are
# appended in Sleeper's own order, so a new league shows up without a code change.
# Matched loosely, so a rename like "The Axe Man Cometh" -> "\U0001fa93 The Axe Man
# Cometh" keeps its slot.
ORDER = [
    "1st or Last",
    "Buschhhhhhhhhhhh League",
    "And the Award Goes To...",
    "The Axe Man Cometh",
]


def get(u):
    req = U.Request(u, headers={"User-Agent": "phargo-startsit/1.0"})
    with U.urlopen(req, timeout=90) as r:
        return json.load(r)


def _key(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def _rank(name):
    k = _key(name)
    for i, want in enumerate(ORDER):
        w = _key(want)
        if k == w or w in k or k in w:
            return i
    return len(ORDER)


def discover():
    """Phargo's leagues for the current season, straight from Sleeper.

    League ids are NOT stable: Sleeper mints a new one every season, and a league
    recreated from scratch does not even carry previous_league_id. A hardcoded list
    therefore goes stale on rollover and the whole run dies on a 404 -- which is
    exactly what happened to "The Axe Man Cometh". Asking Sleeper which leagues the
    user is actually in cannot go stale.
    """
    season = (get(f"{API1}/state/nfl") or {}).get("league_season")
    ls = get(f"{API1}/user/{PUID}/leagues/nfl/{season}") or []
    ls.sort(key=lambda l: (_rank(l.get("name")), l.get("name") or ""))
    print(f"season {season}: {len(ls)} leagues")
    return [(l.get("name") or l["league_id"], l["league_id"]) for l in ls]


# 1) per-league config + Phargo roster
leagues = []
for name, lid in discover():
    L = get(f"{API1}/league/{lid}")
    rosters = get(f"{API1}/league/{lid}/rosters")
    mine = next((r for r in rosters if r.get("owner_id") == PUID
                 or (r.get("co_owners") and PUID in r.get("co_owners"))), None)
    rp = L.get("roster_positions", [])
    rec = L.get("scoring_settings", {}).get("rec", 0)
    scoring = "ppr" if rec >= 1.0 else ("half" if rec >= 0.4 else "standard")
    players = (mine or {}).get("players") or []
    leagues.append({"name": name, "league_id": lid, "roster_positions": rp,
                    "scoring_rec": rec, "scoring": scoring, "superflex": "SUPER_FLEX" in rp,
                    "status": L.get("status"), "season": L.get("season"),
                    "players": players, "starters": (mine or {}).get("starters") or [],
                    "drafted": len(players) > 0})
    print(f"{name:28} scoring={scoring:8} sf={'SUPER_FLEX' in rp} players={len(players)} status={L.get('status')}")

# 2) Sleeper wk1 2026 projections (the 'sl' column), pts per scoring level
proj = {}
pos_q = "&".join(f"position[]={p}" for p in ["QB", "RB", "WR", "TE", "DEF"])
for r in get(f"{APIP}/projections/nfl/2026/1?season_type=regular&{pos_q}&order_by=pts_ppr"):
    pid = str(r.get("player_id")); st = r.get("stats", {}) or {}
    proj[pid] = {"standard": st.get("pts_std"), "half": st.get("pts_half_ppr"), "ppr": st.get("pts_ppr")}
print("sleeper proj players:", len(proj))

# 3) player meta live from Sleeper (fresh injuries/depth) for rostered players only
sp = get(f"{API1}/players/nfl")
meta = {}; need = set()
for lg in leagues:
    need |= set(lg["players"])
for pid in need:
    p = sp.get(pid) or {}
    fp = p.get("fantasy_positions") or ([p.get("position")] if p.get("position") else [])
    nm = p.get("full_name") or (str(p.get("first_name", "")) + " " + str(p.get("last_name", ""))).strip()
    isdef = (p.get("position") == "DEF") or (len(pid) <= 3 and not nm)
    meta[pid] = {"name": nm or (pid + " DEF" if isdef else pid),
                 "pos": ("DEF" if isdef else (fp[0] if fp else p.get("position"))),
                 "team": (pid if isdef else (p.get("team") or "FA")),
                 "age": p.get("age"), "inj": p.get("injury_status"),
                 "inj_part": p.get("injury_body_part"), "depth": p.get("depth_chart_order"),
                 "status": p.get("status")}

json.dump({"leagues": leagues, "sleeper_proj": proj, "meta": meta},
          open(os.path.join(ROOT, "sleeper_input.json"), "w"), indent=0)
print("wrote sleeper_input.json  leagues:", len(leagues), " proj:", len(proj), " meta:", len(meta))
