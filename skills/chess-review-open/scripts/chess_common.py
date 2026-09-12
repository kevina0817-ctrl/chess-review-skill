# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Shared PGN validation and position serialization; requires python-chess."""
import io
import re
from pathlib import Path
try:
    import chess
    import chess.pgn
except ImportError as exc:
    raise SystemExit('python-chess is required. Install into a writable task dependency directory, then set PYTHONPATH to that directory. See references/workflow.md.') from exc

def load_game(path, game_index=None):
    source = Path(path).read_text(encoding='utf-8-sig')
    stream = io.StringIO(source)
    games = []
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        games.append(game)
    if not games:
        raise ValueError('No PGN game found.')
    if game_index is None and len(games) != 1:
        raise ValueError(f'Found {len(games)} games. Select an explicit zero-based --game index.')
    game = games[0 if game_index is None else game_index]
    if game.errors:
        raise ValueError(f'Illegal or ambiguous PGN. Resolve from the source before continuing: {game.errors}')
    board = game.board()
    if board.chess960 or type(board) is not chess.Board:
        raise ValueError('This template supports standard chess only.')
    if not board.is_valid():
        raise ValueError(f'Invalid starting position: {board.fen()}')
    boards, moves = [board.copy()], list(game.mainline_moves())
    if not moves and 'FEN' not in game.headers:
        raise ValueError('No moves found. Supply the scoresheet, or a verified FEN for a position-only exercise.')
    for i, move in enumerate(moves):
        if move not in board.legal_moves:
            raise ValueError(f'Illegal move at ply {i + 1}: {move}')
        board.push(move)
        if not board.is_valid():
            raise ValueError(f'Invalid board at ply {i + 1}.')
        boards.append(board.copy())
    link = game.headers.get('Link', '')
    match = re.fullmatch(r'\[.*?\]\((https?://[^\s)]+)\)', link)
    if match:
        game.headers['Link'] = match.group(1)
    pgn = game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False, columns=84)) + '\n'
    return game, boards, moves, pgn

def label(board, move):
    return f'{board.fullmove_number}' + ('. ' if board.turn else '… ') + board.san(move)

def snapshot(board, move=None, san=''):
    return {'fen':board.fen(), 'san':san,
            'from':chess.square_name(move.from_square) if move else '',
            'to':chess.square_name(move.to_square) if move else '',
            'turn':'白方' if board.turn else '黑方',
            'color':'white' if board.turn else 'black',
            'number':board.fullmove_number,
            'check':chess.square_name(board.king(board.turn)) if board.is_check() else '',
            'mate':board.is_checkmate()}

def pv_san(board, pv, count=10):
    board = board.copy()
    result = []
    for move in pv[:count]:
        result.append(board.san(move))
        board.push(move)
    return result
