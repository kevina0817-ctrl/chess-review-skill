#!/usr/bin/env python3
"""Opt-in, sequential Chess.com PubAPI rating history. No credentials required."""
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

DOC = 'https://www.chess.com/news/view/published-data-api'
DRAW = {'agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient'}
LOSS = {'checkmated', 'timeout', 'resigned', 'lose', 'abandoned', 'kingofthehill', 'threecheck', 'bughousepartnerlose'}

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

def request(url):
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
        '--max-time', '45', '--retry', '2', '--user-agent', 'ChessReview/3.2 (rating history)', url],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def normalize(username, archives, monthly, stats):
    games = {}
    for month in monthly:
        for game in month['games']:
            side = next((s for s in ('white', 'black') if game[s]['username'].casefold() == username.casefold()), None)
            if not side:
                raise ValueError('Archive contains a game belonging to another account')
            me, opp = game[side], game['black' if side == 'white' else 'white']
            match = re.fullmatch(r'https://www\.chess\.com/game/(live|daily)/(\d+)', game['url'])
            if not match or not isinstance(game.get('end_time'), int):
                raise ValueError('Unexpected completed game identity')
            key = '/'.join(match.groups())
            result = 'win' if me['result'] == 'win' else 'draw' if me['result'] in DRAW else 'loss' if me['result'] in LOSS or opp['result'] == 'win' else 'unknown'
            rating = me.get('rating')
            games[key] = dict(id=key, url=game['url'], end_time=game['end_time'], side=side,
                rating=rating if type(rating) is int else None, opponent=opp['username'],
                opponent_rating=opp.get('rating'), result=result, rated=game.get('rated') is True,
                rules=game.get('rules'), pool=game.get('time_class'), time_control=game.get('time_control'))
    return dict(version=1, username=username, source=DOC, synced_at=int(dt.datetime.now(dt.timezone.utc).timestamp()),
        archives=archives, status='ok', games=sorted(games.values(), key=lambda g:(g['end_time'],g['id'])),
        current={key.removeprefix('chess_'):value['last'] for key,value in stats.items()
            if key in ('chess_rapid','chess_blitz','chess_bullet','chess_daily') and 'last' in value})

def sync(username, cache_dir, get=request):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', username):
        raise ValueError('Invalid Chess.com username')
    base = f'https://api.chess.com/pub/player/{username.lower()}'
    archives = get(base + '/games/archives')['archives']
    months = []
    for url in archives:
        if not re.fullmatch(re.escape(base) + r'/games/\d{4}/\d{2}', url, re.I):
            raise ValueError('Unexpected archive URL')
        data = get(url)  # Deliberately sequential: PubAPI can reject parallel requests.
        if not isinstance(data.get('games'), list):
            raise ValueError('Invalid monthly archive')
        months.append(data)
        atomic_json(Path(cache_dir) / (url[-7:].replace('/', '-') + '.json'), data)
    stats = get(base + '/stats')
    history = normalize(username, archives, months, stats)
    atomic_json(Path(cache_dir) / 'history.json', history)  # Only publish a complete snapshot.
    return history

def update_from_config(root, data):
    config_path = root / '.chess-review-ratings.json'
    if not config_path.exists():
        return
    cfg = json.loads(config_path.read_text())
    if cfg['username'].casefold() != data['user'].casefold():
        raise ValueError('Rating account must match review account')
    try:
        data['rating_history'] = sync(cfg['username'], root / cfg['cache_dir'])
        print('Rating history synchronized:', len(data['rating_history']['games']), 'games')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        if 'rating_history' not in data:
            raise RuntimeError('Initial rating history sync failed; no complete snapshot available') from exc
        data['rating_history']['status'] = 'stale'
        print('WARNING: rating sync failed; retained previous complete snapshot. Retry before claiming current data.')
