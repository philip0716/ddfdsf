# ⚽ FM26 Best XI Builder

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

## Funktionen

- `.fm`-Import über **fmsave 0.5.11** oder Import/Export des dokumentierten JSON-Formats.
- Vollständige Neuberechnung von Startelf, Einzelplatzalternativen und Bank bei Änderung von Ziel, Formation, Rollen, Filter oder Verfügbarkeit.
- Fünf Grundformationen: 4-3-3 DM, 4-2-3-1, 4-4-2, 3-4-3, 3-5-2.
- Jeder taktische Platz besitzt getrennte IP-/OOP-Positionen und Rollen. Jede Tabellenzeile bezeichnet denselben Spieler in beiden Phasen. OOP-Positionen können individuell geändert werden.
- Ausgewählter, erweiterbarer FM26-Rollenkatalog; keine FM24-Duties. Nicht alle FM26-Rollen sind enthalten.
- Vereinfilter und Auswahl aller eingelesenen primären und weiteren Nationalitäts-IDs. ID-Namen können im JSON mit `nation_names` ergänzt werden. Nationalität ist kein Nachweis der Nationalteam-Spielberechtigung.
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
- `engine.py`: Validierung, Formmodell, Entwicklungsszenarien und Optimierung.
- `importer.py`: Spielstandadapter; übernimmt keine unbekannten Codes als bekannte Fakten.
- `server.py`: lokale API und Auslieferung der Oberfläche.
- `web/`: deutsche Oberfläche ohne JavaScript-Buildschritt oder externe CDN-Ressourcen.
- `tests/`: automatisierte Algorithmus- und HTTP-Tests, einschließlich Zielwechsel und eines Gegenbeispiels zur gierigen Positionsauswahl.

```sh
python -m unittest discover -s tests -v
node --check web/app.js
```

Testumfang: 28 automatisierte Tests mit synthetischen Spielern, Adapter mit kontrollierten Datensätzen, HTTP-API und Fehlerfällen. Zusätzlich wurden Zielwechsel, Kopieren, Spieleranalyse, OOP-Ansicht, Formationswechsel, Verfügbarkeitsänderung und mobile Seitenbreite in Chromium geprüft. Kein erfolgreich gelesener echter `.fm`-Spielstand und kein Windows-Systemtest sind durch diese Tests belegt. Echte Save-Kompatibilität muss mit dem jeweiligen Spielstand geprüft werden.

Optionaler Browser-Smoke-Test (zusätzlich Node.js benötigt):

```sh
npm install --no-save playwright
npx playwright install chromium
node tests/browser.cjs
```

Der Test startet seinen eigenen lokalen Server auf Port 18765. Er liest keine echten Spielstände.

Der Server bindet ausschließlich `127.0.0.1`, prüft Host/Origin und eine eigene Request-Kennung. Er ist für die lokale Einzelnutzung vorgesehen. Spielstände werden temporär zum Lesen abgelegt und danach entfernt; im Arbeitsspeicher bleibt der gelesene Kader bis zum nächsten Import oder Beenden. JSON-Export sichert den Kader bewusst auf deinem Gerät. Keine `.fm`-Dateien oder persönlichen Kaderdaten gehören ins öffentliche Repository.

## Quellen

- [fmsave API und Grenzen](https://github.com/rhiever/fmsave), getestete Paketversion 0.5.11.
- [Offizielle FM26-Erklärung zu IP-/OOP-Formationen und Rollen](https://www.footballmanager.com/fm26/features/possession-out-possession-fm26s-new-tactical-evolution).
- [OOP-Rollenbeobachtungen des Guide-Autors im SI-Forum](https://community.sports-interactive.com/forums/topic/594846-fm26-out-of-possession-player-roles-guide/).

Eigene Bewertungsgewichte und Referenzziele, keine offiziellen FM26-Formeln. Inoffizielles Fanprojekt; keine Verbindung zu Sports Interactive oder SEGA.
