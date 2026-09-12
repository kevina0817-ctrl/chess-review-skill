#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Merge dated chess reviews into a portable, offline index.html."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path

MARKER = '<!-- chess-review-library:v1 -->'


def read_library(path):
    if not path.exists():
        return {}
    source = path.read_text(encoding='utf-8')
    if MARKER not in source:
        raise ValueError(f'Refusing to overwrite an unrelated page: {path}')
    match = re.search(r'<script id="chess-library-data" type="application/json">(.*?)</script>', source, re.S)
    if not match:
        raise ValueError('Existing library data is missing; preserve the file and investigate.')
    data = json.loads(match.group(1))
    return {game['id']: game for game in data['games']}


def read_review(path):
    source = path.read_text(encoding='utf-8')
    match = re.search(r'const DATA\s*=\s*', source)
    if not match:
        raise ValueError(f'{path.name}: no supported review data. Do not silently omit this review.')
    data, _ = json.JSONDecoder().raw_decode(source[match.end():])
    meta = data['meta']
    date = datetime.date.fromisoformat(meta['date']).isoformat()
    side = meta['user_color']
    if side not in ('white', 'black'):
        raise ValueError(f'{path.name}: unknown user color')
    return {
        'id': path.stem, 'date': date,
        'opponent': meta['black'] if side == 'white' else meta['white'],
        'user': meta['user_name'], 'side': side,
        'result': meta['endLabel'], 'lessons': len(data['lessons']),
        'plies': len(data['states']) - 1,
        'fingerprint': hashlib.sha256(data['pgn'].encode()).hexdigest(),
        'html': source,
    }


def build(directory, output=None):
    directory = Path(directory).resolve()
    output = Path(output).resolve() if output else directory / 'index.html'
    games = read_library(output)
    sources = []
    for path in sorted(directory.glob('*.html')):
        # Only final reviews: never import work/ fixtures, the library, or legacy symlink aliases.
        if path.is_symlink() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_.+\.html', path.name):
            continue
        game = read_review(path)
        for old_id, old in list(games.items()):
            if old.get('fingerprint') == game['fingerprint'] and old_id != game['id']:
                del games[old_id]
        games[game['id']] = game
        sources.append(path.name)
    if not games:
        raise ValueError('No reviews found; create and validate a game review first.')
    ordered = sorted(games.values(), key=lambda game: (game['date'], game['id']), reverse=True)
    payload = json.dumps({'version': 1, 'games': ordered}, ensure_ascii=False)
    payload = payload.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (Path(__file__).resolve().parent.parent / 'assets/library-template.html').read_text(encoding='utf-8')
    content = template.replace('/*__LIBRARY_DATA__*/', payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(output)
    return {'html': str(output), 'games': len(ordered), 'sources': sources,
            'lessons': sum(game['lessons'] for game in ordered)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='Folder containing published dated review HTML files')
    parser.add_argument('--out', help='Default: DIRECTORY/index.html')
    args = parser.parse_args()
    print(json.dumps(build(args.directory, args.out), ensure_ascii=False))
