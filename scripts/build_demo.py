#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Build fictional, legal teaching reviews for public feature screenshots."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'plugins/chess-review/skills/chess-review-open'
sys.path.insert(0,str(SKILL/'scripts'))
from build_review import build
from build_leaks import merge, read_payload, validate, verified_review_info
from plan_common_leaks import plan


def lesson(ply,title,why,fix,better,actual=2,positive=False):
    return dict(ply=ply,tag='示例好棋' if positive else '示例复盘',title=title,summary=why,
                why=why,fix=fix,habit='先检查对手的将军和吃子，再决定自己的走法。',
                hint='先找对手攻击的目标，以及可以保护它的棋子。',actual_plies=actual,
                better=better,positive=positive)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if list(a.out.glob('*.pgn')) or (a.out/'common-leaks.html').exists():
        parser.error('Use an empty demo directory; never overwrite a review archive.')
    entries=[
      ('ExampleA','black','1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0',
       lesson(5,'先挡住后和象对 f7 的攻击','示例原走法 Nf6 没有挡住 h5 白后与 c4 白象对 f7 的攻击，下一手 Qxf7#。','g6 先赶后；示范 Qf3 后 Nf6，再挡住白后沿 f 线的攻击。',['g6','Qf3','Nf6'])),
      ('ExampleB','black','1. e4 e5 2. Bc4 Nc6 3. Qf3 b6 4. Qxf7# 1-0',
       lesson(5,'同一个漏洞，换个局面又出现','示例原走法 b6 没处理 f7 的将死威胁。','Nf6 用马挡住 f3 白后通往 f7 的线路。',['Nf6','Nc3','Bc5'])),
      ('ExampleC','white','1. e4 d5 2. Qh5 Nf6 3. Qxd5 Nxd5 0-1',
       lesson(4,'吃兵之前，先看看谁能吃回你的后','示例里白后吃 d5 兵，随即被 f6 黑马吃掉。','Qe2 先保住后，不用后去换一个兵。',['Qe2','Nc6','Nf3'])),
      ('ExampleD','black','1. e4 e5 2. Qh5 Nc6 3. Bc4 g6 4. Qf3 Nf6 5. Ne2 Bg7 6. d3 O-O 1/2-1/2',
       lesson(5,'这次，先处理 f7 的威胁','在后来的虚构示例中，学习者先用 g6 赶后，再用 Nf6 挡住 f 线。','这段示例保留了 g6、Qf3、Nf6 的原走法，用于演示进步记录。',['g6','Qf3','Nf6'],actual=3,positive=True))
    ]
    # Ten deliberately fictional records demonstrate the same real first-run gate.
    for i in range(4,10):
        entries.append((f'Example{chr(65+i)}','white','1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 1/2-1/2',
                        lesson(2,'先出马，发展棋子','示例中 Nf3 出子并攻击 e5 兵。','保留这个正常的出子动作，不把每盘都强行归为漏洞。',['Nf3'],actual=1,positive=True)))
    stems=[]
    for i,(opponent,color,moves,item) in enumerate(entries,1):
        date=f'2000-01-{i:02d}';stem=date+'_'+opponent;stems.append(stem)
        white,black=('Learner',opponent) if color=='white' else (opponent,'Learner')
        result=moves.split()[-1]
        pgn=f'[Event "Fictional teaching demo"]\n[Site "Local demo"]\n[Date "{date.replace("-",".")}"]\n[White "{white}"]\n[Black "{black}"]\n[Result "{result}"]\n\n{moves}\n'
        source=a.out/(stem+'.pgn');source.write_text(pgn)
        cfg=dict(archive_date=date,timezone='UTC',user_color=color,intro='虚构教学示例，仅演示功能，不代表真实用户棋局。',
            overview=['十盘均为人为构造的合法教学棋谱。'],strengths=['按每一盘具体走法说明。'],training=[dict(title='先看威胁',text='检查对方的将军和直接吃子。')],
            review_guide='在棋盘上比较示例原走法和建议。',ending='教学棋谱按标注结果结束；不是实际网站对局。',
            provenance='虚构教学数据；python-chess 校验走法，人工核对简单战术，未宣称运行引擎。',date_note='2000 年日期仅用于示例排序。',lessons=[item])
        config=a.out/(stem+'.json');config.write_text(json.dumps(cfg,ensure_ascii=False))
        build(source,config,a.out/'generated')
        (a.out/(stem+'.html')).write_bytes((a.out/'generated'/(stem+'.html')).read_bytes())
    case_specs=[
      (0,'direct-threats','后和象一起瞄准 f7',
       ['同一个示例起点：白后 h5、白象 c4 都攻击 f7。','原走法 Nf6，f7 的威胁仍然存在。','白后 Qxf7#，象保护着后，黑王不能吃它。'],
       ['从同一个局面开始，先处理 f7 的威胁。','g6 赶走 h5 的后，截断它通往 f7 的斜线。','示范 Qf3：白后换一条线路继续瞄着 f7。','Nf6 用马挡住 f 线，眼前将死威胁解除。'],
       'Nf6 没处理 f7 的威胁，下一手被将死。','g6 先赶后，再用 Nf6 挡住后续攻击。'),
      (1,'direct-threats','另一个示例，也漏看了 f7',
       ['白后在 f3、白象在 c4，f7 正受到攻击。','原走法 b6，没有处理将死威胁。','Qxf7#，相同问题在另一段示例中再次出现。'],
       ['相同起点，先挡住白后的线路。','Nf6 把马放到 f 线上。','示范白方 Nc3 继续出子。','黑方 Bc5，眼前将死威胁已解除。'],
       'b6 没保护 f7，白后直接将死。','Nf6 先挡住白后，之后再发展其他棋子。'),
      (2,'recapture','吃到一个兵，却丢了后',
       ['d5 黑兵可以吃，但 f6 黑马也保护着 d5。','原走法 Qxd5，白后吃掉一个兵。','黑马 Nxd5，吃掉刚走到 d5 的白后。'],
       ['相同起点，先检查 d5 由谁保护。','Qe2 把后移到安全位置。','示范黑方 Nc6。','白方 Nf3，继续出子，后仍安全。'],
       'Qxd5 只看到吃兵，没看到黑马可以吃后。','Qe2 保住后，再发展棋子。')]
    groups=[dict(id='direct-threats',title='没看到对手在攻击什么',short='先看威胁',desc='自己的计划先放一下：对方现在能吃谁、将什么军？',habit='落子前，先检查对手的将军、一步将死和直接吃子。'),
            dict(id='recapture',title='只算自己吃，没算对方吃回',short='算完吃回',desc='吃到棋子以后，对方最强的回应是什么？',habit='至少算三拍：我走、对方回应、我再怎么办。')]
    cases=[]
    for i,group,title,actual,better,why,fix in case_specs:
        cases.append(dict(stem=stems[i],ply=entries[i][3]['ply'],group_id=group,title=title,
                          contrast=dict(actual=why,better=fix),captions=dict(actual=actual,better=better)))
    cases[0]['arrows']={'actual':{'0':[['h5','f7'],['c4','f7']],'1':[['h5','f7'],['c4','f7']]},'better':{'0':[['h5','f7'],['c4','f7']]}}
    progress=[dict(kind='comparison',title='这次，你先挡住了 f7 的威胁',skill='识别眼前的一步将死',
        explanation='两段虚构示例演示同一能力：较早记录漏防 f7，后来记录先赶后、再挡线。实际使用时，这里展示用户自己的已验证棋谱。',
        habit='先处理对手直接的将死威胁，再继续出子。',limit='演示数据，不代表真实用户进步；一次正确应对也不等于已经稳定掌握。',
        prior=dict(stem=stems[0],ply=5,captions=case_specs[0][3]),
        current=dict(stem=stems[3],ply=5,captions=case_specs[0][4]))]
    update=dict(groups=groups,cases=cases,progress=progress,assessments=[dict(stem=s,outcome='existing' if i<3 else 'none',note='Fictional teaching demo, checked for screenshot generation.') for i,s in enumerate(stems)])
    (a.out/'leaks-update.json').write_text(json.dumps(update,ensure_ascii=False,indent=2))
    batch=plan(a.out,'Learner',True)
    assert batch['status']=='ready' and len(batch['selected'])==10
    (a.out/'leaks-plan.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2))
    import subprocess
    subprocess.run([sys.executable,str(SKILL/'scripts/build_leaks.py'),str(a.out),'--user','Learner','--plan',str(a.out/'leaks-plan.json'),'--merge',str(a.out/'leaks-update.json')],check=True)
    subprocess.run([sys.executable,str(SKILL/'scripts/build_library.py'),str(a.out)],check=True)
    page=a.out/'common-leaks.html';html=page.read_text();html=html.replace('<nav class="top">','<p style="font-size:13px;color:#617168;margin:0 0 16px">演示数据 · 10 盘虚构教学棋谱 · 不代表真实用户记录</p><nav class="top">',1);page.write_text(html)
    print(json.dumps({'demo':str(page),'reviewed_games':10,'cases':3,'progress':1}))


if __name__=='__main__':main()
