# Phargo Start/Sit

A weekly start/sit board across all of Phargo's fantasy leagues, hosted on GitHub Pages.

**Live:** https://phargo361.github.io/phargo-startsit/

One tab per league. Each league is scored to its own rules (half PPR / standard / full PPR),
and the optimal lineup respects that league's slots (including SUPERFLEX). Redraft leagues that
haven't drafted yet show an "awaiting draft" card until a roster exists.

## Data sources
- **Model projection + usage signals** — nflverse game logs via our `wrxp` expected-points model
  (snaps, targets/carries, yards, TDs, hot/cold form). Lives in the `FantasyFootball` repo.
- **Sleeper API** — rosters, league config, and Sleeper's own projection column.

## Regenerate `index.html`
From the `FantasyFootball` repo (which holds the model + cached nflverse parquets):

```
python tools/collect_sleeper.py       # rosters, league config, Sleeper projections
python tools/nflverse_features.py     # model projections + 2025 signals from parquets
python tools/board_build.py           # writes phargo_startsit.html
```
Copy the result to `index.html` here and push. The page is a self-contained static file
(CSS/JS inlined), so GitHub Pages serves it as-is.
