import copy
import unittest
from catalog import slots_for
from demo import demo
from engine import optimize,validate
from squads import squad_for

class SquadTests(unittest.TestCase):
    def test_each_squad_has_independent_xi_and_bench(self):
        for squad in ['senior','second','u19']:
            r=optimize(demo(),dict(slots=slots_for('4-3-3 DM'),objective='form',squad=squad))
            self.assertEqual(len(r['xi']),11)
            self.assertTrue(r['bench'])
            self.assertTrue(all(p['player']['squad']==squad for p in r['xi']+r['bench']))
            self.assertTrue(all(p['player']['squad']==squad for group in r['alternatives'] for p in group))
    def test_membership_does_not_follow_age(self):
        self.assertEqual(squad_for({'age':17,'squad':'senior'},{}),'senior')
        self.assertEqual(squad_for({'age':17,'team_slot':2},{}),'unknown')
    def test_team_mapping_is_specific_to_club_and_team(self):
        p={'club_id':'a','team_id':'42','squad':'unknown'}
        self.assertEqual(squad_for(p,{'a':{'42':'second'}}),'second')
        self.assertEqual(squad_for(p,{'b':{'42':'u19'}}),'unknown')
        self.assertEqual(squad_for(p,{'a':{'43':'u19'}}),'unknown')
    def test_config_mapping_filters_unclassified_import(self):
        d=demo()
        for p in d['players']:p['squad']='unknown'
        c=dict(slots=slots_for('4-3-3 DM'),squad='u19',squad_mappings={'demo':{'demo-u19':'u19'}})
        r=optimize(d,c)
        self.assertTrue(all(x['player']['team_id']=='demo-u19' for x in r['xi']+r['bench']))
    def test_unknown_squad_does_not_fall_back_to_entire_club(self):
        with self.assertRaises(ValueError):optimize(demo(),dict(slots=slots_for('4-3-3 DM'),squad='unknown'))
    def test_legacy_json_is_accepted_without_inventing_membership(self):
        d=demo()
        for p in d['players']:
            p.pop('squad');p.pop('team_id')
        self.assertIs(validate(d),d)
        self.assertEqual(squad_for(d['players'][0],{}),'unknown')
    def test_invalid_membership_and_mapping_are_rejected(self):
        d=demo();d['players'][0]['squad']='U16'
        with self.assertRaises(ValueError):validate(d)
        d=demo();d['squad_mappings']={'demo':{'1':'U16'}}
        with self.assertRaises(ValueError):validate(d)
