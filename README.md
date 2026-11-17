# Depesche

*English summary: Depesche (`DP1`) is a compact, ASCII-only message protocol for a team of Claude Code sessions: one lead session and the sessions it directs. Messages use eight fixed types, short fields, telegram-style English, references instead of copied content, and codes for standing rules. On real messages it needs about two thirds of the tokens of normal prose; the generated skill file shrank by 30 % in tokens. A stdlib-only Python tool expands messages to plain German or English, checks structure and style, and builds the Claude Code skill. Docs below are in German.*

Depesche ist eine Kurzsprache für die Nachrichten zwischen einer Leitsitzung (Teamleiter) und den Claude-Sitzungen, die ihr unterstehen. Sie spart Tokens, lässt sich trotzdem in Klartext übersetzen und ist für andere Teams wiederverwendbar.

Der Name kommt vom Telegramm: Bezahlt wurde pro Wort, deshalb schrieb man knapp. Jede Nachricht beginnt mit der Kennung `DP1`.

## Was es bringt

Messgrundlage: fünf echte Nachrichten aus einem Team von Claude-Code-Sitzungen, vier Aufträge des Teamleiters und ein Bericht. Die Texte liegen in `messung/`, Namen und Pfade nach der Messung anonymisiert.

| Fassung | Zeichen | Tokens netto | gegenüber bisher |
|---|---|---|---|
| bisher: Deutsch mit Markdown (`v.txt`) | 7 044 | ~2 020 | 100 % |
| Depesche, Freitext Deutsch (`d.txt`) | 3 619 | – | ~60–65 % (1. Messung) |
| Depesche, Freitext Englisch (`e.txt`) | 3 286 | ~1 360 | ~67 % |
| Depesche nach Stilregeln (`e2.txt`) | 3 245 | ~1 370 | ~67 % |
| `SKILL.md` alt (Teamteil des Betreibers) | 3 681 | ~1 910 | 100 % |
| `SKILL.md` neu (gleicher Teamteil, gekürzte Regeltexte) | 3 272 | ~1 350 | ~70 % |

**Messmethode (2. Messung, 15.11.2026):**
- Eine Sitzung liest jede Datei mit `cat` ein und fragt direkt danach ihren Kontext ab (`get_usage`). Zählt also der echte Tokenizer des Modells (Claude Opus 5.5).
- Jeder Schritt ist eine eigene Nachricht, ohne Text dazwischen. Werden mehrere Aufrufe in einer Nachricht gebündelt, verfälscht das die Werte.
- Abgezogen ist die Grundlast eines Schritts, gemessen mit der leeren Datei `0.txt`: +767 und +793 Tokens. Rohwerte: `v` +2 805, `e` +2 154, `e2` +2 159, `SKILL.md` alt +2 706, neu +2 140.
- Die 1. Messung (Grundlast schwankte zwischen +1 244 und +2 295) ergab für `e` 40–50 %. Die 2. Messung hat eine stabile Grundlast und ist genauer.

**Was die Zahlen bedeuten:**
- `e2` spart gegenüber `e` keine Tokens: `e` war schon knapp. Die Stilregeln machen Nachrichten einheitlich (eine Sache je Zeile, keine Artikel) und `check` findet Rückfälle in Prosa.
- Die Proben sind voller Nutzlast (Pfade, Versionen, Befehle). Kurze Routinemeldungen wie „VM frei“ schrumpfen stärker.
- `SKILL.md` lädt jede Sitzung, die eine Depesche schreibt oder liest, in ihren Kontext. Die 30 % weniger zählen also in jeder Sitzung des Teams.
- **Grenze:** Den Großteil der Tokens verbrauchen die Sitzungen bei der Arbeit selbst. Die Depesche spart nur bei Nachrichten.

## Aufbau einer Nachricht

```
DP1 REP part #46 #48
did local commits, not pushed: #46 @de98b11 dir ACL outside profile ...
ci local: build 0 warn, 559 tests green, pwsh parse ok. setup needs vm
next after vm: push each branch once, open 2 PRs
need vm window. #45 waits boss
```

- **Zeile 1:** Kennung, Typ, bei `REP` der Status, dann Verweise oder Betreff. `!` am Ende heißt dringend.
- **Folgezeilen:** je ein Punkt: `feld wert`, `TYP text` (Teilauftrag), `- punkt` oder Tabellenzeile. Andere Zeilenanfänge meldet `check`, weil der Übersetzer sie sonst als Feld lesen könnte (`by tomorrow` wäre „Frist: tomorrow“).
- **Tabellen:** `T spalte,spalte`, dann je Zeile ein CSV-Datensatz. Die letzte Spalte nimmt den Rest der Zeile samt Kommas. Eine Leerzeile beendet die Tabelle.
- **Verweise statt Inhalt:** `#n` Issue, `!n` PR, `@sha` Commit, `repo#n`, Dateipfad, Sitzungsname.
- **Kürzel aus dem Teamteil:** feste Regeln (`R push,vm`) und lange Pfade (`$N/plan.md`). In `Backticks` und "Anführungszeichen" bleibt alles wörtlich.
- **Nur ASCII:** Emoji, Unicode-Pfeile und Aufzählungszeichen kosten meist mehr Tokens als Wörter (gemessen auch vom Esoteric AI Protocol).
- **Klartext:** nach einer Zeile `!!` ganze Sätze bis zur nächsten Leerzeile. Darin beginnt keine neue Nachricht, auch wenn eine Zeile mit `DP1` anfängt.

### Freitext im Telegrammstil

Englisch, ohne Artikel, Füllwörter, Höflichkeit, Absicherungen und Wiederholung von Bekanntem. Satzbruchstücke und Imperativ sind erwünscht. Erlaubte Abkürzungen: `cfg dir env dep impl req resp msg fn arg repo ver doc auth perm tmp`.

| schlecht | gut |
|---|---|
| I have pushed the fix and the CI is green now. | `did fix pushed, ci green` |
| Could you please check whether the updater verifies the hash? | `- check updater verifies hash?` |
| It would probably be best to wait for the build first. | `next wait build` |

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

`./depesche.py expand messung/e.txt` übersetzt den Bericht oben so:

```
[DP1] Bericht – teilweise erledigt: #46 #48
Erledigt: local commits, not pushed: #46 @de98b11 dir ACL outside profile ...
CI: local: build 0 warn, 559 tests green, pwsh parse ok. setup needs vm
Als Nächstes: after vm: push each branch once, open 2 PRs
Braucht: vm window. #45 waits boss
```

Regelkürzel schreibt der Übersetzer aus, `R vm` etwa zu „Regel vm (Nur eine VM zur Zeit, das Fenster vergibt der Teamleiter)“. Pfadkürzel werden zum vollen Pfad.

## Regeln für die Sitzungen

1. **Eine Nachricht je Anlass,** Punkte bündeln. Keine Bestätigung: Schweigen heißt angenommen.
2. **Bericht bei Abschluss oder Blockade:** `REP` mit Status, dann `did`, `now`, `next`, `need`, höchstens sechs Zeilen. Das Wichtigste in die ersten 400 Zeichen: oft sieht der Teamleiter nur die.
3. **Fragen nur, wenn es ohne Antwort nicht weitergeht.** Alles andere in den nächsten Bericht.
4. **Klartext** (`!!`) für Sicherheitsfunde, Unumkehrbares, Entscheidungen des Menschen und Freigaben.
5. **Wörtlich** bleiben Code, Befehle, Pfade, Fehlermeldungen und IDs.
6. **Nie in Depesche:** alles, was der Mensch direkt liest: Chat, Abschlussbox, Issues, PRs, Commits.

## Einrichten

1. Teamteil anlegen: `beispiel/glossar-team.tsv` nach `~/.config/depesche/glossar-team.tsv` kopieren, eigene Regeln, Pfade und Wörter eintragen. Der eigene Teamteil gehört nicht in ein öffentliches Repo.
2. `./depesche.py skill` erzeugt `~/.claude/skills/depesche/SKILL.md`. Danach kennt jede neue Claude-Code-Sitzung die Depesche.
3. Der Leitsitzung sagen, dass sie mit ihren Sitzungen in Depesche spricht.

### Als Skill in Claude Desktop oder claude.ai importieren

**Fertige Zip aus dem Release** (ohne Python, ohne Klonen):

1. Unter [Releases](https://github.com/Celestial0579/depesche/releases) `depesche.zip` und `SHA256SUMS.txt` herunterladen.
2. Prüfen (optional): `sha256sum -c SHA256SUMS.txt` und `gh attestation verify depesche.zip --repo Celestial0579/depesche`.
3. In Claude (Desktop oder claude.ai): Seitenleiste **Customize** → **Skills** → **+** → **Upload a skill**, dann die Zip wählen.
4. Den Skill in der Liste einschalten. Skills brauchen die Code-Ausführung: bei Einzelplänen unter **Settings → Capabilities**.

Die Release-Zip enthält nur den allgemeinen Teil (Typen, Status, Felder). Eigene Regeln (`R`), Pfade (`$X`) und Wörter fehlen; wer sie braucht, baut die Zip selbst.

**Eigene Zip mit Teamteil** (nur lokal):

1. `./depesche.py skill --zip` baut `skill/depesche.zip` aus Kern und eigenem Teamteil. Der Ordner `skill/` steht in `.gitignore`: Die Zip enthält den privaten Teamteil und gehört in kein Repo und in kein Release.
2. Import wie oben ab Schritt 3.

**Release bauen:** Ein Tag `vX.Y.Z` auf einem Commit von `main` startet `.github/workflows/release.yml`. Der Lauf baut die Zip mit `./depesche.py --kern skill --zip` nur aus dem Kern, bricht ab, wenn sie Teamregeln, -pfade, -wörter oder private Spuren (Benutzerpfade, Sitzungs-IDs, IP- oder Mailadressen) enthält, und legt `depesche.zip`, `SHA256SUMS.txt` und einen Herkunftsnachweis an. Tags mit Bindestrich (`v1.0.0-beta.1`) werden Vorabversionen.

Das Werkzeug prüft beim Bauen die Upload-Regeln aus der Hilfe von Anthropic (Stand 15.11.2026):
- Die Zip enthält den Ordner `depesche/` als Wurzel, darin `SKILL.md`. Der Ordnername gleicht dem `name` im Frontmatter.
- `name`: höchstens 64 Zeichen aus Kleinbuchstaben, Ziffern und `-`, ohne „anthropic“ und „claude“.
- `description`: nicht leer, höchstens 200 Zeichen (claude.ai; die API erlaubt 1024), ohne XML-Tags. Das Werkzeug lehnt spitze Klammern ganz ab.

Quellen: [How to create custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills), [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude), [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

## Dateien

| Datei | Inhalt |
|---|---|
| `glossar-kern.tsv` | allgemeiner Teil: Typen, Status, Felder, Zeichen, Verweise |
| `beispiel/glossar-team.tsv` | Beispiel für den Teamteil mit Regeln, Pfaden und Wörtern |
| `spec.md` | Vorlage der Regeln für die Sitzungen, englisch und knapp |
| `depesche.py` | Übersetzer, Prüfer, Zähler und Skill-Erzeuger, nur Python-Standardbibliothek |
| `tests/` | Tests, laufen in der CI |
| `.github/workflows/release.yml` | baut bei Tags `v*` die öffentliche Zip und das Release |
| `messung/` | die fünf Proben in vier Fassungen und eine leere Datei; Zeilen mit `===` trennen die Proben |

Die Glossare haben die Spalten Code, Art, Deutsch und Englisch. Neue Kürzel kommen nur dort hinein, danach wird die Skill-Datei neu erzeugt. Codes, deren englische Bedeutung der Code selbst ist (`next`, `ci`, `risk`), stehen in `SKILL.md` ohne Erklärung.

**Neue Kürzel** nur, wenn eine Wendung in den Proben mindestens dreimal vorkommt und das Kürzel Tokens spart. Bei der Prüfung am 15.11.2026 erfüllte keine Wendung das. Bestehende Codes bleiben; umbenennen nur mit Alias für den alten Code.

## Werkzeug

```
./depesche.py expand [--en] [DATEI]   # in Klartext übersetzen, Vorgabe Deutsch
./depesche.py check [DATEI ...]       # Aufbau, Codes, Zeichen und Stil prüfen
./depesche.py stats DATEI ...         # Zeichen, Wörter und Zeilen vergleichen
./depesche.py skill [ZIEL|-]          # SKILL.md erzeugen
./depesche.py skill --zip [ZIEL]      # Zip für den Import in Claude, Vorgabe skill/depesche.zip
./depesche.py verify ZIP ...          # Zip prüfen: Aufbau und Upload-Regeln
./depesche.py --kern skill --zip ZIEL # öffentliche Zip nur aus dem Kern, wie im Release
./depesche.py --kern verify ZIP ...   # dazu prüfen, dass nur der Kern drin ist
./depesche.py --team PFAD ...         # anderen Teamteil verwenden
```

Ohne Datei liest das Werkzeug von der Standardeingabe.

Den Teamteil sucht es in `--team`, dann in `$DEPESCHE_TEAM`, dann unter `~/.config/depesche/glossar-team.tsv`. Fehlt eine ausdrücklich genannte Datei, bricht es ab. Ohne eigenen Teamteil nimmt es `beispiel/glossar-team.tsv` und sagt das auf stderr. `skill` ohne `--kern` bricht dann ab, damit nicht still das Beispiel für alle Sitzungen eingerichtet wird; das Beispiel geht dort nur ausdrücklich mit `--team beispiel/glossar-team.tsv`.

`check` meldet **Fehler** (Rückgabewert 1): unbekannter Typ, unbekannte Regel oder unbekannter Pfad, Bericht ohne Status, keine Kopfzeile.

Dazu **Hinweise** (Rückgabewert bleibt 0):
- Bericht mit mehr als sechs Zeilen;
- teure Nicht-ASCII-Zeichen;
- Zeile länger als 160 Zeichen: in `- `-Punkte teilen;
- Zeile, die weder mit Feld, Typ noch `- ` beginnt;
- Tabellenzeile mit zu wenigen Spalten;
- Stil: Artikel und Füllwörter (`the`, `please`, `just` …, deutsch `der`, `bitte`, `mal` …). Die Sprache bestimmt `check` je Nachricht über häufige Funktionswörter. Ausgenommen sind Code, Zitate, Pfade, Verweise und `!!`-Blöcke. Großes `A` gilt als Bezeichnung (`part A`), nicht als Artikel.

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
