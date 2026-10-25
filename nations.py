"""Display names for FM26 nation IDs. Source and scope documented in README."""
import json
from pathlib import Path

NATION_NAMES = json.loads(Path(__file__).with_name('nations.json').read_text(encoding='utf-8'))

SAVE_NATION_NAMES = json.loads(Path(__file__).with_name('save_nations.json').read_text(encoding='utf-8'))

def resolve_nation_names(overrides=None, id_space='editor'):
    if not isinstance(overrides, dict):
        raise ValueError('nation_names muss ein Objekt mit Ländernamen sein.')
    if any(not isinstance(name, str) or not name.strip() or len(name)>120 for name in overrides.values()):
        raise ValueError('Nationennamen müssen nicht leere Texte mit maximal 120 Zeichen sein.')
    if id_space not in ('editor','save'):
        raise ValueError('nation_id_space muss editor oder save sein.')
    base=SAVE_NATION_NAMES if id_space=='save' else NATION_NAMES
    return {**base, **{str(key): name.strip() for key, name in overrides.items()}}


def apply_nation_names(data):
    space=data.get('nation_id_space', 'save' if 'fmsave' in str(data.get('source','')).lower() else 'editor')
    overrides=data.get('nation_names',{})
    # Earlier exports included the complete editor lookup in save data. Remove only
    # those generated entries; keep names the user actually changed or added.
    if space=='save' and 'nation_id_space' not in data and isinstance(overrides,dict) and all(overrides.get(k)==v for k,v in NATION_NAMES.items()):
        overrides={k:v for k,v in overrides.items() if k not in NATION_NAMES}
    data['nation_names']=resolve_nation_names(overrides,space)
    data['nation_id_space']=space
