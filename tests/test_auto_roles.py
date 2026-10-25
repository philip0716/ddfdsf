import copy
from datetime import date
import unittest
from catalog import ROLES,slots_for
from demo import demo
from engine import evaluate,optimize

class AutoRoleTests(unittest.TestCase):
    def goalkeeper(self,sweeper):
        p=copy.deepcopy(demo()['players'][0]);p['attributes']={key:1 for r in ROLES.values() for key in r['weights']}
        if sweeper:
            p['attributes'].update(passing=20,kicking=20,first_touch=20,decisions=20,composure=20,rushing_out=20,anticipation=20,reflexes=10,handling=10)
        else:
            p['attributes'].update(reflexes=20,handling=20,aerial_reach=20,positioning=20,concentration=20,kicking=10)
        return p
    def test_same_slot_changes_both_roles_for_a_different_profile(self):
        slot=slots_for('4-3-3 DM')[0];before=copy.deepcopy(slot)
        a=evaluate(self.goalkeeper(False),slot,'form',date(2026,10,24))
        b=evaluate(self.goalkeeper(True),slot,'form',date(2026,10,24))
        self.assertEqual(a['resolved_slot']['ip_role'],'ip:No-Nonsense Goalkeeper')
        self.assertEqual(a['resolved_slot']['oop_role'],'oop:Line-Holding Goalkeeper')
        self.assertEqual(b['resolved_slot']['ip_role'],'ip:Ball-Playing Goalkeeper')
        self.assertEqual(b['resolved_slot']['oop_role'],'oop:Sweeper Keeper')
        self.assertEqual(slot,before)
    def test_manual_roles_are_respected_even_when_other_roles_score_higher(self):
        slot=slots_for('4-3-3 DM')[0];slot.update(ip_auto=False,oop_auto=False)
        r=evaluate(self.goalkeeper(False),slot,'form',date(2026,10,24))
        self.assertEqual(r['resolved_slot']['ip_role'],slot['ip_role'])
        self.assertEqual(r['resolved_slot']['oop_role'],slot['oop_role'])
        self.assertEqual(r['role_selection'],{'ip':'manual','oop':'manual'})
    def test_phases_can_be_locked_independently(self):
        slot=slots_for('4-3-3 DM')[0];slot['ip_auto']=False
        r=evaluate(self.goalkeeper(False),slot,'potential',date(2026,10,24))
        self.assertEqual(r['resolved_slot']['ip_role'],slot['ip_role'])
        self.assertEqual(r['resolved_slot']['oop_role'],'oop:Line-Holding Goalkeeper')
    def test_optimization_returns_scored_roles_for_xi_bank_and_alternatives(self):
        data=demo();config=dict(slots=slots_for('4-3-3 DM'),squad='senior')
        r=optimize(data,config)
        cards=r['xi']+r['bench']+[c for group in r['alternatives'] for c in group]
        for c in cards:
            self.assertEqual(c['slot'],c['resolved_slot'])
            self.assertEqual(c['role_selection'],{'ip':'automatic','oop':'automatic'})
            e=evaluate(c['player'],c['slot'],'form',date.fromisoformat(data['date']))
            self.assertEqual(e['score'],c['score'])
            for phase in ['ip','oop']:
                role=ROLES[c['slot'][phase+'_role']]
                self.assertEqual(role['phase'],phase)
                self.assertIn(c['slot'][phase+'_position'],role['positions'])
    def test_invalid_auto_flag_rejected(self):
        slots=slots_for('4-3-3 DM');slots[0]['ip_auto']='true'
        with self.assertRaises(ValueError):optimize(demo(),dict(slots=slots))
