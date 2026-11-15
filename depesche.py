#!/usr/bin/env python3
"""Depesche: Übersetzer und Prüfer für kompakte Nachrichten zwischen Claude-Sitzungen.

Aufrufe:
  depesche.py expand [--en] [DATEI]   Nachrichten in Klartext übersetzen (Vorgabe Deutsch)
  depesche.py check [DATEI ...]       Kopfzeile, Codes und Zeichen prüfen, Rückgabe 1 bei Fehlern
  depesche.py stats DATEI ...         Zeichen, Wörter und Zeilen zählen
  depesche.py skill [ZIEL|-]          SKILL.md erzeugen, Vorgabe ~/.claude/skills/depesche/SKILL.md
Ohne DATEI liest das Werkzeug von der Standardeingabe. Es braucht nur die Python-Standardbibliothek.

Der Teamteil (eigene Regeln, Pfade, Wörter) kommt aus --team, sonst aus $DEPESCHE_TEAM,
sonst aus ~/.config/depesche/glossar-team.tsv, sonst aus beispiel/glossar-team.tsv.
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
TEAM_ORTE = (os.path.expanduser("~/.config/depesche/glossar-team.tsv"),
             os.path.join(HIER, "beispiel", "glossar-team.tsv"))
SKILL_ZIEL = os.path.expanduser("~/.claude/skills/depesche/SKILL.md")


def team_datei(angabe=None):
    for p in (angabe, os.environ.get("DEPESCHE_TEAM")) + TEAM_ORTE:
        if p and os.path.isfile(p):
            return p
    sys.exit("kein Teamteil gefunden (--team, DEPESCHE_TEAM oder ~/.config/depesche/glossar-team.tsv)")

REGEL_IM_TEXT = re.compile(r"(?<![\w$])R ([a-z]+(?:,[a-z]+)*)\b")
PFAD = re.compile(r"\$[A-Z]\b")
WORTE = {"de": ("dringend", "Klartext (kritisch, genau lesen):", "Regel"),
         "en": ("urgent", "Plain text (critical, read exactly):", "rule")}


def lade_glossar(team=None):
    g = {}
    for datei in (KERN, team_datei(team)):
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
    erg = []
    for zeile in text.splitlines():
        if zeile == KENNUNG or zeile.startswith(KENNUNG + " "):
            erg.append([zeile, []])
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
        s = PFAD.sub(lambda m: self.g["pfad"].get(m.group(0), {}).get("de", m.group(0)), s)

        def regel(m):
            codes = m.group(1).split(",")
            if all(c in self.g["regel"] for c in codes):
                return f"{WORTE[self.sp][2]} {self.regeln(codes)}"
            return m.group(0)

        return REGEL_IM_TEXT.sub(regel, s)

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
                werte = [w.strip() for w in s.split(",")]
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
    return [(d, open(d, encoding="utf-8").read()) for d in dateien]


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
        for p in sorted(set(PFAD.findall(alles)) - set(g["pfad"])):
            fehler.append(f"unbekannter Pfad {p}: {kopfz}")
        for z in [kopfz] + zeilen:
            s = z.strip()
            codes = []
            if s.startswith("R "):
                codes = [c for c in re.split(r"[ ,]+", s[2:]) if c]
            else:
                for m in REGEL_IM_TEXT.finditer(s):
                    codes += m.group(1).split(",")
            for c in codes:
                if c not in g["regel"]:
                    fehler.append(f"unbekannte Regel {c!r}: {s}")
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
        basis = basis or z
        print(f"{name}: {z} Zeichen, {len(text.split())} Wörter, {text.count(chr(10))} Zeilen, {z / basis:.0%} der ersten Datei")


def skill(args, g):
    def reihe(art):
        return " | ".join(f"{c}={v['en']}" for c, v in g.get(art, {}).items())

    glossar = "\n".join([
        "- TYPE: " + reihe("typ"),
        "- status: " + reihe("status"),
        "- fields: " + reihe("feld"),
        "- rules: " + reihe("regel"),
        "- paths: " + " | ".join(f"{c}={v['de']}" for c, v in g["pfad"].items()),
        "- words: " + reihe("wort"),
    ])
    with open(os.path.join(HIER, "spec.md"), encoding="utf-8") as f:
        text = f.read()
    text = text.replace("{{NAME}}", NAME).replace("{{KENNUNG}}", KENNUNG).replace("{{GLOSSAR}}", glossar)
    kopfteil = (f"---\nname: {NAME.lower()}\ndescription: {NAME} ({KENNUNG}) compact message protocol between team-lead "
                f"and staff Claude sessions. Use for every SendMessage between team lead and staff sessions and to read "
                f"messages starting with {KENNUNG}.\n---\n\n")
    if args.ziel == "-":
        sys.stdout.write(kopfteil + text)
        return
    ziel = args.ziel or SKILL_ZIEL
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with open(ziel, "w", encoding="utf-8") as f:
        f.write(kopfteil + text)
    print(f"geschrieben: {ziel} ({len(kopfteil + text)} Zeichen, Teamteil {team_datei(args.team)})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--team", help="Pfad zum Teamteil (glossar-team.tsv)")
    sub = p.add_subparsers(dest="befehl", required=True)
    e = sub.add_parser("expand", help="in Klartext übersetzen")
    e.add_argument("--en", action="store_true", help="englischer Klartext statt deutschem")
    e.add_argument("datei", nargs="*")
    c = sub.add_parser("check", help="Aufbau und Codes prüfen")
    c.add_argument("datei", nargs="*")
    s = sub.add_parser("stats", help="Zeichen und Wörter zählen")
    s.add_argument("datei", nargs="+")
    k = sub.add_parser("skill", help="SKILL.md erzeugen")
    k.add_argument("ziel", nargs="?", help="Zieldatei oder - für die Standardausgabe")
    args = p.parse_args()
    g = lade_glossar(args.team)
    rc = {"expand": expand, "check": check, "stats": stats, "skill": skill}[args.befehl](args, g)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
