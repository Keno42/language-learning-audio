"""Trust in a line (the owner, 2026-11-28; G10, #631): a line whose every pair of neighbouring words Icelanders are found writing counts as
checked. ``audiolesson/trust.py`` cuts a line into pairs and lone words, judges it against the looked-up table, and lists every line the
course can say; ``validate`` warns about the lines with a pair no text has and never fails on them."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from audiolesson import trust
from audiolesson.content import load_curriculum
from audiolesson.text import norm_utterance
from audiolesson.themes import load_themes

ROOT = Path(__file__).resolve().parent.parent


class PartsTests(unittest.TestCase):
    def test_pairs_are_neighbouring_words_lower_cased(self):
        self.assertEqual(trust.parts("Hvað heitir þetta fjall?"), trust.Parts(("hvað heitir", "heitir þetta", "þetta fjall"), ()))

    def test_punctuation_and_digits_end_a_stretch(self):
        # no pair across a full stop, a comma or a number: «takk þú» and «klukkan í» are not what the line says
        self.assertEqual(trust.parts("Takk. Þú ert góður."), trust.Parts(("þú ert", "ert góður"), ("takk",)))
        self.assertEqual(trust.parts("Já, takk."), trust.Parts((), ("já", "takk")))
        self.assertEqual(trust.parts("Klukkan 5 í dag."), trust.Parts(("í dag",), ("klukkan",)))

    def test_a_word_alone_in_its_stretch_is_looked_up_as_a_word(self):
        self.assertEqual(trust.parts("Vá! Útsýnið er fallegt."), trust.Parts(("útsýnið er", "er fallegt"), ("vá",)))

    def test_a_proper_name_is_no_evidence_either_way(self):
        # the persona's name and a mountain are in no pair; the first word of a sentence is not a name
        self.assertEqual(trust.parts("Ég heiti Yuki."), trust.Parts(("ég heiti",), ()))
        self.assertEqual(trust.parts("Þarna er Hekla. Hún er eldfjall."), trust.Parts(("þarna er", "hún er", "er eldfjall"), ()))

    def test_a_word_a_name_leaves_alone_is_looked_up_as_a_word(self):
        # review of #632: a name ends a stretch, so a word beside it with no other neighbour is checked alone, not passed over
        self.assertEqual(trust.parts("Komdu, Yuki minn!"), trust.Parts((), ("komdu", "minn")))
        self.assertEqual(trust.parts("Þarna eru Hekla og Katla."), trust.Parts(("þarna eru",), ("og",)))
        self.assertEqual(trust.Trust(pairs={}, words={"komdu": 5, "minn": 0}).verdict("Komdu, Yuki minn!").status, "unusual")


class VerdictTests(unittest.TestCase):
    TABLE = trust.Trust(pairs={"ég heiti": 12, "í dag": 0, "hvað heitir": 9}, words={"klukkan": 30})

    def test_every_pair_found_is_trusted(self):
        self.assertEqual(self.TABLE.verdict("Ég heiti Yuki.").status, "trusted")

    def test_a_pair_no_text_has_makes_the_line_unusual(self):
        v = self.TABLE.verdict("Klukkan 5 í dag.")
        self.assertEqual((v.status, v.absent), ("unusual", ["í dag"]))
        self.assertFalse(self.TABLE.usual("Klukkan 5 í dag."))

    def test_a_pair_not_looked_up_yet_leaves_it_unknown_and_not_held_back(self):
        v = self.TABLE.verdict("Hvað heitir þetta?")
        self.assertEqual((v.status, v.missing), ("unknown", ["heitir þetta"]))
        self.assertTrue(self.TABLE.usual("Hvað heitir þetta?"))

    def test_the_table_round_trips_and_is_absent_until_made(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(trust.load(td))
            trust.save(td, self.TABLE, {"checked_on": "2026-11-28"})
            self.assertEqual(trust.load(td), self.TABLE)


class CourseLinesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.lines = trust.course_lines(cur, load_themes(ROOT / "curricula" / "is-en", cur))
        cls.said = {norm_utterance(t) for t, _ in cls.lines}

    def test_items_patterns_and_scene_lines_are_all_listed_once_and_filled(self):
        self.assertIn(norm_utterance("Afsakið."), self.said)  # an item
        self.assertIn(norm_utterance("Eruð þið með mjólk?"), self.said)  # a pattern's sentence: «Eruð þið með {thing}?» with «mjólk»
        self.assertIn(norm_utterance("Þarna er Hekla. Hún er eldfjall."), self.said)  # a theme partner's variant
        texts = [t for t, _ in self.lines]
        self.assertEqual(len(texts), len(set(texts)))
        self.assertFalse([t for t in texts if "{" in t])


class LookupToolTests(unittest.TestCase):
    def test_a_number_word_is_also_looked_up_in_digits(self):
        # written texts give ages, prices and times in digits: «ertu átján» is found as «Ertu 18 ára?»
        import runpy

        tool = runpy.run_path(str(ROOT / "tools" / "attest_pairs.py"))
        self.assertEqual([tool["as_digits"](k) for k in ("ertu átján", "tvo kaffi", "ég er")], ["ertu 18", "2 kaffi", None])


class ValidateTests(unittest.TestCase):
    def test_validate_warns_about_an_unusual_line_and_never_fails(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "course.toml").write_text(
                '[curriculum]\nname = "x"\ntarget_lang = "is"\nknown_lang = "en"\n\n'
                '[[items]]\nid = "i_dag"\nkind = "phrase"\ntarget = "Klukkan fimm í dag."\nmeaning = "At five today."\n', encoding="utf-8")
            for table, warns in ((None, "not checked against Icelandic texts yet"),
                                 (trust.Trust(pairs={"klukkan fimm": 3, "fimm í": 0}), "no Icelandic text has «fimm í»"),
                                 (trust.Trust(pairs={"klukkan fimm": 3}), "not looked up in Icelandic texts yet"),
                                 (trust.Trust(pairs={"klukkan fimm": 3, "fimm í": 4, "í dag": 9}), None)):
                if table is not None:
                    trust.save(d, table, {})
                err = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    self.assertEqual(main(["validate", str(d)]), 0, warns)
                if warns is None:
                    self.assertNotIn("Icelandic text", err.getvalue())
                else:
                    self.assertIn(warns, err.getvalue())


if __name__ == "__main__":
    unittest.main()
