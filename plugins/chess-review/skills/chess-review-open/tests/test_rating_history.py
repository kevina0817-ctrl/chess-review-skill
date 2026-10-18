import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rating_history as rh

GAME={'url':'https://www.chess.com/game/live/123','end_time':1000,'rated':True,'rules':'chess','time_class':'rapid','time_control':'600',
 'white':{'username':'Example','rating':255,'result':'resigned'},'black':{'username':'Opponent','rating':270,'result':'win'}}
class RatingHistoryTests(unittest.TestCase):
 def test_identity_post_rating_dedup_sort_and_pools(self):
  second=copy.deepcopy(GAME);second.update(url='https://www.chess.com/game/live/124',end_time=2000,time_class='blitz');second['white'],second['black']=second['black'],second['white'];second['black']['rating']=118
  h=rh.normalize('example',[],[{'games':[second,GAME,GAME]}],{})
  self.assertEqual([g['rating'] for g in h['games']],[255,118]);self.assertEqual(h['games'][1]['side'],'black');self.assertEqual(h['games'][0]['result'],'loss')
 def test_draw_unrated_and_missing_rating(self):
  g=copy.deepcopy(GAME);g['white'].update(result='timevsinsufficient',rating=None);g['rated']=False
  h=rh.normalize('Example',[],[{'games':[g]}],{})
  self.assertEqual(h['games'][0]['result'],'draw');self.assertIsNone(h['games'][0]['rating']);self.assertFalse(h['games'][0]['rated'])
 def test_unknown_result_not_assumed_loss(self):
  g=copy.deepcopy(GAME);g['white']['result']=g['black']['result']='new-result'
  self.assertEqual(rh.normalize('Example',[],[{'games':[g]}],{})['games'][0]['result'],'unknown')
 def test_account_mismatch_rejected(self):
  with self.assertRaises(ValueError):rh.normalize('someoneelse',[],[{'games':[GAME]}],{})
 def test_serial_full_snapshot_and_failed_sync_preserves_file(self):
  base='https://api.chess.com/pub/player/example';urls=[base+'/games/2026/09',base+'/games/2026/10'];calls=[]
  def get(url):
   calls.append(url)
   return {'archives':urls} if url.endswith('archives') else {'chess_rapid':{'last':{'rating':255,'date':1000}}} if url.endswith('stats') else {'games':[GAME]}
  with tempfile.TemporaryDirectory() as directory:
   rh.sync('Example',directory,get);self.assertEqual(calls,[base+'/games/archives',*urls,base+'/stats']);old=(Path(directory)/'history.json').read_bytes()
   def fail(url):
    if url==urls[1]:raise OSError('network unavailable')
    return get(url)
   with self.assertRaises(OSError):rh.sync('Example',directory,fail)
   self.assertEqual((Path(directory)/'history.json').read_bytes(),old)
 def test_build_failure_marks_previous_snapshot_stale(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'.chess-review-ratings.json').write_text(json.dumps({'username':'Example','cache_dir':'cache'}))
   d={'user':'Example','rating_history':{'status':'ok','synced_at':123,'games':[{'rating':100}]}}
   with patch.object(rh,'sync',side_effect=OSError('offline')):rh.update_from_config(root,d)
   self.assertEqual(d['rating_history'],{'status':'stale','synced_at':123,'games':[{'rating':100}]})
if __name__=='__main__':unittest.main()
