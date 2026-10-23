"""#311: a phrase that is a known pattern with a new word teaches the word, in other frames."""
import copy
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum, unlinked_instances
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_no_phrase_of_the_curriculum_is_an_unlinked_pattern_instance(self):
        self.assertEqual(unlinked_instances(self.cur), [])

    def test_an_unlinked_one_is_found(self):
        cur = copy.deepcopy(self.cur)
        item = cur.by_id["eg_tharf_ulpu"]
        item.instance_of, item.instance_fill = "", {}
        self.assertEqual(unlinked_instances(cur), [("eg_tharf_ulpu", "eg_tharf", "thing", "ulpu", "")])

    def test_ulpu_is_linked_to_its_pattern(self):
        item = self.cur.by_id["eg_tharf_ulpu"]
        self.assertEqual((item.instance_of, item.instance_fill), ("eg_tharf", {"thing": "ulpu"}))


class ParallelsTests(unittest.TestCase):
    def test_no_lesson_gets_more_than_a_few_parallels_of_one_pattern(self):
        """#316 review (§3, §9 "A pattern is not a lesson's whole supply": about ten is a ceiling, not a target): the thirty links hand a passed phrase's practice to
        its pattern's other instances (#192), which must not make a run of one pattern with random fillers."""
        from collections import defaultdict
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        worst = 0
        for _ in range(70):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            by = defaultdict(set)
            for e in sc.exercises:
                if e.kind == "generative":
                    by[e.item_ids[0]].add(e.label)
            worst = max(worst, max((len(v) for v in by.values()), default=0))
            day += timedelta(days=1)
        self.assertLessEqual(worst, 10)


class HandoffTests(unittest.TestCase):
    def test_a_word_brought_in_by_its_phrase_is_not_handed_back_to_the_word(self):
        """A simulated course, lesson 58: «á flugvöllinn» had no frame, so #262 brought «Á flugvöllinn, takk.» in first (`phrase_first`); #311
        (`new_filler_of`) handed the phrase's turn back to its new word, which brought the phrase in again, until the recursion limit. The phrase now
        comes in for the word, and the word is taken out of it."""
        from unittest import mock

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        for _ in range(3):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day)
        word, phrase = cur.by_id["a_flugvollinn"], cur.by_id["a_flugvollinn_takk"]
        real_phrase_first, real_new_filler_of = planner.phrase_first, planner.new_filler_of
        picks = iter([[word]])
        with (
            mock.patch.object(planner, "phrase_first", lambda item, queued=frozenset(): phrase if item is word else real_phrase_first(item, queued)),
            mock.patch.object(planner, "new_filler_of", lambda item: word if item is phrase else real_new_filler_of(item)),
            mock.patch.object(planner, "select_new", lambda *a, **k: next(picks, [])),
        ):
            sc = planner.build()
        intros = [e.item_ids for e in sc.exercises if e.kind == "intro" and (word.id in e.item_ids or phrase.id in e.item_ids)]
        self.assertEqual(intros[:2], [[phrase.id], [word.id]], "the phrase, then the word out of it")


class IntroductionTests(unittest.TestCase):
    def lesson_with(self, item_id, upto=80):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        for _ in range(upto):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            if item_id in sc.meta["new_items"]:
                return sc
            day += timedelta(days=1)
        self.fail(f"{item_id} was not introduced in {upto} lessons")

    def test_the_new_word_is_taught_as_a_word_and_met_in_other_frames(self):
        sc = self.lesson_with("eg_tharf_ulpu")
        self.assertIn("ulpu", sc.meta["new_items"], "the word is a new item of the lesson")
        self.assertIn("eg_tharf_ulpu", sc.meta["pattern_instances"], "the phrase is covered as a sentence of its pattern")
        spoken = {g.text for g in sc.segments if g.type in ("speak", "answer") and "úlpu" in (g.text or "")}
        others = spoken - {"Ég þarf úlpu.", "úlpu", "úlpu."}
        self.assertGreaterEqual(len(others), 2, f"úlpu is met in at least two other frames: {others}")

    def test_a_phrase_whose_word_was_taught_inside_it_today_is_not_introduced_again_as_new(self):
        """Lesson 26 of the replay (#316 review): «reikninginn» is taught inside «Get ég fengið reikninginn?», which then came again as «Something new»."""
        sc = self.lesson_with("get_eg_fengid_reikninginn")
        mine = [e for e in sc.exercises if "get_eg_fengid_reikninginn" in e.item_ids]
        self.assertEqual([e.kind for e in mine if e.kind == "intro" and e.item_ids[0] == "get_eg_fengid_reikninginn"], [], "the phrase has no introduction of its own (its word's introduction names it, for the next-day question)")
        self.assertFalse(any(e.kind == "embed" for e in mine), "#333: the word was taught inside this very phrase, so the sentence is not played again as «a sentence from a pattern you know»")
        self.assertEqual(sum(1 for g in sc.segments if g.type == "narrate" and (g.text or "").startswith("Something new") and "bill" in (g.text or "")), 0)
        self.assertIn("get_eg_fengid_reikninginn", sc.meta["pattern_instances"])

    def test_the_phrase_is_not_asked_as_the_same_sentence_more_than_three_times(self):
        sc = self.lesson_with("eg_tharf_ulpu")
        asked = [e for e in sc.exercises if any(g.type == "answer" and (g.text or "").strip() == "Ég þarf úlpu." for g in sc.segments if g.exercise == e.index)]
        self.assertLessEqual(len(asked), 3)
        self.assertNotIn("eg_tharf_ulpu", sc.meta["repeated_new_sentences"])



class PatternOfAKnownPhrasePromisesOnlyWhatComesTests(unittest.TestCase):
    """Lesson 34's feedback: «hnetum» was said to be swappable («It is a pattern: you can say it with other words.») and no swap followed: the
    same sentence was asked again, and «fiski» came minutes later. With no other filler known the line says the other words come later; with
    one, the second example shows the swap at once."""

    def lines(self, known):
        from audiolesson.learner import ItemState
        from audiolesson.script import Script
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        l = LearnerState("is", "en", "A1")
        today = date(2026, 3, 1)
        for i in known:
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, interval_days=7, recalled=3, last_outcome="recalled",
                                   due=(today + timedelta(days=5)).isoformat(), last_practiced=(today - timedelta(days=2)).isoformat())
        b = Planner(cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=today).builder
        sc = Script(1, "t", "is", "en")
        ex = b.intro(sc, cur.by_id["ofnaemi_fyrir"])
        return [s.text for s in sc.segments if s.exercise == ex.index and s.text]

    def test_no_other_filler_known_promises_them_later(self):
        said = self.lines(("eg_er_med_ofnaemi_fyrir_hnetum", "hnetum"))
        self.assertIn("It is a pattern: other words can go in its place. You will meet them later.", said)
        self.assertNotIn("It is a pattern: you can say it with other words.", said)

    def test_another_filler_known_is_shown_at_once(self):
        said = self.lines(("eg_er_med_ofnaemi_fyrir_hnetum", "hnetum", "fiski"))
        self.assertIn("It is a pattern: you can say it with other words.", said)
        self.assertIn("Ég er með ofnæmi fyrir fiski.", said, "the swap follows the promise")


class EmbedNeverRepeatsItsSourceTests(unittest.TestCase):
    """Lesson 34's feedback: «á þetta hótel» was taught redundantly. «You know this: Á þetta hótel, takk. This word is in it: á þetta hótel. In
    another sentence: Á þetta hótel, takk.» The phrase is a sentence of «{dest}, takk.», and the embed made the pattern with the part again."""

    def test_the_other_sentence_is_never_the_source(self):
        from audiolesson.learner import ItemState
        from audiolesson.script import Script
        cur = load_curriculum(Path(__file__).resolve().parent.parent / "curricula" / "is-en")
        l = LearnerState("is", "en", "A1")
        today = date(2026, 3, 1)
        for i in ("dest_takk", "a_thetta_hotel_takk", "fer_thessi_straeto_dest", "a_flugvollinn", "i_midbaeinn"):
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, interval_days=7, recalled=3, last_outcome="recalled",
                                   due=(today + timedelta(days=5)).isoformat(), last_practiced=(today - timedelta(days=2)).isoformat())
        b = Planner(cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=today).builder
        heard_before = set(b.heard)
        sc = Script(1, "t", "is", "en")
        ex = b.embed(sc, cur.by_id["a_thetta_hotel"], cur.by_id["a_thetta_hotel_takk"])
        said = [s.text for s in sc.segments if s.role == "embed_sentence"]
        self.assertTrue(ex is None or "Á þetta hótel, takk." not in said, said)
        self.assertIsNone(ex, "«{dest}, takk.» makes only the source, and the bus pattern excludes this hotel: no other sentence, so no embed")
        self.assertEqual(b.heard, heard_before, "the source is excluded only for the choice, not marked heard")


if __name__ == "__main__":
    unittest.main()
