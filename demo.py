"""Deterministic synthetic squad, with distinct senior and prospect lineups."""
import random
from copy import deepcopy
from datetime import date,timedelta
from catalog import POSITIONS, ROLES

def demo():
    rng=random.Random(26); players=[]; today=date(2026,10,24)
    names=['Lukas Berger','David Leitner','Florian Gruber','Tobias Hofer','Maximilian Wolf','Julian Maier',
           'Felix Steiner','Paul Wagner','Simon Huber','Leon Fischer','Matthias Winter','Noah Schmid',
           'Fabian Weber','Alexander Fuchs','Jonas Bauer']
    attributes=sorted({a for r in ROLES.values() for a in r['weights']}|{'determination','injury_proneness'})
    for i,pos in enumerate(POSITIONS):
        for talent in [False,True]:
            index=i*2+int(talent)
            ca=105 if talent else 155; pa=185 if talent else 160
            p=dict(id=str(index+1),name=names[i]+(' Junior' if talent else ''),age=18 if talent else 30,
                   squad='senior',team_id='demo-senior',ca=ca,pa=pa,club='FC Demo Wien',club_id='demo',nation_ids=[1 if i%3 else 2],
                   positions={pos:20},attributes={a:rng.randint(9,12) if talent else rng.randint(13,17) for a in attributes},
                   professionalism=18 if talent else 14,training_environment=80,development_trend=70,
                   fitness=97,sharpness=90,status='available',matches=[],season={})
            if pos=='dc': p['positions']['dm']=15
            if pos in ['ml','mr']: p['positions']['aml' if pos=='ml' else 'amr']=16
            if pos=='dm': p['positions'].update(mc=16,dc=15)
            if pos=='mc': p['positions']['dm']=15
            for k in range(14 if not talent else 4):
                p['matches'].append(dict(date=(today-timedelta(days=4+k*5)).isoformat(),minutes=85 if not talent else 60,
                                         rating=round(rng.uniform(7.3,8.3) if not talent else rng.uniform(6.3,7.2),1)))
            p['season']=dict(minutes=1400 if not talent else 240,average_rating=7.6 if not talent else 6.7,
                expected_goals_per_90=.5,expected_assists_per_90=.2,shots_on_target_per_90=1.4,
                tackles_completed_per_90=2,interceptions_per_90=1.4,headers_won_per_90=3,
                progressive_passes_per_90=6,key_passes_per_90=1.7,save_percent=76,expected_goals_prevented_per_90=.1)
            players.append(p)
    for squad,age,ca,pa in [('second',22,100,160),('u19',17,85,185)]:
        for original in list(players[:28]):
            p=deepcopy(original)
            p.update(id=squad+'-'+p['id'],name=p['name']+' ('+('II' if squad=='second' else 'U19')+')',
                     squad=squad,team_id='demo-'+squad,age=age,ca=ca,pa=pa)
            p['attributes']={k:max(1,v-3) for k,v in p['attributes'].items()}
            p['season'].update(average_rating=6.6,minutes=400)
            for m in p['matches']: m['rating']=6.5
            players.append(p)
    return dict(players=players,date=today.isoformat(),source='DEMO · frei erfundene Spieler',
                managed_clubs=['demo'],nation_names={'1':'Österreich (Demo)','2':'Deutschland (Demo)'},
                notices=['Demodaten: keine echten Spieler und kein echter Spielstand.'])
