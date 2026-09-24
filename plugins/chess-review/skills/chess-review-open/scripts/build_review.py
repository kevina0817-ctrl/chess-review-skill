#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generate a self-contained HTML review from verified PGN and coaching JSON."""
import argparse
import datetime
import hashlib
import html
import json
import re
from pathlib import Path
import chess.svg
from chess_common import chess, load_game, label, snapshot

def esc(value): return html.escape(str(value),quote=True)
def paragraphs(values): return ''.join('<p>'+esc(v)+'</p>' for v in values)

def build(pgn_path,review_path,out_dir,game_index=None):
    config=json.loads(Path(review_path).read_text(encoding='utf-8'))
    game,boards,moves,pgn=load_game(pgn_path,game_index)
    color=config['user_color']
    if color not in ['white','black']:raise ValueError('user_color must be white or black')
    user_color=color=='white'
    date=datetime.date.fromisoformat(config['archive_date']).isoformat()
    opponent=game.headers.get('Black' if user_color else 'White','Unknown')
    safe_opponent=re.sub(r'[^\w.\-]+','_',opponent,flags=re.UNICODE).strip('._')[:80] or 'Unknown'
    suffix=config.get('filename_suffix','')
    if suffix and not re.fullmatch(r'[A-Za-z0-9_-]{1,20}',suffix):raise ValueError('filename_suffix must be 1–20 ASCII letters, digits, underscores or hyphens')
    stem=date+'_'+safe_opponent+('_'+suffix if suffix else '')
    states=[snapshot(boards[0])]
    for i,move in enumerate(moves):states.append(snapshot(boards[i+1],move,label(boards[i],move)))
    lessons=[]
    for raw in config['lessons']:
        item=dict(raw);ply=item['ply']
        if isinstance(ply,bool) or not isinstance(ply,int) or ply<0 or ply>=len(boards):raise ValueError('Invalid lesson ply')
        board=boards[ply]
        if board.turn!=user_color:raise ValueError(f'Lesson at ply {ply} is not the user’s turn')
        for field in ['tag','title','summary','why','fix','habit','hint']:
            if not isinstance(item.get(field),str) or not item[field].strip():raise ValueError(f'Missing lesson {field}')
        count=item.get('actual_plies',4)
        if not isinstance(count,int) or count<1:raise ValueError('actual_plies must be a positive integer')
        item['number']=board.fullmove_number
        item['color']=color;item['side']='白方' if user_color else '黑方'
        item['played']=board.san(moves[ply]) if ply<len(moves) else ''
        item['actualStates']=[snapshot(board)]+states[ply+1:min(ply+1+count,len(states))]
        item['actual']=[state['san'] for state in item['actualStates'][1:]]
        if not item.get('better'):raise ValueError('Each lesson requires at least one verified demonstration move')
        b=board.copy();item['betterStates']=[snapshot(b)]
        for san in item['better']:
            m=b.parse_san(san);lab=label(b,m);b.push(m);item['betterStates'].append(snapshot(b,m,lab))
            if '#' in san and not b.is_checkmate():raise ValueError(f'False mate notation in lesson ply {ply}: {san}')
            if '+' in san and not b.is_check():raise ValueError(f'False check notation in lesson ply {ply}: {san}')
        if item.get('assert_mate') and not b.is_checkmate():raise ValueError(f'Claimed mate is not mate at lesson ply {ply}')
        item['bestUci']=board.parse_san(item['better'][0]).uci()
        item['accepted']={item['bestUci']:item['fix']}
        for accepted in item.get('accepted_moves',[]):
            item['accepted'][board.parse_san(accepted['san']).uci()]=accepted['feedback']
        item['legal']=[]
        for m in board.legal_moves:
            b=board.copy();san=b.san(m);b.push(m)
            item['legal'].append({'uci':m.uci(),'san':san,'state':snapshot(b,m,san)})
        lessons.append(item)
    if not lessons:raise ValueError('At least one instructive lesson or verified position exercise is required')
    pieces={key:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 45 45">'+value+'</svg>' for key,value in chess.svg.PIECES.items()}
    result=game.headers.get('Result','*')
    result_text={'1-0':'白方获胜','0-1':'黑方获胜','1/2-1/2':'和棋','*':'结果未记录'}.get(result,'结果未记录')
    white,black=game.headers.get('White','?'),game.headers.get('Black','?')
    user_name=white if user_color else black
    def rating(key):
        value=game.headers.get(key)
        return ' · '+value if value and value!='?' else ''
    meta={'white':white,'black':black,'white_rating':rating('WhiteElo'),'black_rating':rating('BlackElo'),
          'user_color':color,'user_name':user_name,'date':date,'stem':stem,
          'endLabel':result_text,'endDescription':config['ending'],
          'noteKey':'chess-review-'+date+'-'+hashlib.sha256((pgn+color).encode()).hexdigest()[:16]}
    data={'meta':meta,'states':states,'lessons':lessons,'pieces':pieces,'pgn':pgn}
    template=(Path(__file__).resolve().parent.parent/'assets/review-template.html').read_text(encoding='utf-8')
    link=game.headers.get('Link','')
    link_html='<a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">打开原对局 ↗</a>' if re.match(r'^https?://',link,re.I) else ''
    plan=''.join('<li><strong>'+esc(x['title'])+'</strong> '+esc(x['text'])+'</li>' for x in config['training'])
    timecontrol=game.headers.get('TimeControl','?')
    if re.fullmatch(r'\d+\+\d+',timecontrol):
        base,inc=map(int,timecontrol.split('+'));timecontrol=f'{base/60:g} 分钟 + 每步 {inc} 秒'
    elif re.fullmatch(r'\d+',timecontrol):
        timecontrol=f'{int(timecontrol)/60:g} 分钟 · 无加秒'
    replacements={'PAGE_TITLE':date+' · 对阵 '+opponent+' · 复盘笔记','DATE':date+' · '+config.get('timezone',''),
      'WHITE':white,'BLACK':black,'USER_META':('我执白' if user_color else '我执黑')+rating('WhiteElo' if user_color else 'BlackElo'),
      'OPPONENT_META':'对手'+('执黑' if user_color else '执白')+rating('BlackElo' if user_color else 'WhiteElo'),
      'TIME_CONTROL':timecontrol,'RESULT':result+' · '+result_text,'INTRO':config['intro'],
      'NOTES_PROMPT':config.get('notes_prompt','这盘漏看了什么？下一盘最先提醒自己的一件事是什么？'),
      'REVIEW_GUIDE':config['review_guide'],'PROVENANCE':config['provenance'],'DATE_NOTE':config['date_note']}
    for key,value in replacements.items():template=template.replace('@@'+key+'@@',esc(value))
    for key,value in {'OVERVIEW':paragraphs(config['overview']),'STRENGTHS':paragraphs(config['strengths']),'TRAINING':plan,'GAME_LINK':link_html}.items():
        template=template.replace('@@'+key+'@@',value)
    # Escape closing script tags and JS line separator characters in untrusted PGN names/comments.
    serialized=json.dumps(data,ensure_ascii=False).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=template.replace('/*__GAME_DATA__*/',serialized)
    if re.search(r'@@[A-Z_]+@@',template):raise ValueError('Unresolved template placeholder')
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    html_path=out/(stem+'.html');pgn_out=out/(stem+'.pgn')
    if html_path.exists():
        raise FileExistsError(f'{html_path} already exists. Use an empty staging directory, or obtain authorization to replace this specific review.')
    if pgn_out.exists() and pgn_out.read_text(encoding='utf-8')!=pgn:raise FileExistsError(f'{pgn_out} contains another PGN.')
    html_path.write_text(template,encoding='utf-8');pgn_out.write_text(pgn,encoding='utf-8')
    return {'html':str(html_path),'pgn':str(pgn_out),'positions':len(states),'lessons':len(lessons),'user_color':color}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pgn');p.add_argument('review_json');p.add_argument('--out-dir',required=True);p.add_argument('--game',type=int)
    a=p.parse_args();print(json.dumps(build(a.pgn,a.review_json,a.out_dir,a.game),ensure_ascii=False))
if __name__=='__main__':main()
