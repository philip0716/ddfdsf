"""Verified user checks and context filters shared by club and national planning."""
from copy import deepcopy
from math import isfinite
from squads import squad_for,validate_mappings

CHECK_STATES={'eligible','ineligible','unknown'}
REG_FIELDS={'registered','homegrown_club','homegrown_nation','foreign'}

def checked_player(raw,config):
    p=deepcopy(raw)
    checks=config.get('player_checks',{}).get(p['id'],{})
    if not isinstance(checks,dict): raise ValueError('Ungültige Spielerprüfung.')
    p['eligibility']={**p.get('eligibility',{}),**checks.get('eligibility',{})}
    p['registration']={**p.get('registration',{}),**checks.get('registration',{})}
    for value in p['eligibility'].values():
        if value not in CHECK_STATES:raise ValueError('Ungültige Spielberechtigung.')
    for key,value in p['registration'].items():
        if key in REG_FIELDS and value is not None and type(value) is not bool:raise ValueError('Registrierungsangaben müssen true, false oder null sein.')
    if 'scout_cost' in checks:
        value=checks['scout_cost']
        if value is not None and (not isinstance(value,(int,float)) or not isfinite(value) or value<0):raise ValueError('Ungültige Ablöse.')
        p['scout_cost']=value
    p['status']=config.get('overrides',{}).get(p['id'],p.get('status','unknown'))
    if p['status'] not in ['available','unknown','injured','suspended','unavailable']:raise ValueError('Ungültiger Status.')
    return p

def pool(data,config,external=False):
    mode=config.get('mode','club')
    if mode not in ['club','national']:raise ValueError('Unbekannter Planungsmodus.')
    nation=str(config.get('nation') or '')
    if mode=='national' and not nation:raise ValueError('Für die Nationalmannschaft bitte eine Nation auswählen.')
    mappings=validate_mappings(config.get('squad_mappings',data.get('squad_mappings',{})))
    squad=config.get('squad','')
    if squad not in ['','senior','second','u19','unknown']:raise ValueError('Ungültiger Kaderfilter.')
    minimum=config.get('min_fitness',70)
    if not isinstance(minimum,(int,float)) or not isfinite(minimum) or not 0<=minimum<=100:raise ValueError('Ungültige Fitnessgrenze.')
    selected=config.get('selected_ids')
    if selected is not None and (not isinstance(selected,list) or any(not isinstance(pid,str) for pid in selected)):raise ValueError('Ungültige nominierte Spielerliste.')
    selected=set(selected) if selected is not None else None
    eligible=[];excluded=[]
    for raw in sorted(data['players'],key=lambda p:p['id']):
        if selected is not None and not external and raw['id'] not in selected:continue
        club=str(config.get('club') or '')
        if mode=='club' and club and ((not external and str(raw.get('club_id',''))!=club) or (external and str(raw.get('club_id',''))==club)):continue
        if mode=='national' and nation not in [str(n) for n in raw.get('nation_ids',[])] and config.get('player_checks',{}).get(raw['id'],{}).get('eligibility',{}).get(nation,raw.get('eligibility',{}).get(nation))!='eligible':continue
        p=checked_player(raw,config);p['squad']=squad_for(p,mappings)
        if mode=='club':
            club=str(config.get('club') or '')
            if external:
                if not club:raise ValueError('Für externe Alternativen bitte einen Verein auswählen.')
                if str(p.get('club_id',''))==club:continue
            elif club and str(p.get('club_id',''))!=club:continue
            if not external and squad and p['squad']!=squad:continue
            if nation and nation not in [str(n) for n in p.get('nation_ids',[])]:continue
        else:
            known=p['eligibility'].get(nation,'unknown')
            if nation not in [str(n) for n in p.get('nation_ids',[])] and known!='eligible':continue
        reason=None
        if p['status'] in ['injured','suspended','unavailable']:reason=p['status']
        elif p.get('fitness') is not None and p['fitness']<minimum:reason='Unter Fitnessgrenze'
        elif config.get('only_confirmed') and p['status']!='available':reason='Verfügbarkeit ungeprüft'
        elif config.get('objective','form')=='potential' and any(p.get(k) is None for k in ['pa','ca','age']):reason='PA/CA/Alter unbekannt'
        if mode=='national':
            known=p['eligibility'].get(nation,'unknown');p['eligibility_status']=known
            if known=='ineligible':reason='Für diese Nation nicht spielberechtigt'
            elif config.get('eligibility_strict') and known!='eligible':reason='Spielberechtigung ungeprüft'
        if mode=='club' and not external and config.get('registration_strict') and p['registration'].get('registered') is not True:
            reason='Registrierung nicht bestätigt'
        if reason:excluded.append(dict(id=p['id'],name=p['name'],reason=reason))
        else:eligible.append(p)
    return eligible,excluded
