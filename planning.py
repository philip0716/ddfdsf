"""Club and national-team planning tools, using the same explainable XI model."""
from copy import deepcopy
from datetime import date,timedelta
from math import ceil
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint,linear_sum_assignment
from scipy.sparse import lil_matrix
from catalog import ROLES,FORMATIONS,slots_for,position_rating,base_position
from engine import validate,validate_slots,evaluate,optimize,config_weights,adjust_score,number,clip
from selection import pool


def integer(v,lo,hi,label):
    if type(v) is not int or not lo<=v<=hi:raise ValueError(f'{label}: ganze Zahl zwischen {lo} und {hi} erforderlich.')
    return v

def context(data,config):
    validate(data);validate_slots(config['slots'])
    if config.get('objective','form') not in ['form','potential']:raise ValueError('Unbekanntes Ziel.')
    if not number(config.get('horizon',5),1,10):raise ValueError('Ungültiger Entwicklungshorizont.')
    return date.fromisoformat(data['date']),config_weights(config,config.get('objective','form'))

def scored(p,s,config,today,weights,index):
    minimum=config.get('min_position',12)
    if not number(minimum,1,20):raise ValueError('Ungültige Positionsgrenze.')
    if min(position_rating(p,s['ip_position']),position_rating(p,s['oop_position']))<minimum:return None
    r=evaluate(p,s,config.get('objective','form'),today,config.get('horizon',5),weights)
    if r is None:return None
    r=adjust_score(r,p,config)
    return dict(player=p,slot=r['resolved_slot'],slot_index=index,**r)

def all_cards(data,config,external=False,indices=None):
    today,weights=context(data,config);players,excluded=pool(data,config,external)
    if len(players)>25000:raise ValueError('Mehr als 25.000 Kandidaten: bitte den Filter eingrenzen.')
    indices=range(11) if indices is None else indices
    cards=[]
    for p in players:
        for j in indices:
            c=scored(p,config['slots'][j],config,today,weights,j)
            if c:cards.append(c)
    return players,cards,excluded

def roster(data,config):
    size=integer(config.get('roster_size',26),11,80,'Kadergröße')
    keepers=integer(config.get('goalkeepers',5 if size>=50 else 3 if size>=23 else 1),1,min(8,size-10),'Torhüter')
    players,cards,excluded=all_cards(data,{**config,'selected_ids':None})
    if len(players)<size:raise ValueError(f'Nur {len(players)} verfügbare Kandidaten für {size} Plätze. Filter/Spielberechtigung prüfen.')
    if not cards:raise ValueError('Keine passenden Kandidaten für die Taktik.')
    player_index={p['id']:i for i,p in enumerate(players)}
    # Every selected player is assigned to exactly one tactical depth slot.
    # Ten field slots each receive depth or depth+1 players, GK exactly requested.
    depth=max(1,(size-keepers)//10);upper=ceil((size-keepers)/10)
    if size-keepers<10:raise ValueError('Zu wenige Feldspieler für die Formation.')
    rules=config.get('registration_rules',{}) if config.get('mode','club')=='club' else {}
    limits=[]
    for key,label in [('min_homegrown_club','homegrown_club'),('min_homegrown_nation','homegrown_nation')]:
        v=rules.get(key,0);integer(v,0,size,key)
        if v:limits.append((label,v,np.inf))
    foreign=rules.get('max_foreign')
    if foreign is not None:integer(foreign,0,size,'Maximale Ausländer');limits.append(('foreign',-np.inf,foreign))
    rows=1+len(players)+11+len(limits);a=lil_matrix((rows,len(cards)))
    low=np.full(rows,-np.inf);high=np.full(rows,np.inf);low[0]=high[0]=size
    high[1:1+len(players)]=1
    start=1+len(players)
    for j,s in enumerate(config['slots']):
        low[start+j]=high[start+j]=keepers if s['ip_position']=='gk' else depth
        if s['ip_position']!='gk':high[start+j]=upper
    for j,(_,lo,hi) in enumerate(limits):low[start+11+j]=lo;high[start+11+j]=hi
    for k,c in enumerate(cards):
        a[0,k]=1;a[1+player_index[c['player']['id']],k]=1;a[start+c['slot_index'],k]=1
        reg=c['player'].get('registration',{})
        for j,(field,_,_) in enumerate(limits):
            # Unknown foreign status counts against a configured maximum.
            a[start+11+j,k]=int(reg.get(field) is not False) if field=='foreign' else int(reg.get(field) is True)
    sol=milp(-np.array([c['score'] for c in cards]),integrality=np.ones(len(cards)),bounds=Bounds(0,1),
             constraints=LinearConstraint(a.tocsr(),low,high),options={'time_limit':25,'mip_rel_gap':0})
    if sol.status!=0:raise ValueError('Kadergröße, Positionsabdeckung und Registrierungsregeln sind zusammen nicht erfüllbar. Keine Regeln wurden gelockert.')
    chosen=sorted([cards[i] for i,x in enumerate(sol.x) if x>.5],key=lambda c:(c['slot_index'],-c['score']))
    ids={c['player']['id'] for c in chosen}
    warnings=[]
    unknown=sum(c['player'].get('eligibility_status')=='unknown' for c in chosen)
    if unknown:warnings.append(f'{unknown} nominierte Spieler mit ungeprüfter Spielberechtigung. Dies ist ein Entwurf, keine bestätigte Spielberechtigung.')
    return dict(size=size,goalkeepers=keepers,depth=depth,players=chosen,selected_ids=sorted(ids),
                total_score=round(sum(c['score'] for c in chosen),2),warnings=warnings,excluded=excluded,
                explanation='Globales Optimum mit einmaliger Spielerzuordnung, Torwartvorgabe und Mindestabdeckung jedes taktischen Feldplatzes.')

def depth_chart(data,config):
    _,cards,excluded=all_cards(data,config);rows=[]
    for j,s in enumerate(config['slots']):
        candidates=sorted([c for c in cards if c['slot_index']==j],key=lambda c:-c['score'])
        rows.append(dict(slot_index=j,slot=s,count=len(candidates),first_choices=candidates[:3],
                         status='Lücke' if not candidates else 'Nur einfach besetzt' if len(candidates)==1 else 'Abgedeckt',
                         surplus=max(0,len(candidates)-3)))
    warnings=['Mehrfachpositionen können in mehreren Zeilen erscheinen; die Kadernominierung prüft die gemeinsame Besetzbarkeit.']
    return dict(rows=rows,excluded=excluded,warnings=warnings)

def scouting(data,config):
    mode=config.get('mode','club');external=mode=='club'
    _,cards,_=all_cards(data,{**config,'selected_ids':None},external=external)
    omitted={str(x) for x in config.get('nominated_ids',[])}
    budget=config.get('budget');max_age=config.get('max_age')
    if budget is not None and not number(budget,0,1e12):raise ValueError('Ungültiges Budget.')
    if max_age is not None and not number(max_age,14,65):raise ValueError('Ungültige Altersgrenze.')
    result=[]
    for j in range(11):
        known=[];unknown=[]
        for c in cards:
            if c['slot_index']!=j or c['player']['id'] in omitted:continue
            p=c['player']
            if max_age is not None and (p.get('age') is None or p['age']>max_age):continue
            cost=p.get('scout_cost')
            if cost is not None and not number(cost,0,1e12):raise ValueError('Ungültige bestätigte Ablöse.')
            if external and budget is not None:
                if cost is None:unknown.append(c);continue
                if cost>budget:continue
            known.append(c)
        result.append(dict(slot_index=j,slot=config['slots'][j],candidates=sorted(known,key=lambda c:-c['score'])[:3],
                           unknown_cost=sorted(unknown,key=lambda c:-c['score'])[:3]))
    return dict(rows=result,warnings=['Ablösen nur bei bestätigtem scout_cost in derselben Einheit wie das Budget vergleichbar. Unbekannte Kosten gelten nicht als bezahlbar.'] if external else ['Spielberechtigung bleibt eine eigene Prüfung; Nationalität allein reicht nicht.'])

def compare(data,config,ids,slot_index):
    context(data,config);integer(slot_index,0,10,'Platz')
    if not isinstance(ids,list) or not 2<=len(set(ids))<=5:raise ValueError('Zwei bis fünf unterschiedliche Spieler auswählen.')
    available={p['id']:p for p in data['players']};rows=[]
    for pid in dict.fromkeys(ids):
        if pid not in available:raise ValueError('Unbekannter Spieler.')
        from selection import checked_player
        p=checked_player(available[pid],config);evaluations={}
        for objective in ['form','potential']:
            c={**config,'objective':objective};evaluations[objective]=scored(p,c['slots'][slot_index],c,date.fromisoformat(data['date']),config_weights(c,objective),slot_index)
        rows.append(dict(player=p,evaluations=evaluations))
    return dict(rows=rows,slot_index=slot_index,warnings=['Vergleich bewertet die Passung. Er bestätigt weder Verfügbarkeit noch Registrierung oder Spielberechtigung.'])

def explain(data,config,player_id,slot_index):
    integer(slot_index,0,10,'Platz');baseline=optimize(data,config)
    forced={**config,'locks':{**config.get('locks',{}),str(slot_index):str(player_id)}}
    alternative=optimize(data,forced)
    incumbent=baseline['xi'][slot_index];challenger=alternative['xi'][slot_index]
    changes=[dict(slot_index=a['slot_index'],before=a['player']['name'],after=b['player']['name']) for a,b in zip(baseline['xi'],alternative['xi']) if a['player']['id']!=b['player']['id']]
    return dict(incumbent=incumbent,challenger=challenger,total_delta=round(alternative['total_score']-baseline['total_score'],2),
                changes=changes,explanation='Gesamtscore mit erzwungener Besetzung minus freies Optimum. Andere Plätze werden dabei gemeinsam neu besetzt.')

def recommend_formations(data,config):
    rows=[]
    for name in FORMATIONS:
        try:
            r=optimize(data,{**config,'slots':slots_for(name),'locks':{}})
            rows.append(dict(formation=name,score=round(r['total_score']/11,2),defense=r['defense_average'],xi=r['xi']))
        except ValueError as exc:rows.append(dict(formation=name,error=str(exc)))
    rows.sort(key=lambda r:r.get('score',-1),reverse=True)
    return dict(rows=rows,explanation='Vergleich der angebotenen Grundformationen mit automatischen Rollen, nicht aller denkbaren Fußballformationen.')

def opponent(data,config):
    r=optimize(data,config);club=str(config.get('opponent_club') or '')
    opposition=[p for p in data['players'] if str(p.get('club_id',''))==club] if club else []
    strengths={}
    for label,attrs in {'Luftduelle':['heading','jumping_reach','strength'],'Tempo':['pace','acceleration'],'Ballkontrolle':['first_touch','passing','composure']}.items():
        values=[sum(p['attributes'][a] for a in attrs if a in p['attributes'])/len([a for a in attrs if a in p['attributes']]) for p in opposition if any(a in p['attributes'] for a in attrs)]
        strengths[label]=round(sum(values)/len(values),2) if values else None
    return dict(result=r,opponent_players=len(opposition),strengths=strengths,
                explanation='Gegnerprofil wird ausdrücklich gewählt; Kaderattribute beweisen kein beobachtetes Pressing- oder Spielsystem. Modellbonus maximal ±5 Punkte.')

def rotation(data,config,games):
    if not isinstance(games,list) or not 1<=len(games)<=8:raise ValueError('Ein bis acht Spiele planen.')
    work=deepcopy(data);previous=date.fromisoformat(data['date']);usage={};rows=[]
    for game in games:
        try:when=date.fromisoformat(game['date'])
        except (KeyError,TypeError,ValueError):raise ValueError('Ungültiges Spieldatum.')
        if when<previous:raise ValueError('Spiele müssen chronologisch ab dem Spielstanddatum liegen.')
        duration=integer(game.get('minutes',90),30,120,'Spieldauer')
        recovery=(when-previous).days*8
        for p in work['players']:
            if p.get('fitness') is not None:p['fitness']=min(100,p['fitness']+recovery)
        work['date']=when.isoformat()
        penalties={pid:min(30,sum(minutes for day,minutes in entries if (when-day).days<7)/90*6) for pid,entries in usage.items()}
        c={**config,'selection_penalties':penalties,'opponent_profile':game.get('opponent_profile','balanced')}
        try:r=optimize(work,c)
        except ValueError as exc:
            rows.append(dict(date=when.isoformat(),error=str(exc)));break
        rows.append(dict(date=when.isoformat(),opponent=game.get('opponent',''),minutes=duration,result=r))
        active={x['player']['id'] for x in r['xi']}
        for p in work['players']:
            if p['id'] in active:
                usage.setdefault(p['id'],[]).append((when,duration))
                if p.get('fitness') is not None:p['fitness']=max(0,p['fitness']-16*duration/90)
        previous=when
    return dict(games=rows,warnings=['Belastungsmodell: 8 Fitnesspunkte Erholung pro Tag, 16 Punkte Verbrauch pro 90 Minuten; kein offizieller FM-Verlauf. Alle Starter werden für die angegebene Dauer geplant, Wechsel noch nicht eingerechnet. Unbekannte Fitness bleibt unbekannt.'])

def scenario(data,config,event,injury_id=None):
    if event not in ['injury','leading','trailing']:raise ValueError('Unbekanntes Szenario.')
    base=optimize(data,config)
    if event=='injury':
        if injury_id not in {c['player']['id'] for c in base['xi']}:raise ValueError('Für den Ausfall einen Startelfspieler auswählen.')
        r=optimize(data,{**config,'overrides':{**config.get('overrides',{}),injury_id:'injured'},'locks':{k:v for k,v in config.get('locks',{}).items() if v!=injury_id}})
        changes=[dict(slot_index=a['slot_index'],before=a['player']['name'],after=b['player']['name']) for a,b in zip(base['xi'],r['xi']) if a['player']['id']!=b['player']['id']]
        return dict(event=event,result=r,changes=changes,explanation='Komplette Neuoptimierung ohne den ausgefallenen Spieler.')
    attrs=['positioning','tackling','concentration','work_rate'] if event=='leading' else ['vision','finishing','off_the_ball','passing']
    today,weights=context(data,config);starters=list(base['xi']);bank=list(base['bench']);steps=[]
    for minute in [60,70,80]:
        options=[]
        for incoming in bank:
            p=incoming['player']
            for outgoing in starters:
                j=outgoing['slot_index']
                if config['slots'][j]['ip_position']=='gk':continue
                c=scored(p,config['slots'][j],config,today,weights,j)
                if c:
                    values=[p['attributes'][a] for a in attrs if a in p['attributes']]
                    bonus=(sum(values)/len(values)-10.5)*2 if values else 0
                    options.append((c['score']-outgoing['score']+bonus,c,outgoing))
        if not options:break
        gain,incoming,outgoing=max(options,key=lambda o:o[0])
        steps.append(dict(minute=minute,outgoing=outgoing['player']['name'],incoming=incoming,model_impact=round(gain,2)))
        starters=[c for c in starters if c['player']['id']!=outgoing['player']['id']]
        bank=[c for c in bank if c['player']['id']!=incoming['player']['id']]
    return dict(event=event,steps=steps,explanation='Vorschläge für Führung/Rückstand anhand passender Bankspieler. Modellwirkung, keine Vorhersage des Spielergebnisses; abgewählte Rollen und Positionsgrenzen bleiben erhalten.')

def identity(p):
    if p.get('unique_id') is not None and p.get('birth_date'):
        return 'db:'+str(p['unique_id'])+':'+p['birth_date']
    return 'local:'+p['id']+':'+p['name']+':'+str(p.get('birth_date') or '')

def save_comparison(current,previous):
    if not isinstance(previous,dict) or not isinstance(previous.get('players'),list):raise ValueError('Vorherigen Kaderexport oder Snapshot laden.')
    if len(previous['players'])>100000:raise ValueError('Snapshot zu groß.')
    old={};now={}
    for target,rows in [(old,previous['players']),(now,current['players'])]:
        for p in rows:
            if not isinstance(p,dict) or not isinstance(p.get('id'),str) or not isinstance(p.get('name'),str):raise ValueError('Ungültiger Snapshot-Spieler.')
            key=identity(p)
            if key in target:raise ValueError('Mehrdeutige Spieleridentität im Snapshot.')
            target[key]=p
    changes=[]
    for key in sorted(set(old)&set(now)):
        a,b=old[key],now[key];delta={}
        for field in ['ca','pa','fitness']:
            x,y=a.get(field),b.get(field)
            delta[field]=round(y-x,2) if number(x,0,10000) and number(y,0,10000) else None
        x=a.get('season',{}).get('average_rating');y=b.get('season',{}).get('average_rating')
        delta['rating']=round(y-x,2) if number(x,1,10) and number(y,1,10) else None
        if any(v not in [None,0] for v in delta.values()) or a.get('club_id')!=b.get('club_id'):
            changes.append(dict(id=b['id'],name=b['name'],delta=delta,before_club=a.get('club'),after_club=b.get('club')))
    changes.sort(key=lambda c:-abs(c['delta'].get('ca') or 0))
    return dict(previous_date=previous.get('date'),current_date=current.get('date'),matched=len(set(old)&set(now)),
                added=[dict(id=now[k]['id'],name=now[k]['name']) for k in set(now)-set(old)],
                removed=[dict(id=old[k]['id'],name=old[k]['name']) for k in set(old)-set(now)],changes=changes,
                warnings=['Identität über Datenbank-ID und Geburtsdatum, sonst lokale ID und Name. Vergleiche ohne Datenbankidentität nur innerhalb derselben Karriere zuverlässig. Fehlende Werte erzeugen keinen vermeintlichen Nullwert.'])

ACTIONS={'roster':roster,'depth':depth_chart,'scouting':scouting,'formations':recommend_formations,'opponent':opponent}
def run_action(data,payload):
    if not isinstance(payload,dict):raise ValueError('Ungültige Anfrage.')
    action=payload.get('action');config=payload.get('config',{})
    if action=='restore_nomination':return restore_nomination(data,config)
    if action=='pair_formations':return pair_formations(config,payload.get('formation'))
    if action in ACTIONS:return ACTIONS[action](data,config)
    if action=='compare':return compare(data,config,payload.get('ids',[]),payload.get('slot_index',0))
    if action=='explain':return explain(data,config,payload.get('player_id'),payload.get('slot_index',0))
    if action=='rotation':return rotation(data,config,payload.get('games',[]))
    if action=='scenario':return scenario(data,config,payload.get('event'),payload.get('injury_id'))
    if action=='save_compare':
        ids=payload.get('current_ids')
        current=data if ids is None else {**data,'players':[p for p in data['players'] if p['id'] in set(ids)]}
        previous=payload.get('previous');result=save_comparison(current,previous)
        before=previous.get('nominated_ids');after=config.get('nominated_ids')
        if isinstance(before,list) and isinstance(after,list):
            names={p['id']:p['name'] for p in data['players']};oldnames={p['id']:p['name'] for p in previous['players']}
            result['nomination_added']=[names.get(pid,pid) for pid in set(after)-set(before)]
            result['nomination_removed']=[oldnames.get(pid,pid) for pid in set(before)-set(after)]
        return result
    raise ValueError('Unbekannte Planungsfunktion.')


def pair_formations(config,formation):
    if formation not in FORMATIONS:raise ValueError('Unbekannte OOP-Formation.')
    original=config['slots'];validate_slots(original);target=slots_for(formation)
    def point(pos):
        x=0 if pos in ['dl','dcl','wbl','ml','aml'] else 2 if pos in ['dr','dcr','wbr','mr','amr'] else 1
        b=base_position(pos);y=0 if b=='gk' else 1 if b in ['dc','dl','dr'] else 2 if b in ['dm','wbl','wbr'] else 3 if b in ['ml','mc','mr'] else 4 if b in ['aml','amc','amr'] else 5
        return x,y
    costs=np.zeros((11,11))
    for i,a in enumerate(original):
        x,y=point(a['ip_position'])
        for j,b in enumerate(target):
            xx,yy=point(b['oop_position'])
            costs[i,j]=10000 if (a['ip_position']=='gk')!=(b['oop_position']=='gk') else (x-xx)**2*4+(y-yy)**2*2+(0 if a['ip_position']==b['oop_position'] else .1)+abs(i-j)*.0001
    left,right=linear_sum_assignment(costs)
    result=[dict(s) for s in original]
    for i,j in zip(left,right):result[i].update(oop_position=target[j]['oop_position'],oop_role=target[j]['oop_role'],oop_auto=True)
    return dict(slots=result,explanation='Zuordnung minimiert den schematischen Positionswechsel. Die anschließende Spielerauswahl prüft tatsächliche Positionsvertrautheit; nicht jede Kombination muss mit jedem Kader besetzbar sein.')

def restore_nomination(data,config):
    ids=config.get('selected_ids')
    if not isinstance(ids,list) or len(ids)!=len(set(ids)) or not 11<=len(ids)<=80:raise ValueError('Keine gültige gespeicherte Nominierung vorhanden.')
    _,cards,excluded=all_cards(data,config)
    assignments=config.get('nominated_assignments',{})
    if not isinstance(assignments,dict):raise ValueError('Ungültige gespeicherte Kaderplätze.')
    chosen=[];missing=[]
    for pid in ids:
        options=[c for c in cards if c['player']['id']==pid]
        preferred=[c for c in options if c['slot_index']==assignments.get(pid)]
        if preferred:chosen.append(preferred[0])
        elif options:chosen.append(max(options,key=lambda c:c['score']))
        else:missing.append(pid)
    valid=not missing
    warnings=['Gespeicherte Spielerauswahl wiederhergestellt; Rollen und Verfügbarkeit wurden mit den aktuellen Einstellungen erneut bewertet.']
    if missing:warnings.append(f'{len(missing)} gespeicherte Spieler erfüllen die aktuellen Auswahlbedingungen nicht. Bitte neu nominieren.')
    return dict(size=len(ids),goalkeepers=sum(c['slot']['ip_position']=='gk' for c in chosen),depth=max(1,(len(ids)-config.get('goalkeepers',3))//10),
                players=sorted(chosen,key=lambda c:(c['slot_index'],-c['score'])),selected_ids=ids,total_score=round(sum(c['score'] for c in chosen),2),
                warnings=warnings,excluded=excluded,valid=valid,explanation='Identitäten der gespeicherten Auswahl wurden beibehalten, keine automatische Ersetzung durch andere Spieler.')
