#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Screen every position and refine instructive moves using a local UCI engine."""
import argparse
import json
import shutil
from pathlib import Path
import chess.engine
from chess_common import chess, load_game, label, pv_san

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pgn');p.add_argument('--game',type=int)
    p.add_argument('--perspective',choices=['white','black'],required=True)
    p.add_argument('--engine',default=shutil.which('stockfish'))
    p.add_argument('--seconds',type=float,default=.3)
    p.add_argument('--refine-seconds',type=float,default=1.5)
    p.add_argument('--refine-count',type=int,default=8)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    if not args.engine: p.error('Supply --engine with the verified local Stockfish executable path.')
    if args.seconds<=0 or args.refine_seconds<=0: p.error('Analysis durations must be positive.')
    game,boards,moves,_=load_game(args.pgn,args.game)
    user_color=args.perspective=='white'
    engine=chess.engine.SimpleEngine.popen_uci(args.engine)
    try:
        for key,value in [('Threads',2),('Hash',128)]:
            if key in engine.options: engine.configure({key:value})
        def evaluate(board,seconds):
            info=engine.analyse(board,chess.engine.Limit(time=seconds))
            score=info['score'].pov(user_color)
            return {'cp':score.score(),'mate':score.mate(),'rank_score':score.score(mate_score=100000),
                    'depth':info.get('depth'),'pv':pv_san(board,info.get('pv',[]))}
        evals=[evaluate(b,args.seconds) for b in boards]
        rows=[]
        for i,move in enumerate(moves):
            before,after=evals[i],evals[i+1]
            loss=before['rank_score']-after['rank_score']
            rows.append({'ply':i,'move':label(boards[i],move),'side':'white' if boards[i].turn else 'black',
                         'is_user':boards[i].turn==user_color,'before':before,'after':after,'loss_rank':loss})
        candidates=sorted((r for r in rows if r['is_user']),key=lambda r:r['loss_rank'],reverse=True)[:args.refine_count]
        for row in candidates:
            i=row['ply']; row['before_refined']=evaluate(boards[i],args.refine_seconds)
            row['after_refined']=evaluate(boards[i+1],args.refine_seconds)
            row['loss_rank_refined']=row['before_refined']['rank_score']-row['after_refined']['rank_score']
        data={'engine':engine.id,'perspective':args.perspective,'screen_seconds':args.seconds,'refine_seconds':args.refine_seconds,
              'note':'Scores are from the requested player perspective. rank_score uses an internal mate sentinel; never display it as pawn evaluation. Candidate ranking is not a coaching verdict.',
              'headers':dict(game.headers),'rows':rows,'refined_plies':[r['ply'] for r in candidates]}
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'engine':engine.id,'positions':len(boards),'refined_plies':data['refined_plies'],'output':str(out)},ensure_ascii=False))
    finally: engine.quit()

if __name__=='__main__':main()
