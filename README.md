# Mafia Tournament Analyzer

A web app for analyzing joint game statistics from [mafgame.org](https://mafgame.org) and [imafia.org](https://imafia.org) tournaments.

**Shows which players you've sat at the same table with, and how many times.**

## Features

- Aggregates tournaments from **mafgame.org** and **imafia.org** within ±2 days of today
- Filter by source: All / Mafgame / iMafia
- Marks tournaments with/without seating data
- Click a tournament → player list loads automatically
- Select your nickname → see joint game count with every other player
- Results sorted by number of joint games, with % of your games together
- 10-minute cache with manual refresh button
- UI in English, Russian, Ukrainian

## Stack

- **Backend:** Python + Flask
- **Data sources:**
  - mafgame.org — Inertia.js API (JSON via `X-Inertia` headers)
  - imafia.org — HTML scraping (BeautifulSoup, div-based game layout)
- **Frontend:** Vanilla JS + HTML/CSS (no frameworks)

## Setup

```bash
pip install flask requests beautifulsoup4
python app.py
```

Open [http://localhost:5055](http://localhost:5055)

## How it works

### mafgame.org
Built on Laravel + Inertia.js + React. Page data is embedded as JSON in the HTML (`data-page` attribute) and also available via `X-Inertia` headers. The app reads `game_results` for each tournament, parses the `seats` object (keyed as `part-session-table-seat`), and groups players by table to count co-occurrences.

### imafia.org
Uses a custom div-based layout for game data. Each game is a `div.games_item` containing `div.games_item_tr` rows with `div.games_item_td` cells (seat number, role icon, score, player name). The parser finds these within the `#tournament-results` section and extracts player names to build game tables.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/tournaments` | GET | List tournaments ±2 days from both sources |
| `/api/players?url=` | GET | Get player list for a tournament URL |
| `/api/analyze?url=&nickname=` | GET | Analyze joint games for a player |
| `/api/refresh` | POST | Clear cache (body: `{"url": "..."}` or `{}` for all) |
