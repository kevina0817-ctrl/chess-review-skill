import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chess
from capability_history import mates_in_one,tactical_observations,aggregate
class CapabilityTests(unittest.TestCase):
 def test_mate_opportunity_and_actual_completion(self):
  b=chess.Board('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1');original=b.fen()
  self.assertIn(chess.Move.from_uci('f7g7'),mates_in_one(b));self.assertEqual(b.fen(),original)
  self.assertTrue(tactical_observations(b,chess.Move.from_uci('f7g7'))['mate']['success'])
  self.assertFalse(tactical_observations(b,chess.Move.from_uci('f7e7'))['mate']['success'])
 def test_back_rank_threat_can_be_defended(self):
  b=chess.Board('4r1k1/8/8/8/8/B7/5PPP/6K1 w - - 0 1')
  self.assertTrue(tactical_observations(b,chess.Move.from_uci('h2h3'))['defense']['success'])
  self.assertFalse(tactical_observations(b,chess.Move.from_uci('a3b2'))['defense']['success'])
 def test_current_check_is_not_counted_as_quiet_threat(self):
  b=chess.Board('k7/8/8/8/8/8/5PrP/6K1 w - - 0 1');self.assertTrue(b.is_check())
  self.assertNotIn('defense',tactical_observations(b,chess.Move.from_uci('g1f1')))
 def test_count_opportunities_not_all_moves_and_count_games_once(self):
  g={'id':'one','opponent':'op','end_time':1,'rows':[{'ply':1,'phase':0,'loss_cp':None,'error':False,'mate':{'success':True}},{'ply':3,'phase':0,'loss_cp':250,'error':True,'mate':{'success':False}},{'ply':5,'phase':1,'loss_cp':50,'error':False}]}
  a=aggregate([g]);self.assertEqual((a['mate']['count'],a['mate']['total'],a['mate']['games']),(1,2,1));self.assertEqual((a['errors']['count'],a['errors']['total']),(1,2));self.assertEqual(a['defense']['total'],0)
if __name__=='__main__':unittest.main()
