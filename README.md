# Depesche

*English summary: Depesche (`DP1`) is a compact, ASCII-only message protocol for a team of Claude Code sessions: one lead session and the sessions it directs. Messages use eight fixed types, short fields, references instead of copied content, and codes for standing rules. On real messages it needed about half the tokens of normal prose. A stdlib-only Python tool expands messages to plain German or English, checks them and builds the Claude Code skill. Docs below are in German.*

Depesche ist eine Kurzsprache für die Nachrichten zwischen einer Leitsitzung (Teamleiter) und den Claude-Sitzungen, die ihr unterstehen. Sie spart Tokens, lässt sich trotzdem in Klartext übersetzen und ist für andere Teams wiederverwendbar.

Der Name kommt vom Telegramm: Bezahlt wurde pro Wort, deshalb schrieb man knapp. Jede Nachricht beginnt mit der Kennung `DP1`.

## Was es bringt

Gemessen wurden fünf echte Nachrichten aus einem Team von Claude-Code-Sitzungen: vier Aufträge des Teamleiters und ein Bericht. Die Texte liegen in `messung/`. Namen und Pfade sind dort nach der Messung anonymisiert, die Zeichenzahlen beziehen sich auf die anonymisierte Fassung.

| Fassung | Zeichen | Tokens gegenüber bisher |
|---|---|---|
| bisher: Deutsch mit Markdown (`v.txt`) | 7 044 | 100 % |
| Depesche, Freitext Deutsch (`d.txt`) | 3 619 | etwa 60–65 % |
| Depesche, Freitext Englisch (`e.txt`) | 3 286 | etwa 40–50 % |

**So wurde gemessen:**
- Die Leitsitzung hat jede Datei einmal eingelesen und vorher und nachher ihren Kontext abgefragt. Gezählt hat also der echte Tokenizer des Modells (Claude Opus 5.5).
- Die Grundlast einer Abfrage ist mit einer leeren Datei abgezogen. Weil sie schwankt, stehen hier Spannen.
- Rohwerte: `v` +4 995, `d` +3 506, `e` +2 741, leere Datei +1 244 bis +2 295.

**Was die Zahlen bedeuten:**
- Die Proben sind voller Nutzlast wie Pfade, Versionen und Befehle. Kurze Routinemeldungen wie „VM frei“ oder „fertig, CI grün“ schrumpfen viel stärker.
- Englischer Freitext spart gegenüber deutschem noch einmal etwa ein Viertel, weil der Tokenizer Englisch günstiger zerlegt.
- Weitere Einsparung bringen die Verhaltensregeln: kein Nachlesen ganzer Verläufe, keine Bestätigungen, keine wiederholten Regeln.
- **Grenze:** Den Großteil der Tokens verbrauchen die Sitzungen bei der Arbeit selbst. Die Depesche spart nur bei den Nachrichten.

## Aufbau einer Nachricht

```
DP1 REP part #46 #48
did local commits, not pushed: #46 @de98b11 dir ACL outside profile ...
ci local: build 0 warn, 559 tests green, pwsh parse ok. setup needs vm
next after vm: push each branch once, open 2 PRs
need vm window. #45 waits boss
```

- **Zeile 1:** Kennung und Typ, bei einem Bericht der Status, dann Betreff oder Verweise. Ein `!` am Ende heißt dringend.
- **Folgezeilen:** je ein Punkt, entweder als `feld wert` oder als `- punkt`.
- **Freitext:** knappes Englisch ohne Füllwörter, Artikel und Höflichkeit.
- **Verweise statt Inhalt:** `#n` Issue, `!n` PR, `@sha` Commit, `repo#n`, Dateipfad, Sitzungsname.
- **Kürzel aus dem Teamteil:** feste Regeln (`R push,vm`) und lange Pfade (`$N/plan.md`).
- **Nur ASCII:** Emoji, Unicode-Pfeile und Aufzählungszeichen kosten meist mehr Tokens als normale Wörter. Das hat auch das Esoteric AI Protocol gemessen.

| Typ | Bedeutung | | Feld | Bedeutung |
|---|---|---|---|---|
| `DO` | Auftrag | | `did` | erledigt |
| `ASK` | Frage, Antwort nötig | | `now` | Stand |
| `ANS` | Antwort | | `next` | als Nächstes |
| `REP ok/part/fail/blk` | Bericht mit Status | | `need` | braucht |
| `GO` | Freigabe | | `ci`, `why`, `risk` | CI, Grund, Risiko |
| `NO` | Ablehnung | | `src`, `by`, `out` | entschieden von, Frist, Ergebnis in |
| `STOP` | sofort anhalten, sichern, warten | | `R` | Regeln |
| `FYI` | zur Kenntnis, keine Antwort | | `T` | Tabelle: Kopf einmal, dann CSV-Zeilen |

`./depesche.py expand messung/e.txt` übersetzt die Nachricht oben so:

```
[DP1] Bericht – teilweise erledigt: #46 #48
Erledigt: local commits, not pushed: #46 @de98b11 dir ACL outside profile ...
CI: local: build 0 warn, 559 tests green, pwsh parse ok. setup needs vm
Als Nächstes: after vm: push each branch once, open 2 PRs
Braucht: vm window. #45 waits boss
```

Regelkürzel schreibt der Übersetzer aus. `R vm` wird zum Beispiel zu „Regel vm (Nur eine VM zur Zeit, das Fenster vergibt der Teamleiter)“. Pfadkürzel werden zum vollen Pfad.

## Regeln für die Sitzungen

1. **Eine Nachricht je Anlass,** Punkte bündeln. Keine Bestätigung: Schweigen heißt angenommen.
2. **Bericht bei Abschluss oder wenn es hakt:** `REP` mit Status, dann `did`, `now`, `next` und `need`, höchstens sechs Zeilen. Das Wichtigste gehört in die ersten 400 Zeichen, denn oft sieht der Teamleiter nur die.
3. **Fragen nur, wenn es ohne Antwort nicht weitergeht.** Alles andere kommt in den nächsten Bericht.
4. **Klartext:** Nach einer Zeile `!!` folgen ganze, klare Sätze. Das gilt für Sicherheitsfunde, Unumkehrbares, Entscheidungen für den Menschen und Freigaben.
5. **Wörtlich** bleiben Code, Befehle, Pfade, Fehlermeldungen und IDs.
6. **Nie in Depesche:** alles, was der Mensch direkt liest, also Chat, Abschlussbox, Issues, PRs und Commits.

## Einrichten

1. Leg den Teamteil an: `beispiel/glossar-team.tsv` nach `~/.config/depesche/glossar-team.tsv` kopieren und eigene Regeln, Pfade und Wörter eintragen. Der eigene Teamteil gehört nicht in ein öffentliches Repo.
2. `./depesche.py skill` erzeugt `~/.claude/skills/depesche/SKILL.md`. Danach kennt jede neue Claude-Code-Sitzung die Depesche.
3. Der Leitsitzung sagen, dass sie mit ihren Sitzungen in Depesche spricht.

## Dateien

| Datei | Inhalt |
|---|---|
| `glossar-kern.tsv` | allgemeiner Teil: Typen, Status, Felder, Zeichen, Verweise |
| `beispiel/glossar-team.tsv` | Beispiel für den Teamteil mit Regeln, Pfaden und Wörtern |
| `spec.md` | Vorlage der Regeln für die Sitzungen, englisch und knapp |
| `depesche.py` | Übersetzer, Prüfer, Zähler und Skill-Erzeuger, nur Python-Standardbibliothek |
| `tests/` | Tests, laufen in der CI |
| `messung/` | die fünf Proben in drei Fassungen und eine leere Datei |

Die Glossare haben die Spalten Code, Art, Deutsch und Englisch. Neue Kürzel kommen nur dort hinein, danach wird die Skill-Datei neu erzeugt. So bleibt es bei einer Quelle.

## Werkzeug

```
./depesche.py expand [--en] [DATEI]   # in Klartext übersetzen, Vorgabe Deutsch
./depesche.py check [DATEI ...]       # Kopfzeile, Codes und teure Zeichen prüfen
./depesche.py stats DATEI ...         # Zeichen, Wörter und Zeilen vergleichen
./depesche.py skill [ZIEL|-]          # SKILL.md erzeugen
./depesche.py --team PFAD ...         # anderen Teamteil verwenden
```

Ohne Datei liest das Werkzeug von der Standardeingabe. `check` gibt bei Fehlern den Rückgabewert 1 zurück: bei unbekannten Typen, Regeln oder Pfaden und bei einem Bericht ohne Status.

## Vorbilder

Die Suche am 15.11.2026 auf GitHub und in der Forschung fand einiges. Für ein Team aus Claude-Sitzungen mit festen Regeln eines Betreibers war nichts dabei. Die Zahlen sind Angaben der jeweiligen Autoren.

| Vorbild | Idee | übernommen |
|---|---|---|
| [caveman-claude-skill](https://github.com/amanattar/caveman-claude-skill) | Antworten ohne Füllwörter, laut Autor etwa 75 % weniger; Klartext bei Sicherheit und Unumkehrbarem | knapper Freitext, `!!` |
| [Esoteric AI Protocol](https://github.com/kagioneko/esoteric-ai-protocol) | Pakete aus Absicht, Ziel und Daten; laut eigener Messung kosten Unicode-Zeichen mehr als ASCII | Kopfzeile, nur ASCII |
| [Slipstream](https://zenodo.org/records/18115418) | gemeinsames Begriffsverzeichnis mit kurzen Merkkürzeln | Regel- und Pfadkürzel |
| [PACT](https://papers.cool/arxiv/2606.05304) | knappe Datensätze zu Handlung und Zustand | Bericht mit `did`, `now`, `next`, `need` |
| [TOON](https://github.com/toon-format/toon) | Tabellen mit einmaligem Kopf statt JSON, laut Autoren 30–60 % weniger | `T`-Tabellen |
| [CRISP](https://neurips.cc/virtual/2026/170669), [BabelTele](https://www.emergentmind.com/papers/2606.19857), [ACCP](https://ftp.sjtu.edu.cn/pub/internet-drafts/draft-benzing-accp-00.html) | symbolische Kompression zwischen Agenten, laut Autoren 44–90 % weniger | nur als Bestätigung, zu weit weg von lesbarem Text |
| [SynthLang](https://github.com/ruvnet/SynthLang) | Prompt-Sprache mit Logogrammen | nein: Sonderzeichen sind teuer und schwer zu übersetzen |
| FIPA-ACL und KQML (1990er) | feste Nachrichtentypen wie inform, request, refuse | die acht Typen |

## Lizenz

MIT, siehe `LICENSE`.
