#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Maintain a single self-contained, cumulative chess leak comparison page."""
import argparse
import ast
import copy
import datetime
import hashlib
import io
import json
import re
from pathlib import Path
import chess
import chess.pgn

MIN_INITIAL_REVIEWS = 10

DATA_RE = r'<script id="visual-data" type="application/json">(.*?)</script>'


def game_info(root, stem, user=None):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_[\w.-]+', stem):
        raise ValueError(f'Invalid game stem: {stem}')
    g = chess.pgn.read_game(io.StringIO((root / (stem + '.pgn')).read_text()))
    if g is None or g.errors or g.headers.get('Result') not in ('1-0', '0-1', '1/2-1/2'):
        raise ValueError(f'Invalid or incomplete PGN: {stem}')
    if g.headers.get('Variant', 'Standard') not in ('Standard', 'Chess'):
        raise ValueError('Only standard chess is supported')
    side = next((side for side in ('white', 'black') if g.headers[side.title()].casefold() == user.casefold()), None)
    if side is None:
        raise ValueError(f'{user} is not a player in {stem}')
    moves = list(g.mainline_moves())
    signature = hashlib.sha256(json.dumps([g.headers['White'].casefold(), g.headers['Black'].casefold(),
        g.board().fen(), [m.uci() for m in moves]], separators=(',', ':')).encode()).hexdigest()
    link = g.headers.get('Link', '')
    match = re.search(r'chess\.com/(?:analysis/)?(?:game/(?:live/|daily/)?|live/game/)(\d+)', link)
    fallback = signature + g.headers.get('UTCDate', g.headers.get('Date', '')) + g.headers.get('UTCTime', '')
    key = 'chesscom:' + match[1] if match else 'pgn:' + hashlib.sha256(fallback.encode()).hexdigest()
    return g, {'game_key': key, 'signature': signature, 'side': side, 'opponent': g.headers['Black' if side == 'white' else 'White']}


def review(root, stem):
    s = (root / (stem + '.html')).read_text()
    m = re.search(r'const DATA\s*=\s*', s)
    if not m:
        raise ValueError(f'Missing validated review: {stem}')
    return json.JSONDecoder().raw_decode(s[m.end():])[0]


def verified_review_info(root, stem, user):
    """Count a completed review only when its embedded game matches the PGN."""
    game, info = game_info(root, stem, user)
    data = review(root, stem)
    if not isinstance(data, dict) or not isinstance(data.get('meta'), dict):
        raise ValueError('Review payload must contain verified game metadata')
    meta = data.get('meta', {})
    embedded = chess.pgn.read_game(io.StringIO(data.get('pgn', '')))
    if not embedded or embedded.errors:
        raise ValueError('Review does not contain a valid PGN')
    if (meta.get('user_color') != info['side'] or
        meta.get('user_name', '').casefold() != user.casefold() or
        meta.get('stem') != stem or
        any(embedded.headers.get(k) != game.headers.get(k) for k in ('White','Black','Result')) or
        embedded.board().fen() != game.board().fen() or
        list(embedded.mainline_moves()) != list(game.mainline_moves()) or
        not data.get('lessons')):
        raise ValueError('Review identity or moves do not match this completed game')
    boards = [game.board()]
    for move in game.mainline_moves():
        board = boards[-1].copy(); board.push(move); boards.append(board)
    if [x.get('fen') for x in data.get('states', [])] != [b.fen() for b in boards]:
        raise ValueError('Review must contain the complete verified game replay')
    return game, info


def read_payload(path):
    if not path.exists():
        return {'version': 2, 'user': None, 'groups': [], 'cases': [], 'assessments': [], 'pieces': {}}
    source = path.read_text()
    match = re.search(DATA_RE, source, re.S)
    if not match:
        raise ValueError('Refusing to overwrite a page without supported leak data')
    d = json.loads(match[1])
    if d.get('version', 1) == 1:
        # One-time migration of the legacy comparison page.
        m = re.search(r'const comparisons=(\[.*?\n\]);', source, re.S)
        if not m:
            raise ValueError('Legacy contrasts missing; preserve page and migrate explicitly')
        contrasts = ast.literal_eval(m[1])
        if len(contrasts) != len(d['cases']):
            raise ValueError('Legacy case/contrast mismatch')
        ids = ['direct-threats', 'recapture', 'opened-lines', 'development']
        for i, group in enumerate(d['groups']):
            group['id'] = ids[i] if i < len(ids) else 'leak-' + hashlib.sha256(group['title'].encode()).hexdigest()[:12]
        for c, contrast in zip(d['cases'], contrasts):
            c['group_id'] = d['groups'][c['group']]['id']
            c['contrast'] = dict(zip(('actual', 'better'), contrast))
        d.update(version=2, user=None, assessments=[])
    if d['version'] != 2:
        raise ValueError('Unsupported data version')
    return d


def checked_frame(board, san='', move=None, caption='', arrows=None):
    return dict(fen=board.fen(), san=san, **{'from': chess.square_name(move.from_square) if move else '',
        'to': chess.square_name(move.to_square) if move else ''}, mate=board.is_checkmate(),
        check=chess.square_name(board.king(board.turn)) if board.is_check() else '', caption=caption, arrows=arrows or [])


def expand_case(root, item, user):
    """Read existing validated review lessons; never invent actual continuation."""
    if 'branches' in item:
        return copy.deepcopy(item)
    r = review(root, item['stem'])
    lesson = next((x for x in r['lessons'] if x['ply'] == item['ply']), None)
    if not lesson:
        raise ValueError('Add and validate this lesson in the single-game review first')
    c = {k: copy.deepcopy(item[k]) for k in ('stem', 'ply', 'group_id', 'title', 'contrast')}
    c.update(date=item['stem'][:10], why=lesson['why'], fix=lesson['fix'], branches={})
    for key in ('actual', 'better'):
        states = lesson[key + 'States']
        captions = item['captions'][key]
        if len(states) != len(captions):
            raise ValueError(f'{key}: provide one caption per state, including the common start')
        c['branches'][key] = {'frames': [dict(s, caption=t, arrows=item.get('arrows', {}).get(key, {}).get(str(i), []))
            for i, (s, t) in enumerate(zip(states, captions))]}
    if item.get('threat'):
        extra = item['threat']
        if len(extra['captions']) != len(extra['moves']) + 1:
            raise ValueError('Threat caption count mismatch')
        board = chess.Board(c['branches']['actual']['frames'][0]['fen'])
        states = [checked_frame(board, caption=extra['captions'][0])]
        for san, caption in zip(extra['moves'], extra['captions'][1:]):
            move = board.parse_san(san)
            label = str(board.fullmove_number) + ('. ' if board.turn else '… ') + board.san(move)
            board.push(move)
            states.append(checked_frame(board, label, move, caption))
        c['branches']['threat'] = {'frames': states}
    return c


def validate_case(root, c, d):
    game, info = game_info(root, c['stem'], d['user'])
    for field in ('side', 'opponent', 'game_key', 'signature'):
        if field in c and c[field] != info[field]:
            raise ValueError(f'{c["stem"]}: conflicting {field}')
        c[field] = info[field]
    c['id'] = info['game_key'] + ':' + str(c['ply'])
    if c['date'] != c['stem'][:10]:
        raise ValueError('Case date must match the validated local-date review filename')
    group_ids = [g['id'] for g in d['groups']]
    c['group'] = group_ids.index(c['group_id'])
    for key in ('actual', 'better'):
        if not c['contrast'].get(key, '').strip():
            raise ValueError('Both short contrast explanations are required')
    moves = list(game.mainline_moves())
    if not isinstance(c['ply'], int) or not 0 <= c['ply'] < len(moves):
        raise ValueError('ply must be a move-before position in the actual PGN')
    board = game.board()
    for move in moves[:c['ply']]:
        board.push(move)
    if board.turn != (c['side'] == 'white'):
        raise ValueError('The case must begin before the user moves')
    initial = board.fen()
    for key, branch in c['branches'].items():
        if key not in ('actual', 'better', 'threat'):
            raise ValueError('Unknown branch kind')
        fs = branch['frames']
        if len(fs) < 2 or fs[0]['fen'] != initial:
            raise ValueError('Both boards and hypothetical branches must share the actual start')
        b = board.copy()
        for i, f in enumerate(fs):
            if not f.get('caption', '').strip():
                raise ValueError('Every frame needs a brief caption')
            if i:
                m = b.parse_san(re.sub(r'^\d+[.…]\s*', '', f['san']))
                if key == 'actual' and (c['ply'] + i > len(moves) or m != moves[c['ply'] + i - 1]):
                    raise ValueError('Actual branch deviates from the original PGN')
                if f.get('from') != chess.square_name(m.from_square) or f.get('to') != chess.square_name(m.to_square):
                    raise ValueError('Animation squares do not match the move')
                b.push(m)
            if b.fen() != f['fen'] or b.is_checkmate() != f['mate']:
                raise ValueError('Incorrect board or mate flag')
            check = chess.square_name(b.king(b.turn)) if b.is_check() else ''
            if f.get('check', '') != check:
                raise ValueError('Incorrect check marker')
            for a, z in f.get('arrows', []):
                chess.parse_square(a); chess.parse_square(z)
    return c


def progress_clip(root, item, d, positive=False):
    r = review(root, item['stem'])
    lesson = next((x for x in r['lessons'] if x['ply'] == item['ply']), None)
    if not lesson or (positive and not lesson.get('positive')):
        raise ValueError('Progress needs a verified positive lesson; prior examples need a verified lesson')
    clip = copy.deepcopy(item)
    if 'frames' not in clip:
        states = lesson['actualStates']
        captions = clip.pop('captions')
        if len(states) != len(captions):
            raise ValueError('Progress captions must match actual states, including the start')
        clip['frames'] = [dict(f, caption=t, arrows=[]) for f, t in zip(states, captions)]
    proxy = dict(stem=clip['stem'], ply=clip['ply'], date=clip['stem'][:10],
        group_id=d['groups'][0]['id'], contrast={'actual':'validation','better':'validation'},
        branches={k:{'frames':copy.deepcopy(clip['frames'])} for k in ('actual','better')})
    validate_case(root, proxy, d)
    for key in ('game_key','signature','side','opponent','date','id'):
        clip[key] = proxy[key]
    return clip


def progress_item(root, item, d):
    p = copy.deepcopy(item)
    for key in ('title','skill','explanation','habit','limit'):
        if not p.get(key, '').strip():
            raise ValueError('Progress needs specific evidence, repeatable action and an honest scope: '+key)
    if p.get('kind') not in ('comparison','repeated','good_move'):
        raise ValueError('Unknown progress evidence kind')
    p['current'] = progress_clip(root, p['current'], d, positive=True)
    p['id'] = 'progress:' + p['current']['id']
    if p['kind'] in ('comparison','repeated') and not p.get('prior'):
        raise ValueError('A comparison or repeated ability requires earlier evidence')
    if p.get('prior'):
        p['prior'] = progress_clip(root, p['prior'], d, positive=p['kind']=='repeated')
        # Different earlier games; never compare the two sides as the same position.
        def start(clip):
            g,_ = game_info(root, clip['stem'], d['user'])
            date=g.headers.get('UTCDate', g.headers.get('Date',''))
            return datetime.datetime.strptime(date + ' ' + g.headers.get('UTCTime', g.headers.get('StartTime','00:00:00')), '%Y.%m.%d %H:%M:%S')
        if p['prior']['game_key'] == p['current']['game_key'] or start(p['prior']) >= start(p['current']):
            raise ValueError('Prior evidence must come from a genuinely earlier, different game')
    return p


def validate(root, d):
    ids = [g['id'] for g in d['groups']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate group ids')
    for g in d['groups']:
        for field in ('id', 'title', 'short', 'desc', 'habit'):
            if not g.get(field, '').strip():
                raise ValueError(f'Group is missing {field}')
    seen = set()
    for c in d['cases']:
        validate_case(root, c, d)
        if c['id'] in seen:
            raise ValueError('Duplicate game and ply; keep one primary leak category')
        seen.add(c['id'])
    if any(not any(c['group_id'] == g['id'] for c in d['cases']) for g in d['groups']):
        raise ValueError('Every visible leak category needs at least one validated case')
    for a in d.setdefault('assessments', []):
        _, info = game_info(root, a['stem'], d['user'])
        a.update(info)
        if a.get('outcome') not in ('existing', 'new', 'none') or not a.get('note', '').strip():
            raise ValueError('Assessment needs existing/new/none and an evidence-based note')
        matching = [c for c in d['cases'] if c['game_key'] == a['game_key']]
        if a['outcome'] != 'none' and not matching:
            raise ValueError('A leak finding must have a validated case')
        if a['outcome'] == 'none' and matching:
            raise ValueError('Use existing/new when this game has recorded leak cases')
    d['progress'] = [progress_item(root, p, d) for p in d.get('progress', [])]
    if len({p['id'] for p in d['progress']}) != len(d['progress']):
        raise ValueError('Duplicate progress evidence')
    if len({a['game_key'] for a in d['assessments']}) != len(d['assessments']):
        raise ValueError('Duplicate game assessment')


def merge(root, d, update, replace_cases=False):
    for g in update.get('groups', []):
        old = next((x for x in d['groups'] if x['id'] == g['id']), None)
        if old is None:
            d['groups'].append(g)
        else:
            old.update(g)
    for item in update.get('cases', []):
        c = validate_case(root, expand_case(root, item, d['user']), d)
        old = next((x for x in d['cases'] if x['id'] == c['id']), None)
        if old is None:
            d['cases'].append(c)
        elif old != c:
            if not replace_cases:
                raise ValueError(f'{c["id"]} already exists; use --replace-cases only for an intentional correction')
            d['cases'][d['cases'].index(old)] = c
    for item in update.get('assessments', []):
        a = copy.deepcopy(item)
        _, info = game_info(root, a['stem'], d['user'])
        a.update(info)
        old = next((x for x in d['assessments'] if x['game_key'] == a['game_key']), None)
        if old:
            d['assessments'][d['assessments'].index(old)] = a
        else:
            d['assessments'].append(a)
    for item in update.get('progress', []):
        p = progress_item(root, item, d)
        old = next((x for x in d.setdefault('progress', []) if x['id'] == p['id']), None)
        if old is None:
            d['progress'].append(p)
        elif old != p:
            if not replace_cases:
                raise ValueError('Progress already exists; use --replace-cases for a deliberate correction')
            d['progress'][d['progress'].index(old)] = p
    if not d['pieces'] and d['cases']:
        d['pieces'] = review(root, d['cases'][0]['stem'])['pieces']
    validate(root, d)


def locate(root, name):
    if name:
        if Path(name).name != name or not name.endswith('.html'):
            raise ValueError('--page must be a simple HTML filename in the review folder')
        return root / name
    found = sorted(root.glob('common-leaks*.html'))
    if len(found) > 1:
        raise ValueError('Multiple leak pages; select the existing canonical filename with --page')
    return found[0] if found else root / 'common-leaks.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--user', help='Confirmed PGN username, required for a new archive')
    parser.add_argument('--plan', type=Path, help='Opted-in batch plan for first creation')
    parser.add_argument('--page', help='Keep the existing page filename and URL')
    parser.add_argument('--merge', type=Path, help='Incremental groups/cases/assessments JSON')
    parser.add_argument('--export', type=Path, help='Export existing data without changing HTML')
    parser.add_argument('--replace-cases', action='store_true', help='Explicitly replace corrected cases with the same identity')
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    target = locate(root, args.page)
    d = read_payload(target)
    if args.user:
        if d.get('user') and d['user'].casefold()!=args.user.casefold():
            raise ValueError('Use a separate review folder for another player')
        d['user']=args.user
    if not d.get('user'):
        raise ValueError('Confirm the PGN username and provide --user; never assume an account')
    if not target.exists() and not args.export:
        if not args.plan:
            raise ValueError('First creation needs an opted-in plan with at least 10 completed reviews')
        plan=json.loads(args.plan.read_text())
        if plan.get('enabled') is not True or plan.get('status')!='ready' or plan.get('eligible_games',0)<MIN_INITIAL_REVIEWS or len(plan.get('selected',[]))<MIN_INITIAL_REVIEWS or plan.get('user','').casefold()!=d['user'].casefold():
            raise ValueError('Plan must confirm consent, player identity and at least 10 selected completed reviews')
        verified = set()
        for item in plan['selected']:
            _, info = verified_review_info(root, item['stem'], d['user'])
            if info['game_key'] != item['game_key']:
                raise ValueError('Planned game changed; recheck the source review')
            verified.add(info['game_key'])
        if len(verified) < MIN_INITIAL_REVIEWS:
            raise ValueError('First creation needs 10 distinct completed reviews, not duplicate files')
    validate(root, d)
    if args.merge:
        merge(root, d, json.loads(args.merge.read_text()), args.replace_cases)
    if not target.exists() and not args.export and args.plan:
        completed={a['game_key'] for a in d['assessments']}
        selected={g['game_key'] for g in plan['selected']}
        if len(completed & selected)<MIN_INITIAL_REVIEWS or not selected.issubset(completed):
            raise ValueError('Record an assessment for each selected first-batch game; inputs alone are not analysis')
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'export': str(args.export), 'cases': len(d['cases'])})); return
    if not d['cases']:
        raise ValueError('No verified leak examples yet; do not fabricate an empty learning page')
    template = (Path(__file__).resolve().parent.parent / 'assets/leaks-template.html').read_text()
    payload = json.dumps(d, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    output = template.replace('__DATA__', payload)
    temp = target.with_suffix('.html.tmp')
    temp.write_text(output)
    temp.replace(target)
    print(json.dumps({'html': str(target), 'groups': len(d['groups']), 'cases': len(d['cases']),
        'games': len({c['game_key'] for c in d['cases']}), 'assessments': len(d['assessments']), 'progress': len(d.get('progress', []))}))


if __name__ == '__main__':
    main()
