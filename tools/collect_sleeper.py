import json, urllib.request as U, os
API1="https://api.sleeper.app/v1"; APIP="https://api.sleeper.com"
PUID="325677742303494144"
SCRATCH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO=r"C:\Users\rober\Python Programs\fantasyfootball\FantasyFootball"
LEAGUES=[
 ("1st or Last","1389754074538205184"),
 ("Buschhhhhhhhhhhh League","1335758318781616128"),
 ("And the Award Goes To...","1312151628572274688"),
 ("The Axe Man Cometh","1309393563053744128"),
]
def get(u):
    req=U.Request(u, headers={"User-Agent":"Mozilla/5.0 (board)"})
    with U.urlopen(req, timeout=60) as r: return json.load(r)

leagues=[]
for name,lid in LEAGUES:
    L=get(f"{API1}/league/{lid}")
    rosters=get(f"{API1}/league/{lid}/rosters")
    mine=next((r for r in rosters if r.get("owner_id")==PUID or (r.get("co_owners") and PUID in r.get("co_owners"))), None)
    rp=L.get("roster_positions",[])
    rec=L.get("scoring_settings",{}).get("rec",0)
    scoring = "ppr" if rec>=1.0 else ("half" if rec>=0.4 else "standard")
    players=(mine or {}).get("players") or []
    leagues.append({"name":name,"league_id":lid,"roster_positions":rp,
        "scoring_rec":rec,"scoring":scoring,"superflex":"SUPER_FLEX" in rp,
        "status":L.get("status"),"season":L.get("season"),
        "players":players,"starters":(mine or {}).get("starters") or [],
        "drafted": len(players)>0})
    print(f"{name:28} scoring={scoring:8} sf={'SUPER_FLEX' in rp} players={len(players)} status={L.get('status')}")

proj={}
pos_q="&".join(f"position[]={p}" for p in ["QB","RB","WR","TE","DEF"])
plist=get(f"{APIP}/projections/nfl/2026/1?season_type=regular&{pos_q}&order_by=pts_ppr")
for r in plist:
    pid=str(r.get("player_id")); st=r.get("stats",{}) or {}
    proj[pid]={"standard":st.get("pts_std"),"half":st.get("pts_half_ppr"),"ppr":st.get("pts_ppr")}
print("sleeper proj players:", len(proj))

sp=json.load(open(os.path.join(REPO,"data","sleeper_players.json"),encoding="utf-8"))
meta={}; need=set()
for lg in leagues: need|=set(lg["players"])
for pid in need:
    p=sp.get(pid) or {}
    fp=p.get("fantasy_positions") or ([p.get("position")] if p.get("position") else [])
    nm=p.get("full_name") or (str(p.get("first_name","") )+" "+str(p.get("last_name",""))).strip()
    isdef = (p.get("position")=="DEF") or (len(pid)<=3 and not nm)
    meta[pid]={"name": nm or (pid+" DEF" if isdef else pid),
        "pos": ("DEF" if isdef else (fp[0] if fp else p.get("position"))),
        "team": (pid if isdef else (p.get("team") or "FA")),
        "age": p.get("age"), "inj": p.get("injury_status"),
        "inj_part": p.get("injury_body_part"), "depth": p.get("depth_chart_order"),
        "status": p.get("status")}
json.dump({"leagues":leagues,"sleeper_proj":proj,"meta":meta},
          open(os.path.join(SCRATCH,"sleeper_input.json"),"w"), indent=0)
print("wrote sleeper_input.json  leagues:",len(leagues)," proj:",len(proj)," meta:",len(meta))
