#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Normalize a selected PGN and list verified positions without guessing moves."""
import argparse
import json
from pathlib import Path
from chess_common import load_game, label, snapshot

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pgn')
    parser.add_argument('--game',type=int)
    parser.add_argument('--out-dir',required=True)
    args = parser.parse_args()
    game, boards, moves, pgn = load_game(args.pgn,args.game)
    out = Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    states = [snapshot(boards[0])]
    for i, move in enumerate(moves):
        states.append(snapshot(boards[i+1],move,label(boards[i],move)))
    (out/'normalized.pgn').write_text(pgn,encoding='utf-8')
    data = {'headers':dict(game.headers),'plies':len(moves),'states':states,'result':game.headers.get('Result','*')}
    (out/'positions.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'headers':dict(game.headers),'verified_plies':len(moves),'output':str(out)},ensure_ascii=False))

if __name__ == '__main__': main()
