import copy
from datetime import date
import unittest
from unittest.mock import patch
from catalog import slots_for, ROLES
from demo import demo
from engine import optimize, form, evaluate, validate, development, window

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.data=demo(); self.config=dict(slots=slots_for('4-3-3 DM'),objective='form')
    def test_both_objectives_recompute_and_do_not_duplicate_players(self):
        a=optimize(self.data,self.config)
        b=optimize(self.data,{**self.config,'objective':'potential'})
        for r in [a,b]:
            ids=[x['player']['id'] for x in r['xi']+r['bench']]
            self.assertEqual(len(r['xi']),11); self.assertEqual(len(set(ids)),len(ids))
            self.assertEqual(len(r['bench']),9)
            self.assertGreaterEqual(r['defense_average'],40)
        self.assertNotEqual({x['player']['id'] for x in a['xi']},{x['player']['id'] for x in b['xi']})
        self.assertLess(sum(x['player']['age'] for x in b['xi']),sum(x['player']['age'] for x in a['xi']))
    def test_verified_unavailability_excludes_even_best_players(self):
        target=next(p for p in self.data['players'] if p['positions'].get('gk'))
        target['status']='injured'
        r=optimize(self.data,self.config)
        self.assertNotIn(target['id'],[x['player']['id'] for x in r['xi']+r['bench']])
        self.assertIn(target['id'],[x['id'] for x in r['excluded']])
    def test_unknown_status_is_visible_and_strict_mode_excludes(self):
        self.data['players'][0]['status']='unknown'
        r=optimize(self.data,self.config)
        c=next(x for x in r['xi'] if x['player']['id']==self.data['players'][0]['id'])
        self.assertIn('Verfügbarkeit ungeprüft',c['warnings'])
        r=optimize(self.data,{**self.config,'only_confirmed':True})
        self.assertNotIn(self.data['players'][0]['id'],[x['player']['id'] for x in r['xi']])
    def test_low_fitness_excludes_players(self):
        self.data['players'][0]['fitness']=20
        r=optimize(self.data,self.config)
        self.assertNotIn('1',[x['player']['id'] for x in r['xi']+r['bench']])
        self.assertEqual(next(x['reason'] for x in r['excluded'] if x['id']=='1'),'Unter Fitnessgrenze')
    def test_override_applies_before_selection(self):
        r=optimize(self.data,{**self.config,'overrides':{'1':'suspended'}})
        self.assertNotIn('1',[x['player']['id'] for x in r['xi']])
    def test_no_silent_out_of_position_fill(self):
        self.data['players']=[p for p in self.data['players'] if not p['positions'].get('gk')]
        with self.assertRaises(ValueError): optimize(self.data,self.config)
    def test_oop_familiarity_is_required(self):
        self.config['slots'][10]['oop_position']='gk'
        self.config['slots'][10]['oop_role']='oop:Sweeper Keeper'
        with self.assertRaises(ValueError): optimize(self.data,self.config)
    def test_incompatible_role_rejected(self):
        self.config['slots'][0]['ip_role']='ip:Channel Forward'
        with self.assertRaises(ValueError): optimize(self.data,self.config)
    def test_missing_pa_is_not_invented(self):
        self.data['players'][0]['pa']=None
        r=optimize(self.data,{**self.config,'objective':'potential'})
        self.assertIn('1',[p['id'] for p in r['excluded']])
    def test_small_sample_is_shrunk_towards_season(self):
        p=copy.deepcopy(self.data['players'][0]);p['season']['average_rating']=7
        p['matches']=[dict(date='2026-10-23',minutes=10,rating=10)]
        f=form(p,date(2026,10,24),'gk')
        self.assertLess(f['rating'],7.1)
        self.assertLess(f['confidence'],50)
    def test_newer_games_count_more(self):
        p=copy.deepcopy(self.data['players'][0]);p['matches']=[dict(date='2026-10-23',minutes=90,rating=9),dict(date='2026-07-01',minutes=90,rating=5)]
        a=form(p,date(2026,10,24),'gk')['rating']
        for m in p['matches']: m['rating']=14-m['rating']
        self.assertGreater(a,form(p,date(2026,10,24),'gk')['rating'])
    def test_future_and_old_matches_do_not_inflate_form(self):
        p=copy.deepcopy(self.data['players'][0]);p['matches']=[dict(date='2030-01-01',minutes=90,rating=10),dict(date='2020-01-01',minutes=90,rating=10)]
        self.assertEqual(form(p,date(2026,10,24),'gk')['games'],0)
        self.assertEqual(form(p,date(2026,10,24),'gk')['source'],'Saisonersatz')
    def test_completely_missing_data_remain_disclosed(self):
        p=copy.deepcopy(self.data['players'][0]);p['matches']=[];p['season']={};p['attributes']={};p['professionalism']=None;p.pop('training_environment');p.pop('development_trend');p['fitness']=None;p['sharpness']=None
        d,c=development(p);self.assertEqual((d,c),(50,0))
        r=evaluate(p,self.config['slots'][0],'form',date(2026,10,24))
        self.assertEqual(r['coverage']['ip'],0);self.assertTrue(r['warnings']);self.assertEqual(r['parts']['readiness'],50)
    def test_projection_is_capped_and_labeled(self):
        for p in self.data['players']:
            key=next(k for k in ROLES if ROLES[k]['phase']=='ip' and next(iter(p['positions'])) in ROLES[k]['positions'])
            pos=next(iter(p['positions']));s=dict(ip_position=pos,oop_position=pos,ip_role=key,oop_role=next(k for k in ROLES if ROLES[k]['phase']=='oop' and pos in ROLES[k]['positions']))
            r=evaluate(p,s,'potential',date(2026,10,24))
            self.assertLessEqual(r['projected_ca'],p['pa']);self.assertGreaterEqual(r['projected_ca'],p['ca'])
            self.assertIn('Modellszenario',r['projection_label'])
    def test_goalkeeper_window_is_later(self):
        p=self.data['players'][0];a=window(p);p=copy.deepcopy(p);p['positions']={'dc':20}
        self.assertGreater(a,window(p))
    def test_validation_duplicate_ids_nan_and_invalid_date(self):
        for mutate in [lambda d:d['players'].append(d['players'][0]),lambda d:d['players'][0].update(ca=float('nan')),lambda d:d.update(date='bad')]:
            d=copy.deepcopy(self.data);mutate(d)
            with self.assertRaises(ValueError):validate(d)
    def test_optimizer_beats_greedy_for_shared_positions(self):
        # 9 forced slots, 2 shared MC places. Greedy 100+1 loses to 99+98.
        slots=slots_for('4-3-3 DM');players=[]
        for j,s in enumerate(slots):
            p=copy.deepcopy(self.data['players'][0]);p.update(id=f'{j:02}',name=f'P{j}',positions={s['ip_position']:20});players.append(p)
        d={**self.data,'players':players}
        def scored(p,s,*args):
            j=slots.index(s);i=int(p['id'])
            if j in [6,7]: score={(6,6):100,(6,7):99,(7,6):98,(7,7):1}.get((i,j),0)
            else: score=100 if i==j else 0
            return dict(score=score,defense=100)
        # Give identical-position slots unique IDs so list.index is unambiguous.
        with patch('engine.evaluate',side_effect=scored):r=optimize(d,{**self.config,'slots':slots})
        picks={c['slot_index']:c['player']['id'] for c in r['xi']}
        self.assertEqual(picks[6],'07');self.assertEqual(picks[7],'06')
    def test_all_formation_presets_have_feasible_complete_solutions(self):
        from catalog import FORMATIONS
        for f in FORMATIONS:
            r=optimize(self.data,{**self.config,'slots':slots_for(f)})
            self.assertEqual(len(r['xi']),11)
    def test_infeasible_defense_does_not_relax_silently(self):
        with self.assertRaises(ValueError):optimize(self.data,{**self.config,'min_defense':100})
if __name__=='__main__': unittest.main()
