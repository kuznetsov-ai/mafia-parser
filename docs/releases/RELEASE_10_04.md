# Release 10.04.2026

## Fix imafia.org seating parser + UI improvements

### Bug fix: imafia game parsing

**Problem:** The imafia.org parser searched for `<table>` HTML elements to find game seating data. However, imafia.org uses a `<div>`-based layout (`div.games_item`) for games, not `<table>`. The participants list (`players_info_table`) happened to have the same 4-column structure as what the parser expected for game tables, causing:
- Tournaments with no games were falsely reported as having seating data
- The participant list was treated as a single game table, producing incorrect joint-game analysis
- Referee tables were also incorrectly matched

**Fix:** Rewrote `fetch_imafia()` to parse the actual game structure:
- Finds `div.games_item_js` elements inside `#tournament-results` section
- Extracts player rows from `div.games_item_content > div.games_item_tr`
- Player name from the 4th `games_item_td` (index 3) in each row
- Tournaments without games now correctly return 0 game tables

**Verified on:**
- Tournament 1600 (no games): 0 tables, empty players (was: 1 fake table with 10 "players")
- Tournament 1560 (6 games, 10 players): 6 tables x 10 players each
- Tournament 1520 (10 games, 10 players): correct parsing and analysis

### New features

- **Source filter tabs** (All / Mafgame / iMafia) — filter tournament list by platform
- **iMafia badge** on tournament cards
- **Cache refresh button** (↻) — clears cache and reloads tournament data
- **`/api/refresh` endpoint** — POST to clear cache (specific URL or all)
- Clean up empty location/participant display for imafia tournaments

### Files changed

- `app.py` — rewrote `fetch_imafia()`, added `cache_bust()`, `/api/refresh` route, imafia tournament merging, site detection
- `templates/index.html` — source filter tabs, refresh button, iMafia badge styling, i18n keys
