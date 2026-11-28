"""«Áttu …?», «Ertu með …?» and «Eruð þið með …?» told apart (the owner, 2026-11-28, on a new learner's lesson 1).

The two were told apart only by a nuance of their glosses («牛乳はありますか？» / «牛乳は置いてありますか？»), and the lesson never said where either is
said. «Áttu» (eiga) asks whether someone has a thing at all, «Ertu með» (vera með) whether they have it on them now, and a shop is asked the
second, to the staff together. The glosses say so; a pattern's sentence is introduced in its scene, the scene check's line in the learner's
language; and an aside says the difference once both are known (candidates until native-checked, #209)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from audiolesson.cli import main
from audiolesson.content import load_curriculum
from tests.audiolesson_common import ROOT


class HaveFramesTests(unittest.TestCase):
    def test_the_glosses_say_at_all_against_on_you_now(self):
        en, ja = (load_curriculum(ROOT / "curricula" / "is-en", known_lang=k) for k in ("en", "ja"))
        self.assertEqual((en.by_id["attu"].meaning, en.by_id["ertu_med"].meaning), ("Do you have {thing}?", "Do you have {thing} on you?"))
        self.assertEqual((ja.by_id["attu"].meaning, ja.by_id["ertu_med"].meaning, ja.by_id["erud_thid_med"].meaning),
                         ("{thing}ある？", "今{thing}持ってる？", "{thing}は置いてありますか？"))

    def test_an_introduction_says_its_scene_first(self):
        for lang, shop in (("en", "In a shop, you can't see what you want."), ("ja", "お店で、欲しいものが見当たりません。")):
            with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
                main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "--known", lang, "-l", str(Path(td) / "l.json"), "-o", td,
                      "-m", "15", "--no-audio", "--date", "2026-12-01"])
                script = json.loads((Path(td) / "lesson-001.script.json").read_text("utf-8"))
            intro = next(e for e in script["exercises"] if e["label"] == "new pattern: Eruð þið með {thing}?")
            said = [g["text"] for g in script["segments"] if g.get("exercise") == intro["index"] and g.get("text")]
            self.assertEqual(said[0], shop, lang)

    def test_the_aside_tells_the_two_apart_once_both_are_known(self):
        note = next(n for n in load_curriculum(ROOT / "curricula" / "is-en").notes if n.id == "attu_ertu_med")
        self.assertEqual(set(note.items), {"attu", "ertu_med"})
        self.assertTrue(note.contrast)
        for words in ("at all", "on them now", "«Eruð þið með»"):
            self.assertIn(words, note.text)


if __name__ == "__main__":
    unittest.main()
