import contextlib
import glob
import io
import os
import sys
import tempfile
import unittest
import unittest.mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)
import depesche  # noqa: E402


class PrivatTest(unittest.TestCase):
    """Proben in messung/ ohne private Spuren; nur die Platzhalter sind erlaubt."""

    def test_proben_ohne_private_spuren(self):
        proben = sorted(glob.glob(os.path.join(HIER, "messung", "*.txt")))
        self.assertTrue(proben)
        for pfad in proben:
            with open(pfad, encoding="utf-8") as f:
                self.assertEqual(depesche.private_spuren(f.read()), [], pfad)

    def test_spuren_fallen_auf(self):
        text = "a ~/Projekte/x\nb /home/x\nc local_0123abcd\nd 10.0.0.1\ne a.b@example.org\n"
        funde = depesche.private_spuren(text)
        self.assertEqual([zeile for zeile, _, _ in funde], [1, 2, 3, 4, 5])

    def test_platzhalter_sind_erlaubt(self):
        text = "`~/notizen/teamleiter/plan.md` an `local_00000000-0000-0000-0000-000000000000`\n"
        self.assertEqual(depesche.private_spuren(text), [])

    def test_befehl_meldet_funde_mit_rueckgabewert(self):
        with tempfile.TemporaryDirectory() as tmp:
            sauber, privat = os.path.join(tmp, "s.txt"), os.path.join(tmp, "p.txt")
            with open(sauber, "w", encoding="utf-8") as f:
                f.write("DP1 FYI ok\n")
            with open(privat, "w", encoding="utf-8") as f:
                f.write("DP1 FYI ok\n- see ~/Projekte/x\n")
            for datei, erwartet in ((sauber, 0), (privat, 1)):
                aus = io.StringIO()
                with unittest.mock.patch.object(sys, "argv", ["depesche.py", "privat", datei]), \
                        contextlib.redirect_stdout(aus), self.assertRaises(SystemExit) as ende:
                    depesche.main()
                self.assertEqual(ende.exception.code, erwartet, aus.getvalue())
                if erwartet:
                    self.assertIn(":2: Benutzerpfad", aus.getvalue())


if __name__ == "__main__":
    unittest.main()
