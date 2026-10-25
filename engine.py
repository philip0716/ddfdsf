"""Explainable scoring and simultaneous, constrained XI optimisation."""
from datetime import date
from math import exp, log, sqrt, isfinite
from statistics import pstdev
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix
from catalog import ROLES, POSITIONS, position_rating, base_position
from selection import pool as candidate_pool
from squads import SQUADS, squad_for, validate_mappings

FORM_WEIGHTS = dict(form=.45, ip=.20, oop=.15, position=.10, readiness=.10)
POT_WEIGHTS = dict(potential=.27, gap=.21, window=.14, development=.10,
                   future_ip=.13, future_oop=.09, current=.06)

def clip(x, lo=0, hi=100):
    return max(lo, min(hi, float(x)))

def number(v, lo=0, hi=100):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) and lo<=v<=hi

def validate(data):
    if not isinstance(data,dict) or not isinstance(data.get('players'),list):
        raise ValueError('JSON benötigt eine Liste „players“.')
    if not 1<=len(data['players'])<=100000:
        raise ValueError('Zwischen 1 und 100.000 Spieler erforderlich.')
    validate_mappings(data.get('squad_mappings',{}))
    ids=set()
    for p in data['players']:
        if not isinstance(p,dict) or not isinstance(p.get('id'),str) or not p['id']:
            raise ValueError('Jeder Spieler benötigt eine nicht leere String-ID.')
        if p['id'] in ids: raise ValueError('Doppelte Spieler-ID: '+p['id'])
        ids.add(p['id'])
        if p.get('squad') is not None and p['squad'] not in SQUADS: raise ValueError('Ungültiger Kader.')
        if p.get('team_id') is not None and not isinstance(p['team_id'],(str,int)): raise ValueError('Ungültige Team-ID.')
        for field in ['eligibility','registration']:
            if not isinstance(p.get(field,{}),dict):raise ValueError(field+' muss ein Objekt sein.')
        if p.get('scout_cost') is not None and not number(p['scout_cost'],0,1e12):raise ValueError('Ungültige bestätigte Ablöse.')
        if not isinstance(p.get('nation_ids',[]),list): raise ValueError('nation_ids muss eine Liste sein.')
        for field in ['training_environment','development_trend']:
            if p.get(field) is not None and not number(p[field],0,100): raise ValueError('Ungültiger Teilscore: '+field)
        if p.get('professionalism') is not None and not number(p['professionalism'],1,20): raise ValueError('Professionalität muss 1–20 sein.')
        if not isinstance(p.get('name'),str): raise ValueError('Spielername fehlt.')
        if p.get('pa') is not None and p.get('ca') is not None and number(p['pa'],0,200) and number(p['ca'],0,200) and p['pa']<p['ca']: raise ValueError('PA darf nicht unter CA liegen.')
        for field,upper in [('ca',200),('pa',200),('age',65),('fitness',100),('sharpness',100)]:
            if p.get(field) is not None and not number(p[field],0,upper):
                raise ValueError(f'{p["name"]}: ungültiger Wert für {field}.')
        for field in ['positions','attributes']:
            if not isinstance(p.get(field),dict): raise ValueError(field+' muss ein Objekt sein.')
            if any(not number(v,0,20) for v in p[field].values()):
                raise ValueError(field+': Werte müssen zwischen 0 und 20 liegen.')
        if p.get('status','unknown') not in ['unknown','available','injured','suspended','unavailable']:
            raise ValueError('Ungültige Verfügbarkeit.')
        if not isinstance(p.get('matches',[]),list) or not isinstance(p.get('season',{}),dict):
            raise ValueError('matches muss Liste, season muss Objekt sein.')
        for m in p.get('matches',[]):
            if not isinstance(m,dict): raise ValueError('Ungültiger Spieleintrag.')
            try: date.fromisoformat(m['date'])
            except (ValueError,KeyError,TypeError): raise ValueError('Spieldatum muss ISO-Datum sein.')
            if m.get('rating') is not None and not number(m['rating'],1,10): raise ValueError('Ungültige Spielnote.')
            if m.get('minutes') is not None and not number(m['minutes'],0,130): raise ValueError('Ungültige Minuten.')
        for k,v in p.get('season',{}).items():
            if v is not None and not number(v,-1000000,1000000): raise ValueError('Ungültiger Saisonwert: '+k)
    try: date.fromisoformat(data['date'])
    except (ValueError,KeyError,TypeError): raise ValueError('Das Spielstanddatum fehlt oder ist ungültig.')
    from nations import apply_nation_names
    apply_nation_names(data)
    return data

def blend(items, prior=50):
    """Missing data remain unknown; disclosed neutral prior, never implicit zero."""
    known=[(w,v) for w,v in items if v is not None]
    total=sum(w for w,v in items)
    coverage=sum(w for w,v in known)/total if total else 0
    value=sum(w*v for w,v in known)/sum(w for w,v in known) if known else prior
    return value, coverage

def role_score(p, key, gain=0):
    role=ROLES[key]
    items=[(w,clip((min(20,p['attributes'][a]+gain)-1)/19*100))
           if a in p['attributes'] and p['attributes'][a]>=1 else (w,None)
           for a,w in role['weights'].items()]
    return blend(items)

def window(p):
    if p.get('age') is None: return None
    curve=[(15,100),(18,100),(21,85),(24,55),(27,20),(30,3),(35,0)]
    age=p['age']-(3 if p['positions'].get('gk',0)>=15 else 0)
    if age<=curve[0][0]: return 100
    for (a,x),(b,y) in zip(curve,curve[1:]):
        if age<=b: return x+(y-x)*(age-a)/(b-a)
    return 0

def development(p):
    a=p['attributes']; s=p.get('season',{})
    return blend([(3,p.get('professionalism')*5 if number(p.get('professionalism'),1,20) else None),
                  (2,a.get('determination',0)*5 if a.get('determination',0)>=1 else None),
                  (2,clip(s['minutes']/1800*100) if number(s.get('minutes'),0,100000) else None),
                  (1,p.get('training_environment')),
                  (1,105-a['injury_proneness']*5 if a.get('injury_proneness',0)>=1 else None),
                  (1,p.get('development_trend'))])

def form(p, today, position):
    season=p.get('season',{}); rows=[]
    for m in p.get('matches',[]):
        age=(today-date.fromisoformat(m['date'])).days
        if 0<=age<=180 and number(m.get('rating'),1,10) and number(m.get('minutes'),1,130):
            rows.append((age,m))
    rows=sorted(rows,key=lambda x:x[0])[:20]
    weights=[exp(-log(2)*age/30)*min(90,m['minutes'])/90 for age,m in rows]
    evidence=sum(weights)
    baseline=season.get('average_rating')
    if not number(baseline,1,10): baseline=6.7
    if evidence:
        rating=(sum(w*m['rating'] for w,(_,m) in zip(weights,rows))+5*baseline)/(evidence+5)
        source='Einzelspiele + geglättete Saisonbasis'
    else:
        rating=baseline
        source='Saisonersatz' if number(season.get('average_rating'),1,10) else 'Unbekannt · neutrale Modellbasis'
    rating_score=clip((rating-5.5)/3*100)
    # Fixed, documented per-position targets; not cross-position raw-stat rankings.
    metrics = {
      'gk':[('save_percent',85),('expected_goals_prevented_per_90',.5)],
      'def':[('tackles_completed_per_90',4),('interceptions_per_90',3),('headers_won_per_90',6)],
      'mid':[('progressive_passes_per_90',10),('key_passes_per_90',3),('expected_assists_per_90',.4)],
      'att':[('expected_goals_per_90',.8),('expected_assists_per_90',.4),('shots_on_target_per_90',2.5)]}
    family='gk' if position=='gk' else 'def' if position in ['dc','dl','dr','wbl','wbr','dm'] else 'mid' if position in ['mc','ml','mr','amc'] else 'att'
    kpi,cov=blend([(1,clip(season[k]/target*100)) if number(season.get(k),-100,100000) else (1,None) for k,target in metrics[family]])
    season_minutes=season.get('minutes',0) or 0
    kpi=50+(kpi-50)*season_minutes/(season_minutes+450)
    consistency=clip(100-pstdev([m['rating'] for _,m in rows])*35) if len(rows)>=3 else 50
    reliability=clip(evidence/8*100)
    dependable=.5*consistency+.3*clip(season_minutes/900*100)+.2*reliability
    f=.65*rating_score+.20*kpi+.15*dependable
    confidence=.65*min(1,evidence/8)+.2*cov+.15*min(1,len(rows)/10)
    if not rows and number(season.get('average_rating'),1,10): confidence+=.25
    return dict(value=f,source=source,games=len(rows),minutes=sum(m['minutes'] for _,m in rows),
                confidence=clip(confidence*100),rating=rating,kpi=kpi,reliability=reliability)

def resolve_roles(p,slot,gain=0):
    resolved=dict(slot)
    for phase in ['ip','oop']:
        if not slot.get(phase+'_auto',False): continue
        candidates=[key for key,r in ROLES.items() if r['phase']==phase and slot[phase+'_position'] in r['positions']]
        def rank(key):
            value,coverage=role_score(p,key,gain)
            return (value,coverage,key==slot[phase+'_role'])
        resolved[phase+'_role']=max(candidates,key=rank)
    return resolved

def evaluate(p,slot,objective,today,horizon=5,weights_override=None):
    pos=min(position_rating(p,slot['ip_position']),position_rating(p,slot['oop_position']))*5
    ready,rc=blend([(7,p.get('fitness')),(3,p.get('sharpness'))])
    f=form(p,today,base_position(slot['ip_position'])); d,dc=development(p); y=window(p)
    pa=p.get('pa'); ca=p.get('ca')
    projection=None; interval=None; gain=0
    if pa is not None and ca is not None and y is not None:
        increment=max(0,pa-ca)*(y/100)*(.25+.5*d/100)*min(1,horizon/5)
        projection=min(pa,ca+increment) if pa>=ca else ca
        interval=[round(ca+increment*.5,1),round(min(max(pa,ca),ca+increment*1.5),1)]
        gain=min(3,increment/40)
    slot=resolve_roles(p,slot,gain if objective=='potential' else 0)
    ip,ic=role_score(p,slot['ip_role']); oop,oc=role_score(p,slot['oop_role'])
    fi,fic=role_score(p,slot['ip_role'],gain); fo,foc=role_score(p,slot['oop_role'],gain)
    if objective=='potential':
        if pa is None or ca is None or y is None: return None
        parts=dict(potential=pa/2,gap=clip(max(0,pa-ca)/80*100),window=y,development=d,
                   future_ip=fi,future_oop=fo,current=.4*(ca/2)+.4*ready+.2*pos)
        weights=POT_WEIGHTS
    else:
        parts=dict(form=f['value'],ip=ip,oop=oop,position=pos,readiness=ready); weights=FORM_WEIGHTS
    if weights_override is not None: weights=weights_override
    missing=[]
    if p.get('eligibility_status')=='unknown': missing.append('Spielberechtigung für diese Nation ungeprüft')
    if p.get('status','unknown')=='unknown': missing.append('Verfügbarkeit ungeprüft')
    if rc<1: missing.append('Fitness/Spielpraxis teilweise unbekannt')
    if ic<1 or oc<1: missing.append('Rollenattribute unvollständig · neutraler Prior 50 bei vollständigem Fehlen')
    if dc<1: missing.append('Entwicklungsbedingungen unvollständig')
    if not f['games']: missing.append(f['source'])
    return dict(resolved_slot=slot,role_selection={phase:'automatic' if slot.get(phase+'_auto',False) else 'manual' for phase in ['ip','oop']},
                score=round(sum(weights[k]*v for k,v in parts.items()),4),
                parts={k:round(v,2) for k,v in parts.items()},weights=weights,form=f,
                pa=pa,projected_ca=round(projection,1) if projection is not None else None,
                projection_interval=interval,projection_label='Modellszenario, keine FM-Prognose',
                coverage=dict(ip=ic,oop=oc,development=dc,readiness=rc),warnings=missing,
                defense=role_score(p,'oop:Covering Centre-Back')[0])

def validate_slots(slots):
    if not isinstance(slots,list) or len(slots)!=11: raise ValueError('Genau elf taktische Plätze erforderlich.')
    for s in slots:
        for phase in ['ip','oop']:
            if type(s.get(phase+'_auto',False)) is not bool: raise ValueError('Automatische Rollenwahl muss true oder false sein.')
            pos=s.get(phase+'_position'); key=s.get(phase+'_role')
            if pos not in POSITIONS or key not in ROLES or ROLES[key]['phase']!=phase or pos not in ROLES[key]['positions']:
                raise ValueError('Rolle und Position passen nicht zusammen.')
    for phase in ['ip','oop']:
        if sum(s[phase+'_position']=='gk' for s in slots)!=1: raise ValueError('Jede Phase benötigt genau einen Torhüter.')
    oop=[base_position(s['oop_position']) for s in slots]
    if oop.count('dc')<2 or not any(p in ['dm','mc'] for p in oop):
        raise ValueError('Defensive Balance benötigt mindestens zwei Innenverteidiger und einen zentralen Mittelfeldspieler.')

def optimize(data, config):
    validate(data)
    slots=config['slots']; validate_slots(slots)
    objective=config.get('objective','form')
    if objective not in ['form','potential']: raise ValueError('Unbekanntes Optimierungsziel.')
    threshold=config.get('min_position',12); defense=config.get('min_defense',40); horizon=config.get('horizon',5)
    if not number(threshold,1,20) or not number(defense,0,100) or not number(horizon,1,10): raise ValueError('Ungültige Optimierungsparameter.')
    min_fitness=config.get('min_fitness',70)
    if not number(min_fitness,0,100): raise ValueError('Ungültige Fitnessgrenze.')
    bench_size=config.get('bench_size',9)
    if type(bench_size)!=int or not 1<=bench_size<=15: raise ValueError('Bankgröße muss 1–15 sein.')
    today=date.fromisoformat(data['date'])
    players,excluded=candidate_pool(data,config)
    weights=config_weights(config,objective)
    locks=config.get('locks',{})
    if not isinstance(locks,dict):raise ValueError('Spielerfixierungen müssen ein Objekt sein.')
    if any(str(k) not in [str(i) for i in range(11)] for k in locks):raise ValueError('Ungültiger fixierter Platz.')
    if len(players)>5000: raise ValueError('Mehr als 5.000 Kandidaten. Bitte Verein oder Nationalität eingrenzen.')
    if len(players)<11: raise ValueError(f'Nur {len(players)} geeignete Spieler im Filter. Mindestens elf erforderlich.')
    edges=[]; results={}
    for i,p in enumerate(players):
        for j,s in enumerate(slots):
            if min(position_rating(p,s['ip_position']),position_rating(p,s['oop_position']))<threshold: continue
            if str(j) in locks and str(locks[str(j)])!=p['id']:continue
            r=evaluate(p,s,objective,today,horizon,weights)
            if r:r=adjust_score(r,p,config)
            if r: edges.append((i,j)); results[i,j]=r
    if not edges: raise ValueError('Keine Spieler erfüllen die Positionsanforderungen.')
    n=len(edges); a=lil_matrix((11+len(players)+1,n)); low=np.full(a.shape[0],-np.inf); high=np.full(a.shape[0],np.inf)
    low[:11]=1; high[:11]=1; high[11:11+len(players)]=1
    backs=[j for j,s in enumerate(slots) if base_position(s['oop_position']) in ['dc','dl','dr','wbl','wbr','dm']]
    low[-1]=defense*len(backs)
    for k,(i,j) in enumerate(edges):
        a[j,k]=1; a[11+i,k]=1
        if j in backs: a[-1,k]=results[i,j]['defense']
    c=-np.array([results[e]['score'] for e in edges])
    solution=milp(c,integrality=np.ones(n),bounds=Bounds(0,1),
                  constraints=LinearConstraint(a.tocsr(),low,high),options={'time_limit':20,'mip_rel_gap':0})
    if solution.status!=0:
        raise ValueError('Keine nachweislich optimale Elf gefunden. Positionsgrenze, Filter oder defensive Mindestqualität prüfen.')
    chosen=sorted([edges[k] for k,v in enumerate(solution.x) if v>.5],key=lambda e:e[1])
    selected={i for i,j in chosen}
    def card(i,j):
        p=players[i]
        return dict(player=p,slot=results[i,j].get('resolved_slot',slots[j]),slot_index=j,**results[i,j])
    xi=[card(i,j) for i,j in chosen]
    # Bench: first cover GK/defence/midfield/attack; then best remaining scores.
    candidates=[]
    for i,p in enumerate(players):
        choices=[(results[i,j]['score'],j) for j in range(11) if (i,j) in results]
        if i not in selected and choices:
            _,j=max(choices); candidates.append((i,j))
    bank=[]; used=set(); coverage=[]
    groups=[('Tor',{'gk'}),('Abwehr',{'dc','dl','dr','wbl','wbr'}),('Mittelfeld',{'dm','mc','ml','mr','amc'}),('Angriff',{'aml','amr','stc'})]
    for label,positions in groups:
        pool=[e for e in candidates if e[0] not in used and base_position(slots[e[1]]['ip_position']) in positions]
        if pool and len(bank)<bench_size:
            e=max(pool,key=lambda e:results[e]['score']); bank.append(card(*e)); used.add(e[0])
        else: coverage.append('Bank ohne zusätzliche Abdeckung: '+label)
    for e in sorted(candidates,key=lambda e:-results[e]['score']):
        if e[0] not in used and len(bank)<bench_size: bank.append(card(*e)); used.add(e[0])
    alternatives=[]
    for j in range(11):
        pool=sorted([(i,j) for i in range(len(players)) if (i,j) in results and i not in selected],key=lambda e:-results[e]['score'])[:3]
        alternatives.append([card(*e) for e in pool])
    return dict(xi=xi,bench=bank,alternatives=alternatives,excluded=excluded,warnings=coverage,
                objective=objective,total_score=round(sum(r['score'] for r in xi),2),
                defense_average=round(sum(results[e]['defense'] for e in chosen if e[1] in backs)/len(backs),2),
                solver='Globales ganzzahliges Optimum; Ersatzbank nach Abdeckung und Score')


def config_weights(config,objective):
    defaults=POT_WEIGHTS if objective=='potential' else FORM_WEIGHTS
    custom_all=config.get('weights',{})
    if not isinstance(custom_all,dict):raise ValueError('Gewichte müssen ein Objekt sein.')
    custom=custom_all.get(objective)
    if custom is None:return defaults
    if not isinstance(custom,dict) or set(custom)!=set(defaults) or any(not number(v,0,100) for v in custom.values()) or sum(custom.values())<=0:
        raise ValueError('Gewichte müssen vollständig, nicht negativ und zusammen größer als null sein.')
    total=sum(custom.values());return {k:v/total for k,v in custom.items()}

def adjust_score(result,p,config):
    profiles={'high_press':['first_touch','passing','composure','decisions'],
              'aerial':['heading','jumping_reach','strength'],
              'low_block':['vision','passing','technique','off_the_ball'],
              'pace':['anticipation','positioning','pace','acceleration']}
    profile=config.get('opponent_profile','balanced')
    if profile not in ['balanced',*profiles]:raise ValueError('Unbekanntes Gegnerprofil.')
    bonus=0
    if profile!='balanced':
        values=[p['attributes'][a] for a in profiles[profile] if a in p['attributes']]
        if values:bonus=(sum(values)/len(values)-10.5)/1.9
    penalty=config.get('selection_penalties',{}).get(p['id'],0)
    if not number(penalty,0,30):raise ValueError('Ungültige Belastungsstrafe.')
    result=dict(result);result['base_score']=result['score'];result['selection_adjustment']=round(bonus-penalty,3)
    result['opponent_profile']=profile;result['rotation_penalty']=penalty
    result['score']=round(clip(result['score']+bonus-penalty),4)
    return result
