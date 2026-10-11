"""#270, the pilot: a noun is one entry whose forms are items; the learner keeps a state per form; an old id resolves to its noun and form."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.nouns import noun_forms, noun_report
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 1)


def raw(extra=()):
    return {
        "curriculum": {"name": "t", "target_lang": "is", "known_lang": "en"},
        "items": [
            {"id": "koku", "kind": "vocab", "target": "köku", "meaning": "cake", "gender": "fem", "noun": "kaka", "form": "acc", "noun_base": "kaka"},
            {"id": "kaka_nom", "kind": "vocab", "target": "kaka", "meaning": "cake", "gender": "fem", "noun": "kaka", "form": "nom"},
            *extra,
        ],
    }


class NounEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_pilot_words_are_grouped_by_noun_with_gender_and_form(self):
        expected = {
            "koku": ("kaka", "acc", "fem"), "klosettid": ("klosett", "nom_def", "neut"), "kronur": ("krona", "pl", "fem"), "thusund": ("thusund", "nom", "neut"),
            "eldfjall": ("eldfjall", "nom", "neut"), "jokull": ("jokull", "nom", "masc"), "hraun": ("hraun", "nom", "neut"),
            "sturtan": ("sturta", "nom_def", "fem"), "reykjavik_dat": ("reykjavik", "dat", "fem"),
        }
        for item_id, (noun, form, gender) in expected.items():
            self.assertEqual(self.cur.noun_form(item_id), (noun, form), item_id)
            self.assertEqual(self.cur.nouns[noun]["gender"], gender, item_id)
            self.assertEqual(self.cur.nouns[noun]["forms"][form], item_id)
        self.assertEqual(self.cur.nouns["kaka"]["base"], "kaka")
        self.assertIsNone(self.cur.noun_form("takk"), "not a noun")
        self.assertIsNone(self.cur.noun_form("no_such_item"))

    def test_validation_keeps_one_noun_one_gender_and_one_item_per_form(self):
        curriculum_from_dict(raw())
        bad = {
            "a noun without a form": {"id": "x", "kind": "vocab", "target": "x", "meaning": "x", "gender": "fem", "noun": "kaka"},
            "a form without a gender": {"id": "x", "kind": "vocab", "target": "x", "meaning": "x", "noun": "kaka", "form": "dat"},
            "two items for one form": {"id": "x", "kind": "vocab", "target": "x", "meaning": "x", "gender": "fem", "noun": "kaka", "form": "acc"},
            "forms that disagree about the gender": {"id": "x", "kind": "vocab", "target": "x", "meaning": "x", "gender": "masc", "noun": "kaka", "form": "dat"},
            "a base equal to the form": {"id": "x", "kind": "vocab", "target": "x", "meaning": "x", "gender": "fem", "noun": "y", "form": "acc", "noun_base": "x"},
        }
        for name, item in bad.items():
            with self.subTest(name), self.assertRaises(CurriculumError):
                curriculum_from_dict(raw([item]))

    def test_a_new_form_is_named_once_against_its_basic_word(self):
        learner = LearnerState("is", "en", "A1")
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        met = [i.id for i in self.cur.items if i.order < self.cur.by_id["koku"].order and i.id != "koku"]
        for i in met:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        ex = b.intro(sc, self.cur.by_id["koku"])
        self.assertEqual(ex.label, "new: Ég ætla að fá köku. (köku)")
        speech = [g.text for g in sc.segments if g.exercise == ex.index and g.type in ("speak", "narrate")]
        self.assertIn("kaka", speech)
        self.assertEqual(speech.count(Prompts.load("en").get("form_of_base")), 1)
        self.assertLess(speech.index("köku"), speech.index("kaka"), "the part first, then the basic word")
        sc2 = Script(1, "t", "is", "en")
        b.intro(sc2, self.cur.by_id["hraun"])
        self.assertNotIn(Prompts.load("en").get("form_of_base"), [g.text for g in sc2.segments if g.type == "narrate"], "a basic form is not contrasted with itself")


class PerFormStateTests(unittest.TestCase):
    """The ids did not change, so a learner file and a review queue written before the grouping load as they were, and every id resolves."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def old_learner_file(self):
        learner = LearnerState("is", "en", "A1")
        learner.items["koku"] = ItemState(stage="situation", successes=4, durable_successes=3, interval_days=7, recalled=4, last_practiced="2026-02-27")
        learner.items["klosettid"] = ItemState(stage="meaning", successes=1, last_practiced="2026-02-28")
        data = learner.to_dict() if hasattr(learner, "to_dict") else None
        return learner

    def test_an_old_learner_file_and_review_queue_resolve_with_their_history(self):
        learner = self.old_learner_file()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner.json"
            learner.save(path)
            raw_file = json.loads(path.read_text())
            raw_file.pop("learned_wholes", None)  # a file from before #269 has no such key either
            path.write_text(json.dumps(raw_file))
            loaded = LearnerState.load(path)
        for item_id, stage, successes in (("koku", "situation", 4), ("klosettid", "meaning", 1)):
            self.assertEqual((loaded.items[item_id].stage, loaded.items[item_id].successes), (stage, successes), "no reset of history")
            self.assertIsNotNone(self.cur.noun_form(item_id))
        forms = noun_forms(self.cur, loaded)
        self.assertTrue(forms["kaka"]["forms"]["acc"]["met"])
        self.assertEqual(forms["kaka"]["forms"]["acc"]["successes"], 4)
        self.assertEqual(forms["kaka"]["forms"]["acc"]["last_practiced"], "2026-02-27")
        self.assertFalse(forms["hraun"]["forms"]["nom"]["met"])
        self.assertIn("kaka: acc", noun_report(self.cur, loaded))
        # the bot's queue keys its entries by item ids: {"items": [...], "prompt", "answer"}; every one resolves
        queue = [{"items": ["koku"], "prompt": "Say: a piece of cake.", "answer": "köku"}, {"items": ["klosettid", "hvar_er"], "prompt": "Where is the toilet?", "answer": "Hvar er klósettið?"}]
        resolved = [[self.cur.noun_form(i) for i in e["items"]] for e in queue]
        self.assertEqual(resolved, [[("kaka", "acc")], [("klosett", "nom_def"), None]])

    def test_a_failure_of_one_form_moves_no_other_state(self):
        learner = self.old_learner_file()
        before = copy.deepcopy(learner.items["klosettid"])
        learner.report(["koku"], [], date(2026, 3, 2), lesson_number=3, recalled=[])
        self.assertEqual(learner.items["klosettid"], before)
        self.assertTrue(learner.is_open("koku"))


class BareNounRowTests(unittest.TestCase):
    def test_the_bare_noun_row_counts_by_the_exercise_not_by_the_label(self):
        """#276 review: the row compared the label with the item's meaning, so only «krónur» (meaning equal to target) was ever counted."""
        from datetime import timedelta

        from audiolesson.cando import load_cando
        from audiolesson.planner import BARE_STAGES, PlanConfig, Planner, apply_to_learner
        from audiolesson.themes import load_themes, scenario_order

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cur)
        themes = load_themes(ROOT / "curricula" / "is-en", cur, scenarios)
        learner, day = LearnerState("is", "en", "A1"), TODAY
        counted = 0
        differing = 0
        for n in range(1, 23):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"),
                         PlanConfig(minutes=30, new_target=8, themes=themes, theme_scenarios=scenario_order(scenarios)), today=day).build()
            expected = []
            for e in sc.exercises:
                it = cur.by_id.get(e.item_ids[0]) if len(e.item_ids) == 1 else None
                if e.kind == "recall" and e.stage in BARE_STAGES and it is not None and it.noun and any(g.type == "answer" and g.exercise == e.index and g.text == it.target for g in sc.segments):
                    expected.append(e.label)
                    differing += it.meaning.lower() != it.target.lower()
            self.assertEqual(sc.meta["second_half"]["bare_noun_recalls"] if "second_half" in sc.meta else sc.meta["bare_noun_recalls"], expected)
            counted += len(expected)
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreater(differing, 0, "a noun whose meaning differs from its word is counted (köku, þúsund…)")


if __name__ == "__main__":
    unittest.main()
