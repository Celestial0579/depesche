#!/usr/bin/env python3
"""Depesche: Übersetzer und Prüfer für kompakte Nachrichten zwischen Claude-Sitzungen.

Aufrufe:
  depesche.py expand [--en] [DATEI]   Nachrichten in Klartext übersetzen (Vorgabe Deutsch)
  depesche.py check [DATEI ...]       Aufbau, Codes, Zeichen und Stil prüfen, Rückgabe 1 nur bei Fehlern
  depesche.py stats DATEI ...         Zeichen, Wörter und Zeilen zählen
  depesche.py skill [ZIEL|-]          SKILL.md erzeugen, Vorgabe ~/.claude/skills/depesche/SKILL.md
  depesche.py skill --zip [ZIEL]      Zip für den Import in Claude Desktop, Vorgabe skill/depesche.zip
  depesche.py verify ZIP ...          Skill-Zip prüfen: Aufbau und Upload-Regeln
  depesche.py privat [DATEI ...]      Proben auf private Spuren prüfen, Rückgabe 1 bei Funden
  depesche.py --kern skill --zip ZIEL öffentlicher Build nur aus dem Kern, bricht bei Teamteil oder privaten Spuren ab
Ohne DATEI liest das Werkzeug von der Standardeingabe. Es braucht nur die Python-Standardbibliothek.

Der Teamteil (eigene Regeln, Pfade, Wörter) kommt aus --team, sonst aus $DEPESCHE_TEAM,
sonst aus ~/.config/depesche/glossar-team.tsv. Fehlt eine ausdrücklich genannte Datei, bricht das
Werkzeug ab. Ohne eigenen Teamteil nimmt es beispiel/glossar-team.tsv und sagt das auf stderr;
skill ohne --kern braucht dann ausdrücklich --team beispiel/glossar-team.tsv.
"""
import argparse
import os
import re
import sys
import unicodedata

HIER = os.path.dirname(os.path.abspath(__file__))
NAME = "Depesche"
KENNUNG = "DP1"  # steht am Anfang jeder Nachricht
KERN = os.path.join(HIER, "glossar-kern.tsv")
TEAM_EIGEN = os.path.expanduser("~/.config/depesche/glossar-team.tsv")
BEISPIEL = os.path.join(HIER, "beispiel", "glossar-team.tsv")
SKILL_ZIEL = os.path.expanduser("~/.claude/skills/depesche/SKILL.md")


def team_datei(angabe=None, beispiel_erlaubt=True):
    """Pfad zum Teamteil. Ausdrücklich genannt (--team, $DEPESCHE_TEAM) muss er da sein, sonst Abbruch.
    Ohne eigenen Teamteil das Beispiel nur mit beispiel_erlaubt, und mit Hinweis auf stderr."""
    for quelle, p in (("--team", angabe), ("DEPESCHE_TEAM", os.environ.get("DEPESCHE_TEAM"))):
        if p:
            if not os.path.isfile(p):
                sys.exit(f"Teamteil aus {quelle} nicht gefunden: {p}")
            return p
    if os.path.isfile(TEAM_EIGEN):
        return TEAM_EIGEN
    if beispiel_erlaubt:
        print(f"Hinweis: kein eigener Teamteil, nutze das Beispiel {BEISPIEL}", file=sys.stderr)
        return BEISPIEL
    sys.exit("kein eigener Teamteil (--team, DEPESCHE_TEAM oder ~/.config/depesche/glossar-team.tsv); "
             "das Beispiel nur ausdrücklich mit --team beispiel/glossar-team.tsv")

REGEL_IM_TEXT = re.compile(r"(?<![\w$])R ([a-z]+(?:,[a-z]+)*)\b")
PFAD = re.compile(r"\$[A-Z]\b")
WORTE = {"de": ("dringend", "Klartext (kritisch, genau lesen):", "Regel"),
         "en": ("urgent", "Plain text (critical, read exactly):", "rule")}
WOERTLICH = re.compile(r"`[^`]*`|\"[^\"]*\"")  # Code und Zitate: nichts ausschreiben, nichts bemängeln
TRENNER = "==="  # Zeilen mit === am Anfang trennen Proben in einer Datei (messung/)
MAX_ZEILE = 160  # längere Freitextzeilen meldet check: lieber in "- "-Punkte teilen
# Telegrammstil: Artikel und Füllwörter je Sprache. Die Sprache bestimmt check je Nachricht über MARKER.
STIL = {  # Sprache: (Artikel, Füllwörter, Füllphrasen)
    "en": ("a an the".split(),
           "please kindly just really very basically actually simply quite maybe perhaps probably somewhat "
           "thanks thank sorry hello hi".split(),
           ["i think", "i believe", "it seems", "in order to", "as mentioned", "note that", "of course"]),
    "de": ("der die das den dem des ein eine einen einem einer eines".split(),
           "bitte eigentlich einfach eben mal wohl vielleicht doch gerne danke schon ziemlich quasi sozusagen "
           "eventuell".split(),
           ["ich denke", "ich glaube", "im grunde", "an sich"]),
}
MARKER = {"en": set("and not is are with for to of on after or if then also only was be".split()),
          "de": set("und nicht ist sind mit für zu auf nach oder wenn dann auch nur noch bei vor kein keine".split())}


def lade_glossar(team=None, nur_kern=False, beispiel_erlaubt=True):
    """Kern plus Teamteil; nur_kern=True lässt den Teamteil weg (öffentlicher Build)."""
    g = {}
    for datei in (KERN,) if nur_kern else (KERN, team_datei(team, beispiel_erlaubt)):
        with open(datei, encoding="utf-8") as f:
            for nr, zeile in enumerate(f, 1):
                zeile = zeile.rstrip("\n")
                if not zeile.strip() or zeile.startswith("#"):
                    continue
                teile = zeile.split("\t")
                if len(teile) < 3:
                    sys.exit(f"{datei}:{nr}: erwartet Code<TAB>Art<TAB>Deutsch[<TAB>Englisch]")
                code, art, de = teile[:3]
                en = teile[3] if len(teile) > 3 and teile[3] else de
                g.setdefault(art, {})[code] = {"de": de, "en": en}
    for art in ("typ", "status", "feld", "regel", "pfad"):
        g.setdefault(art, {})
    return g


def bloecke(text):
    """Teilt den Text in Blöcke [kopfzeile, zeilen]. Zeilen vor der ersten Kopfzeile haben kopfzeile None."""
    erg, klartext = [], False
    for zeile in text.splitlines():
        s = zeile.strip()
        if klartext:  # im !!-Block beginnt keine neue Nachricht, er endet an einer Leerzeile
            klartext = bool(s)
            erg[-1][1].append(zeile)
        elif zeile == KENNUNG or zeile.startswith(KENNUNG + " "):
            erg.append([zeile, []])
        elif zeile.startswith(TRENNER):  # Trennzeile zwischen Proben, gehört zu keiner Nachricht
            erg.append([None, [zeile]])
        elif s == "!!" and erg and erg[-1][0] is not None:
            klartext = True
            erg[-1][1].append(zeile)
        elif not erg or erg[-1][0] is None:
            if not erg:
                erg.append([None, []])
            erg[-1][1].append(zeile)
        else:
            erg[-1][1].append(zeile)
    return erg


def kopf(zeile, g):
    teile = zeile.split()[1:]
    typ = teile[0] if teile else ""
    rest = teile[1:]
    status = ""
    if typ == "REP" and rest and rest[0] in g["status"]:
        status, rest = rest[0], rest[1:]
    dringend = bool(rest) and rest[-1] == "!"
    if dringend:
        rest = rest[:-1]
    return typ, status, " ".join(rest), dringend


def ausserhalb_woertlich(s, fn):
    """Wendet fn nur auf die Teile von s an, die nicht in `Backticks` oder "Anführungszeichen" stehen."""
    aus, pos = [], 0
    for m in WOERTLICH.finditer(s):
        aus += [fn(s[pos:m.start()]), m.group(0)]
        pos = m.end()
    return "".join(aus + [fn(s[pos:])])


def ohne_woertlich(s):
    return WOERTLICH.sub(" ", s)


def tabellenzeile(spalten, s):
    """Die letzte Spalte nimmt den Rest der Zeile, Kommas darin bleiben erhalten."""
    return [w.strip() for w in s.split(",", len(spalten) - 1)]


class Uebersetzer:
    def __init__(self, g, sp):
        self.g, self.sp = g, sp

    def regeln(self, codes):
        teile = []
        for c in codes:
            r = self.g["regel"].get(c)
            teile.append(f"{c} ({r[self.sp]})" if r else f"{c} (?)")
        return "; ".join(teile)

    def text(self, s):
        def regel(m):
            codes = m.group(1).split(",")
            if all(c in self.g["regel"] for c in codes):
                return f"{WORTE[self.sp][2]} {self.regeln(codes)}"
            return m.group(0)

        def frei(t):
            t = PFAD.sub(lambda m: self.g["pfad"].get(m.group(0), {}).get("de", m.group(0)), t)
            return REGEL_IM_TEXT.sub(regel, t)

        return ausserhalb_woertlich(s, frei)

    def kopfzeile(self, zeile):
        typ, status, betreff, dringend = kopf(zeile, self.g)
        s = self.g["typ"].get(typ, {}).get(self.sp, f"? {typ}")
        if status:
            s += " – " + self.g["status"][status][self.sp]
        if betreff:
            s += ": " + self.text(betreff)
        if dringend:
            s += f" ({WORTE[self.sp][0]})"
        return f"[{KENNUNG}] {s}"

    def block(self, zeilen):
        aus, klartext, spalten = [], False, None
        for z in zeilen:
            s = z.strip()
            if klartext:
                if not s:
                    klartext = False
                aus.append("    " + z if s else "")
                continue
            if not s:
                spalten = None
                aus.append("")
                continue
            wort, _, rest = s.partition(" ")
            if s == "!!":
                klartext = True
                aus.append(WORTE[self.sp][1])
            elif s.startswith("- "):
                spalten = None
                aus.append("  • " + self.text(s[2:]))
            elif wort == "R":
                aus.append(f"{self.g['feld']['R'][self.sp]}: {self.regeln([c for c in re.split(r'[ ,]+', rest) if c])}")
            elif wort == "T":
                spalten = [c.strip() for c in rest.split(",")]
                aus.append(f"{self.g['feld']['T'][self.sp]} ({', '.join(spalten)}):")
            elif spalten and "," in s and wort not in self.g["feld"] and wort not in self.g["typ"]:
                werte = tabellenzeile(spalten, s)
                aus.append("  " + ", ".join(f"{k}={v}" for k, v in zip(spalten, werte)))
            elif wort in self.g["feld"]:
                spalten = None
                aus.append(f"{self.g['feld'][wort][self.sp]}: {self.text(rest)}")
            elif wort in self.g["typ"]:
                spalten = None
                aus.append(f"{self.g['typ'][wort][self.sp]}: {self.text(rest)}")
            else:
                aus.append(self.text(s))
        return aus


def lies(dateien):
    if not dateien:
        return [("-", sys.stdin.read())]
    erg = []
    for d in dateien:
        with open(d, encoding="utf-8") as f:
            erg.append((d, f.read()))
    return erg


def expand(args, g):
    u = Uebersetzer(g, "en" if args.en else "de")
    for _, text in lies(args.datei):
        for kopfz, zeilen in bloecke(text):
            if kopfz is None:
                print("\n".join(zeilen))
                continue
            print(u.kopfzeile(kopfz))
            for z in u.block(zeilen):
                print(z)


def sprache(zeilen):
    """Schätzt die Sprache des Freitexts über häufige Funktionswörter: "de" oder "en"."""
    woerter = re.findall(r"[a-zäöüß]+", " ".join(ohne_woertlich(z) for z in zeilen).lower())
    return "de" if sum(w in MARKER["de"] for w in woerter) > sum(w in MARKER["en"] for w in woerter) else "en"


def stil(s, sp):
    """Artikel und Füllwörter in einer Freitextzeile, ohne Code, Zitate, Pfade und Verweise."""
    frei = " ".join(w for w in ohne_woertlich(s).split() if not re.search(r"[/\\#@$]", w))
    artikel, fuell, phrasen = STIL[sp]
    woerter = re.findall(r"[A-Za-zÄÖÜäöüß]+", frei)
    # großes "A" ist meist eine Bezeichnung (part A, Antwort A), kein Artikel
    funde = [w.lower() for w in woerter if (w.lower() in artikel and w != "A") or w.lower() in fuell]
    funde += [ph for ph in phrasen if re.search(rf"\b{ph}\b", frei.lower())]
    return sorted(set(funde), key=funde.index)


def pruefe(text, g):
    fehler, hinweise = [], []
    nachrichten = [b for b in bloecke(text) if b[0] is not None]
    if not nachrichten:
        fehler.append(f"keine Kopfzeile mit {KENNUNG} gefunden")
    for kopfz, zeilen in nachrichten:
        typ, status, _, _ = kopf(kopfz, g)
        if typ not in g["typ"]:
            fehler.append(f"unbekannter Typ {typ!r}: {kopfz}")
        if typ == "REP" and not status:
            fehler.append(f"REP ohne Status ({'|'.join(g['status'])}): {kopfz}")
        if typ == "REP" and len([z for z in zeilen if z.strip()]) > 6:
            hinweise.append(f"REP mit mehr als 6 Zeilen: {kopfz}")
        alles = "\n".join([kopfz] + zeilen)
        for p in sorted(set(PFAD.findall(ohne_woertlich(alles))) - set(g["pfad"])):
            fehler.append(f"unbekannter Pfad {p}: {kopfz}")
        sp = sprache([kopfz] + zeilen)
        klartext, spalten = False, None
        for nr, z in enumerate([kopfz] + zeilen):
            s = z.strip()
            if klartext:  # ganze Sätze sind hier gewollt, Codes werden nicht ausgeschrieben
                klartext = bool(s)
                continue
            if not s:
                spalten = None
                continue
            frei = ohne_woertlich(s)
            wort = s.split()[0]
            codes = []
            if wort == "R":
                codes = [c for c in re.split(r"[ ,]+", frei[2:]) if c]
            else:
                for m in REGEL_IM_TEXT.finditer(frei):
                    codes += m.group(1).split(",")
            for c in codes:
                if c not in g["regel"]:
                    fehler.append(f"unbekannte Regel {c!r}: {s}")
            if s == "!!":
                klartext = True
                continue
            if nr and wort == "T":
                spalten = [c.strip() for c in s[2:].split(",")]
                continue
            if nr and spalten and wort not in g["feld"] and wort not in g["typ"]:
                if s.count(",") < len(spalten) - 1:
                    hinweise.append(f"Tabellenzeile mit weniger als {len(spalten)} Spalten: {s}")
                continue
            spalten = None
            if nr and wort not in g["feld"] and wort not in g["typ"] and not s.startswith("- "):
                hinweise.append(f"Zeile beginnt weder mit Feld, Typ noch '- ': {s}")
            if len(s) > MAX_ZEILE:
                hinweise.append(f"Zeile länger als {MAX_ZEILE} Zeichen ({len(s)}), in '- '-Punkte teilen: {s[:60]}...")
            funde = stil(s, sp)
            if funde:
                hinweise.append(f"Stil ({sp}): {', '.join(funde)} streichen: {s}")
        teuer = sorted({ch for ch in alles if ord(ch) > 127 and not unicodedata.category(ch).startswith("L")})
        for ch in teuer:
            hinweise.append(f"Zeichen {ch!r} (U+{ord(ch):04X}) kostet meist mehr Tokens als ASCII: {kopfz}")
    return fehler, hinweise


def check(args, g):
    rc = 0
    for name, text in lies(args.datei):
        fehler, hinweise = pruefe(text, g)
        for f in fehler:
            print(f"{name}: FEHLER {f}")
        for h in hinweise:
            print(f"{name}: Hinweis {h}")
        if not fehler and not hinweise:
            print(f"{name}: ok")
        rc |= bool(fehler)
    return rc


def stats(args, g):
    basis = None
    for name, text in lies(args.datei):
        z = len(text)
        basis = z if basis is None else basis
        anteil = f", {z / basis:.0%} der ersten Datei" if basis else ""
        print(f"{name}: {z} Zeichen, {len(text.split())} Wörter, {text.count(chr(10))} Zeilen{anteil}")


# Upload-Regeln für Skills in Claude (claude.ai, Claude Desktop), Stand 15.11.2026:
# Zip mit dem Skill-Ordner als Wurzel, Ordnername = name; name höchstens 64 Zeichen aus a-z, 0-9 und -,
# ohne "anthropic" und "claude"; description nicht leer, höchstens 200 Zeichen (Hilfe-Center, die API
# erlaubt 1024), ohne XML-Tags. Spitze Klammern meidet das Werkzeug ganz.
NAME_MAX, BESCHREIBUNG_MAX = 64, 200
ZIP_ZIEL = os.path.join(HIER, "skill", NAME.lower() + ".zip")


def skill_text(g):
    def reihe(art, sp="en"):
        # Codes, die ihre eigene Bedeutung sind (next=next, ci=CI), stehen ohne Erklärung da
        return "; ".join(c if v[sp].lower() == c.lower() else f"{c}={v[sp]}" for c, v in g.get(art, {}).items())

    zeilen = [("TYPE", reihe("typ")), ("status", reihe("status")), ("fields", reihe("feld")),
              ("rules", reihe("regel")), ("paths", reihe("pfad", "de")), ("words", reihe("wort"))]
    glossar = "\n".join(f"- {titel}: {inhalt}" for titel, inhalt in zeilen if inhalt)
    with open(os.path.join(HIER, "spec.md"), encoding="utf-8") as f:
        text = f.read()
    text = text.replace("{{NAME}}", NAME).replace("{{KENNUNG}}", KENNUNG).replace("{{GLOSSAR}}", glossar)
    kopfteil = (f"---\nname: {NAME.lower()}\ndescription: {NAME} ({KENNUNG}) compact message protocol between team-lead "
                f"and staff Claude sessions. Use for every SendMessage between them and to read messages starting "
                f"{KENNUNG}.\n---\n\n")
    return kopfteil + text


def pruefe_skill(text, ordner):
    """Prüft SKILL.md gegen die Upload-Regeln. Gibt eine Liste von Fehlern zurück."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["SKILL.md beginnt nicht mit YAML-Frontmatter (---)"]
    felder = dict(z.split(": ", 1) for z in m.group(1).splitlines() if ": " in z)
    name, beschreibung = felder.get("name", ""), felder.get("description", "")
    fehler = []
    if not re.fullmatch(r"[a-z0-9-]{1,%d}" % NAME_MAX, name):
        fehler.append(f"name {name!r}: 1-{NAME_MAX} Zeichen aus a-z, 0-9, -")
    if "anthropic" in name.lower() or "claude" in name.lower():
        fehler.append(f"name {name!r} darf anthropic oder claude nicht enthalten")
    if name != ordner:
        fehler.append(f"name {name!r} muss dem Ordnernamen {ordner!r} gleichen")
    if not beschreibung or len(beschreibung) > BESCHREIBUNG_MAX:
        fehler.append(f"description: 1-{BESCHREIBUNG_MAX} Zeichen, hat {len(beschreibung)}")
    if re.search(r"[<>]", beschreibung):
        fehler.append("description ohne spitze Klammern (XML-Tags verboten)")
    return fehler


# Öffentlicher Build: nur Kern-Codes im Glossar, keine privaten Spuren. Namen prüft die Liste nicht,
# sie stünden sonst selbst im Repo; der Kern-Abgleich schließt Teamregeln, -pfade und -wörter aus.
PRIVAT = [(re.compile(r"~/|/home/|/Users/|[A-Za-z]:\\Users\\"), "Benutzerpfad"),
          (re.compile(r"\blocal_[0-9a-f]{8}"), "Sitzungs-ID"),
          (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "IP-Adresse"),
          (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "Mailadresse"),
          (re.compile(r"\$[A-Z]="), "Pfadcode")]
# Platzhalter in den Proben (messung/): Beispielpfad des Teamteils und eine genullte Sitzungs-ID
PLATZHALTER = ("~/notizen/teamleiter", "local_00000000")


def private_spuren(text):
    """(Zeile, Art, Treffer) je privater Spur nach PRIVAT, Platzhalter ausgenommen."""
    funde = []
    for muster, was in PRIVAT:
        for m in muster.finditer(text):
            if not any(text.startswith(p, m.start()) for p in PLATZHALTER):
                funde.append((text.count("\n", 0, m.start()) + 1, was, m.group(0)))
    return sorted(funde)


def privat(args, g):
    """Proben auf private Spuren prüfen: Benutzerpfade, Sitzungs-IDs, IP- und Mailadressen."""
    rc = 0
    for name, text in lies(args.datei):
        funde = private_spuren(text)
        for zeile, was, treffer in funde:
            print(f"{name}:{zeile}: {was} {treffer!r}")
        if not funde:
            print(f"{name}: ok")
        rc |= bool(funde)
    return rc


def pruefe_oeffentlich(text):
    """Fehlerliste, wenn SKILL.md mehr als den Kern enthält oder private Spuren trägt."""
    with open(KERN, encoding="utf-8") as f:
        kern = {z.split("\t")[0] for z in f if z.strip() and not z.startswith("#")}
    fehler = []
    glossar = text.split("\nGlossary\n", 1)[1] if "\nGlossary\n" in text else ""
    for zeile in glossar.splitlines():
        titel, _, inhalt = zeile.partition(": ")
        if titel not in ("- TYPE", "- status", "- fields"):
            fehler.append(f"Glossarzeile außerhalb des Kerns: {titel or zeile!r}")
            continue
        for eintrag in inhalt.split("; "):
            code = eintrag.split("=", 1)[0]
            if code not in kern:
                fehler.append(f"Code {code!r} steht nicht im Kern")
    for muster, was in PRIVAT:
        for m in muster.finditer(text):
            fehler.append(f"{was}: {m.group(0)!r}")
    return fehler


def lies_zip(pfad):
    """Liest eine Skill-Zip; gibt (SKILL.md-Text, Fehlerliste zum Aufbau) zurück."""
    import zipfile
    ordner = NAME.lower()
    with zipfile.ZipFile(pfad) as z:
        namen = z.namelist()
        fehler = [] if namen == [ordner + "/", ordner + "/SKILL.md"] else [f"Zip-Inhalt {namen}, erwartet {ordner}/ und {ordner}/SKILL.md"]
        text = z.read(ordner + "/SKILL.md").decode("utf-8") if ordner + "/SKILL.md" in namen else ""
    return text, fehler


def schreibe_zip(text, ziel):
    """Zip mit dem Ordner NAME/ als Wurzel und SKILL.md darin, feste Zeitstempel für gleiche Bytes."""
    import zipfile
    ordner = NAME.lower()
    fehler = pruefe_skill(text, ordner)
    if fehler:
        sys.exit("Skill entspricht nicht den Upload-Regeln:\n" + "\n".join(fehler))
    os.makedirs(os.path.dirname(os.path.abspath(ziel)), exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(ordner + "/", (1980, 1, 1, 0, 0, 0)), "")
        info = zipfile.ZipInfo(ordner + "/SKILL.md", (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, text.encode("utf-8"))


def skill(args, g):
    text = skill_text(g)
    if getattr(args, "kern", False):
        fehler = pruefe_oeffentlich(text)
        if fehler:
            sys.exit("öffentlicher Build enthält mehr als den Kern:\n" + "\n".join(fehler))
    if getattr(args, "zip", False):
        ziel = args.ziel or ZIP_ZIEL
        schreibe_zip(text, ziel)
        print(f"geschrieben: {ziel} (Ordner {NAME.lower()}/, {teil(args)})")
        return
    fehler = pruefe_skill(text, NAME.lower())
    if fehler:
        sys.exit("Skill entspricht nicht den Upload-Regeln:\n" + "\n".join(fehler))
    if args.ziel == "-":
        sys.stdout.write(text)
        return
    ziel = args.ziel or SKILL_ZIEL
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"geschrieben: {ziel} ({len(text)} Zeichen, {teil(args)})")


def teil(args):
    return "nur Kern" if getattr(args, "kern", False) else f"Teamteil {team_datei(args.team, False)}"


def verify(args, g):
    """Prüft fertige Skill-Zips: Aufbau, Upload-Regeln, mit --kern auch öffentlich."""
    rc = 0
    for pfad in args.datei:
        text, fehler = lies_zip(pfad)
        if text:
            fehler += pruefe_skill(text, NAME.lower())
            if args.kern:
                fehler += pruefe_oeffentlich(text)
        for f in fehler:
            print(f"{pfad}: {f}")
        if fehler:
            rc = 1
        else:
            print(f"{pfad}: ok ({'öffentlich, nur Kern' if args.kern else 'Aufbau und Upload-Regeln'})")
    return rc


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--team", help="Pfad zum Teamteil (glossar-team.tsv)")
    p.add_argument("--kern", action="store_true", help="nur allgemeiner Teil, ohne Teamteil (öffentlicher Build)")
    sub = p.add_subparsers(dest="befehl", required=True)
    e = sub.add_parser("expand", help="in Klartext übersetzen")
    e.add_argument("--en", action="store_true", help="englischer Klartext statt deutschem")
    e.add_argument("datei", nargs="*")
    c = sub.add_parser("check", help="Aufbau und Codes prüfen")
    c.add_argument("datei", nargs="*")
    s = sub.add_parser("stats", help="Zeichen und Wörter zählen")
    s.add_argument("datei", nargs="+")
    k = sub.add_parser("skill", help="SKILL.md oder Zip für den Import in Claude erzeugen")
    k.add_argument("--zip", action="store_true", help="Zip für Claude Desktop/claude.ai, Vorgabe skill/depesche.zip")
    k.add_argument("ziel", nargs="?", help="Zieldatei oder - für die Standardausgabe")
    v = sub.add_parser("verify", help="Skill-Zip prüfen (mit --kern: öffentlich, nur Kern)")
    v.add_argument("datei", nargs="+")
    pv = sub.add_parser("privat", help="Proben auf private Spuren prüfen (Pfade, Sitzungs-IDs, IP, Mail)")
    pv.add_argument("datei", nargs="*")
    args = p.parse_args()
    # skill richtet die Depesche für alle neuen Sitzungen ein: das Beispiel dort nur ausdrücklich
    g = None if args.befehl == "privat" else lade_glossar(
        args.team, args.kern, beispiel_erlaubt=not (args.befehl == "skill" and not args.kern))
    rc = {"expand": expand, "check": check, "stats": stats, "skill": skill, "verify": verify,
          "privat": privat}[args.befehl](args, g)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
