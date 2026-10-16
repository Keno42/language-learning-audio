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

    def test_the_course_never_says_the_sentences_found_by_chance(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for pattern, fill in (("eg_nenni_ekki", "sofa"), ("ma_eg_inf", "sofa"), ("attu", "leigubil"), ("fer_thessi_straeto_dest", "a_stoppistodina"), ("fer_thessi_straeto_dest", "a_thetta_hotel")):
            c = cur.by_id[pattern]
            self.assertNotIn(fill, [f.id for f in cur.items_with_tag(next(iter(c.slots.values())), c)], (pattern, fill))
        self.assertIn("fara_ut", cur.by_id["eg_nenni_ekki"].fill_scenes)
        self.assertEqual([r for r in scene_sheet(cur, ["eg_nenni_ekki"])], [], "every fill of «Ég nenni ekki að …» has its verdict")


if __name__ == "__main__":
    unittest.main()
