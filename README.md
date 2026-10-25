# ⚽ FM26 Vereins- & Nationalteam-Manager · v1.0

Lokale Browser-Anwendung für Football Manager 26 mit zwei getrennten Optimierungszielen: **Formstärkste Startelf** und **Höchstes Entwicklungspotenzial**. Python liest den Spielstand, SciPy/HiGHS besetzt alle elf taktischen Plätze gemeinsam. Die Oberfläche läuft unter `http://127.0.0.1:8765`.

## Start unter Windows

1. [Python 3.12](https://www.python.org/downloads/) installieren (mit Python Launcher).
2. Dieses Repository als ZIP herunterladen und **vollständig entpacken**.
3. `start.bat` doppelklicken. Beim ersten Start werden die Python-Abhängigkeiten installiert; danach öffnet sich die Anwendung im Browser.
4. Zunächst die ausdrücklich gekennzeichnete Demo ausprobieren oder über **Spielstand öffnen** eine `.fm`-Datei wählen.

Das Terminal offen lassen. Zum Beenden `Strg+C` im Terminal drücken. Dies ist eine lokale Web-Anwendung, keine eigenständige Windows-EXE und kein gehosteter Online-Dienst.

Alternativ, auch für macOS/Linux (Python 3.12+):

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Auf macOS/Linux alternativ `sh start.sh`. Bei einem Update Abhängigkeiten erneut mit `python -m pip install -r requirements.txt` innerhalb der aktivierten Umgebung installieren. Anderer Port: `python server.py --port 8766`. Ohne automatisches Browserfenster: `--no-browser`.

## Die zehn Manager-Funktionen

Alle Werkzeuge verwenden den Planungsmodus **Verein** oder **Nationalmannschaft** oben links. Im Nationalmodus werden Vereins- und Senior/2nd/U19-Filter ignoriert; gesucht wird über alle Vereine im Save.

| Nr. | Funktion | Umsetzung |
|---|---|---|
| 1 | Gesamten Kader nominieren | Vereins-Saisonkader und Nationalteam mit 23/25/26/30/55 Spielern, eigener Torwartzahl, Rollen und mehrfacher Positionsabdeckung. Nach der ersten Nominierung auf Wunsch automatische Neuberechnung bei geänderten Einstellungen. |
| 2 | FM26-Taktikeditor | Unabhängige IP-/OOP-Formationen, Positionsübergänge, 40 IP- und 39 OOP-Rollen nach der dokumentierten Rollenreferenz, automatische oder fixierte Rollen und Spielerfixierungen. Vorschlag der besten angebotenen Grundformation. |
| 3 | Weitere Kandidaten | Vereinsmodus: Spieler anderer Vereine nach Einsatzscore, Altersgrenze und bestätigtem Transferbudget. Nationalmodus: weitere noch nicht nominierte Kandidaten derselben Nation. |
| 4 | Spielberechtigung und Registrierung | Manuelle verifizierte Prüfungen pro Spieler; strenger Modus für bestätigte Angaben. Vereinsregeln für Mindestzahlen im Verein/im Land ausgebildeter Spieler und maximale Ausländerzahl. |
| 5 | Positionsübersicht | Erste, zweite und dritte Wahl je taktischem Platz, verfügbare Kandidatenzahl, Lücken und einfache Besetzung. Mehrfachpositionen werden sichtbar eingeordnet; die Kadernominierung prüft gemeinsame Besetzbarkeit. |
| 6 | Spielervergleich | Zwei bis fünf Spieler, Attribute, CA/PA, Formscore, Potenzialscore und beide Rollen. „Warum dieser Spieler?“ vergleicht das freie Gesamtoptimum mit einem erzwungenen Kandidaten. |
| 7 | Rotation | Bis zu acht chronologische Spiele mit Dauer, Gegnerprofil und nachvollziehbarem Fitness-/Belastungsmodell. |
| 8 | Gegnerabhängige Auswahl | Manuell gewähltes Gegnerprofil, Kaderattributübersicht eines Gegners und separat ausgewiesener Auswahlbonus. |
| 9 | Wechsel und Ausfälle | Vorschläge für Führung/Rückstand, eindeutige Ein-/Auswechslungen und komplette Neuoptimierung bei Ausfall eines Starters. |
| 10 | Profile und Verlauf | Benannte Profile, automatische Wiederherstellung pro Datensatz, JSON-Import/Export, bis zu fünf gefilterte Browser-Snapshots und Vergleich früherer Kaderstände/Nominierungen. |

### Nominierungsmodell

Ein binäres Zuordnungsmodell wählt **genau** die angegebene Spielerzahl, jeden Spieler höchstens einmal, und weist jeden Nominierten genau einem der elf taktischen Kaderplätze zu. Torhüterzahl ist exakt. Jeder der zehn Feldplätze erhält mindestens `floor((Kadergröße−Torhüterzahl)/10)` Spieler, höchstens die aufgerundete Zahl. Beispiel 26/3: zwei bis drei Spieler je Feldplatz und drei Torhüter; Beispiel 55/5: fünf Spieler je Feldplatz und fünf Torhüter. Benutzerdefinierte Rollen, Positionsvertrautheit, bestätigte Verfügbarkeit, Spielberechtigung und Vereinsregistrierungsregeln bleiben wirksam. Ein Spieler kann durch Flexibilität zusätzliche Positionen abdecken, zählt aber in dieser Optimierung nur auf einem Platz.

Für die Startelf gelten weiterhin die unten beschriebenen Qualitäts- und Balancegrenzen. Die Mindestqualität der Startelf ist keine zusätzliche Mindestqualität jedes einzelnen Nachrückers im größeren Kader. Bei unbesetzbaren Vorgaben wird ein Fehler angezeigt; die App mischt keine anderen Nationalitäten oder Vereinsgruppen hinzu und liefert keinen still verkleinerten Kader. Eine Nominierung wird erst mit **Diese Auswahl für Startelf verwenden** zum aktiven Auswahlpool.

### Prüfungen und Grenzen

- **Nationalität ist keine Spielberechtigung.** Die Liste enthält alle gelesenen Nationen-IDs. Landnamen werden über 433 mitgelieferte FM26-Zuordnungen auf Deutsch angezeigt; eigene `nation_names` im JSON haben Vorrang. Unbekannte IDs bleiben als ungeklärt markiert. Unter **Prüfen** bestätigst du die Berechtigung für die gerade gewählte Nation. Explizit nicht spielberechtigte Spieler sind ausgeschlossen; ungeprüfte bleiben im Entwurfsmodus sichtbar und werden im strengen Modus ausgeschlossen.
- Registrierungsregeln werden manuell für den betreffenden Wettbewerb eingegeben. Die App behauptet nicht, alle Wettbewerbsregeln oder Nationalteam-Bindungen aus dem Save zu erkennen. Homegrown-Mindestzahlen zählen nur bestätigte Angaben. Ein unbekannter Ausländerstatus zählt bei gesetzter Obergrenze vorsichtig als Ausländer.
- Die Ablöse `scout_cost` muss bestätigt sein und dieselbe Einheit wie das Budget verwenden. `market_value_raw` aus fmsave ist ausdrücklich keine bestätigte Ablöse und wird nicht als solche behandelt. Kandidaten mit unbekannten Kosten werden separat aufgeführt.
- Unabhängige Formationen werden nach minimalem schematischem Positionswechsel zugeordnet. Du kannst jede Positionspaarung manuell ändern. Danach prüft die Optimierung echte Positionsvertrautheit; nicht jede Formationskombination ist mit jedem Kader besetzbar.
- Gegnerprofile `high_press`, `aerial`, `low_block`, `pace` bevorzugen passende Attributgruppen mit höchstens ±5 Punkten. Kaderattribute des Gegners belegen kein tatsächlich beobachtetes Spielsystem. Der Bonus ist ein transparentes App-Modell.
- Rotation ist eine Planung, keine echte FM-Simulation: 8 Fitnesspunkte Erholung pro Tag, 16 Punkte Verbrauch pro 90 Minuten, maximal 30 Auswahlpunkte Belastungsabzug aus den letzten sieben Tagen. Unbekannte Fitness bleibt unbekannt. Starter werden für die eingetragene Dauer geplant; Wechsel sind dort noch nicht eingerechnet.
- Benannte Profile werden im Browser gespeichert (maximal 20), Snapshots ebenfalls (maximal fünf mit jeweils bis zu 3.000 Spielern). Vollständige Kaderdaten können als JSON exportiert werden. Profiles aus einem anderen Datensatz übernehmen keine ungeprüften Spielerfixierungen oder personenbezogenen Bestätigungen.
- Save-Vergleiche nutzen Datenbank-ID plus Geburtsdatum, sonst lokale ID und Name. Ohne sichere Datenbankidentität nur Stände derselben Karriere vergleichen. Fehlende Werte werden nicht als Null interpretiert. Kaderzugänge/-abgänge beziehen sich auf die verglichenen Filter, nicht automatisch auf tatsächlich erfolgte Transfers.

## Weitere Funktionen

- `.fm`-Import über **fmsave 0.5.11** oder Import/Export des dokumentierten JSON-Formats.
- Kaderauswahl **Senior Squad**, **2nd Squad**, **U19 Squad**, alle Kader oder nicht zugeordnet. Der Filter gilt für Startelf, Bank, Alternativen und Spielerliste.
- Vollständige Neuberechnung von Startelf, Einzelplatzalternativen und Bank bei Änderung von Ziel, Formation, Rollen, Filter oder Verfügbarkeit.
- Fünf Grundformationen: 4-3-3 DM, 4-2-3-1, 4-4-2, 3-4-3, 3-5-2.
- Jeder taktische Platz besitzt getrennte IP-/OOP-Positionen und Rollen. Standard ist **Automatisch**: Für jeden Spieler und jeden Platz werden die kompatiblen IP- und OOP-Rollen einzeln bewertet und die besten übernommen. Konkret ausgewählte Rollen bleiben pro Phase fixiert. **Alle Rollen automatisch wählen** setzt die manuellen Rollenbindungen zurück. Die Vorschau unter dem Rollenfeld zeigt die tatsächlich ausgewählte Rolle. Jede Tabellenzeile bezeichnet denselben Spieler in beiden Phasen. OOP-Positionen können individuell geändert werden.
- Spieler auf dem Feld, auf der Bank und unter den Alternativen zeigen ihre **IP- und OOP-Rolle gleichzeitig**. Eine zusätzliche Startelftabelle zeigt beide vollständigen Rollennamen; die Spieleranalyse benennt beide Phasen ausdrücklich. Diese Rollen gehören zum jeweiligen taktischen Einsatz, nicht pauschal zum Spieler.
- FM26-Rollenkatalog mit 40 IP- und 39 OOP-Rollen und getrennten Listen, u. a. Inside Forward, Free Role, Deep-Lying Playmaker, Wide Outlet Winger und Dropping Defensive Midfielder; keine FM24-Duties. Die Referenzliste ist in den Quellen verlinkt; keine FM24-Duties.
- Vereinfilter und Auswahl aller eingelesenen primären und weiteren Nationalitäts-IDs. Ländernamen werden automatisch auf Deutsch aufgelöst und können im JSON mit `nation_names` überschrieben werden. Nationalität ist kein Nachweis der Nationalteam-Spielberechtigung.
- Namen einzeln sowie Startelf und Bank gesammelt kopieren.
- Manuelle Verfügbarkeit: ungeprüft, verfügbar, verletzt, gesperrt, nicht verfügbar. Änderungen werden beim Kaderexport mitgesichert.
- Erklärung aller Teilwerte, Gewichte, Datenabdeckung, gespeicherten Noten und Potenzialszenarien.
- Responsive Oberfläche für Desktop und schmale Browserfenster. Suche zeigt bis zu 200 Kaderzeilen; die Optimierung verwendet den gesamten gefilterten Kandidatenpool bis maximal 5.000 Spielern.

## Auswahlregeln

Für jeden zulässigen Spieler-Platz-Kandidaten wird eine binäre Variable `x[p,j]` gebildet. Maximiert wird die Summe aller elf Einsatzscores:

- Genau ein Spieler pro Platz, höchstens ein Platz pro Spieler.
- Genau ein Torhüter pro Phase.
- Mindestens zwei Innenverteidiger und mindestens ein DM/MC in der OOP-Struktur.
- Positionsvertrautheit muss **in beiden Phasen** mindestens 12/20 betragen (anpassbar).
- Bekannte Fitness muss mindestens 70/100 betragen (anpassbar). Fehlende Fitness bleibt unbekannt und sichtbar.
- Bestätigt verletzte, gesperrte und nicht verfügbare Spieler sind ausgeschlossen. Optional ausschließlich bestätigte Verfügbarkeit.
- Abwehrplätze und DM müssen zusammen eine durchschnittliche defensive Attributqualität von mindestens 40/100 erreichen (anpassbar). Diese Modellgröße wird aus dem Profil für Covering Centre-Back gebildet; sie simuliert keine echte Match Engine.

SciPy `milp` / HiGHS löst die Auswahl mit binären Variablen, ohne Ziellücke und maximal 20 Sekunden Laufzeit. Nur ein nachweislich optimales Ergebnis wird angezeigt. Bei unbesetzbaren Positionen oder Zeitlimit erscheint eine Fehlermeldung; Regeln werden nicht stillschweigend gelockert. Die Balance prüft Struktur und Attributqualität, keine vollständige taktische Simulation.

Die Bank wird anschließend heuristisch besetzt: zuerst je ein zusätzlicher Torwart, Abwehr-, Mittelfeld- und Angriffsspieler, soweit passende Kandidaten vorhanden sind; dann die höchsten verbleibenden Einsatzscores. Ein Spieler zählt für seine am besten bewertete taktische Position. Fehlende Gruppenabdeckung wird gemeldet. Die Bank ist ausdrücklich keine zweite globale Optimierung und garantiert nicht für jeden einzelnen Startelfplatz einen Ersatz. Alternativen beziehen sich auf Einzelplätze und können beim direkten Austausch die Gesamtbalance ändern.

## Formmodell

```text
S = 0,45 F + 0,20 IP + 0,15 OOP + 0,10 Position + 0,10 Einsatzbereitschaft
F = 0,65 Notenwert + 0,20 Positions-KPI + 0,15 Verlässlichkeit
```

Alle Teilwerte liegen bei 0–100. Aktuell werden die letzten maximal 20 gültigen bewerteten Spiele aus 180 Tagen verwendet; zukünftige Einträge werden ignoriert. Zeitbezug ist das **Spielstanddatum**, nicht die Computeruhr.

```text
w_i = 2^(-Tage_seit_Spiel/30) × min(Minuten_i,90)/90
geglättete Note = (Σ w_i × Note_i + 5 × Saisonbasis) / (Σ w_i + 5)
Notenwert = clamp((Note − 5,5) / 3 × 100, 0, 100)
```

Saisonbasis ist die gespeicherte Saisonnote; ohne diese gilt die ausdrücklich als Modellbasis gekennzeichnete Note 6,7. Ohne Einzelspielnoten wird die Saisonersatzbasis angezeigt. Wenige Kurzeinsätze können die Saisonbasis deshalb nicht durch einzelne Spitzennoten verdrängen.

Positions-KPIs sind normierte Saisonraten. Referenzziele für 100 Punkte:

| Einsatzgruppe | Kennzahlen und Modellziele |
|---|---|
| Tor | Paradenquote 85 %, xG verhindert/90 = 0,5 |
| Abwehr und DM | Erfolgreiche Tacklings/90 = 4, Interceptions/90 = 3, gewonnene Kopfbälle/90 = 6 |
| Zentrales/breites Mittelfeld, AMC | Progressive Pässe/90 = 10, Schlüsselpässe/90 = 3, xA/90 = 0,4 |
| Flügelangriff und Spitze | xG/90 = 0,8, xA/90 = 0,4, Schüsse aufs Tor/90 = 2,5 |

Bekannte Kennzahlen werden gleich gewichtet und gekappt. Bei wenigen Saisonminuten wird der KPI-Wert mit `Minuten/(Minuten+450)` zur neutralen Basis 50 geglättet. Dies ist ein einfaches Modell mit festen Referenzzielen, keine Liga- oder Gegnerstärkenbereinigung.

Verlässlichkeit = 50 % Notenkonstanz (`100 − 35 × Standardabweichung`, ab drei Noten), 30 % Saisonminuten (`100 × Minuten/900`, gekappt), 20 % zeitgewichtete Evidenz (`100 × Σw/8`, gekappt). Form-Datenvertrauen ist ein separat ausgewiesener heuristischer Abdeckungswert, keine statistisch kalibrierte Wahrscheinlichkeit.

Bei automatischer Rollenwahl wird die beste kompatible Rolle für das jeweilige Spielerprofil ermittelt, bevor dessen Spieler-Platz-Score in die globale Optimierung eingeht. Das Formziel verwendet aktuelle Attribute, das Potenzialziel das beschriebene zukünftige Attribut-Szenario. Die berechnete Rollenwahl wird zusammen mit dem Score auf Startelf, Bank, Alternativen und Vorschau übernommen. Vorgegebene Positionspaare bleiben erhalten. Ohne Auto-Flag bleiben bestehende API-Aufrufe bei fixierten Rollen. Gleiche optimale Rollen dürfen erhalten bleiben; ein Wechsel des Spielers oder Optimierungsziels erzwingt keine künstlich anderen Rollen. DCL/DCR stehen für äußere Innenverteidigerplätze; spezielle breite Innenverteidigerrollen werden nicht auf dem zentralen DC-Platz angeboten.

IP-/OOP-Eignung: gewichteter Mittelwert der im Rollenkatalog hinterlegten Attribute, mit `(Attribut−1)/19 × 100`. Position: der niedrigere Vertrautheitswert beider Phasen × 5. Einsatzbereitschaft: 70 % Fitness und 30 % Match Sharpness.

## Potenzialmodell

```text
S = 0,27 P + 0,21 G + 0,14 Y + 0,10 D + 0,13 zukünftiges IP
    + 0,09 zukünftiges OOP + 0,06 aktuelle Einsatzbereitschaft
P = PA / 2
G = 100 × min(1, max(0,PA−CA)/80)
```

Für dieses Ziel werden Spieler ohne lesbare PA, CA oder Alter ausgeschlossen und mit Grund zurückgegeben. Negative PA-Range-Codes werden nicht in vermeintlich exakte PA-Werte übersetzt.

Alterskurve Y (lineare Interpolation): 15/18 Jahre = 100, 21 = 85, 24 = 55, 27 = 20, 30 = 3, 35+ = 0. Bei Torhütern wird das Alter für diese Kurve um drei Jahre verschoben. Dies sind konfigurierbare Modellannahmen im Code, keine empirisch validierten Entwicklungswahrscheinlichkeiten.

Entwicklungsbedingungen D: Professionalität (Gewicht 3), Entschlossenheit (2), Saisonminuten (2), Trainingsumfeld (1), inverses Verletzungsrisiko (1), bisheriger Entwicklungstrend (1). Attribute werden auf 0–100 skaliert; Spielzeit erreicht bei 1.800 Saisonminuten ihr Modellmaximum. Trainingsumfeld und Entwicklungstrend werden beim `.fm`-Import **nicht erfunden** und bleiben unbekannt; JSON kann sie ausdrücklich als manuell erhobene Werte ergänzen. Saisonminuten sind nur ein Ersatzindikator für Entwicklungsspielzeit, keine Prognose zukünftiger Minuten.

Modellszenario für den gewählten Horizont H:

```text
CA-Zuwachs = max(0,PA−CA) × Y/100 × (0,25+0,5×D/100) × min(1,H/5)
CA-Szenario = CA + CA-Zuwachs (bei PA gedeckelt)
Szenarioband = 0,5–1,5 × Zuwachs, zwischen CA und PA gekappt
Attributzuwachs für zukünftige Rollen = min(3, CA-Zuwachs/40)
```

Der Horizont skaliert bis fünf Jahre; oberhalb bleibt der konservative Zuwachsdeckel bestehen. Der zukünftige Rollenwert setzt diesen **gleichmäßigen** Attributzuwachs im Rollenprofil an. Das ist eine einfache, sichtbare Szenarioannahme; CA lässt sich nicht zuverlässig linear in einzelne Attribute umrechnen. Weder Szenario noch Band sind eine offizielle FM-Prognose oder ein kalibriertes Konfidenzintervall. **PA-Obergrenze, CA-Szenario und Entwicklungsscore werden getrennt dargestellt.**

Aktuelle Einsatzbereitschaft im Potenzialziel: 40 % CA/2, 40 % Fitness/Sharpness-Teilwert, 20 % Positionswert. Eine junge Alterszahl allein reicht somit nicht für einen guten Gesamtscore.

Fehlende Komponenten werden innerhalb des betreffenden Teilwerts aus den vorhandenen Daten neu gewichtet. Wenn überhaupt keine Komponente bekannt ist, wird die neutrale Modellbasis 50 mit Abdeckung 0 verwendet. Unbekannt ist kein tatsächlicher Messwert von 50; die Oberfläche zeigt Abdeckung und Hinweise separat. Diese Unsicherheit kann Empfehlungen beeinflussen.

## Import und Datenqualität

Der Adapter nutzt die öffentlichen Leser `players()`, `player_match_stats()`, `player_season_stats()` und `managed_clubs()`. Saisonwerte stammen aus genau einer `overall`-Zeile pro Spieler, bevorzugt aus dem aktuellen Verein, sonst der Zeile mit den meisten Minuten. Wettbewerbssummen werden nicht zusätzlich auf `overall` addiert. Nach Transfers kann diese Auswahl einen anderen Beobachtungszeitraum als die Einzelspielhistorie repräsentieren.

Der Parser unterstützt nicht jeden FM-Build und nicht jedes Feld. Die gespeicherte Einzelspielhistorie ist unvollständig; Freundschafts-, Jugend- und Länderspiele gehören nicht zum verwendeten Einzelspielleser. CA/PA und mehrere Einzelspielfelder sind in fmsave noch als **unbestätigt** eingestuft. Gespeicherte Sperren können veraltet oder wettbewerbsspezifisch sein; der Adapter meldet sie als Prüfhinweis und leitet keine pauschale Sperre für das nächste Spiel daraus ab. Aktuelle Verletzung/Verfügbarkeit muss manuell bestätigt werden. Taktische Zahlen aus dem Save werden nicht als vermeintlich bekannte Rollen interpretiert: Formation und Rollen werden in der App gewählt.

### Kaderzuordnung

Nach dem Verein wählst du **Senior Squad**, **2nd Squad** oder **U19 Squad**. Ohne Auswahl gilt **Alle Kader**, damit alte JSON-Dateien weiterhin funktionieren. Ist der gewählte Kader zu klein oder fehlen Positionen, erscheint eine Fehlermeldung; andere Kader werden nicht automatisch zugemischt.

fmsave liefert `team_id` und `team_slot`, bestätigt aber noch nicht, ob ein gespeicherter Slot Reserve oder Jugend bedeutet. Daher übernimmt der Import beide Rohwerte, markiert den Kader zunächst als unbekannt und bietet **Kaderzuordnung prüfen** an. Dort ordnest du pro Verein die tatsächlichen Team-IDs nach Abgleich mit dem Spiel zu. Es wird weder `Slot 1 = Reserve` noch `Alter unter 19 = U19` angenommen. Auch ein 17-Jähriger kann im Senior Squad stehen.

Die Zuordnung wird beim JSON-Export im Feld `squad_mappings` gesichert und beim erneuten Import wiederverwendet. Alternativ können normalisierte Spielerdatensätze `squad` direkt enthalten (`senior`, `second`, `u19`, `unknown`). Explizite Teamzuordnungen haben Vorrang. Beispiel:

```json
{"squad_mappings": {"club-1": {"team-101": "senior", "team-102": "second", "team-103": "u19"}}}
```

Bei Spielern ohne lesbare Team-ID bleibt nur eine explizite `squad`-Angabe im JSON. Die Demo enthält alle drei Kader mit je 28 erfundenen Spielern bei einem Verein sowie 28 zusätzliche Spieler eines anderen Vereins. Die bestätigten Beispielprüfungen sind frei erfundene Demodaten.

### JSON-Schema (normalisiertes App-Format)

Nicht jeder beliebige fmsave-JSON-Export kann direkt importiert werden. Ein vollständiges Beispiel liefert **Kader als JSON sichern** aus der Demo.

```json
{
  "date": "2026-10-24",
  "source": "Eigener verifizierter Export",
  "nation_names": {"1": "Österreich"},
  "players": [{
    "id": "123", "name": "Beispielspieler", "age": 18,
    "ca": 105, "pa": 180,
    "club_id": "club-1", "club": "Beispielverein", "nation_ids": [1],
    "squad": "senior", "team_id": "team-101",
    "positions": {"mc": 20, "dm": 16},
    "attributes": {"passing": 14, "vision": 13, "decisions": 12},
    "fitness": 95, "sharpness": 85, "status": "unknown",
    "professionalism": 16,
    "matches": [{"date": "2026-10-20", "minutes": 90, "rating": 7.4}],
    "season": {"minutes": 800, "average_rating": 7.2, "expected_assists_per_90": 0.2}
  }]
}
```

`id` muss je Save eindeutig und ein String sein. Attribute und Positionswerte verwenden 1–20 bzw. 0–20; Fitness/Sharpness verwenden 0–100, CA/PA 1–200. Unbekannte optionale Werte weglassen oder `null` setzen. Für eine Elf sind mindestens elf geeignete Spieler und die benötigte Positionsabdeckung notwendig.

## Architektur und Prüfung

```text
Browser → lokaler Python-HTTP-Server → fmsave-Adapter → normalisierte Spielerdaten
                                             ↓
                                  Bewertungsmodell → MILP → Startelf + Bank
```

- `catalog.py`: Positions- und Rollenprofile sowie Formationen.
- `planning.py`: Kadernominierung, Abdeckung, Scouting, Vergleiche, Formationstausch, Gegner, Rotation und Szenarien.
- `selection.py`: gemeinsame Kontext- und Berechtigungsfilter.
- `web/manager.js`: Manager-Werkzeuge, Prüfungen, Profile und Snapshots.
- `engine.py`: Validierung, Formmodell, Entwicklungsszenarien und Optimierung.
- `importer.py`: Spielstandadapter; übernimmt keine unbekannten Codes als bekannte Fakten.
- `server.py`: lokale API und Auslieferung der Oberfläche.
- `web/`: deutsche Oberfläche ohne JavaScript-Buildschritt oder externe CDN-Ressourcen.
- `tests/`: automatisierte Algorithmus- und HTTP-Tests, einschließlich Zielwechsel und eines Gegenbeispiels zur gierigen Positionsauswahl.

```sh
python -m unittest discover -s tests -v
node --check web/app.js
```

Testumfang: 83 automatisierte Tests mit synthetischen Spielern, Adapter mit kontrollierten Datensätzen, HTTP-API und Fehlerfällen. Zusätzlich wurden Zielwechsel, Kopieren, Spieleranalyse, OOP-Ansicht, Formationswechsel, Verfügbarkeitsänderung und mobile Seitenbreite in Chromium geprüft. Ein zweiter Browserlauf prüft alle zehn Manager-Bereiche einschließlich Vereins-26er-Kader, Nationalteam-55er-Kader, automatischer Neunominierung, Profile, Neustart und Export. Zusätzlicher Praxistest am 25.10.2026: Ein echter lokaler FM26-Spielstand wurde über den Adapter erfolgreich eingelesen. Beide Optimierungsziele lieferten elf Starter und neun Ersatzspieler; Startelf und mehrere IP-/OOP-Rollen unterschieden sich zwischen den Zielen. Die erweiterten Werkzeuge wurden ebenfalls mit diesem Spielstand geprüft: Vereins-26er-Kader, Nationalteam-26er-/55er-Entwurf, elf Tiefenpositionen, 33 externe Kandidaten, fünf besetzbare Grundformationen, zwei geplante Spiele, Ausfallszenario und Gegnerprofil. Bei Nationalteam-Entwürfen wurden ungeklärte Spielberechtigungen ausdrücklich gemeldet. Die Originaldatei und die persönlichen Spielerdaten wurden nicht ins Repository übernommen. Dieser Test belegt den getesteten Spielstand, keine allgemeine Kompatibilität mit sämtlichen FM-Builds. Ein Windows-Systemtest steht weiterhin aus.

Optionaler Browser-Smoke-Test (zusätzlich Node.js benötigt):

```sh
npm install --no-save playwright
npx playwright install chromium
node tests/browser.cjs
node tests/manager-browser.cjs
```

Die Tests starten ihre eigenen lokalen Server auf Port 18765 bzw. 18766. Er liest keine echten Spielstände.

Der Server bindet ausschließlich `127.0.0.1`, prüft Host/Origin und eine eigene Request-Kennung. Er ist für die lokale Einzelnutzung vorgesehen. Spielstände werden temporär zum Lesen abgelegt und danach entfernt; im Arbeitsspeicher bleibt der gelesene Kader bis zum nächsten Import oder Beenden. JSON-Export sichert den Kader bewusst auf deinem Gerät. Keine `.fm`-Dateien oder persönlichen Kaderdaten gehören ins öffentliche Repository.

## Quellen

- [fmsave API und Grenzen](https://github.com/rhiever/fmsave), getestete Paketversion 0.5.11.
- [Offizielle FM26-Erklärung zu IP-/OOP-Formationen und Rollen](https://www.footballmanager.com/fm26/features/possession-out-possession-fm26s-new-tactical-evolution).
- [FM26-Rollen und Phasenzuordnung anhand der Spielanzeigen im SI-Forum](https://community.sports-interactive.com/forums/topic/600770-football-manager-26-roles-attributes/).
- [OOP-Rollenbeobachtungen des Guide-Autors im SI-Forum](https://community.sports-interactive.com/forums/topic/594846-fm26-out-of-possession-player-roles-guide/).

Eigene Bewertungsgewichte und Referenzziele, keine offiziellen FM26-Formeln. Inoffizielles Fanprojekt; keine Verbindung zu Sports Interactive oder SEGA.

Nationenzuordnung: `nations.json`, 433 Nationseinträge einschließlich separater FM26-Einträge, abgeglichen am 25.10.2026 mit https://sortitoutsi.net/football-manager-2026/database. Namen dienen nur der Anzeige; Filter und Spielberechtigungen verwenden unverändert die ursprünglichen IDs. Keine Ableitung einer Nation aus Spielernamen oder Vereinsstandorten.

Korrektur der Nationenanzeige: FM26-Spielstände verwenden interne Nationen-IDs (z. B. 129 Österreich, 145 Deutschland), keine Editor-IDs (755/771). `save_nations.json` enthält alle 251 internen Einträge 0–250, einschließlich historischer Nationen und Herkunftsgruppen. `nation_id_space` unterscheidet `save` und `editor`; der FM-Import setzt `save` automatisch. Alte fmsave-JSON-Exporte mit der vollständigen automatisch eingefügten Editor-Liste werden beim Import korrigiert. Quelle für die interne Liste: https://github.com/fifteen15-labs/gilet/blob/main/crates/fm-save/src/person.rs (228 Zuordnungen); die vollständige Reihenfolge einschließlich historischer Einträge wurde mit https://sortitoutsi.net/content/76922/fm26-nations-update abgeglichen. Eigene Namen haben Vorrang.
