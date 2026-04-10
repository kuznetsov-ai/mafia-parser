from flask import Flask, render_template, request, jsonify
import requests
import re
import json
import html as html_lib
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo('Europe/Nicosia')
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

app = Flask(__name__)

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0'})

# Simple TTL cache
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 600  # 10 minutes


def cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() - entry['ts'] < CACHE_TTL:
            return entry['val']
    return None


def cache_set(key, val):
    with _cache_lock:
        _cache[key] = {'val': val, 'ts': time.time()}


def cache_bust(url):
    """Remove a specific URL from cache."""
    with _cache_lock:
        keys_to_delete = [k for k in _cache if url in k]
        for k in keys_to_delete:
            del _cache[k]


# ── imafia.org parser ──────────────────────────────────────────────────────

def _is_game_table(rows):
    """Check if a table is a game seating table (4 cols, digit seat, player name).
    Legacy: only used for old-format imafia pages that still use <table> for games.
    """
    if len(rows) < 2:
        return False
    header_cells = rows[0].find_all(['td', 'th'])
    header_text = ' '.join(c.get_text(strip=True) for c in header_cells)
    if 'Гравець' in header_text or ('Б' in header_text and 'Ci' in header_text):
        return False
    valid_rows = 0
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 4:
            continue
        seat = cells[0].get_text(strip=True)
        player = cells[2].get_text(strip=True)
        if seat.isdigit() and int(seat) <= 15 and re.search(r'[A-Za-zА-Яа-яёЁіІїЇєЄ]', player):
            valid_rows += 1
    return valid_rows >= 2


def _extract_nick(raw):
    """Extract nickname from 'Nick(Real Name)' format."""
    m = re.match(r'^([^(]+)', raw)
    return m.group(1).strip() if m else raw.strip()


def fetch_imafia_tournaments(date_from, date_to):
    """Fetch imafia.org tournament list filtered by date range."""
    from bs4 import BeautifulSoup

    cache_key = f'imafia_list:{date_from}:{date_to}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        r = SESSION.get('https://imafia.org/tournaments', timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception:
        return []

    # Collect basic info from listing page first
    pending = []
    links = [l for l in soup.find_all('a', href=True) if '/tournament/' in l.get('href', '')]

    for l in links:
        text = l.get_text(separator=' ', strip=True)
        m = re.match(r'(\d{2})\.(\d{2})\.(\d{2})\b', text)
        if not m:
            continue
        day, month, year = m.groups()
        year = f'20{year}' if len(year) == 2 else year
        date_str = f'{year}-{month}-{day}'

        if not (date_from <= date_str <= date_to):
            continue

        tid = l['href'].split('/')[-1]
        url = f'https://imafia.org/tournament/{tid}'

        level_img = l.find('img', class_='tournaments_item_level_img')
        level = level_img.get('title', '') if level_img else ''

        # Participants: last number before "/" in listing text (e.g. "10 / Серія")
        parts_match = re.search(r'(\d+)\s*/\s*\S+\s*$', text)
        participants = int(parts_match.group(1)) if parts_match else 0

        pending.append({
            'tid': tid, 'url': url, 'date': date_str, 'level': level,
            'online': 'online' in text.lower(), 'participants': participants,
        })

    # Fetch name + seating for each tournament in parallel (single request per tournament)
    def _fetch_one(info):
        data = fetch_imafia(info['url'])
        return {
            'id': info['tid'],
            'name': data.get('name') or f'iMafia #{info["tid"]}',
            'city': '',
            'country': '',
            'date': info['date'],
            'stars': '',
            'level': info['level'],
            'online': info['online'],
            'participants': info['participants'],
            'has_seating': len(data.get('game_tables', [])) > 0,
            'url': info['url'],
            'source': 'imafia',
        }

    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_one, p): p for p in pending}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    results.sort(key=lambda t: t['date'])
    cache_set(cache_key, results)
    return results


def fetch_imafia(url):
    """Fetch imafia.org tournament page. Returns name + game_tables (single HTTP request).

    game_tables: list of lists — each inner list is players at one game table.
    """
    from bs4 import BeautifulSoup

    cache_key = f'imafia:{url}'
    cached = cache_get(cache_key)
    if cached:
        return cached

    r = SESSION.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Extract name from h1
    h1 = soup.find('h1')
    name = h1.get_text(strip=True).replace('share', '').strip() if h1 else ''

    # Parse games from div-based layout
    game_tables = []
    results_section = soup.find('div', id='tournament-results')
    if results_section:
        game_items = results_section.find_all(
            'div', class_=lambda c: c and 'games_item_js' in c.split())
        for gi in game_items:
            content = gi.find('div', class_='games_item_content')
            if not content:
                continue
            players_in_game = []
            rows = content.find_all(
                'div', class_=lambda c: c and 'games_item_tr' in c.split(),
                recursive=False)
            for row in rows:
                tds = row.find_all('div', class_='games_item_td', recursive=False)
                if len(tds) >= 4:
                    nick = tds[3].get_text(strip=True)
                    if nick:
                        players_in_game.append(nick)
            if players_in_game:
                game_tables.append(players_in_game)

    result = {'name': name, 'game_tables': game_tables}
    cache_set(cache_key, result)
    return result


def imafia_get_players(data):
    """Get all unique players from imafia game tables."""
    players = set()
    for table in data['game_tables']:
        players.update(table)
    return sorted(players)


def imafia_analyze(data, target_nickname):
    """Count joint games for target player from imafia data."""
    joint_games = defaultdict(int)
    player_games = defaultdict(int)
    target_games = 0

    for players in data['game_tables']:
        for p in players:
            player_games[p] += 1
        if target_nickname in players:
            target_games += 1
            for p in players:
                if p != target_nickname:
                    joint_games[p] += 1

    results = [
        {'player': p, 'joint': c, 'total': player_games[p],
         'pct': round(c / target_games * 100) if target_games else 0}
        for p, c in sorted(joint_games.items(), key=lambda x: x[1], reverse=True)
    ]
    return results, target_games


def get_inertia_data(url):
    """Fetch Inertia.js page data from mafgame.org."""
    cache_key = f'inertia:{url}'
    cached = cache_get(cache_key)
    if cached:
        return cached

    r0 = SESSION.get(url, timeout=15)
    r0.raise_for_status()
    m = re.search(r'data-page="([^"]+)"', r0.text)
    if not m:
        raise ValueError('Could not find page data. Make sure this is a mafgame.org page.')
    version = json.loads(html_lib.unescape(m.group(1))).get('version', '1')

    tid = re.search(r'/tournaments/(\d+)', url)
    if not tid:
        raise ValueError('Could not determine tournament ID from URL')
    tid = tid.group(1)

    r = SESSION.get(f'https://mafgame.org/tournaments/{tid}/game_results',
                    headers={'X-Inertia': 'true', 'X-Inertia-Version': version, 'Accept': 'application/json'},
                    timeout=15)
    r.raise_for_status()
    result = r.json()['props']
    cache_set(cache_key, result)
    return result


def parse_seats(props):
    """Parse seats data: {round-table-game-seat: player_info}"""
    games_data = props.get('games', {})
    if not isinstance(games_data, dict):
        return {}
    seats = games_data.get('seats', {})
    # Seats is a list when tournament has no seating yet — return empty dict
    if not isinstance(seats, dict):
        return {}
    return seats


def get_all_players(seats):
    """Get sorted list of all unique player nicknames."""
    players = set()
    for seat_data in seats.values():
        nick = seat_data.get('original_nickname') or seat_data.get('player', {}).get('nickname', '')
        if nick:
            players.add(nick)
    return sorted(players)


def analyze(seats, target_nickname):
    """Count joint games (same table) for target player."""
    # Group players by table: key format is part-session-table-seat, group by first 3 parts
    tables = defaultdict(list)
    for key, seat_data in seats.items():
        parts = key.split('-')
        if len(parts) >= 4:
            table_key = '-'.join(parts[:3])
            nick = seat_data.get('original_nickname') or seat_data.get('player', {}).get('nickname', '')
            if nick:
                tables[table_key].append(nick)

    joint_games = defaultdict(int)
    player_games = defaultdict(int)
    target_games = 0

    for table_key, players in tables.items():
        for p in players:
            player_games[p] += 1
        if target_nickname in players:
            target_games += 1
            for p in players:
                if p != target_nickname:
                    joint_games[p] += 1

    results = []
    for player, count in sorted(joint_games.items(), key=lambda x: x[1], reverse=True):
        results.append({
            'player': player,
            'joint': count,
            'total': player_games[player],
            'pct': round(count / target_games * 100) if target_games else 0,
        })

    return results, target_games


def get_inertia_version():
    r = SESSION.get('https://mafgame.org/tournaments', timeout=10)
    m = re.search(r'data-page="([^"]+)"', r.text)
    if m:
        return json.loads(html_lib.unescape(m.group(1))).get('version', '1')
    return '1'


def has_seating(tournament_id):
    """Check if a tournament has seating data."""
    cache_key = f'seating:{tournament_id}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        props = get_inertia_data(f'https://mafgame.org/tournaments/{tournament_id}/view')
        seats = parse_seats(props)
        result = len(seats) > 0
    except Exception:
        result = False
    cache_set(cache_key, result)
    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/tournaments')
def api_tournaments():
    today = datetime.now(TIMEZONE)
    date_from = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    date_to = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    cache_key = f'tournaments:{date_from}:{date_to}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    try:
        version = get_inertia_version()
        # Single request — mafgame.org API filters by date range server-side
        r = SESSION.get('https://mafgame.org/tournaments',
            headers={'X-Inertia': 'true', 'X-Inertia-Version': version, 'Accept': 'application/json'},
            params={'date_from': date_from, 'date_to': date_to, 'per_page': 100},
            timeout=15)
        r.raise_for_status()
        results = r.json().get('props', {}).get('search_results', {})
        all_tournaments = results.get('data', [])

        # Strict date filter in case API returns extra results
        all_tournaments = [t for t in all_tournaments
                           if date_from <= t.get('start_date', '') <= date_to]

        all_tournaments.sort(key=lambda t: t.get('start_date', ''))

        # Check seating for each tournament in parallel
        def check_t(t):
            seating = has_seating(t['id'])
            return {
                'id': t['id'],
                'name': t['name'],
                'city': t.get('city', ''),
                'country': t.get('country', ''),
                'date': t.get('start_date', ''),
                'stars': '⭐' * int(t.get('no_of_stars', 0)),
                'online': bool(t.get('online')),
                'participants': t.get('expected_participants', 0),
                'has_seating': seating,
                'url': f"https://mafgame.org/tournaments/{t['id']}/view",
            }

        result = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(check_t, t): t for t in all_tournaments}
            for future in as_completed(futures):
                result.append(future.result())

        result.sort(key=lambda t: t['date'])

        # Add source tag for mafgame tournaments
        for t in result:
            t['source'] = 'mafgame'

        # Merge imafia tournaments
        try:
            imafia_tournaments = fetch_imafia_tournaments(date_from, date_to)
            result.extend(imafia_tournaments)
        except Exception:
            pass  # Don't fail if imafia is unavailable

        result.sort(key=lambda t: t['date'])

        payload = {'tournaments': result, 'date_from': date_from, 'date_to': date_to}
        cache_set(cache_key, payload)
        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _detect_site(url):
    """Detect which site the URL belongs to."""
    if 'imafia.org' in url:
        return 'imafia'
    return 'mafgame'


@app.route('/api/players')
def api_players():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    try:
        if _detect_site(url) == 'imafia':
            data = fetch_imafia(url)
            players = imafia_get_players(data)
            if not players:
                return jsonify({'error': 'Seating not ready — no game data available yet'}), 404
        else:
            props = get_inertia_data(url)
            seats = parse_seats(props)
            if not seats:
                return jsonify({'error': 'Seating not ready — no game data available yet'}), 404
            players = get_all_players(seats)
        return jsonify({'players': players})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze')
def api_analyze():
    url = request.args.get('url', '').strip()
    nickname = request.args.get('nickname', '').strip()
    if not url or not nickname:
        return jsonify({'error': 'URL and nickname are required'}), 400
    try:
        site = _detect_site(url)
        if site == 'imafia':
            data = fetch_imafia(url)
            players = imafia_get_players(data)
            results, total = imafia_analyze(data, nickname)
        else:
            props = get_inertia_data(url)
            seats = parse_seats(props)
            players = get_all_players(seats)
            results, total = analyze(seats, nickname)

        if not results:
            match = next((p for p in players if p.lower() == nickname.lower()), None)
            if match:
                if site == 'imafia':
                    results, total = imafia_analyze(data, match)
                else:
                    results, total = analyze(seats, match)
                nickname = match
            else:
                return jsonify({'error': f'Player "{nickname}" not found in this tournament.'}), 404
        return jsonify({'results': results, 'total_games': total, 'nickname': nickname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Force clear cache for a specific tournament URL."""
    url = request.json.get('url', '').strip() if request.json else ''
    if url:
        cache_bust(url)
    else:
        # Clear all cache
        with _cache_lock:
            _cache.clear()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True, port=5055)

