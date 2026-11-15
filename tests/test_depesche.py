import contextlib
import io
import os
import sys
import unittest
import unittest.mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)
import depesche  # noqa: E402

BEISPIEL = os.path.join(HIER, "beispiel", "glossar-team.tsv")


class DepescheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = depesche.lade_glossar(BEISPIEL)

    def probe(self, name):
        with open(os.path.join(HIER, "messung", name), encoding="utf-8") as f:
            return depesche.pruefe(f.read(), self.g)

    def test_proben_sind_gueltig(self):
        for name in ("d.txt", "e.txt", "e2.txt"):
            self.assertEqual(self.probe(name)[0], [], name)

    def test_e2_folgt_dem_telegrammstil(self):
        self.assertEqual(self.probe("e2.txt")[1], [])

    def test_e_hat_noch_stilhinweise(self):
        hinweise = self.probe("e.txt")[1]
        self.assertTrue(any(h.startswith("Stil (en)") for h in hinweise))
        self.assertTrue(any("länger als" in h for h in hinweise))

    def test_stil_englisch(self):
        _, hinweise = depesche.pruefe("DP1 DO fix\n- please just check the updater, part A first\n", self.g)
        stil = [h for h in hinweise if h.startswith("Stil (en)")]
        self.assertEqual(len(stil), 1)
        self.assertIn("please, just, the", stil[0])
        self.assertNotIn(" a,", stil[0])

    def test_stil_deutsch(self):
        _, hinweise = depesche.pruefe("DP1 DO fix\n- bitte den Updater prüfen und dann mal bauen\n", self.g)
        self.assertTrue(any(h.startswith("Stil (de): bitte, den, mal") for h in hinweise))

    def test_stil_ignoriert_code_zitate_pfade(self):
        text = 'DP1 DO fix\n- run `git log --the a` + send "the end", see a/the/x.md\n'
        self.assertEqual(depesche.pruefe(text, self.g)[1], [])

    def test_klartext_ohne_stilpruefung(self):
        text = "DP1 FYI risk\n!!\nThe script deletes the whole disk. Please confirm.\n\nnext wait\n"
        self.assertEqual(depesche.pruefe(text, self.g)[1], [])

    def test_lange_zeile_und_zeilenanfang(self):
        text = "DP1 DO x\n- " + "word " * 40 + "\nsomething without field\n"
        fehler, hinweise = depesche.pruefe(text, self.g)
        self.assertEqual(fehler, [])
        self.assertTrue(any("länger als 160" in h for h in hinweise))
        self.assertTrue(any("weder mit Feld" in h for h in hinweise))

    def test_hinweise_aendern_rueckgabewert_nicht(self):
        class A:
            datei = []
        with contextlib.redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stdin", io.StringIO("DP1 DO x\n- the a\n")):
            self.assertEqual(depesche.check(A, self.g), 0)
        with contextlib.redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stdin", io.StringIO("DP1 XX\n")):
            self.assertEqual(depesche.check(A, self.g), 1)

    def test_tabelle_letzte_spalte_nimmt_rest(self):
        u = depesche.Uebersetzer(self.g, "de")
        zeilen = u.block(["T repo,note", "a,ok, CI green, 2 PRs"])
        self.assertEqual(zeilen[1], "  repo=a, note=ok, CI green, 2 PRs")
        _, hinweise = depesche.pruefe("DP1 FYI x\nT repo,ci,note\na,ok\n", self.g)
        self.assertTrue(any("weniger als 3 Spalten" in h for h in hinweise))

    def test_backticks_bleiben_woertlich(self):
        u = depesche.Uebersetzer(self.g, "de")
        self.assertEqual(u.text("`echo $N R push` + $N"), "`echo $N R push` + ~/notizen/teamleiter")
        fehler, _ = depesche.pruefe("DP1 DO x\n- run `echo $Q R xyz`\n", self.g)
        self.assertEqual(fehler, [])

    def test_kennung_im_klartext_beginnt_keine_nachricht(self):
        b = depesche.bloecke("DP1 FYI x\n!!\nDP1 is just a word here.\n\nnext y\n")
        self.assertEqual(len(b), 1)

    def test_trennzeile_gehoert_zu_keiner_nachricht(self):
        b = depesche.bloecke("=== S1\nDP1 GO vm\n=== S2\nDP1 GO x\n")
        self.assertEqual([k for k, _ in b], [None, "DP1 GO vm", None, "DP1 GO x"])

    def test_stats_mit_leerer_erster_datei(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            leer, voll = os.path.join(d, "0"), os.path.join(d, "1")
            open(leer, "w").close()
            with open(voll, "w") as f:
                f.write("DP1 GO x\n")

            class A:
                datei = [leer, voll]
            with contextlib.redirect_stdout(io.StringIO()) as aus:
                depesche.stats(A, self.g)
        self.assertIn("0 Zeichen", aus.getvalue())

    def test_fehler_werden_erkannt(self):
        fehler, hinweise = depesche.pruefe("DP1 REP\nR push,xyz\nsiehe $Q → fertig\n", self.g)
        self.assertTrue(any("REP ohne Status" in f for f in fehler))
        self.assertTrue(any("'xyz'" in f for f in fehler))
        self.assertTrue(any("$Q" in f for f in fehler))
        self.assertTrue(any("U+2192" in h for h in hinweise))

    def test_ohne_kopfzeile(self):
        fehler, _ = depesche.pruefe("nur Text\n", self.g)
        self.assertTrue(fehler)

    def test_kopfzeile_wird_uebersetzt(self):
        u = depesche.Uebersetzer(self.g, "de")
        self.assertEqual(u.kopfzeile("DP1 REP part #46 !"), "[DP1] Bericht – teilweise erledigt: #46 (dringend)")
        self.assertEqual(depesche.Uebersetzer(self.g, "en").kopfzeile("DP1 GO vm"), "[DP1] go-ahead: vm")

    def test_regeln_und_pfade_werden_ausgeschrieben(self):
        u = depesche.Uebersetzer(self.g, "de")
        zeilen = u.block(["R push", "- siehe $N/plan.md. R vm", "T repo,ci", "a,ok"])
        self.assertIn("Vor dem Push lokal bauen", zeilen[0])
        self.assertIn("~/notizen/teamleiter/plan.md", zeilen[1])
        self.assertIn("Nur eine VM zur Zeit", zeilen[1])
        self.assertEqual(zeilen[3], "  repo=a, ci=ok")

    def test_klartext_bleibt_woertlich(self):
        u = depesche.Uebersetzer(self.g, "de")
        zeilen = u.block(["!!", "Das Löschen von R push ist endgültig.", "", "did x"])
        self.assertEqual(zeilen[1], "    Das Löschen von R push ist endgültig.")
        self.assertEqual(zeilen[3], "Erledigt: x")

    def test_skill_enthaelt_glossar(self):
        class A:
            ziel, team = "-", BEISPIEL
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            depesche.skill(A, self.g)
        text = puffer.getvalue()
        self.assertTrue(text.startswith("---\nname: depesche\n"))
        self.assertIn("- rules: push=", text)
        self.assertIn("; next;", text)  # Code ohne eigene Erklärung
        self.assertLess(len(text), 2600)
        self.assertNotIn("{{", text)


if __name__ == "__main__":
    unittest.main()
