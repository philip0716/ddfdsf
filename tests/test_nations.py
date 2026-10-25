import unittest
from nations import resolve_nation_names
from engine import validate
from demo import demo

class NationTests(unittest.TestCase):
    def test_fm26_names_and_separate_entries(self):
        names=resolve_nation_names({})
        self.assertEqual(names['755'],'Österreich')
        self.assertEqual(names['771'],'Deutschland')
        self.assertEqual(names['2000169627'],'Deutschland')
        self.assertEqual(names['798'],'Schweiz')
        self.assertNotIn('987654321',names)

    def test_override_keeps_ids_and_demo(self):
        data=demo();data['nation_names']={'771':'Eigener Ländername','1':'Österreich (Demo)'}
        before=[p['nation_ids'][:] for p in data['players']]
        result=validate(data)
        self.assertEqual(result['nation_names']['771'],'Eigener Ländername')
        self.assertEqual(result['nation_names']['1'],'Österreich (Demo)')
        self.assertEqual(before,[p['nation_ids'] for p in result['players']])

    def test_invalid_names_rejected(self):
        for value in [[],None,{'755':23},{'755':''}]:
            with self.assertRaises(ValueError):resolve_nation_names(value)

    def test_all_internal_entries_and_collisions(self):
        names=resolve_nation_names({},'save')
        self.assertEqual(set(names),{str(i) for i in range(251)})
        for key,name in [('0','Algerien'),('5','Burundi'),('129','Österreich'),('145','Deutschland'),('200','Baskenland'),('238','Monaco')]:
            self.assertEqual(names[key],name)

    def test_legacy_export_migration(self):
        from nations import NATION_NAMES
        data=demo();data['source']='FM26 · fmsave 0.5.11';data['nation_names']=dict(NATION_NAMES)
        result=validate(data)
        self.assertEqual(result['nation_id_space'],'save')
        self.assertEqual(result['nation_names']['5'],'Burundi')
        self.assertEqual(result['nation_names']['145'],'Deutschland')

    def test_save_override_is_preserved(self):
        data=demo();data.update(source='fmsave',nation_id_space='save',nation_names={'129':'Mein Österreich'})
        self.assertEqual(validate(data)['nation_names']['129'],'Mein Österreich')
