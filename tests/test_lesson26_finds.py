"""#333: the finds of the lesson-26 preview: a pattern phrase the link check missed, a redundant pattern play, a stage direction read aloud, «Má ég sofa?»."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum, unlinked_instances
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


def known(*ids):
    l = LearnerState("is", "en", "A1")
    for i in ids:
        l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled",
                               due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
    l.lessons_completed = 12
    return l


class Lesson26Finds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_link_check_sees_a_filler_with_a_tag_of_the_same_case(self):
        base = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
        items = [
            {"id": "get", "kind": "construction", "target": "Get ég fengið {thing}?", "meaning": "Can I have {thing}?", "slots": {"thing": "acc_request"}, "example": {"thing": "kaffi"}, "prereqs": ["kaffi"]},
            {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["acc_request"]},
            {"id": "bill", "kind": "vocab", "target": "leigubíl", "meaning": "a taxi", "tags": ["acc_thing"]},
            {"id": "phrase", "kind": "phrase", "target": "Get ég fengið leigubíl?", "meaning": "Can I get a taxi?", "prereqs": ["get", "bill"]},
        ]
        found = unlinked_instances(curriculum_from_dict({**base, "items": items}))
        self.assertEqual([(f[0], f[1], f[3]) for f in found], [("phrase", "get", "bill")])
        items[3]["not_instance"] = True
        self.assertEqual(unlinked_instances(curriculum_from_dict({**base, "items": items})), [], "a coincidence of text is declared, not linked")

    def test_the_course_has_none_unlinked_and_the_taxi_request_is_linked(self):
        self.assertEqual(unlinked_instances(self.cur), [])
        phrase = self.cur.by_id["get_eg_fengid_leigubil"]
        self.assertEqual((phrase.instance_of, phrase.instance_fill), ("get_eg_fengid", {"thing": "leigubil"}))
        self.assertIn("acc_request", self.cur.by_id["leigubil"].tags)

    def test_no_cue_reads_a_stage_direction_aloud(self):
        for i in self.cur.items:
            self.assertNotIn("showing the address", (i.meaning_spoken or "").lower(), i.id)
        self.assertEqual(self.cur.by_id["a_thetta_hotel_takk"].spoken_meaning, "To this hotel, please.")
        self.assertIn("booking", self.cur.by_id["a_thetta_hotel_takk"].situation, "the situation still says what is shown")

    def test_may_i_sleep_is_never_generated(self):
        c = self.cur.by_id["ma_eg_inf"]
        self.assertNotIn("sofa", [i.id for i in self.cur.items_with_tag("inf", c)])
        from audiolesson.exercises import Builder

        l = known("ma_eg_borga_med_korti", "eg_vil", "fara_heim", "sofa", "kaupa_mida", "ma_eg_inf")
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), l)
        made = others = 0
        for seed in range(30):
            b.rng.seed(seed)
            gen = b.generate(c, met_fills=True, forms=True)
            if gen is not None:
                made += 1
                self.assertNotIn("sofa", gen.item_ids)
            gen = b.generate_with(self.cur.by_id["sofa"], forms=True)
            if gen is not None:
                others += 1
                self.assertNotEqual(gen.construction.id, "ma_eg_inf")
        self.assertGreater(made, 0, "the pattern does make sentences with the other infinitives: the exclusion is exercised, not vacuous")
        self.assertGreater(others, 0, "and «sofa» is still said in the other patterns that take it")

    def test_a_phrase_whose_word_was_taught_inside_it_is_not_played_again_as_a_pattern_sentence(self):
        l = known("get_eg_fengid", "eg_aetla_ad_fa", "kaffi", "te")
        cfg = PlanConfig(minutes=20, new_items=2, max_new_items=2, seed=1, priority=["reikninginn", "get_eg_fengid_reikninginn"])
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        target = "Get ég fengið reikninginn?"
        intro = [e for e in sc.exercises if e.kind == "intro" and target in e.label]
        again = [e for e in sc.exercises if e.kind == "embed" and e.label == f"pattern: {target}"]
        self.assertTrue(intro, "the word is introduced inside the phrase")
        self.assertEqual(again, [], "and the phrase is not played again as «a sentence from a pattern you know»")
        self.assertIn("get_eg_fengid_reikninginn", sc.meta["new_items"], "but it is covered: a new item")
        # ... with its next-day question, which the learner's answer settles (the review of #345: it stayed embedded for ever, and the cafe dialogue waited for it)
        questions = [q for q in sc.review_questions() if "get_eg_fengid_reikninginn" in q["items"]]
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["answer"], target)
        from audiolesson.planner import apply_to_learner

        apply_to_learner(sc, l, TODAY)
        self.assertIn("get_eg_fengid_reikninginn", l.embedded)
        l.report([], [], TODAY + timedelta(days=1), lesson_number=sc.lesson_number, recalled=["get_eg_fengid_reikninginn"])
        self.assertNotIn("get_eg_fengid_reikninginn", l.embedded, "the answer settles it")
        self.assertIn("get_eg_fengid_reikninginn", l.items)


if __name__ == "__main__":
    unittest.main()
