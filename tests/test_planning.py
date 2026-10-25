import copy
from datetime import date
import unittest
from catalog import ROLES,slots_for,base_position
from demo import demo
from engine import optimize
from planning import (roster,depth_chart,scouting,compare,explain,rotation,scenario,
                      recommend_formations,opponent,save_comparison,run_action)
from selection import pool

class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.d=demo();self.c=dict(slots=slots_for('4-3-3 DM'),mode='club',club='demo',objective='form')
    def test_national_strength_rosters_and_xi(self):
        from engine import evaluate,config_weights
        for size,gk in [(26,3),(55,5)]:
            c={**self.c,'mode':'national','nation':'1','objective':'strength','roster_size':size,'goalkeepers':gk}
            r=roster(self.d,c)
            self.assertEqual(len(r['players']),size)
            self.assertEqual(len(set(r['selected_ids'])),size)
            self.assertEqual(sum(x['slot']['ip_position']=='gk' for x in r['players']),gk)
            self.assertTrue(all('ability' in x['parts'] and 'form' not in x['parts'] for x in r['players']))
        result=optimize(self.d,c)
        self.assertEqual(result['objective'],'strength')
        p=copy.deepcopy(self.d['players'][0]);p['ca']=None
        self.assertIsNone(evaluate(p,c['slots'][0],'strength',date.fromisoformat(self.d['date'])))

    def test_strength_ignores_form_and_pa(self):
        from engine import evaluate
        p=copy.deepcopy(self.d['players'][0]);s=self.c['slots'][0];today=date.fromisoformat(self.d['date'])
        before=evaluate(p,s,'strength',today)
        p['matches']=[];p['season']={};p['pa']=200
        self.assertEqual(before['score'],evaluate(p,s,'strength',today)['score'])
        p['ca']-=20
        self.assertAlmostEqual(before['score']-evaluate(p,s,'strength',today)['score'],6)

    def test_club_roster_is_exact_unique_and_position_balanced(self):
        r=roster(self.d,{**self.c,'roster_size':26,'goalkeepers':3})
        self.assertEqual(len(r['players']),26);self.assertEqual(len(set(r['selected_ids'])),26)
        self.assertEqual(sum(c['slot']['ip_position']=='gk' for c in r['players']),3)
        for j in range(1,11):self.assertGreaterEqual(sum(c['slot_index']==j for c in r['players']),2)
        self.assertTrue(all(c['player']['club_id']=='demo' for c in r['players']))
    def test_national_55_uses_all_clubs_and_ignores_club_squad_filters(self):
        c={**self.c,'mode':'national','nation':'1','squad':'u19','roster_size':55,'goalkeepers':5,'eligibility_strict':True}
        r=roster(self.d,c)
        self.assertEqual(len(r['players']),55)
        self.assertTrue(all(c['player']['eligibility_status']=='eligible' for c in r['players']))
        self.assertGreater(len({c['player']['club_id'] for c in r['players']}),1)
        self.assertGreater(len({c['player']['squad'] for c in r['players']}),1)
    def test_unknown_eligibility_is_disclosed_and_strictly_excluded(self):
        for p in self.d['players']:p['eligibility']={}
        c={**self.c,'mode':'national','nation':'1'}
        r=roster(self.d,c);self.assertTrue(r['warnings'])
        with self.assertRaises(ValueError):roster(self.d,{**c,'eligibility_strict':True})
    def test_ineligible_player_is_excluded_even_in_non_strict_mode(self):
        c={**self.c,'mode':'national','nation':'1','player_checks':{'1':{'eligibility':{'1':'ineligible'}}}}
        players,excluded=pool(self.d,c)
        self.assertNotIn('1',[p['id'] for p in players]);self.assertIn('1',[p['id'] for p in excluded])
    def test_manual_eligibility_can_add_a_second_nation_without_guessing(self):
        p=self.d['players'][0]
        c={**self.c,'mode':'national','nation':'999','player_checks':{p['id']:{'eligibility':{'999':'eligible'}}}}
        players,_=pool(self.d,c);self.assertEqual([p['id'] for p in players],[p['id']])
    def test_registration_constraints_are_enforced(self):
        c={**self.c,'registration_rules':{'max_foreign':10,'min_homegrown_club':3,'min_homegrown_nation':4}}
        r=roster(self.d,c);regs=[c['player']['registration'] for c in r['players']]
        self.assertLessEqual(sum(r.get('foreign') is not False for r in regs),10)
        self.assertGreaterEqual(sum(r.get('homegrown_club') is True for r in regs),3)
    def test_unknown_foreign_status_cannot_pass_zero_limit(self):
        for p in self.d['players']:p['registration']={}
        with self.assertRaises(ValueError):roster(self.d,{**self.c,'registration_rules':{'max_foreign':0}})
    def test_registration_strict_excludes_unknown(self):
        for p in self.d['players']:p['registration']={}
        with self.assertRaises(ValueError):optimize(self.d,{**self.c,'registration_strict':True})
    def test_insufficient_55_candidates_does_not_return_26(self):
        with self.assertRaises(ValueError):roster(self.d,{**self.c,'squad':'senior','roster_size':55,'goalkeepers':5})
    def test_depth_identifies_missing_keeper(self):
        self.d['players']=[p for p in self.d['players'] if not p['positions'].get('gk')]
        r=depth_chart(self.d,self.c);self.assertEqual(r['rows'][0]['status'],'Lücke')
    def test_external_candidates_are_from_other_clubs(self):
        r=scouting(self.d,self.c)
        candidates=[c for row in r['rows'] for c in row['candidates']]
        self.assertTrue(candidates);self.assertTrue(all(c['player']['club_id']!='demo' for c in candidates))
    def test_unknown_cost_is_not_claimed_affordable(self):
        for p in self.d['players']:p['scout_cost']=None
        r=scouting(self.d,{**self.c,'budget':100})
        self.assertTrue(any(row['unknown_cost'] for row in r['rows']))
        self.assertTrue(all(not row['candidates'] for row in r['rows']))
    def test_confirmed_cost_override_is_used(self):
        c={**self.c,'budget':100,'player_checks':{'external-1':{'scout_cost':50}}}
        r=scouting(self.d,c)
        self.assertIn('external-1',[c['player']['id'] for row in r['rows'] for c in row['candidates']])
    def test_national_scout_excludes_nominated_players(self):
        c={**self.c,'mode':'national','nation':'1','nominated_ids':['1','2']}
        r=scouting(self.d,c)
        self.assertNotIn('1',[c['player']['id'] for row in r['rows'] for c in row['candidates']])
    def test_compare_both_objectives_and_unknown_pa(self):
        self.d['players'][0]['pa']=None
        r=compare(self.d,self.c,['1','2'],0)
        self.assertIsNone(r['rows'][0]['evaluations']['potential'])
        self.assertIsNotNone(r['rows'][0]['evaluations']['form'])
    def test_compare_requires_two_to_five_distinct_players(self):
        with self.assertRaises(ValueError):compare(self.d,self.c,['1'],0)
    def test_counterfactual_locks_and_explains_total_delta(self):
        base=optimize(self.d,self.c);candidate=base['alternatives'][0][0]['player']['id']
        r=explain(self.d,self.c,candidate,0)
        self.assertEqual(r['challenger']['player']['id'],candidate)
        self.assertLessEqual(r['total_delta'],.02)
        self.assertTrue(r['changes'])
    def test_manual_player_lock_is_preserved(self):
        r=optimize(self.d,{**self.c,'locks':{'0':'2'}})
        self.assertEqual(r['xi'][0]['player']['id'],'2')
    def test_two_locked_positions_cannot_use_same_player(self):
        with self.assertRaises(ValueError):optimize(self.d,{**self.c,'locks':{'2':'5','3':'5'}})
    def test_weight_customization_is_normalized_and_validated(self):
        c={**self.c,'weights':{'form':{'form':100,'ip':0,'oop':0,'position':0,'readiness':0}}}
        r=optimize(self.d,c);self.assertEqual(r['xi'][0]['weights']['form'],1)
        with self.assertRaises(ValueError):optimize(self.d,{**self.c,'weights':{'form':{'form':100}}})
    def test_recommendations_score_each_preset(self):
        r=recommend_formations(self.d,self.c)
        self.assertEqual(len(r['rows']),5);self.assertIn('xi',r['rows'][0])
    def test_opponent_adjustment_is_visible(self):
        r=opponent(self.d,{**self.c,'opponent_profile':'high_press','opponent_club':'external'})
        self.assertEqual(r['opponent_players'],28)
        self.assertTrue(any(c['selection_adjustment'] for c in r['result']['xi']))
        self.assertTrue(all(abs(c['selection_adjustment'])<=5 for c in r['result']['xi']))
    def test_rotation_is_chronological_and_discloses_projection(self):
        r=rotation(self.d,self.c,[{'date':'2026-10-24'},{'date':'2026-10-25','minutes':120}])
        self.assertEqual(len(r['games']),2);self.assertTrue(r['warnings'])
        self.assertEqual(len(r['games'][1]['result']['xi']),11)
        with self.assertRaises(ValueError):rotation(self.d,self.c,[{'date':'2026-10-23'}])
    def test_injury_scenario_removes_player_everywhere(self):
        pid=optimize(self.d,self.c)['xi'][0]['player']['id']
        r=scenario(self.d,self.c,'injury',pid)
        self.assertNotIn(pid,[c['player']['id'] for c in r['result']['xi']+r['result']['bench']])
    def test_substitution_plan_does_not_reuse_players(self):
        for event in ['leading','trailing']:
            r=scenario(self.d,self.c,event)
            self.assertGreater(len(r['steps']),0)
            self.assertEqual(len({s['incoming']['player']['id'] for s in r['steps']}),len(r['steps']))
            self.assertEqual(len({s['outgoing'] for s in r['steps']}),len(r['steps']))
    def test_save_compare_distinguishes_missing_and_zero(self):
        old=copy.deepcopy(self.d);self.d['players'][0]['ca']+=2;old['players'][0]['fitness']=None
        r=save_comparison(self.d,old)
        changed=next(c for c in r['changes'] if c['id']=='1')
        self.assertEqual(changed['delta']['ca'],2);self.assertIsNone(changed['delta']['fitness'])
    def test_save_compare_reused_id_with_other_name_is_not_matched(self):
        old=copy.deepcopy(self.d);self.d['players'][0]['name']='New person'
        r=save_comparison(self.d,old)
        self.assertEqual(r['matched'],len(self.d['players'])-1)
    def test_snapshot_comparison_uses_selected_current_pool(self):
        old={'players':[self.d['players'][0]],'date':self.d['date']}
        r=run_action(self.d,{'action':'save_compare','previous':old,'current_ids':['1'],'config':self.c})
        self.assertEqual(r['added'],[]);self.assertEqual(r['removed'],[])
    def test_selected_nomination_limits_the_starting_xi(self):
        plan=roster(self.d,self.c);r=optimize(self.d,{**self.c,'selected_ids':plan['selected_ids']})
        self.assertTrue(all(c['player']['id'] in plan['selected_ids'] for c in r['xi']+r['bench']))
    def test_79_role_catalogue_and_wide_cb_restriction(self):
        self.assertEqual(len(ROLES),79)
        self.assertNotIn('dc',ROLES['ip:Overlapping Centre-Back']['positions'])
        self.assertIn('dcl',ROLES['ip:Overlapping Centre-Back']['positions'])
    def test_nominating_more_players_ignores_old_active_nomination(self):
        c={**self.c,'mode':'national','nation':'1'}
        first=roster(self.d,c)
        second=roster(self.d,{**c,'selected_ids':first['selected_ids'],'roster_size':55,'goalkeepers':5})
        self.assertEqual(len(second['players']),55)
    def test_oop_pairing_preserves_ip_and_all_target_positions(self):
        from planning import pair_formations
        r=pair_formations(self.c,'4-2-3-1')
        self.assertEqual([s['ip_position'] for s in r['slots']],[s['ip_position'] for s in self.c['slots']])
        self.assertCountEqual([s['oop_position'] for s in r['slots']],[s['oop_position'] for s in slots_for('4-2-3-1')])
        self.assertEqual(r['slots'][0]['oop_position'],'gk')
        self.assertEqual(len(optimize(self.d,{**self.c,'slots':r['slots']})['xi']),11)
    def test_export_snapshot_nomination_changes_are_named(self):
        old={'players':self.d['players'],'date':self.d['date'],'nominated_ids':['1']}
        r=run_action(self.d,dict(action='save_compare',previous=old,config={**self.c,'nominated_ids':['2']}))
        self.assertEqual(r['nomination_added'],[self.d['players'][1]['name']])
        self.assertEqual(r['nomination_removed'],[self.d['players'][0]['name']])
    def test_unknown_registration_is_not_used_to_reject_external_signings(self):
        for p in self.d['players']:p['registration']={}
        r=scouting(self.d,{**self.c,'registration_strict':True})
        self.assertTrue(any(row['candidates'] for row in r['rows']))
    def test_saved_nomination_restores_ids_and_assignments(self):
        from planning import restore_nomination
        r=roster(self.d,self.c)
        restored=restore_nomination(self.d,{**self.c,'selected_ids':r['selected_ids'],'nominated_assignments':{c['player']['id']:c['slot_index'] for c in r['players']}})
        self.assertTrue(restored['valid'])
        self.assertEqual(set(restored['selected_ids']),set(r['selected_ids']))
        self.assertEqual({c['player']['id']:c['slot_index'] for c in restored['players']},{c['player']['id']:c['slot_index'] for c in r['players']})
    def test_invalidated_saved_nomination_does_not_silently_replace_players(self):
        from planning import restore_nomination
        r=roster(self.d,self.c);pid=r['selected_ids'][0]
        restored=restore_nomination(self.d,{**self.c,'selected_ids':r['selected_ids'],'overrides':{pid:'injured'}})
        self.assertFalse(restored['valid']);self.assertEqual(len(restored['players']),25)
        self.assertNotIn(pid,[c['player']['id'] for c in restored['players']])
