from contextlib import nullcontext
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import patch
import unittest
from importer import from_save

@dataclass
class Attrs:
    passing:int=15
    reflexes:int=0
@dataclass
class Positions:
    mc:int=20
    dm:int=16

class ImportTests(unittest.TestCase):
    def test_pinned_public_api_fields_exist(self):
        from fmsave.models.players import Player
        from fmsave.models.matches import PlayerMatchStats
        from fmsave.models.season_stats import PlayerSeasonStats
        for cls,fields in [(Player,['uid','ability','positions','raw_condition','raw_match_sharpness','second_nation_ids']),
                           (PlayerMatchStats,['player_uid','date','rating','minutes','stats_in_range']),
                           (PlayerSeasonStats,['player_uid','kind','minutes','average_rating'])]:
            for field in fields:self.assertIn(field,cls.__dataclass_fields__)
    def test_join_scales_missing_pa_and_ambiguous_suspension(self):
        player=NS(uid=99,name='Test',age=18,ability=NS(current=105,potential=None),club_uid=7,
                  club_name='Testclub',nation_id=1,second_nation_ids=(2,),positions=Positions(),
                  attributes=Attrs(),raw_condition=9200,raw_match_sharpness=8100,
                  personality=NS(professionalism=16),suspensions=[NS()])
        matches=[NS(player_uid=99,stats_in_range=True,has_stats=True,date=date(2026,10,22),rating=7.4,minutes=90)]
        stats=[NS(player_uid=99,club_uid=7,kind='overall',minutes=600,average_rating=7.2),
               NS(player_uid=99,club_uid=7,kind='league',minutes=500,average_rating=9.0)]
        save=NS(info=NS(game_date=date(2026,10,24)),players=lambda:[player],player_match_stats=lambda:matches,
                player_season_stats=lambda:stats,managed_clubs=lambda:[NS(club_uid=7)])
        with patch('fmsave.open',return_value=nullcontext(save)):data=from_save('synthetic.fm')
        p=data['players'][0]
        self.assertEqual(p['id'],'99');self.assertEqual(p['nation_ids'],[1,2])
        self.assertEqual(p['fitness'],92);self.assertEqual(p['sharpness'],81)
        self.assertIsNone(p['pa']);self.assertEqual(p['season']['minutes'],600)
        self.assertEqual(p['season']['average_rating'],7.2)
        self.assertEqual(p['status'],'unknown');self.assertTrue(p['notes'])
        self.assertNotIn('reflexes',p['attributes']);self.assertEqual(p['matches'][0]['rating'],7.4)
if __name__=='__main__':unittest.main()
