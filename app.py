from flask import Flask, render_template, request, jsonify
import requests
import re
import json
import html as html_lib
from collections import defaultdict
from datetime import datetime, timedelta
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
    # Use UTC+3 (Cyprus/Moscow) for tournament dates
    today = datetime.utcnow() + timedelta(hours=3)
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

        payload = {'tournaments': result, 'date_from': date_from, 'date_to': date_to}
        cache_set(cache_key, payload)
        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/players')
def api_players():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    try:
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
        props = get_inertia_data(url)
        seats = parse_seats(props)
        results, total = analyze(seats, nickname)
        if not results:
            players = get_all_players(seats)
            # Fallback: case-insensitive match
            match = next((p for p in players if p.lower() == nickname.lower()), None)
            if match:
                results, total = analyze(seats, match)
                nickname = match
            else:
                return jsonify({'error': f'Player "{nickname}" not found in this tournament.'}), 404
        return jsonify({'results': results, 'total_games': total, 'nickname': nickname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5055)

