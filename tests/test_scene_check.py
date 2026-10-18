"""The scene check (owner, 2026-10-16): every sentence a pattern can make gets a verdict once, in [scenes.<pattern>]: a scene the learner can picture,
used as the cue, or false, never generated. «Ég nenni ekki að sofa.» (lesson 27), «Má ég sofa?» (#333) and the bus «to the bus stop» (#336) were each found
by chance; the sheet lists the sentences nobody has judged."""
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum, scene_sheet
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
BASE = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
ITEMS = [
    {"id": "nenni", "kind": "construction", "target": "Ég nenni ekki að {inf}.", "meaning": "I can't be bothered to {inf}.", "slots": {"inf": "inf"}, "example": {"inf": "fara_ut"}},
    {"id": "fara_ut", "kind": "vocab", "target": "fara út", "meaning": "go out", "meaning_spoken": "to go out", "tags": ["inf"]},
    {"id": "sofa", "kind": "vocab", "target": "sofa", "meaning": "sleep", "meaning_spoken": "to sleep", "tags": ["inf"]},
    {"id": "elda", "kind": "vocab", "target": "elda", "meaning": "cook", "meaning_spoken": "to cook", "tags": ["inf"]},
]


def curriculum(scenes, known_lang=None):
    return curriculum_from_dict({**BASE, "items": [dict(i) for i in ITEMS], "scenes": scenes}, known_lang=known_lang)


def knows(*ids):
    l = LearnerState("is", "en", "A1")
    for i in ids:
        l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled")
    return l


class SceneCheckTests(unittest.TestCase):
    def test_a_verdict_is_a_scene_or_false(self):
        cur = curriculum({"nenni": {"fara_ut": "It's raining hard, and your friend suggests a walk.", "sofa": False}})
        c = cur.by_id["nenni"]
        self.assertEqual(c.fill_scenes, {"fara_ut": "It's raining hard, and your friend suggests a walk."})
        self.assertEqual(c.exclude_fills, ["sofa"], "false: never generated")
        self.assertEqual([f.id for f in cur.items_with_tag("inf", c)], ["fara_ut", "elda"])
        self.assertEqual([f.id for _, f, _, _ in scene_sheet(cur)], ["elda"], "the sheet lists what has no verdict")

    def test_a_verdict_names_a_pattern_and_one_of_its_fills_and_lives_only_in_the_scenes_table(self):
        with self.assertRaises(CurriculumError):
            curriculum({"fara_ut": {"sofa": False}})  # not a pattern
        with self.assertRaises(CurriculumError):
            curriculum({"nenni": {"nenni": "x"}})  # not a fill of its slot
        with self.assertRaises(CurriculumError):
            curriculum({"nenni": {"elda": 3}})
        with self.assertRaises(CurriculumError):
            curriculum_from_dict({**BASE, "items": [{**ITEMS[0], "fill_scenes": {"fara_ut": "x"}}, *ITEMS[1:]]})

    def test_the_scene_is_the_cue_when_the_sentence_is_asked(self):
        cur = curriculum({"nenni": {"fara_ut": "It's raining hard, and your friend suggests a walk.", "sofa": False, "elda": False}})
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), knows("nenni", "fara_ut", "sofa", "elda"))
        sc = Script(1, "t", "is", "en")
        ex = b.recall(sc, cur.by_id["nenni"], "meaning")
        self.assertEqual(ex.label, "situation: Ég nenni ekki að fara út.")
        self.assertIn("It's raining hard, and your friend suggests a walk. Say: I can't be bothered to go out.", sc.transcript())
        b.recall(sc, cur.by_id["nenni"], "hinted")
        self.assertIn("It starts with", sc.transcript(), "a hint stays a hint")

    def test_a_learner_of_another_language_gets_the_meaning_until_a_line_in_theirs_is_written(self):
        cur = curriculum({"nenni": {"fara_ut": "It's raining hard.", "sofa": False}}, known_lang="ja")
        self.assertEqual(cur.by_id["nenni"].fill_scenes, {})
        self.assertEqual(cur.by_id["nenni"].exclude_fills, ["sofa"], "a false holds for every language")
        both = curriculum({"nenni": {"fara_ut": {"en": "It's raining hard.", "ja": "大雨です。"}}}, known_lang="ja")
        self.assertEqual(both.by_id["nenni"].fill_scenes, {"fara_ut": "大雨です。"})

    def test_a_line_in_several_languages_is_read_by_language_not_by_order(self):
        """Review of #352: the primary language took the first value of the table, so an English learner heard the Japanese line."""
        verdict = {"nenni": {"fara_ut": {"ja": "大雨です。", "en": "It is raining."}}}
        self.assertEqual(curriculum(verdict).by_id["nenni"].fill_scenes, {"fara_ut": "It is raining."})
        self.assertEqual(curriculum(verdict, known_lang="ja").by_id["nenni"].fill_scenes, {"fara_ut": "大雨です。"})
        self.assertEqual(curriculum({"nenni": {"fara_ut": {"ja": "大雨です。"}}}).by_id["nenni"].fill_scenes, {}, "none in the learner's language: the meaning alone")

    def test_every_path_that_asks_a_judged_sentence_gives_its_scene(self):
        """Review of #352: a sibling's practice and a short item's sentence recall asked the judged sentence from its meaning alone."""
        cur = curriculum({"nenni": {"fara_ut": "It's raining hard.", "sofa": False, "elda": False}})
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), knows("nenni", "fara_ut", "sofa", "elda"))
        sc = Script(1, "t", "is", "en")
        sib = b.sibling_recall(sc, cur.by_id["nenni"], {})
        self.assertEqual(sib.label, "situation: Ég nenni ekki að fara út.")
        sent = b.sentence_recall(sc, cur.by_id["fara_ut"])
        self.assertEqual(sent.label, "situation: Ég nenni ekki að fara út.")
        self.assertEqual(sc.transcript().count("It's raining hard. Say: I can't be bothered to go out."), 2)

    def test_a_scene_keeps_the_news_that_the_sentence_is_new(self):
        """CI of #354: with a scene, «Now something you haven't heard yet.» (#197) was dropped with the rest of the cue. The scene takes the place of
        «Say: …» only; the written review asks from the scene, without the lesson's lead."""
        cur = curriculum({"nenni": {"fara_ut": "It's raining hard.", "sofa": "You're on a long flight.", "elda": "Your friend offers to cook."}})
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), knows("nenni", "fara_ut", "sofa", "elda"))
        sc = Script(1, "t", "is", "en")
        ex = b._recombine(sc, cur.by_id["nenni"], met_fills=True)
        narr = [g.text for g in sc.segments if g.exercise == ex.index and g.type == "narrate"]
        self.assertEqual(narr[0], "Now something you haven't heard yet.")
        self.assertRegex(narr[1], r"\. Say: I can't be bothered to ")
        self.assertNotIn("haven't heard", sc.review_questions()[-1]["prompt"])

    def test_each_lead_is_how_its_cue_begins(self):
        for lang in ("en", "ja"):
            p = Prompts.load(lang)
            for key in ("recombine_new", "recombine_again", "recombine_vocab_again"):
                self.assertTrue(p.get(key, meaning="X").startswith(p.get(f"{key}_lead")), (lang, key))

    def test_the_sheet_is_valid_toml_and_a_filled_line_loads_back(self):
        """Review of #352: ids such as «strætó» were printed as bare keys, which TOML rejects, so the sheet could not be pasted back."""
        import contextlib
        import io
        import tomllib
        from types import SimpleNamespace

        from audiolesson.cli import cmd_scene_check

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            cmd_scene_check(SimpleNamespace(curriculum=str(ROOT / "curricula" / "is-en"), pattern=None, met_learner=None, judged=True))
        sheet = tomllib.loads(out.getvalue())["scenes"]
        self.assertTrue(any(not k.isascii() for p in sheet.values() for k in p), "an id with Icelandic letters is in the sheet")
        self.assertEqual(sheet["eg_nenni_ekki"]["sofa"], False)
        import shutil
        import tempfile

        judged = set(tomllib.loads((ROOT / "curricula" / "is-en" / "95-scenes.toml").read_text(encoding="utf-8"))["scenes"])  # a table may be declared in one file only
        pattern, fills = next((p, f) for p, f in sheet.items() if any(not k.isascii() for k in f) and p not in judged)
        word = next(k for k in fills if not k.isascii())
        lines = out.getvalue().splitlines()
        head = next(n for n, line in enumerate(lines) if line.startswith("[scenes.") and pattern in line)
        row = next(line for line in lines[head + 1 :] if line.startswith(f'"{word}" = '))
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "is-en"
            shutil.copytree(ROOT / "curricula" / "is-en", copy)
            (copy / "96-filled.toml").write_text(lines[head] + "\n" + row.replace('= ""', '= "A scene."', 1) + "\n", encoding="utf-8")
            filled = load_curriculum(copy)
        self.assertEqual(filled.by_id[pattern].fill_scenes.get(next(i.id for i in filled.items if i.id == word)), "A scene.", "the filled line loads back")

    def test_the_course_never_says_the_sentences_found_by_chance(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for pattern, fill in (("eg_nenni_ekki", "sofa"), ("ma_eg_inf", "sofa"), ("attu", "leigubil"), ("fer_thessi_straeto_dest", "a_stoppistodina"), ("fer_thessi_straeto_dest", "a_thetta_hotel")):
            c = cur.by_id[pattern]
            self.assertNotIn(fill, [f.id for f in cur.items_with_tag(next(iter(c.slots.values())), c)], (pattern, fill))
        self.assertIn("fara_ut", cur.by_id["eg_nenni_ekki"].fill_scenes)
        self.assertEqual([r for r in scene_sheet(cur, ["eg_nenni_ekki"])], [], "every fill of «Ég nenni ekki að …» has its verdict")


if __name__ == "__main__":
    unittest.main()
