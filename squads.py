"""Explicit squad membership; never inferred from player age or raw team slot."""
SQUADS = {'senior':'Senior Squad', 'second':'2nd Squad', 'u19':'U19 Squad', 'unknown':'Nicht zugeordnet'}

def validate_mappings(mappings):
    if not isinstance(mappings,dict): raise ValueError('Kaderzuordnung muss ein Objekt sein.')
    for club, teams in mappings.items():
        if not isinstance(teams,dict) or any(value not in SQUADS for value in teams.values()):
            raise ValueError('Ungültige Kaderzuordnung.')
    return mappings

def squad_for(player, mappings):
    club=str(player.get('club_id',''))
    team=player.get('team_id')
    if team is not None:
        assigned=mappings.get(club,{}).get(str(team))
        if assigned is not None: return assigned
    return player.get('squad') or 'unknown'
