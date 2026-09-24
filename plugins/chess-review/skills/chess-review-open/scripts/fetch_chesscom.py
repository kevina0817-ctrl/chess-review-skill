#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fetch a bounded batch of completed public games; never analyzes or publishes."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import chess
import chess.pgn

API = 'https://api.chess.com/pub/player/'
USER_AGENT = 'ChessReviewSkill/1.0 (+https://github.com/kevina0817-ctrl/chess-review-skill)'


def username(value):
    value = value.strip().casefold()
    if not re.fullmatch(r'[a-z0-9_-]{1,100}', value):
        raise ValueError('Supply a Chess.com username, not an email, password, or URL.')
    return value


def game_id(url):
    match = re.search(r'https://(?:www\.)?chess\.com/(?:analysis/)?(?:game/(?:live/|daily/)?|live/game/)(\d+)(?=[/?#\s\]\")]|$)', url or '')
    return match[1] if match else None


def get_json(url, timeout=20):
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            if not response.url.startswith(API):
                raise ValueError('Unexpected API redirect; stop and inspect the account URL.')
            return json.load(response)
    except HTTPError as e:
        message = {404: 'Account or archive not found; check the username.',
                   429: 'Chess.com rate limit; retry later, do not loop.',
                   403: 'Public API access unavailable; try the browser history.',
                   410: 'This archive is unavailable.'}.get(e.code, 'Public API request failed.')
        raise ValueError(f'HTTP {e.code}: {message}') from e
    except (URLError, TimeoutError) as e:
        raise ValueError('Public API network request failed; no older game was substituted.') from e


def parse_game(text):
    stream = io.StringIO(text)
    game = chess.pgn.read_game(stream)
    if game is None or game.errors or game.headers.get('Result') not in ('1-0', '0-1', '1/2-1/2'):
        raise ValueError('Missing, invalid, or unfinished PGN; do not substitute an older game.')
    if chess.pgn.read_game(stream) is not None:
        raise ValueError('Expected a single game in this archive entry.')
    board = game.board()
    if type(board) is not chess.Board or board.chess960 or not board.is_valid():
        raise ValueError('Only standard chess positions are supported.')
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            raise ValueError('Illegal move in PGN.')
        board.push(move)
    return game


def signature(game):
    fields = [game.headers.get('White', '').casefold(), game.headers.get('Black', '').casefold(),
              game.board().fen(), [m.uci() for m in game.mainline_moves()]]
    return hashlib.sha256(json.dumps(fields, separators=(',', ':')).encode()).hexdigest()


def existing_reviews(root):
    rows, warnings = [], []
    for path in sorted(root.glob('*.pgn')):
        if path.is_symlink() or not path.with_suffix('.html').is_file():
            continue
        try:
            game = parse_game(path.read_text(encoding='utf-8'))
        except (ValueError, OSError) as e:
            warnings.append(f'Could not check existing review {path.name}: {e}')
            continue
        rows.append((game_id(game.headers.get('Link')), signature(game),
                     game.headers.get('UTCDate', game.headers.get('Date')),
                     str(path.with_suffix('.html').resolve())))
    return rows, warnings


def fetch_latest(user, count=1, request=get_json, max_months=6, budget_seconds=120):
    user = username(user)
    if not 1 <= count <= 5 or not 1 <= max_months <= 24:
        raise ValueError('Use 1–5 games and 1–24 archive months per request.')
    base = API + user + '/games/'
    deadline = time.monotonic() + budget_seconds
    def fetch(url):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('Retrieval budget exceeded; do not call partial data the latest games.')
        return request(url, timeout=min(20, remaining))
    archives = fetch(base + 'archives').get('archives', [])
    pattern = re.escape(base) + r'\d{4}/(0[1-9]|1[0-2])'
    if any(not isinstance(url, str) or not re.fullmatch(pattern, url) for url in archives):
        raise ValueError('Unexpected archive URL in API response.')
    archives = sorted(set(archives), reverse=True)
    games, skipped, months = {}, [], []
    for url in archives[:max_months]:
        months.append(url)
        for item in fetch(url).get('games', []):
            end = item.get('end_time')
            if not isinstance(end, (int, float)) or end <= 0:
                continue
            if item.get('rules') != 'chess':
                skipped.append({'url': item.get('url'), 'end_time': end, 'reason': 'nonstandard'})
                continue
            key = game_id(item.get('url'))
            if key is None:
                raise ValueError('Unexpected standard-game URL in archive.')
            games[key] = item
        if len(games) >= count:
            break
    selected = sorted(games.values(), key=lambda g: g['end_time'], reverse=True)[:count]
    return selected, {'months_requested': months, 'skipped_nonstandard': skipped,
                      'search_limited': len(selected) < count and len(months) < len(archives)}


def save_games(root, user, games, zone=None):
    prior, warnings = existing_reviews(root)
    records = []
    for item in games:
        game = parse_game(item.get('pgn', ''))
        side = next((s for s in ('white', 'black')
                     if game.headers.get(s.title(), '').casefold() == user), None)
        if side is None or item.get(side, {}).get('username', '').casefold() != user:
            raise ValueError('Account and PGN identity mismatch.')
        key = game_id(item['url'])
        linked = game_id(game.headers.get('Link'))
        if linked and linked != key:
            raise ValueError('API and PGN game IDs disagree.')
        sig = signature(game)
        date = game.headers.get('UTCDate', game.headers.get('Date'))
        reviewed = []
        for old_id, old_sig, old_date, html in prior:
            if old_id == key:
                if old_sig != sig:
                    raise ValueError('Existing game ID has different moves; inspect before overwriting.')
                reviewed.append(html)
            elif not old_id and old_sig == sig and old_date == date:
                reviewed.append(html)
        start = None
        if game.headers.get('UTCDate') and game.headers.get('UTCTime'):
            try:
                dt = datetime.strptime(game.headers['UTCDate'] + ' ' + game.headers['UTCTime'], '%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc)
                start = dt.astimezone(zone or timezone.utc).isoformat()
            except ValueError:
                warnings.append(f'Invalid start timestamp for game {key}; retain original PGN date.')
        out = root / 'work' / 'chesscom' / user / key
        out.mkdir(parents=True, exist_ok=True)
        (out / 'input.pgn').write_text(item['pgn'], encoding='utf-8')
        (out / 'source.json').write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')
        record = {'game_id': key, 'url': item['url'], 'user_color': side,
                  'opponent': game.headers['Black' if side == 'white' else 'White'],
                  'result': game.headers['Result'], 'start_time': start,
                  'original_date': game.headers.get('Date'), 'end_time_utc': datetime.fromtimestamp(item['end_time'], timezone.utc).isoformat(),
                  'plies': len(list(game.mainline_moves())), 'signature': sig,
                  'pgn': str((out / 'input.pgn').resolve()), 'already_reviewed': reviewed}
        (out / 'summary.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        records.append(record)
    return records, warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path, help='User review directory')
    p.add_argument('--user', help='Confirmed Chess.com username; remembered locally after successful retrieval')
    p.add_argument('--count', type=int, default=1)
    p.add_argument('--connect-only', action='store_true', help='Validate and remember a public username without reviewing or fetching games')
    p.add_argument('--timezone', help='Confirmed IANA timezone, e.g. Europe/London; default UTC')
    p.add_argument('--max-months', type=int, default=6)
    a = p.parse_args()
    try:
        root = a.directory.resolve()
        config = root / '.chess-review-account.json'
        settings = json.loads(config.read_text()) if config.exists() else {}
        user = username(a.user or settings.get('chesscom_username', ''))
        if settings.get('chesscom_username') and settings['chesscom_username'] != user:
            raise ValueError('This review folder belongs to a different account; use a separate directory.')
        tz = a.timezone or settings.get('timezone')
        zone = ZoneInfo(tz) if tz else None
        if a.connect_only:
            profile = get_json(API + user)
            if profile.get('username', '').casefold() != user:
                raise ValueError('Account profile mismatch; confirm the current Chess.com username.')
            root.mkdir(parents=True, exist_ok=True)
            config.write_text(json.dumps({'chesscom_username': user, 'timezone': tz}, indent=2)+'\n', encoding='utf-8')
            print(json.dumps({'status': 'connected', 'user': user, 'mode': 'public_read_only',
                              'note': 'Username saved locally. No login, game analysis, or background monitor started.'}))
            return
        games, info = fetch_latest(user, a.count, max_months=a.max_months)
        root.mkdir(parents=True, exist_ok=True)
        records, warnings = save_games(root, user, games, zone)
        status = 'ready' if len(records) == a.count else ('partial' if records else 'no_public_games')
        if records:
            config.write_text(json.dumps({'chesscom_username': user, 'timezone': tz}, indent=2)+'\n', encoding='utf-8')
        report = dict(status=status, user=user, requested=a.count, returned=len(records), games=records, warnings=warnings,
                      retrieved_at_utc=datetime.now(timezone.utc).isoformat(), **info,
                      freshness='Latest available completed standard games in public archives; recently finished games may be delayed. Verify browser history if recent data is missing.')
        out = root / 'work' / 'chesscom' / user / 'latest.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as e:
        p.exit(1, json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
