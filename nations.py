"""Display names for FM26 nation IDs. Source and scope documented in README."""
import json
from pathlib import Path

NATION_NAMES = json.loads(Path(__file__).with_name('nations.json').read_text(encoding='utf-8'))

def resolve_nation_names(overrides=None):
    if not isinstance(overrides, dict):
        raise ValueError('nation_names muss ein Objekt mit Ländernamen sein.')
    if any(not isinstance(name, str) or not name.strip() or len(name)>120 for name in overrides.values()):
        raise ValueError('Nationennamen müssen nicht leere Texte mit maximal 120 Zeichen sein.')
    return {**NATION_NAMES, **{str(key): name.strip() for key, name in overrides.items()}}
