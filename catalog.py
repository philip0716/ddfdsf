"""Small FM26 role catalogue. Attribute weights are our model, not FM internals."""
POSITIONS = ['gk','dl','dc','dr','wbl','wbr','dm','ml','mc','mr','aml','amc','amr','stc']
ROLES = {}
def role(phase, name, positions, **weights):
    ROLES[phase + ':' + name] = dict(phase=phase, name=name, positions=positions.split(), weights=weights)

role('ip','Ball-Playing Goalkeeper','gk',passing=3,kicking=3,first_touch=2,decisions=2,composure=2,reflexes=3,handling=3)
role('ip','No-Nonsense Goalkeeper','gk',reflexes=3,handling=3,aerial_reach=2,positioning=2,kicking=1)
role('ip','Centre-Back','dc',marking=3,tackling=3,positioning=3,heading=2,jumping_reach=2,passing=1)
role('ip','Overlapping Centre-Back','dc',passing=2,dribbling=2,crossing=2,pace=2,stamina=2,tackling=2,marking=2)
role('ip','Full-Back','dl dr',crossing=2,passing=2,stamina=2,pace=2,tackling=2,positioning=2)
role('ip','Playmaking Wing-Back','dl dr wbl wbr',passing=3,vision=3,decisions=2,technique=2,stamina=2)
role('ip','Advanced Wing-Back','dl dr wbl wbr',crossing=3,dribbling=2,off_the_ball=3,pace=2,stamina=3)
role('ip','Defensive Midfielder','dm',positioning=3,tackling=3,passing=2,decisions=2,teamwork=2)
role('ip','Midfield Playmaker','mc',passing=3,vision=3,technique=2,decisions=3,first_touch=2)
role('ip','Wide Central Midfielder','mc',passing=2,off_the_ball=3,dribbling=2,stamina=2,crossing=2)
role('ip','Winger','ml mr aml amr',crossing=3,dribbling=3,pace=3,acceleration=2,off_the_ball=2)
role('ip','Wide Forward','aml amr',finishing=3,off_the_ball=3,pace=3,dribbling=2,composure=2)
role('ip','Attacking Midfielder','mc amc',passing=2,vision=3,off_the_ball=3,first_touch=2,technique=2)
role('ip','Channel Forward','stc',off_the_ball=3,pace=3,acceleration=2,finishing=3,composure=2)
role('oop','Sweeper Keeper','gk',rushing_out=3,anticipation=3,decisions=3,reflexes=2,one_on_ones=2)
role('oop','Line-Holding Goalkeeper','gk',positioning=3,concentration=3,reflexes=3,handling=3)
role('oop','Covering Centre-Back','dc',anticipation=3,pace=3,marking=3,positioning=3,concentration=2)
role('oop','Stopping Centre-Back','dc',aggression=3,tackling=3,strength=3,anticipation=2)
role('oop','Holding Full-Back','dl dr',concentration=3,positioning=3,marking=3,tackling=2)
role('oop','Pressing Full-Back','dl dr',work_rate=3,anticipation=3,aggression=3,stamina=2)
role('oop','Holding Wing-Back','wbl wbr',concentration=3,positioning=3,marking=3,stamina=2)
role('oop','Pressing Wing-Back','wbl wbr',work_rate=3,anticipation=3,aggression=3,stamina=3)
role('oop','Screening Defensive Midfielder','dm',positioning=3,concentration=3,marking=3,anticipation=2)
role('oop','Pressing Defensive Midfielder','dm',work_rate=3,anticipation=3,aggression=3,stamina=2)
role('oop','Screening Central Midfielder','mc',positioning=3,concentration=3,marking=3,anticipation=2)
role('oop','Pressing Central Midfielder','mc',anticipation=3,work_rate=3,aggression=3,stamina=2)
role('oop','Tracking Wide Midfielder','ml mr',stamina=3,work_rate=3,marking=3,positioning=2)
role('oop','Tracking Winger','aml amr',stamina=3,work_rate=3,marking=3,positioning=2)
role('oop','Tracking Attacking Midfielder','amc',stamina=3,work_rate=3,marking=3,positioning=2)
role('oop','Tracking Centre Forward','stc',work_rate=3,stamina=3,marking=3,teamwork=2)
role('oop','Central Outlet Centre Forward','stc',anticipation=3,off_the_ball=3,decisions=3,pace=2)

FORMATIONS = {
 '4-3-3 DM': ['gk','dl','dc','dc','dr','dm','mc','mc','aml','amr','stc'],
 '4-2-3-1': ['gk','dl','dc','dc','dr','dm','dm','aml','amc','amr','stc'],
 '4-4-2': ['gk','dl','dc','dc','dr','ml','mc','mc','mr','stc','stc'],
 '3-4-3': ['gk','dc','dc','dc','wbl','dm','dm','wbr','aml','amr','stc'],
 '3-5-2': ['gk','dc','dc','dc','wbl','dm','mc','mc','wbr','stc','stc'],
}
def default_role(phase, position):
    return next(k for k,v in ROLES.items() if v['phase']==phase and position in v['positions'])
def slots_for(formation):
    return [dict(id=str(i),ip_position=p,oop_position=p,
                 ip_role=default_role('ip',p),oop_role=default_role('oop',p))
            for i,p in enumerate(FORMATIONS[formation])]
