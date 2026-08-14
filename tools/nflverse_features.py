"""Model projections + 2025 usage signals from nflverse parquets, keyed by
normalized player name (the Sleeper<->nflverse bridge). Output: features.json."""
import pandas as pd, numpy as np, json, re, os
REPO=r"C:\Users\rober\Python Programs\fantasyfootball\FantasyFootball"
SCRATCH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
def norm(s): return re.sub(r'[^a-z]','',str(s).lower())
YEAR=2025
SUFFIX={"ppr":"","half":"_half","standard":"_standard"}

# ---- model projections: mean 2025 opponent-adjusted exp_fpts, per scoring ----
model={}  # norm_name -> {scoring: proj}
for scoring,suf in SUFFIX.items():
    for pos in ("wr","rb","te"):
        f=f"data/expected_fpts_{pos}{suf}.parquet"
        if not os.path.exists(f): continue
        d=pd.read_parquet(f)
        d=d[d.season==YEAR]
        g=d.groupby("player_display_name")["exp_fpts"].mean()
        for nm,v in g.items():
            model.setdefault(norm(nm),{})[scoring]=round(float(v),1)

# ---- QB model projection: carry-forward 2025 mean fantasy pts (std QB scoring) ----
qb=pd.read_parquet("data/qb_weekly_full.parquet")
qb=qb[qb.season==YEAR].copy()
qb["fp"]=qb.passing_yards*0.04+qb.passing_tds*4+qb.interceptions.fillna(0)*(-1)+qb.rushing_yards*0.1+qb.rushing_tds*6
qbg=qb.groupby("player_display_name").agg(gp=("week","size"),fp=("fp","mean"),
    att=("attempts","mean"),pyd=("passing_yards","mean"),ptd=("passing_tds","sum"),
    ryd=("rushing_yards","mean"),rtd=("rushing_tds","sum"))
for nm,r in qbg.iterrows():
    v=round(float(r.fp),1)
    model.setdefault(norm(nm),{}).update({"ppr":v,"half":v,"standard":v})  # QB same across scorings

# ---- signals (2025): usage + form ----
sig={}
def last3_mean(s): 
    a=s.dropna().tolist(); return round(float(np.mean(a[-3:])),1) if a else None
for pos in ("wr","rb","te"):
    d=pd.read_parquet(f"data/{pos}_weekly_full.parquet")
    d=d[d.season==YEAR].copy()
    d["fp_half"]=d.receptions*0.5+d.receiving_yards*0.1+d.receiving_tds*6+d.rushing_yards*0.1+d.rushing_tds*6
    d["gtd"]=d.receiving_tds+d.rushing_tds
    for nm,grp in d.sort_values("week").groupby("player_display_name"):
        gp=len(grp)
        sig[norm(nm)]={"pos":pos.upper(),"gp":int(gp),
            "snap":int(round(grp.snap_share.mean())) if grp.snap_share.notna().any() else None,
            "tgt_pg":round(grp.targets.mean(),1),"car_pg":round(grp.carries.mean(),1),
            "ryd_pg":round(grp.receiving_yards.mean(),1),"rush_pg":round(grp.rushing_yards.mean(),1),
            "td":int(grp.gtd.sum()),
            "l3":last3_mean(grp.fp_half),"sea":round(grp.fp_half.mean(),1),
            "td_l3":int(grp.gtd.tolist()[-3:] and sum(grp.gtd.tolist()[-3:]))}
# QB signals
qb2=qb.sort_values("week")
for nm,grp in qb2.groupby("player_display_name"):
    sig[norm(nm)]={"pos":"QB","gp":int(len(grp)),
        "att_pg":round(grp.attempts.mean(),1),"pyd_pg":int(round(grp.passing_yards.mean())),
        "ptd":int(grp.passing_tds.sum()),"rush_pg":round(grp.rushing_yards.mean(),1),
        "rtd":int(grp.rushing_tds.sum()),
        "l3":last3_mean(grp.fp),"sea":round(grp.fp.mean(),1)}

json.dump({"model":model,"signals":sig}, open(os.path.join(SCRATCH,"features.json"),"w"))
print("features: model",len(model),"signals",len(sig))
# spot checks
for nm in ["justinjefferson","saquonbarkley","patrickmahomes","quinshonjudkins","tetairoamcmillan"]:
    print(f"  {nm:20} model={model.get(nm)} sig_gp={sig.get(nm,{}).get('gp')}")
