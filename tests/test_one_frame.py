"""A new word is taught in the one frame its lesson teaches for it (the owner, 2026-11-26, on a new learner's first lesson).

Lesson 1 taught «mjólk» inside «Áttu mjólk?» («牛乳はありますか？»), the sentence ``whole_home`` found for it, and two exercises later the pattern
«Eruð þið með {thing}?», whose example is «mjólk» («牛乳は置いてありますか？»): two frames for one word in the same form on day one, told apart
only by a nuance of the cue. A pattern still to come in the lesson whose example is the word now comes first, and the word is taken out of its
sentence (#262); the introduction before them is recalled first, so no three new items come back to back (#86).
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from audiolesson.cli import main
from tests.audiolesson_common import ROOT


class OneFrameTests(unittest.TestCase):
    def test_the_first_lesson_teaches_milk_in_the_pattern_it_teaches(self):
        for lang in ("en", "ja"):
            with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
                main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "--known", lang, "-l", str(Path(td) / "l.json"), "-o", td,
                      "-m", "15", "--no-audio", "--date", "2026-12-01"])
                script = json.loads((Path(td) / "lesson-001.script.json").read_text("utf-8"))
            exercises, segments = script["exercises"], script["segments"]
            intros = [e["label"] for e in exercises if e["kind"] == "intro"]
            self.assertIn("new pattern: Eruð þið með {thing}?", intros, lang)
            self.assertIn("new: Eruð þið með mjólk? (mjólk)", intros, lang)
            self.assertLess(intros.index("new pattern: Eruð þið með {thing}?"), intros.index("new: Eruð þið með mjólk? (mjólk)"), lang)
            self.assertFalse([g["text"] for g in segments if g.get("text") and "Áttu mjólk" in g["text"]], f"{lang}: no second frame for the same word")
            kinds = "".join("i" if e["kind"] == "intro" else "-" for e in exercises)
            self.assertNotIn("iii", kinds, lang)


if __name__ == "__main__":
    unittest.main()
