# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/chess-review/skills/chess-review-open/scripts'))
import fetch_chesscom as f


def entry(n, end, side='white', rules='chess'):
    white, black = ('Learner', 'Opponent') if side == 'white' else ('Opponent', 'Learner')
    pgn = f'''[Event "Fictional test"]
[White "{white}"]
[Black "{black}"]
[Date "2000.01.01"]
[UTCDate "2000.01.01"]
[UTCTime "00:05:00"]
[Result "1-0"]
[Link "https://www.chess.com/game/live/{n}"]

1. e4 e5 2. Nf3 Nc6 1-0
'''
    return dict(url=f'https://www.chess.com/game/live/{n}',end_time=end,rules=rules,pgn=pgn,
                white={'username':white},black={'username':black})


class FetchTests(unittest.TestCase):
    def test_sequential_latest_sort_cross_month_and_bound(self):
        base=f.API+'learner/games/'
        calls=[]
        data={base+'archives':{'archives':[base+'2000/01',base+'2000/02',base+'2000/03']},
              base+'2000/03':{'games':[entry(1,30),entry(3,50,rules='chess960'),entry(2,40)]},
              base+'2000/02':{'games':[entry(4,20)]}}
        def get(url, **kwargs): calls.append(url);return data[url]
        games,meta=f.fetch_latest('LEARNER',1,get)
        self.assertEqual([g['url'] for g in games],[entry(2,40)['url']])
        self.assertEqual(len(calls),2)
        self.assertEqual(len(meta['skipped_nonstandard']),1)
        calls.clear()
        games,meta=f.fetch_latest('learner',3,get)
        self.assertEqual([g['end_time'] for g in games],[40,30,20])
        self.assertEqual(calls,[base+'archives',base+'2000/03',base+'2000/02'])
        games,meta=f.fetch_latest('learner',5,get,max_months=1)
        self.assertTrue(meta['search_limited'])
        self.assertEqual(len(games),2)

    def test_untrusted_url_and_username_rejected(self):
        with self.assertRaises(ValueError): f.username('../someone')
        with self.assertRaises(ValueError):
            f.fetch_latest('learner',request=lambda *a,**k:{'archives':['https://example.com/data']})
        for url in ['https://www.chess.com/game/123','https://www.chess.com/analysis/game/live/123?move=0','https://www.chess.com/live/game/123']:
            self.assertEqual(f.game_id(url),'123')
        self.assertIsNone(f.game_id('https://evil.example/game/123'))

    def test_sides_timezone_and_duplicate_never_substituted(self):
        from zoneinfo import ZoneInfo
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old=entry(1,10)
            (root/'2000-01-01_Opponent.pgn').write_text(old['pgn'].replace('/game/live/1','/analysis/game/live/1?move=0'))
            html=root/'2000-01-01_Opponent.html';html.write_text('review')
            records,warnings=f.save_games(root,'learner',[old,entry(2,20,'black')],ZoneInfo('America/Toronto'))
            self.assertEqual(records[0]['already_reviewed'],[str(html.resolve())])
            self.assertEqual(records[1]['already_reviewed'],[])
            self.assertEqual([r['user_color'] for r in records],['white','black'])
            self.assertTrue(records[0]['start_time'].startswith('1999-12-31'))
            no_link=entry(3,30)
            no_link['pgn']=no_link['pgn'].replace('[Link "https://www.chess.com/game/live/3"]\n','')
            records,_=f.save_games(root,'learner',[no_link])
            self.assertEqual(records[0]['already_reviewed'],[]) # Same moves, distinct known IDs.
            self.assertEqual((root/'work/chesscom/learner/1/input.pgn').read_text(),old['pgn'])

    def test_missing_link_signature_and_identity_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);item=entry(1,10)
            (root/'old.pgn').write_text(item['pgn'].replace('[Link "https://www.chess.com/game/live/1"]\n',''))
            (root/'old.html').write_text('review')
            records,_=f.save_games(root,'learner',[item]);self.assertTrue(records[0]['already_reviewed'])
            item['white']['username']='someone_else'
            with self.assertRaises(ValueError):f.save_games(root,'learner',[item])
            item=entry(1,10);item['pgn']=item['pgn'].replace('game/live/1','game/live/999')
            with self.assertRaises(ValueError):f.save_games(root,'learner',[item])

    def test_unfinished_pgn_rejected(self):
        with self.assertRaises(ValueError):f.parse_game(entry(1,10)['pgn'].replace('1-0','*'))
        with self.assertRaises(ValueError):f.parse_game(entry(1,10)['pgn']+'\n'+entry(2,20)['pgn'])

    def test_cli_remembers_account_and_defaults_one_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(f,'fetch_latest',return_value=([entry(1,10)],{})) as fetch:
                with patch.object(sys,'argv',['fetch_chesscom',tmp,'--user','Learner']),contextlib.redirect_stdout(io.StringIO()):f.main()
                self.assertEqual(fetch.call_args.args,('learner',1))
                self.assertEqual(json.loads((root/'.chess-review-account.json').read_text())['chesscom_username'],'learner')
                with patch.object(sys,'argv',['fetch_chesscom',tmp]),contextlib.redirect_stdout(io.StringIO()):f.main()
                self.assertEqual(fetch.call_args.args,('learner',1))
                with patch.object(sys,'argv',['fetch_chesscom',tmp,'--user','Another']),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):f.main()

    def test_connect_only_remembers_username_without_games_or_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(f,'get_json',return_value={'username':'Learner'}) as get, patch.object(f,'fetch_latest') as fetch:
                with patch.object(sys,'argv',['fetch_chesscom',tmp,'--user','Learner','--connect-only']), contextlib.redirect_stdout(io.StringIO()) as output:
                    f.main()
                self.assertEqual(json.loads(output.getvalue())['status'],'connected')
                self.assertEqual(json.loads((Path(tmp)/'.chess-review-account.json').read_text())['chesscom_username'],'learner')
                get.assert_called_once_with(f.API+'learner')
                fetch.assert_not_called()
                self.assertFalse((Path(tmp)/'work').exists())


if __name__=='__main__':unittest.main()
