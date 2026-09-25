import copy,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'plugins/chess-review/skills/chess-review-open'
sys.path.insert(0,str(SKILL/'scripts'))
from chess_common import chess,load_game
from review_analytics import build_analytics,identify_opening,phase,white_evaluation,summarize
from build_review import build

class AnalyticsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.pgn=self.root/'game.pgn'
  self.pgn.write_text('[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0\n')
  self.game,self.boards,self.moves,self.text=load_game(self.pgn)
 def tearDown(self):self.tmp.cleanup()
 def data(self,perspective='white'):
  sign=1 if perspective=='white' else -1
  positions=[]
  for i,b in enumerate(self.boards):
   e={'fen':b.fen(),'cp':100*i*sign,'mate':None,'depth':12,'pv':[]}
   if b.is_checkmate():e.update(cp=None,mate=0)
   elif i==len(self.moves)-1:e.update(cp=None,mate=sign,pv=['Qxf7#'])
   positions.append(e)
  rows=[{'ply':i,'uci':m.uci(),'side':'white' if self.boards[i].turn else 'black','before':positions[i],'after':positions[i+1]} for i,m in enumerate(self.moves)]
  return {'source_pgn_sha256':hashlib.sha256(self.text.encode()).hexdigest(),'perspective':perspective,'rows':rows}
 def test_perspective_sign_mate_and_empty_phases(self):
  a=build_analytics(self.data(),self.boards,self.moves,self.text)
  b=build_analytics(self.data('black'),self.boards,self.moves,self.text)
  self.assertEqual(a['positions'],b['positions']);self.assertEqual(a['sides'],b['sides'])
  self.assertEqual(a['positions'][-1]['terminal'],'white');self.assertEqual(a['positions'][-1]['advantage'],100)
  self.assertEqual(a['phases']['white']['endgame']['score'],None)
  self.assertLess(a['sides']['black']['score'],a['sides']['white']['score'])
  self.assertLess(a['sides']['white']['cp_samples'],a['sides']['white']['moves'])
 def test_reject_wrong_game_fen_order_and_illegal_pv(self):
  for change in ('hash','fen','order','pv','nan'):
   d=self.data()
   if change=='hash':d['source_pgn_sha256']='wrong'
   elif change=='fen':d['rows'][0]['before']['fen']=self.boards[1].fen()
   elif change=='order':d['rows'][0]['uci']='d2d4'
   elif change=='pv':d['rows'][0]['before']['pv']=['Qh8#']
   else:d['rows'][0]['before']['cp']=float('nan')
   with self.subTest(change=change),self.assertRaises(ValueError):build_analytics(d,self.boards,self.moves,self.text)
 def test_refined_score_preferred_and_stalemate(self):
  d=self.data();d['rows'][0]['before_refined']={**d['rows'][0]['before'],'cp':125,'depth':25,'pv':['e4','e5']}
  a=build_analytics(d,self.boards,self.moves,self.text)
  self.assertEqual(a['positions'][0]['cp'],125);self.assertTrue(a['rows'][0]['preferred'])
  b=chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
  e=white_evaluation({'fen':b.fen(),'cp':0,'mate':None,'pv':[]},b,'white')
  self.assertEqual(e['terminal'],'draw');self.assertEqual(e['advantage'],50)
 def test_black_mate_and_score_bounds(self):
  b=chess.Board()
  for san in ['f3','e5','g4','Qh4#']:b.push_san(san)
  self.assertTrue(b.is_checkmate())
  for pov in ('white','black'):
   e=white_evaluation({'fen':b.fen(),'cp':None,'mate':0,'pv':[]},b,pov)
   self.assertEqual(e['terminal'],'black');self.assertEqual(e['advantage'],0)
  d=self.data();a=build_analytics(d,self.boards,self.moves,self.text)
  self.assertTrue(all(0<=r['quality']<=100 for r in a['rows']))
  self.assertTrue(all(r['cp_loss'] is None or r['cp_loss']>=0 for r in a['rows']))
 def test_opening_transposition_and_nonstandard_position(self):
  def boards(line):
   b=chess.Board();result=[b.copy()]
   for move in line.split():b.push_san(move);result.append(b.copy())
   return result
  first=identify_opening(boards('e4 e5 Nf3 Nc6 Bc4'))
  second=identify_opening(boards('e4 e5 Bc4 Nc6 Nf3'))
  self.assertEqual(first['epd'],second['epd']);self.assertTrue(first['name'].startswith('Italian Game'))
  self.assertIsNone(identify_opening([chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')]))
 def test_opponent_lesson_and_backwards_compatible_build(self):
  config=json.loads((SKILL/'examples/white-review.json').read_text());config['archive_date']='2000-01-01'
  item=config['lessons'][0];item.update(ply=5,actor='opponent',better=['g6'],assert_mate=False)
  path=self.root/'review.json';path.write_text(json.dumps(config))
  result=build(self.pgn,path,self.root/'out')
  html=Path(result['html']).read_text();self.assertIn('"actor": "opponent"',html);self.assertIn('"analytics": null',html)
  item['actor']='user';path.write_text(json.dumps(config))
  with self.assertRaises(ValueError):build(self.pgn,path,self.root/'wrong')
if __name__=='__main__':unittest.main()
