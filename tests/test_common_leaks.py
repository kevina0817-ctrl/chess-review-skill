# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Only fictional local teaching games; never use a person's archive in public tests."""
import copy, json, sys, tempfile, unittest, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugins/chess-review/skills/chess-review-open/scripts'))
import build_leaks as leaks
from plan_common_leaks import plan
from build_review import build

class CommonLeaksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.stems=[]
        for i in range(1,13):
            date=f'2000.01.{i:02d}';stem=f'2000-01-{i:02d}_FictionalOpponent{i}'
            (self.root/(stem+'.pgn')).write_text(f'[Event "Fictional test"]\n[Date "{date}"]\n[White "Learner"]\n[Black "FictionalOpponent{i}"]\n[Result "1-0"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0\n')
            self.stems.append(stem)

    def test_opt_in_threshold_scope_and_budget(self):
        self.assertEqual(plan(self.root,'Learner',None)['status'],'needs_opt_in')
        self.assertEqual(plan(self.root,'Learner',False)['status'],'disabled')
        result=plan(self.root,'Learner',True)
        self.assertEqual(result['status'],'need_more_reviews')
        self.assertEqual(result['missing_games'],10) # Twelve PGNs alone are not twelve reviews.
        for i in range(9):self.make_review(i)
        self.assertEqual(plan(self.root,'Learner',True)['missing_games'],1)
        self.make_review(9)
        result=plan(self.root,'Learner',True)
        self.assertEqual(result['status'],'ready');self.assertEqual(len(result['selected']),10)
        self.assertEqual(result['selected'][0]['stem'],self.stems[9])
        self.make_review(10)
        result=plan(self.root,'Learner',True)
        self.assertEqual(len(result['selected']),10);self.assertEqual(len(result['deferred']),1)
        self.assertEqual(result['budget_minutes'],25)
        self.assertEqual(plan(self.root,'SomeoneElse',True)['eligible_games'],0)
        self.assertEqual(plan(self.root,'Learner',True,maximum=5)['status'],'batch_too_small')
        self.assertEqual(plan(self.root,'Learner',True,budget=6)['status'],'batch_too_small')
        # Corrupt or missing review content cannot satisfy the threshold.
        (self.root/(self.stems[9]+'.html')).write_text('<html>not a verified review</html>')
        (self.root/(self.stems[10]+'.html')).unlink()
        self.assertEqual(plan(self.root,'Learner',True)['eligible_games'],9)

    def make_review(self,index):
        cfg=json.loads((ROOT/'plugins/chess-review/skills/chess-review-open/examples/white-review.json').read_text())
        cfg['archive_date']=self.stems[index][:10]
        config=self.root/'review.json';config.write_text(json.dumps(cfg))
        build(self.root/(self.stems[index]+'.pgn'),config,self.root/'generated')
        for f in (self.root/'generated').glob('*'):
            if f.suffix in ('.html','.pgn'):shutil.copy2(f,self.root/f.name)

    def test_opponent_lesson_cannot_be_user_progress(self):
        cfg=json.loads((ROOT/'plugins/chess-review/skills/chess-review-open/examples/white-review.json').read_text())
        cfg['archive_date']=self.stems[0][:10]
        cfg['lessons'][0].update(ply=5,actor='opponent',positive=True,better=['g6'],assert_mate=False,actual_plies=2)
        config=self.root/'opponent.json';config.write_text(json.dumps(cfg))
        built=build(self.root/(self.stems[0]+'.pgn'),config,self.root/'opponent-out')
        shutil.copy2(built['html'],self.root/(self.stems[0]+'.html'))
        d={'user':'Learner','groups':[{'id':'defense'}]}
        clip={'stem':self.stems[0],'ply':5,'captions':['start','reply','mate']}
        with self.assertRaisesRegex(ValueError,'before the user moves'):
            leaks.progress_clip(self.root,clip,d,positive=True)

    def test_incremental_progress_dedup_and_integrity(self):
        for i in range(11):self.make_review(i)
        d={'version':2,'user':'Learner','groups':[],'cases':[],'pieces':{},'assessments':[]}
        update={'groups':[{'id':'fixture','title':'虚构测试','short':'测试','desc':'仅测试结构','habit':'核对真实走法'}],
          'cases':[{'stem':self.stems[0],'ply':6,'group_id':'fixture','title':'虚构测试局面','contrast':{'actual':'测试','better':'测试'},'captions':{'actual':['起点','将死'],'better':['起点','将死']}}],
          'progress':[{'kind':'repeated','title':'虚构测试进步','skill':'检查将死','explanation':'两段已校验的虚构样例','habit':'检查解将方法','limit':'测试，不代表真实表现',
          'prior':{'stem':self.stems[0],'ply':6,'captions':['起点','将死']},'current':{'stem':self.stems[1],'ply':6,'captions':['起点','将死']}}]}
        update['assessments']=[{'stem':self.stems[i],'outcome':'existing' if i==0 else 'none','note':'Fictional reviewed fixture'} for i in range(10)]
        update_path=self.root/'update.json';update_path.write_text(json.dumps(update))
        command=[sys.executable,str(ROOT/'plugins/chess-review/skills/chess-review-open/scripts/build_leaks.py'),str(self.root),'--user','Learner','--merge',str(update_path)]
        rejected=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(rejected.returncode,0);self.assertIn('opted-in plan',rejected.stderr)
        plan_path=self.root/'plan.json';plan_path.write_text(json.dumps(plan(self.root,'Learner',True,self.stems[:10])))
        # Reject fabricated counts and incomplete assessment coverage, not just small plans.
        valid_plan=json.loads(plan_path.read_text())
        forged=copy.deepcopy(valid_plan);forged['selected']=[valid_plan['selected'][0]]*10
        plan_path.write_text(json.dumps(forged))
        rejected=subprocess.run(command+['--plan',str(plan_path)],capture_output=True,text=True)
        self.assertNotEqual(rejected.returncode,0);self.assertIn('distinct',rejected.stderr)
        plan_path.write_text(json.dumps(valid_plan))
        short_update=copy.deepcopy(update);short_update['assessments']=short_update['assessments'][:9]
        update_path.write_text(json.dumps(short_update))
        rejected=subprocess.run(command+['--plan',str(plan_path)],capture_output=True,text=True)
        self.assertNotEqual(rejected.returncode,0);self.assertIn('assessment',rejected.stderr)
        update_path.write_text(json.dumps(update))
        built=subprocess.run(command+['--plan',str(plan_path)],capture_output=True,text=True)
        self.assertEqual(built.returncode,0,built.stderr)
        actual_archive=leaks.read_payload(self.root/'common-leaks.html')
        self.assertEqual(actual_archive['user'],'Learner');self.assertEqual(len(actual_archive['assessments']),10)
        (self.root/'common-leaks.html').unlink()
        leaks.merge(self.root,d,copy.deepcopy(update));before=copy.deepcopy(d)
        leaks.merge(self.root,d,copy.deepcopy(update));self.assertEqual(d,before)
        self.assertEqual(plan(self.root,'Learner',True,self.stems[:10])['eligible_games'],11);self.assertEqual(len(d['cases']),1);self.assertEqual(len(d['progress']),1)
        wrong=copy.deepcopy(d['progress'][0]);wrong['prior'],wrong['current']=wrong['current'],wrong['prior']
        with self.assertRaisesRegex(ValueError,'earlier'):leaks.progress_item(self.root,wrong,d)
        wrong=copy.deepcopy(d);wrong['cases'][0]['side']='black'
        with self.assertRaises(ValueError):leaks.validate(self.root,wrong)
        self.assertEqual(before['cases'][0]['branches']['actual']['frames'][0]['fen'],before['cases'][0]['branches']['better']['frames'][0]['fen'])
        page=self.root/'common-leaks.html';page.write_text('<script id="visual-data" type="application/json">'+json.dumps(d)+'</script>')
        self.assertEqual(plan(self.root,'Learner',True)['status'],'specify_new_games')
        result=plan(self.root,'Learner',True,[self.stems[10]])
        self.assertEqual(result['mode'],'incremental');self.assertEqual(len(result['selected']),1)

if __name__=='__main__':unittest.main()
