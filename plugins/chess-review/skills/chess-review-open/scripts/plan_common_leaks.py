#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Plan optional aggregation of 10 completed reviews, then small incremental updates."""
import argparse
import datetime
import json
from pathlib import Path
from build_leaks import game_info, verified_review_info, read_payload, MIN_INITIAL_REVIEWS


def plan(root, user, enabled, stems=None, maximum=None, budget=25, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if maximum is not None and not 1 <= maximum <= 10:
        raise ValueError('Use a maximum of 1–10 reviewed games')
    if not 6 <= budget <= 30:
        raise ValueError('Use a 6–30 minute budget')
    games, excluded, awaiting_review = {}, [], []
    for path in sorted(root.glob('*.pgn')):
        if path.is_symlink(): continue
        try:
            _, source_info = game_info(root, path.stem, user)
        except (ValueError, KeyError, OSError) as e:
            excluded.append({'stem':path.stem,'reason':str(e)}); continue
        try:
            game, info = verified_review_info(root, path.stem, user)
        except (ValueError, KeyError, TypeError, OSError) as e:
            awaiting_review.append({'stem':path.stem,'reason':str(e)}); continue
        if info['game_key'] in games: continue
        games[info['game_key']] = dict(info, stem=path.stem,
            plies=len(list(game.mainline_moves())), has_review=True,
            sort_key=game.headers.get('UTCDate',game.headers.get('Date',''))+' '+game.headers.get('UTCTime',''))
    pages=list(root.glob('common-leaks*.html'))
    if len(pages)>1: raise ValueError('Select one canonical archive before planning')
    archive=read_payload(pages[0]) if pages else {}
    if archive and archive.get('user','').casefold()!=user.casefold():
        raise ValueError('Archive belongs to another player; use a separate folder')
    base={'user':user,'eligible_games':len(games),'minimum_games':MIN_INITIAL_REVIEWS,'enabled':enabled,
        'excluded':excluded,'awaiting_review':awaiting_review,'selected':[],'deferred':[],
        'budget_minutes':budget,'started_at':now.isoformat(),
        'stop_new_work_at':(now+datetime.timedelta(minutes=budget-5)).isoformat(),
        'finish_by':(now+datetime.timedelta(minutes=budget)).isoformat(),
        'timing_note':'已有分析的整理预算，非保证；不自动重跑历史引擎。最后 5 分钟用于校验。'}
    if enabled is not True:
        return dict(base,status='needs_opt_in' if enabled is None else 'disabled',
                    eligible_to_start=len(games)>=MIN_INITIAL_REVIEWS)
    if not archive and len(games)<MIN_INITIAL_REVIEWS:
        return dict(base,status='need_more_reviews',missing_games=MIN_INITIAL_REVIEWS-len(games),
                    note='继续做单盘复盘；仅有 PGN 不算已完成复盘，不自动抓取补满历史。')
    known={c['game_key'] for c in archive.get('cases',[])}|{a['game_key'] for a in archive.get('assessments',[])}
    known|={p['current']['game_key'] for p in archive.get('progress',[])}
    if archive and not stems:
        return dict(base,status='specify_new_games',note='只传本次新增复盘的 --stems，不重跑历史。')
    requested=set(stems or [])
    if requested-{g['stem'] for g in games.values()}:
        raise ValueError('Requested stems must have complete reviews for this player')
    selected=sorted([g for g in games.values() if (not requested or g['stem'] in requested) and g['game_key'] not in known],key=lambda g:g['sort_key'],reverse=True)
    limit=maximum if maximum is not None else (5 if archive else MIN_INITIAL_REVIEWS)
    used=0
    for g in selected:
        # Only aggregation of existing reviewed evidence; no fresh engine estimate.
        cost=45
        if len(base['selected'])<limit and used+cost<=(budget-5)*60:
            base['selected'].append(g);used+=cost
        else:base['deferred'].append(g['stem'])
    n=len(base['selected'])
    if not archive and n<MIN_INITIAL_REVIEWS:
        return dict(base,status='batch_too_small',note='首次整理需要 10 盘已完成复盘及其检查记录；增加预算或批次上限，不降低门槛。')
    return dict(base,status='ready' if n else 'up_to_date',mode='incremental' if archive else 'initial',
        estimated_minutes=[max(2,round(used/60)),min(budget,max(5,round(used/60*1.7+3)))],
        note='仅整理 selected；deferred 留待后续，不将未检查棋局说成已分析。')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--user',required=True)
    consent=p.add_mutually_exclusive_group();consent.add_argument('--enable',action='store_true');consent.add_argument('--disable',action='store_true')
    p.add_argument('--stems',nargs='+');p.add_argument('--max-games',type=int);p.add_argument('--budget-minutes',type=int,default=25);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();root=a.directory.resolve();root.mkdir(parents=True,exist_ok=True)
    if (a.max_games is not None and not 1<=a.max_games<=10) or not 6<=a.budget_minutes<=30:
        p.error('Use 1–10 reviewed games and a 6–30 minute budget')
    preferences=root/'.chess-review-preferences.json';all_prefs=json.loads(preferences.read_text()) if preferences.exists() else {}
    profile=all_prefs.setdefault(a.user.casefold(),{})
    if a.enable or a.disable:
        profile['common_leaks_enabled']=a.enable;preferences.write_text(json.dumps(all_prefs,ensure_ascii=False,indent=2)+'\n')
    result=plan(root,a.user,profile.get('common_leaks_enabled'),a.stems,a.max_games,a.budget_minutes)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
