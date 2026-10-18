#!/usr/bin/env python3
"""Attach unmistakably fictional trend counts to the generated teaching demo only."""
import json,re
from pathlib import Path

def attach(directory, skill):
    page=Path(directory)/'common-leaks.html'
    source=page.read_text()
    data=json.loads(re.search(r'<script id="visual-data" type="application/json">(.*?)</script>',source,re.S)[1])
    if data.get('user')!='Learner':raise ValueError('Only the fictional Learner demo may receive synthetic counts')
    en=skill.name.endswith('-en');start=946684800;games=[]
    for i in range(60):
        games.append(dict(id=f'demo/{i}',url='https://www.chess.com/',end_time=start+i*86400,side='white' if i%2==0 else 'black',rating=500+i*2+(i%7-3)*5,opponent='DemoOpponent'+str(i+1),opponent_rating=510+i*2,result=['win','draw','loss'][i%3],rated=True,rules='chess',pool='rapid',time_control='600'))
    # An additional independent pool exercises filtering without implying cross-pool equivalence.
    games.append(dict(games[-1],id='demo/blitz',pool='blitz',rating=400))
    history=dict(version=1,username='Learner',source='https://www.chess.com/news/view/published-data-api',synced_at=start+60*86400,archives=[],status='ok',games=games,current={'rapid':{'rating':games[-2]['rating'],'date':games[-2]['end_time']},'blitz':{'rating':400,'date':games[-1]['end_time']}})
    def metric(count,total,games):return dict(count=count,total=total,games=games,examples=[])
    windows=[]
    for i,errors in enumerate([80,65,50]):
        windows.append(dict(games=20,start=start+i*20*86400,end=start+(i*20+19)*86400,moves=600,errors=metric(errors,500,20),phases=[metric([20,17,12][i],200,20),metric([45,35,26][i],200,20),metric([15,13,12][i],100,10)],mate=metric(i+3,10,7),defense=metric(i+4,10,6)))
    data['rating_history']=history;data['capability_history']=dict(status='ok',version='fictional-demo',engine='Synthetic demonstration counts — not engine analysis',engine_sha256='',pool='rapid',synced_at=history['synced_at'],games=60,start=start,end=start+59*86400,window_size=20,windows=windows,game_ids=[])
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    template=(skill/'assets/leaks-template.html').read_text().replace('__RATING_SCRIPT__',(skill/'assets/rating-history.js').read_text()).replace('__CAPABILITY_SCRIPT__',(skill/'assets/capability-history.js').read_text()).replace('__DATA__',payload)
    label='DEMO · Fictional games and synthetic trend counts. Not a real player or engine-derived results.' if en else '演示数据 · 虚构棋局及合成趋势统计，不代表真实棋手或引擎分析结果。'
    template=template.replace('<main class="wrap">','<main class="wrap"><p class="notice" id="demo-notice">'+label+'</p>',1)
    page.write_text(template)
