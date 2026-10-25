"""Adapter for the pinned fmsave public API; raw unknown codes are never interpreted."""
from collections import defaultdict
from dataclasses import asdict
import warnings
from engine import validate


def from_save(path):
    import fmsave
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with fmsave.open(path) as save:
            if save.info.game_date is None:
                raise ValueError('Spielstanddatum nicht lesbar. JSON mit verifiziertem Datum verwenden.')
            records=save.players()
            history=defaultdict(list)
            season=defaultdict(list)
            notices=[]
            try:
                for m in save.player_match_stats():
                    if m.stats_in_range and m.has_stats:
                        history[m.player_uid].append(dict(date=m.date.isoformat(),rating=m.rating,minutes=m.minutes))
            except (ValueError,RuntimeError) as exc:
                notices.append('Einzelspielhistorie nicht lesbar: '+type(exc).__name__)
            try:
                for row in save.player_season_stats():
                    if str(row.kind)=='overall': season[row.player_uid].append(row)
            except (ValueError,RuntimeError) as exc:
                notices.append('Saisonwerte nicht lesbar: '+type(exc).__name__)
            players=[]
            for p in records:
                rows=season[p.uid]
                current=[r for r in rows if r.club_uid==p.club_uid]
                # OVERALL already includes the competition rows; never sum it with them.
                best=max(current or rows,key=lambda r:r.minutes,default=None)
                stats={}
                if best:
                    keys=['minutes','average_rating','save_percent','expected_goals_prevented_per_90',
                          'tackles_completed_per_90','interceptions_per_90','headers_won_per_90',
                          'progressive_passes_per_90','key_passes_per_90','expected_assists_per_90',
                          'expected_goals_per_90','shots_on_target_per_90']
                    stats={k:getattr(best,k,None) for k in keys}
                attrs={k:v for k,v in asdict(p.attributes).items() if 1<=v<=20}
                pa=p.ability.potential
                players.append(dict(id=str(p.uid),name=p.name or f'Spieler {p.uid}',age=p.age,
                    ca=p.ability.current if 1<=p.ability.current<=200 else None,
                    pa=pa if pa is not None and 1<=pa<=200 else None,
                    club_id=str(p.club_uid) if p.club_uid is not None else '',club=p.club_name or 'Ohne Vereinsname',
                    team_id=str(p.team_id) if getattr(p,'team_id',None) is not None else None,
                    team_slot=getattr(p,'team_slot',None),squad='unknown',
                    nation_ids=list(dict.fromkeys([n for n in [p.nation_id,*p.second_nation_ids] if n is not None])),
                    positions=asdict(p.positions),attributes=attrs,
                    fitness=p.raw_condition/100 if 0<=p.raw_condition<=10000 else None,
                    sharpness=p.raw_match_sharpness/100 if 0<=p.raw_match_sharpness<=10000 else None,
                    professionalism=p.personality.professionalism if p.personality else None,
                    status='unknown',matches=history[p.uid],season=stats,
                    notes=['Gespeicherte Sperren vorhanden; Gültigkeit für den nächsten Wettbewerb prüfen.'] if p.suspensions else []))
            managed=[str(c.club_uid) for c in save.managed_clubs()]
            notices += ['Kaderzuordnung: Team-IDs bitte unter Kaderzuordnung prüfen als Senior, 2nd oder U19 bestätigen. Slotnummer und Alter bestimmen keinen Kader.',
                        'FM-Verfügbarkeit wird nicht automatisch bestätigt; bitte im Kader prüfen.',
                        'Einzelspielhistorie ist unvollständig; keine Freundschafts-, Jugend- oder Länderspiele.',
                        'CA, PA, Namen und Teile der Einzelspielwerte sind im Parser noch unbestätigte Felder.',
                        'Nationennamen benötigen eine zusätzliche ID-Zuordnung; alle gelesenen IDs bleiben auswählbar.']
            notices += [str(w.message) for w in caught][:20]
            data=dict(players=players,date=save.info.game_date.isoformat(),source='FM26 · fmsave 0.5.11',
                      notices=notices,managed_clubs=managed,nation_names={})
    return validate(data)
