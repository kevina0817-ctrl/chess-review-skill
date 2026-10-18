#!/usr/bin/env python3
"""Comparable, cached capability observations across completed rated standard games."""
import hashlib
import io
import json
import os
from pathlib import Path
import chess
import chess.engine
import chess.pgn
from rating_history import atomic_json

VERSION = 'capabilities-1-n40000-r200000-cp200'

def mates_in_one(board):
    found=[]
    for move in list(board.legal_moves):
        if not board.gives_check(move):
            continue
        board.push(move)
        if board.is_checkmate():found.append(move)
        board.pop()
    return found

def tactical_observations(board, move):
    """Exact legal one-ply outcomes. Threat tests exclude positions currently in check."""
    after=board.copy();after.push(move)
    opportunities=mates_in_one(board)
    result={}
    if opportunities:result['mate']={'success':after.is_checkmate(),'alternatives':[m.uci() for m in opportunities]}
    if not board.is_check():
        passed=board.copy();passed.push(chess.Move.null())
        threats=mates_in_one(passed)
        if threats:
            safe=not mates_in_one(after)
            alternative=move if safe else None
            if not safe:
                for candidate in list(board.legal_moves):
                    trial=board.copy();trial.push(candidate)
                    if not mates_in_one(trial):alternative=candidate;break
            if alternative is not None:
                result['defense']={'success':safe,'alternative':alternative.uci(),'threats':[m.uci() for m in threats]}
    return result

def analyze_game(raw, user, engine):
    game=chess.pgn.read_game(io.StringIO(raw['pgn']))
    if game is None or game.errors:raise ValueError('Invalid archived PGN')
    side=next((s for s in ('white','black') if raw[s]['username'].casefold()==user.casefold()),None)
    if side is None or game.headers.get(side.title(),'').casefold()!=user.casefold():raise ValueError('PGN/account mismatch')
    color=side=='white';board=game.board();moves=list(game.mainline_moves());rows=[]
    engine.configure({'Clear Hash':None})
    def score(b,nodes):
        info=engine.analyse(b,chess.engine.Limit(nodes=nodes))
        return info['score'].pov(color).score(),info.get('pv',[None])[0] if info.get('pv') else None
    for ply,move in enumerate(moves):
        if board.turn==color:
            r={'ply':ply+1,'round':board.fullmove_number,'uci':move.uci(),'phase':0 if board.fullmove_number<=10 else 1 if board.fullmove_number<=25 else 2}
            r.update(tactical_observations(board,move))
            before,best=score(board,40000)
            after_board=board.copy();after_board.push(move)
            after=before if move==best else score(after_board,40000)[0]
            loss=None if before is None or after is None else max(0,before-after)
            if loss is not None and loss>=150:
                before,best=score(board,200000)
                after=before if move==best else score(after_board,200000)[0]
                loss=None if before is None or after is None else max(0,before-after)
                r['refined']=True
            r.update(loss_cp=loss,error=loss is not None and loss>=200)
            rows.append(r)
        board.push(move)
    return {'id':raw['url'],'end_time':raw['end_time'],'side':side,'opponent':raw['black' if color else 'white']['username'],
            'rows':rows,'plies':len(moves),'engine':engine.id.get('name','Stockfish'),'version':VERSION}

def aggregate(games):
    def metric(kind,phase=None):
        events=[]
        for g in games:
            for r in g['rows']:
                if phase is not None and r['phase']!=phase:continue
                if kind=='errors':
                    if r['loss_cp'] is None:continue
                    success=r['error']
                else:
                    if kind not in r:continue
                    success=r[kind]['success']
                events.append({'game':g['id'],'opponent':g['opponent'],'ply':r['ply'],'success':success})
        return {'count':sum(e['success'] for e in events),'total':len(events),'games':len({e['game'] for e in events}),
                'examples':events[-6:]}
    return {'games':len(games),'start':games[0]['end_time'],'end':games[-1]['end_time'],'moves':sum(len(g['rows']) for g in games),
            'errors':metric('errors'),'phases':[metric('errors',i) for i in range(3)],'mate':metric('mate'),'defense':metric('defense')}

def build(root,cfg,history):
    spec=cfg['capabilities'];cache=root/spec['cache_dir'];cache.mkdir(parents=True,exist_ok=True)
    raw=[]
    for url in history['archives']:
        month=json.loads((root/cfg['cache_dir']/(url[-7:].replace('/','-')+'.json')).read_text())
        raw.extend(g for g in month['games'] if g.get('rules')=='chess' and g.get('rated') and g.get('time_class')==spec.get('pool','rapid'))
    raw=list({g['url']:g for g in raw}.values());raw.sort(key=lambda g:(g['end_time'],g['url']));raw=raw[-60:]
    if not raw:return {'status':'empty','games':0,'windows':[],'pool':spec.get('pool','rapid')}
    binary=Path(os.path.expandvars(spec['engine']));engine_hash=hashlib.sha256(binary.read_bytes()).hexdigest()
    engine=None;analyzed=[]
    try:
        for g in raw:
            fingerprint=hashlib.sha256((VERSION+engine_hash+cfg['username'].lower()+g['pgn']).encode()).hexdigest()
            path=cache/(fingerprint+'.json')
            if path.exists():item=json.loads(path.read_text())
            else:
                if engine is None:
                    engine=chess.engine.SimpleEngine.popen_uci(str(binary));engine.configure({'Threads':1,'Hash':64})
                item=analyze_game(g,cfg['username'],engine);atomic_json(path,item)
                print('Capability analyzed',len(analyzed)+1,'/',len(raw),g['url'],flush=True)
            analyzed.append(item)
    finally:
        if engine:engine.quit()
    # Three disjoint windows; do not silently compare unequal-size or partial batches.
    size=20;complete=len(analyzed)//size*size;comparable=analyzed[-complete:] if complete else []
    windows=[aggregate(comparable[i:i+size]) for i in range(0,len(comparable),size)]
    result={'status':'ok','version':VERSION,'engine':analyzed[0]['engine'],'engine_sha256':engine_hash,'pool':spec.get('pool','rapid'),
        'synced_at':history['synced_at'],'games':len(analyzed),'start':analyzed[0]['end_time'],'end':analyzed[-1]['end_time'],
        'window_size':size,'windows':windows,'game_ids':[g['id'] for g in analyzed]}
    atomic_json(cache/'summary.json',result);return result

def update(root,data,cfg):
    if not cfg.get('capabilities'):return
    try:
        if data.get('rating_history',{}).get('status')!='ok':raise ValueError('Rating source stale')
        data['capability_history']=build(root,cfg,data['rating_history'])
    except (OSError,ValueError,KeyError,chess.engine.EngineError) as exc:
        if 'capability_history' in data:data['capability_history']['status']='stale'
        else:data['capability_history']={'status':'unavailable','windows':[]}
        print('WARNING: capability analysis unavailable; no new progress claims.',type(exc).__name__,flush=True)

def update_from_config(root,data):
    path=root/'.chess-review-ratings.json'
    if path.exists():update(root,data,json.loads(path.read_text()))
