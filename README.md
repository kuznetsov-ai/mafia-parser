# Mafia Tournament Analyzer

A web app for analyzing joint game statistics from [mafgame.org](https://mafgame.org) tournaments.

**Shows which players you've sat at the same table with, and how many times.**

## Features

- Displays tournaments from mafgame.org within ±2 days of today
- Marks tournaments with/without seating data
- Click a tournament → player list loads automatically
- Select your nickname → see joint game count with every other player
- Results sorted by number of joint games, with % of your games together
- 10-minute cache — first load warms it up, subsequent visits are instant
- UI in English, Russian, Ukrainian

## Stack

- **Backend:** Python + Flask
- **Data source:** mafgame.org Inertia.js API (no scraping, uses the site's own JSON)
- **Frontend:** Vanilla JS + HTML/CSS (no frameworks)

## Setup

```bash
pip install flask requests beautifulsoup4
python app.py
```

Open [http://localhost:5055](http://localhost:5055)

## How it works

mafgame.org is built on Laravel + Inertia.js + React. Page data is embedded as JSON in the HTML (`data-page` attribute) and also available via `X-Inertia` headers. The app reads `game_results` for each tournament, parses the `seats` object (keyed as `part-session-table-seat`), and groups players by table to count co-occurrences.
