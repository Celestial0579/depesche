import contextlib
import io
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)
import depesche  # noqa: E402

BEISPIEL = os.path.join(HIER, "beispiel", "glossar-team.tsv")


class DepescheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = depesche.lade_glossar(BEISPIEL)

    def test_proben_sind_gueltig(self):
        for name in ("d.txt", "e.txt"):
            with open(os.path.join(HIER, "messung", name), encoding="utf-8") as f:
                fehler, hinweise = depesche.pruefe(f.read(), self.g)
            self.assertEqual(fehler, [], name)
            self.assertEqual(hinweise, [], name)

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
        self.assertNotIn("{{", text)


if __name__ == "__main__":
    unittest.main()
