# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Verified offline metrics, evaluation history and opening-position matching."""
import hashlib
import json
import math
from pathlib import Path
from chess_common import chess, label, snapshot

FORMULA_URL = 'https://lichess.org/page/accuracy'


def white_evaluation(raw, board, perspective):
    if raw.get('fen') != board.fen():
        raise ValueError('Analysis FEN does not match the game position')
    cp, mate = raw.get('cp'), raw.get('mate')
    if (cp is None) == (mate is None):
        raise ValueError('Evaluation must contain exactly one of cp or mate')
    value = cp if cp is not None else mate
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Invalid engine score')
    sign = 1 if perspective == 'white' else -1
    cp = cp * sign if cp is not None else None
    mate = mate * sign if mate is not None else None
    terminal = None
    if board.is_checkmate():
        terminal = 'black' if board.turn else 'white'
    elif board.is_game_over():
        terminal = 'draw'
    if terminal:
        advantage = {'white':100., 'black':0., 'draw':50.}[terminal]
    elif mate is not None:
        if mate == 0:
            raise ValueError('Zero mate score is only meaningful in checkmate')
        advantage = 100. if mate > 0 else 0.
    else:
        advantage = 50. + 50. * math.tanh(.00368208 * cp / 2)
    b = board.copy()
    frames = [snapshot(b)]
    for san in raw.get('pv', [])[:10]:
        if b.is_game_over():
            break
        move = b.parse_san(san)
        text = label(b, move)
        b.push(move)
        frames.append(snapshot(b, move, text))
    return {'fen':board.fen(), 'cp':cp, 'mate':mate, 'terminal':terminal,
            'advantage':advantage, 'depth':raw.get('depth'), 'forecast':frames}


def phase(board):
    nonpawn = sum(len(board.pieces(pt, color))*weight for color in chess.COLORS
                  for pt, weight in [(chess.KNIGHT,3),(chess.BISHOP,3),(chess.ROOK,5),(chess.QUEEN,9)])
    if nonpawn <= 13 or (not board.queens and nonpawn <= 26):
        return 'endgame'
    return 'opening' if board.fullmove_number <= 10 else 'middlegame'


def summarize(rows):
    cp_rows = [r['cp_loss'] for r in rows if r['cp_loss'] is not None]
    return {'moves':len(rows), 'score':round(sum(r['quality'] for r in rows)/len(rows),1) if rows else None,
            'acpl':round(sum(cp_rows)/len(cp_rows),1) if cp_rows else None,
            'cp_samples':len(cp_rows), 'blunders':sum(r['classification']=='blunder' for r in rows),
            'mistakes':sum(r['classification']=='mistake' for r in rows),
            'inaccuracies':sum(r['classification']=='inaccuracy' for r in rows),
            'preferred':sum(r['preferred'] for r in rows)}


def build_analytics(analysis, boards, moves, pgn):
    if analysis.get('source_pgn_sha256') != hashlib.sha256(pgn.encode()).hexdigest():
        raise ValueError('Engine analysis belongs to a different PGN; rerun analyze_game.py')
    perspective = analysis.get('perspective')
    if perspective not in ('white','black'):
        raise ValueError('Missing analysis perspective')
    raw_rows = analysis.get('rows', [])
    if len(raw_rows) != len(moves) or not raw_rows:
        raise ValueError('Analysis must cover every move')
    positions = [None] * len(boards)
    def take(i, raw):
        item = white_evaluation(raw, boards[i], perspective)
        if positions[i] is None or (item['depth'] or 0) >= (positions[i]['depth'] or 0):
            positions[i] = item
    for i, row in enumerate(raw_rows):
        side = 'white' if boards[i].turn else 'black'
        if row.get('ply') != i or row.get('side') != side or row.get('uci') != moves[i].uci():
            raise ValueError('Analysis move order/side mismatch')
        take(i, row['before']); take(i+1, row['after'])
        for key, index in [('before_refined',i),('after_refined',i+1)]:
            if key in row: take(index,row[key])
    rows = []
    for i, move in enumerate(moves):
        before, after = positions[i:i+2]
        sign = 1 if boards[i].turn else -1
        loss = max(0., sign*(before['advantage']-after['advantage']))
        quality = 100. if loss == 0 else max(0.,min(100.,103.1668*math.exp(-.04354*loss)-3.1669))
        cp_loss = max(0.,sign*(before['cp']-after['cp'])) if before['cp'] is not None and after['cp'] is not None else None
        preferred = len(before['forecast'])>1 and before['forecast'][1]['from'] == chess.square_name(move.from_square) and before['forecast'][1]['to'] == chess.square_name(move.to_square) and before['forecast'][1]['fen'] == boards[i+1].fen()
        kind = 'blunder' if loss >= 20 else 'mistake' if loss >= 10 else 'inaccuracy' if loss >= 5 else 'steady'
        rows.append({'ply':i,'move':label(boards[i],move),'side':'white' if boards[i].turn else 'black',
                     'phase':phase(boards[i]),'loss':round(loss,2),'quality':round(quality,2),
                     'cp_loss':cp_loss,'classification':kind,'preferred':preferred,
                     'check':boards[i+1].is_check(),'capture':boards[i].is_capture(move)})
    return {'version':1,'engine':analysis.get('engine',{}),'screen_seconds':analysis.get('screen_seconds'),
            'refine_seconds':analysis.get('refine_seconds'),'positions':positions,'rows':rows,
            'sides':{side:summarize([r for r in rows if r['side']==side]) for side in ('white','black')},
            'phases':{side:{key:summarize([r for r in rows if r['side']==side and r['phase']==key])
                            for key in ('opening','middlegame','endgame')} for side in ('white','black')},
            'formula_url':FORMULA_URL}


def identify_opening(boards):
    catalog_path=Path(__file__).resolve().parent.parent/'assets/openings.json'
    if not catalog_path.exists():
        return None
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    by_position={item['epd']:item for item in catalog['openings']}
    for ply in range(min(len(boards)-1,40),0,-1):
        item=by_position.get(boards[ply].epd())
        if item:
            return {**item,'ply':ply,'source':catalog['source'],'source_revision':catalog['revision'],
                    'resource':'https://lichess.org/opening'}
    return None
