import contextlib
import io
import os
import sys
import tempfile
import unittest
import unittest.mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)
import depesche  # noqa: E402

BEISPIEL = os.path.join(HIER, "beispiel", "glossar-team.tsv")


class TeamteilTest(unittest.TestCase):
    """Teamteil nur ausdrücklich oder aus ~/.config; skill nimmt das Beispiel nie still."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fehlt = os.path.join(tmp.name, "fehlt.tsv")
        umgebung = unittest.mock.patch.dict(os.environ)
        umgebung.start()
        self.addCleanup(umgebung.stop)
        os.environ.pop("DEPESCHE_TEAM", None)
        eigen = unittest.mock.patch.object(depesche, "TEAM_EIGEN", self.fehlt)
        eigen.start()
        self.addCleanup(eigen.stop)

    def starte(self, *argumente):
        aus, fehler = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(sys, "argv", ["depesche.py", *argumente]), \
                contextlib.redirect_stdout(aus), contextlib.redirect_stderr(fehler), \
                self.assertRaises(SystemExit) as ende:
            depesche.main()
        return ende.exception.code, aus.getvalue(), fehler.getvalue()

    def test_fehlendes_team_argument_bricht_ab(self):
        with self.assertRaises(SystemExit) as ende:
            depesche.team_datei(self.fehlt)
        self.assertIn("--team", str(ende.exception.code))

    def test_fehlende_umgebungsvariable_bricht_ab(self):
        os.environ["DEPESCHE_TEAM"] = self.fehlt
        with self.assertRaises(SystemExit) as ende:
            depesche.team_datei()
        self.assertIn("DEPESCHE_TEAM", str(ende.exception.code))

    def test_ausdruecklich_genanntes_beispiel_gilt(self):
        self.assertEqual(depesche.team_datei(BEISPIEL, beispiel_erlaubt=False), BEISPIEL)

    def test_beispiel_als_rueckfall_mit_hinweis(self):
        fehler = io.StringIO()
        with contextlib.redirect_stderr(fehler):
            self.assertEqual(depesche.team_datei(), depesche.BEISPIEL)
        self.assertIn("Beispiel", fehler.getvalue())

    def test_check_laeuft_mit_beispiel_und_hinweis(self):
        code, aus, fehler = self.starte("check", os.path.join(HIER, "messung", "e2.txt"))
        self.assertEqual(code, 0)
        self.assertIn("ok", aus)
        self.assertIn("Beispiel", fehler)

    def test_skill_ohne_eigenen_teamteil_bricht_ab(self):
        code, aus, _ = self.starte("skill", "-")
        self.assertIn("--team beispiel/glossar-team.tsv", str(code))
        self.assertEqual(aus, "")

    def test_skill_zip_ohne_eigenen_teamteil_bricht_ab(self):
        code, _, _ = self.starte("skill", "--zip", os.path.join(os.path.dirname(self.fehlt), "d.zip"))
        self.assertIn("kein eigener Teamteil", str(code))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.fehlt), "d.zip")))

    def test_skill_mit_ausdruecklichem_beispiel(self):
        code, aus, _ = self.starte("--team", BEISPIEL, "skill", "-")
        self.assertEqual(code, 0)
        self.assertTrue(aus.startswith("---\nname: depesche\n"))

    def test_kern_braucht_keinen_teamteil(self):
        code, aus, fehler = self.starte("--kern", "skill", "-")
        self.assertEqual(code, 0)
        self.assertTrue(aus.startswith("---\nname: depesche\n"))
        self.assertEqual(fehler, "")


if __name__ == "__main__":
    unittest.main()
