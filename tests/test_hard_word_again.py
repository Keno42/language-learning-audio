"""#337: a phrase's hard words are modelled slowly and split at its introduction; a word reported hard gets the model again before its next practice."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.sounds import hard_words_of
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class HardWordAgainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def builder(self):
        return Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))

    def test_the_words_of_the_learners_remark_have_authored_syllables(self):
        got = {i: hard_words_of(self.cur.by_id[i]) for i in ("vegurinn_er_lokadur", "get_eg_fengid_reikninginn", "er_vegurinn_opinn", "reikninginn")}
        self.assertEqual(got["vegurinn_er_lokadur"], [("vegurinn", ["veg", "ur", "inn"]), ("lokaður", ["lok", "að", "ur"])])
        self.assertEqual(got["get_eg_fengid_reikninginn"], [("reikninginn", ["reik", "ning", "inn"])])
        self.assertEqual(got["reikninginn"], [("reikninginn", ["reik", "ning", "inn"])])

    def test_a_phrase_names_its_hard_words_and_the_introduction_models_them_after_the_phrase(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["vegurinn_er_lokadur"])
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertTrue({"veg", "inn", "lok", "að"} <= set(slow))
        said = [g.text for g in sc.segments if g.type == "speak" and g.rate == 1.0]
        self.assertIn("vegurinn", said)
        self.assertIn("lokaður", said)

    def test_a_phrase_with_nothing_authored_is_introduced_as_before(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["er_thetta_saeti_laust"])
        self.assertNotIn("in parts", sc.transcript())

    def test_a_reported_item_without_authored_syllables_takes_the_word_with_most_hard_sounds(self):
        item = self.cur.by_id["er_thetta_saeti_laust"]
        self.assertEqual(hard_words_of(item), [], "not reported, nothing authored: no hard word")
        self.assertEqual(hard_words_of(item, reported=True), [("þetta", None)], "reported: «þetta» holds the old «tt» rule")

    def test_the_slow_exercise_says_the_phrase_then_its_words_in_pieces(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        ex = b.slow_word_exercise(sc, self.cur.by_id["get_eg_fengid_reikninginn"])
        self.assertEqual((ex.kind, ex.stage), ("model", "slow"))
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertEqual(slow, ["reik", "ning", "inn"])

    def test_a_word_asked_for_is_modelled_whatever_its_letters(self):
        """Lesson 42: «regnhlíf» was reported hard to say, and with no authored split and none of the sound rules in it nothing was modelled: the
        request was saved and dropped. A one-word item reported hard is always its own word: split when authored («regn · hlíf»), else said once
        more at natural speed (#302: never stretched). The same holds for a word of one syllable and one no rule reads."""
        from audiolesson.sounds import HARD_SOUNDS, REPORTED_SOUNDS

        rules = (*HARD_SOUNDS.values(), *REPORTED_SOUNDS.values())
        self.assertEqual(hard_words_of(self.cur.by_id["regnhlif"], reported=True), [("regnhlíf", ["regn", "hlíf"])])
        plain = [i for i in self.cur.items if i.kind == "vocab" and i.word_count == 1 and not i.syllables and not any(rx.search(i.target.lower()) for rx in rules)]
        short = next(i for i in plain if len(i.target.strip(".?!")) <= 3)
        long_ = next(i for i in plain if len(i.target) >= 6)
        for item in (short, long_):
            word = item.target.lower().strip(".?!")
            self.assertEqual(hard_words_of(item, reported=True), [(word, None)], item.id)
            sc = Script(1, "t", "is", "en")
            ex = self.builder().slow_word_exercise(sc, item)
            self.assertIsNotNone(ex, item.id)
            spoken = [g for g in sc.segments if g.exercise == ex.index and g.type == "speak"]
            self.assertEqual([g.text for g in spoken], [item.target], f"{item.id}: said once more")
            self.assertTrue(all(g.rate == 1 for g in spoken), "never stretched (#302)")
        self.assertEqual(hard_words_of(self.cur.by_id["regnhlif"]), [("regnhlíf", ["regn", "hlíf"])], "authored: also at its introduction")

    def test_a_say_request_from_the_form_reaches_the_next_lesson(self):
        """The real order (lesson 42): the word is taught, the form reports it «sooner» with the reason «say», and the next lesson plays its model."""
        l = LearnerState("is", "en", "A1")
        l.items["regnhlif"] = ItemState(stage="meaning", successes=3, recalled=1, interval_days=1, last_outcome="recalled",
                                        due=(TODAY + timedelta(days=1)).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        l.lessons_completed = 20
        l.report([], [], TODAY - timedelta(days=1), sooner=["regnhlif"], sooner_reasons=["say"])
        planner = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual(planner.slow_owed_items(), ["regnhlif"])
        sc = planner.build()
        self.assertEqual(sc.meta["slow_models_reported"], ["regnhlif"])
        ex = next(e for e in sc.exercises if e.kind == "model" and e.stage == "slow")
        self.assertEqual([g.text for g in sc.segments if g.exercise == ex.index and g.type == "speak" and g.rate < 1], ["regn", "hlíf"])

    def lesson_after_report(self, practised: bool, recalled_at_review: bool):
        """The real order: the report (the feedback form's «sooner») comes first, the next morning's review after it, then the lesson is built."""
        l = LearnerState("is", "en", "A1")
        for i in ("vegurinn_er_lokadur", "get_eg_fengid_reikninginn", "er_vegurinn_opinn"):
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                   due=(TODAY + (timedelta(days=0) if practised else timedelta(days=60))).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        l.report([], [], TODAY - timedelta(days=1), sooner=["vegurinn_er_lokadur", "get_eg_fengid_reikninginn"])
        if recalled_at_review:
            l.report([], [], TODAY, recalled=["vegurinn_er_lokadur", "get_eg_fengid_reikninginn"], gaps={"vegurinn_er_lokadur": 1, "get_eg_fengid_reikninginn": 1})
        for i in ("vegurinn_er_lokadur", "get_eg_fengid_reikninginn", "er_vegurinn_opinn"):  # the report moves the date: set it after, so the two cases differ
            l.items[i].due = (TODAY + (timedelta(days=0) if practised else timedelta(days=60))).isoformat()
        l.lessons_completed = 20
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        return l, sc

    def test_the_model_is_owed_in_the_next_lesson_whether_or_not_the_item_is_practised_in_it(self):
        practice = {}
        for practised in (True, False):
            l, sc = self.lesson_after_report(practised, recalled_at_review=False)
            practice[practised] = sum(1 for e in sc.exercises if "vegurinn_er_lokadur" in e.item_ids and e.kind in ("recall", "generative", "connect"))
            self.assertEqual(sorted(sc.meta["slow_models_reported"]), ["get_eg_fengid_reikninginn", "vegurinn_er_lokadur"], f"practised={practised}")
            self.assertEqual(len([e for e in sc.exercises if e.kind == "model" and e.stage == "slow"]), 2)
        self.assertGreater(practice[True], 0, "in one case the item is practised in the lesson")
        self.assertEqual(practice[False], 0, "in the other it is not, and the model is played all the same")

    def test_a_recall_at_the_review_clears_the_connections_flag_but_not_the_owed_model(self):
        """The review of #342: the new items' next-day check is in the bot's review, and a 言えた there says nothing about how the word sounds."""
        l, sc = self.lesson_after_report(False, recalled_at_review=True)
        self.assertEqual(l.items["vegurinn_er_lokadur"].reported_hard, "", "the recall settles the connections of #326")
        self.assertNotEqual(l.items["vegurinn_er_lokadur"].slow_owed, "", "but not the pronunciation")
        self.assertEqual(sorted(sc.meta["slow_models_reported"]), ["get_eg_fengid_reikninginn", "vegurinn_er_lokadur"])

    def test_a_file_from_before_the_field_owes_the_model_once(self):
        """Review of #342: lesson 26's «sooner» reports were made before ``slow_owed`` existed; they are carried over on load, once."""
        import tempfile

        l, _ = self.lesson_after_report(False, recalled_at_review=False)
        old = l.to_dict()
        for st in old["items"].values():
            del st["slow_owed"]  # a file saved before the field
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            import json

            path.write_text(json.dumps(old), encoding="utf-8")
            back = LearnerState.load(path)
            self.assertEqual(back.items["vegurinn_er_lokadur"].slow_owed, (TODAY - timedelta(days=1)).isoformat(), "carried over from reported_hard")
            self.assertEqual(back.items["er_vegurinn_opinn"].slow_owed, "", "not reported: nothing owed")
            back.report([], [], TODAY, recalled=["vegurinn_er_lokadur"], gaps={"vegurinn_er_lokadur": 1})  # the morning review clears reported_hard...
            back.save(path)
            again = LearnerState.load(path)
            self.assertNotEqual(again.items["vegurinn_er_lokadur"].slow_owed, "", "... and the carried-over debt stays")
            again.items["vegurinn_er_lokadur"].slow_owed = ""  # the model was played
            again.save(path)
            self.assertEqual(LearnerState.load(path).items["vegurinn_er_lokadur"].slow_owed, "", "and is not carried over again")

    def test_a_word_alone_is_introduced_without_a_sentence_to_say_first(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.slow_word_exercise(sc, self.cur.by_id["reikninginn"])
        self.assertIn("Do you remember how to say this? The bill.", sc.transcript(), "a word has no sentence to say first: it is asked from its meaning")
        self.assertEqual([g.text for g in sc.segments if g.type == "speak" and g.rate < 1], ["reik", "ning", "inn"])

    def test_playing_the_model_clears_what_is_owed_and_it_is_not_played_twice(self):
        from audiolesson.planner import apply_to_learner

        l, sc = self.lesson_after_report(True, recalled_at_review=False)
        apply_to_learner(sc, l, TODAY)
        self.assertEqual((l.items["vegurinn_er_lokadur"].slow_owed, l.items["get_eg_fengid_reikninginn"].slow_owed), ("", ""))
        again = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY + timedelta(days=1)).build()
        self.assertEqual(again.meta["slow_models_reported"], [])

    def test_an_old_report_is_not_owed(self):
        l, _ = self.lesson_after_report(True, recalled_at_review=False)
        late = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY + timedelta(days=40))
        self.assertEqual(late.slow_owed_items(), [])

    def test_a_pattern_is_modelled_through_its_example_and_its_slot_names_are_not_words(self):
        """Review of #342: «Get ég fengið {thing}?» reported hard must not be read out with «{thing}», and «{language}» is not a hard word. Lesson 27: a pattern
        reported hard («Ég nenni ekki að …») is heard through the sentence it was introduced with, in words the learner has («fara heim», not the authored
        «versla»)."""
        b = self.builder()
        b.learner.items["fara_heim"] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled")
        sc = Script(1, "t", "is", "en")
        for c in self.cur.items:
            if c.kind == "construction":
                self.assertEqual(hard_words_of(c, reported=True), [], c.id)
        ex = b.slow_word_exercise(sc, self.cur.by_id["eg_nenni_ekki"])
        self.assertEqual(ex.label, "slow: Ég nenni ekki að fara heim.")
        self.assertNotIn("{", sc.transcript())

    def test_a_sentence_without_authored_hard_words_is_heard_whole_slowly_then_at_natural_speed(self):
        """Lesson 27: «Við erum fjögur.» was hard to hear, and the guess by sounds picked «fjögur». A reported sentence that names no hard word of its own is
        tried from its meaning (#423), said word by word, and whole again, each repeated."""
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        ex = b.slow_word_exercise(sc, self.cur.by_id["vid_erum_fjogur"])
        self.assertEqual((ex.kind, ex.stage, ex.label), ("model", "slow", "slow: Við erum fjögur."))
        spoken = [g.text for g in sc.segments if g.type == "speak" and g.exercise == ex.index and g.role != "narration"]
        self.assertNotIn("fjögur", spoken, "no single guessed word")
        self.assertIn("Let's try to say this sentence in Icelandic again: There are four of us.", sc.transcript())
        self.assertIn("Við · erum · fjögur.", sc.transcript(), "word by word")

    def test_a_gendered_pattern_is_heard_in_the_form_of_the_voice_and_asking_moves_no_turn(self):
        """Review of #351: «Ég er {state}.» with «glöð / glaður»: the check for a model must not take a gender turn, and the model says the woman's form in
        the woman's voice."""
        b = self.builder()
        for i in ("eg_er_state", "glod"):
            b.learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled")
        pattern = self.cur.by_id["eg_er_state"]
        self.assertTrue(b.slow_model_possible(pattern))
        self.assertEqual(b._gender_uses, {}, "no gender turn taken by asking")
        sc = Script(1, "t", "is", "en")
        ex = b.slow_word_exercise(sc, pattern)
        said = {(g.text, g.speaker) for g in sc.segments if g.type == "speak" and g.exercise == ex.index and g.role != "narration"}
        self.assertIn(("Ég er glöð.", "native_a"), said)
        self.assertFalse([t for t, _ in said if "glaður" in t], said)

    def test_a_reported_pattern_and_a_reported_sentence_are_owed_their_model(self):
        l = LearnerState("is", "en", "A1")
        for i in ("eg_nenni_ekki", "vid_erum_fjogur", "fara_heim"):
            l.items[i] = ItemState(stage="meaning", durable_successes=1, successes=3, recalled=1, interval_days=1, last_outcome="recalled",
                                   due=(TODAY + timedelta(days=1)).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        l.report([], [], TODAY - timedelta(days=1), sooner=["eg_nenni_ekki", "vid_erum_fjogur"])
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual(sorted(p.slow_owed_items()), ["eg_nenni_ekki", "vid_erum_fjogur"])

    def test_word_syllables_are_checked(self):
        base = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
        def make(extra):
            return curriculum_from_dict({**base, "items": [{"id": "a", "kind": "phrase", "target": "Vegurinn er lokaður.", "meaning": "The road is closed.", **extra}]})
        make({"word_syllables": {"vegurinn": ["veg", "ur", "inn"]}})
        for bad in ({"vegurinn": ["veg", "urinn", "x"]}, {"vegurinn": ["vegurinn"]}, {"nope": ["no", "pe"]}, {"Vegurinn": ["Veg", "ur", "inn"]}):
            with self.assertRaises(CurriculumError, msg=str(bad)):
                make({"word_syllables": bad})


if __name__ == "__main__":
    unittest.main()
