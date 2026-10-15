"""#336: fixed phrases of a scene that share a frame and differ in one stretch are found by their text, and the transport scene's frames are patterns."""
import unittest
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum, phrase_frames

ROOT = Path(__file__).resolve().parent.parent
BASE = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}


def cur(items):
    return curriculum_from_dict({**BASE, "items": items})


def phrase(i, target, topics=("transport",), **kw):
    return {"id": i, "kind": "phrase", "target": target, "meaning": target, "topics": list(topics), **kw}


class PhraseFrameTests(unittest.TestCase):
    def test_phrases_that_differ_in_one_stretch_are_a_frame_by_their_text(self):
        c = cur([
            phrase("a", "Fer þessi strætó í miðbæinn?"),
            phrase("b", "Fer þessi strætó á flugvöllinn?"),
            phrase("c", "Hvenær kemur strætó?"),
            phrase("d", "Á flugvöllinn, takk."),
            phrase("e", "Á þetta hótel, takk."),
        ])
        found = {frame: ids for frame, ids in phrase_frames(c)}
        self.assertEqual(found["fer þessi strætó … "], ["a", "b"])
        self.assertEqual(found["á … takk"], ["d", "e"])

    def test_a_subject_or_a_copula_alone_is_not_a_frame(self):
        c = cur([phrase("a", "Ég er hér."), phrase("b", "Ég er þreytt."), phrase("c", "Þetta er gott."), phrase("d", "Þetta er dýrt.")])
        self.assertEqual(phrase_frames(c), [])

    def test_phrases_of_other_scenes_are_not_compared(self):
        c = cur([phrase("a", "Fer þessi strætó í miðbæinn?"), phrase("b", "Fer þessi strætó á flugvöllinn?", topics=("weather",))])
        self.assertEqual(phrase_frames(c), [])

    def test_a_group_made_by_one_pattern_is_not_reported(self):
        c = cur([
            {"id": "dest_takk", "kind": "construction", "target": "{dest}, takk.", "meaning": "{dest}, please.", "slots": {"dest": "dest"}, "example": {"dest": "x"}, "prereqs": ["x"]},
            {"id": "x", "kind": "vocab", "target": "á flugvöllinn", "meaning": "to the airport", "tags": ["dest"]},
            {"id": "y", "kind": "vocab", "target": "á þetta hótel", "meaning": "to this hotel", "tags": ["dest"]},
            phrase("d", "Á flugvöllinn, takk.", instance_of="dest_takk", instance_fill={"dest": "x"}),
            phrase("e", "Á þetta hótel, takk.", instance_of="dest_takk", instance_fill={"dest": "y"}),
        ])
        self.assertEqual(phrase_frames(c), [])


class TransportFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_bus_and_taxi_phrases_are_instances_of_two_patterns_with_the_scenes_destinations(self):
        by = {i: self.cur.by_id[i] for i in ("fer_thessi_straeto_i_midbaeinn", "fer_thessi_straeto_a_flugvollinn", "a_flugvollinn_takk", "a_thetta_hotel_takk")}
        self.assertEqual({i.instance_of for i in list(by.values())[:2]}, {"fer_thessi_straeto_dest"})
        self.assertEqual({i.instance_of for i in list(by.values())[2:]}, {"dest_takk"})
        self.assertEqual(by["a_flugvollinn_takk"].instance_fill, {"dest": "a_flugvollinn"})

    def test_a_destination_shared_by_both_patterns_connects_them(self):
        shared = [c.id for c in self.cur.items if c.kind == "construction" and "dest" in c.slots.values() and "a_flugvollinn" in c.prereqs + list(c.example.values())]
        self.assertEqual(sorted(shared), ["dest_takk", "fer_thessi_straeto_dest"])

    def test_the_patterns_say_the_new_destinations(self):
        for ctor, fill, want in (
            ("fer_thessi_straeto_dest", "a_safnid", "Fer þessi strætó á safnið?"),
            ("dest_takk", "a_stoppistodina", "Á stoppistöðina, takk."),
            ("dest_takk", "i_midbaeinn", "Í miðbæinn, takk."),
        ):
            text, meaning = self.cur.resolve_slots(self.cur.by_id[ctor], {"dest": self.cur.by_id[fill]})
            self.assertEqual(text, want)
            self.assertNotIn("{", meaning)

    def test_the_linked_transport_frames_are_not_reported_again(self):
        """The two frames the issue named are patterns now: «fer þessi strætó …» and «á … takk» are not reported (other frames that hold one of these phrases, such as
        «… í miðbæinn», still are, with the phrases that are not linked)."""
        frames = {f.strip() for f, _ in phrase_frames(self.cur)}
        self.assertNotIn("fer þessi strætó …", frames)
        self.assertNotIn("á … takk", frames)

    def test_a_frame_with_a_question_word_or_a_modal_is_reported_even_when_it_is_large(self):
        """Review of #346: «Hvar er …» (13), «Ég þarf …» (7) are frames; only pronouns, the copula and prepositions alone are not."""
        frames = {f.strip(): ids for f, ids in phrase_frames(self.cur)}
        self.assertGreaterEqual(len(frames["hvar er …"]), 10)
        self.assertIn("ég þarf …", frames)
        self.assertNotIn("ég er …", frames)
        self.assertNotIn("þetta er …", frames)

    def test_the_bus_pattern_does_not_say_the_bus_stop_or_this_hotel(self):
        c = self.cur.by_id["fer_thessi_straeto_dest"]
        ids = [i.id for i in self.cur.items_with_tag("dest", c)]
        self.assertEqual(sorted(ids), ["a_flugvollinn", "a_safnid", "i_midbaeinn"])
        self.assertIn("a_stoppistodina", [i.id for i in self.cur.items_with_tag("dest", self.cur.by_id["dest_takk"])], "a taxi does go there")

    def test_the_japanese_meanings_of_the_destinations_match_the_authored_phrases(self):
        c = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        text, meaning = c.resolve_slots(c.by_id["dest_takk"], {"dest": c.by_id["a_flugvollinn"]})
        self.assertEqual((text, meaning), ("Á flugvöllinn, takk.", c.by_id["a_flugvollinn_takk"].meaning))


class UnitsCoveredTests(unittest.TestCase):
    """The review of #346: the destinations are met inside the phrases that hold them, not introduced again, and then the patterns come."""

    @classmethod
    def setUpClass(cls):
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order

        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scen = load_cando(ROOT / "curricula" / "is-en")
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scen)
        cls.order = scenario_order(scen)
        cls.priority = next(sc for sc in __import__("tomllib").loads((ROOT / "curricula" / "is-en" / "cando" / "travel.toml").read_text(encoding="utf-8"))["scenarios"] if sc["id"] == "B4")["items"]

    def course(self, n):
        from datetime import date, timedelta

        from audiolesson.learner import LearnerState
        from audiolesson.planner import PlanConfig, Planner, apply_to_learner
        from audiolesson.prompts import Prompts
        from audiolesson.timing import Timing

        l, day = LearnerState("is", "en", "A1"), date(2026, 3, 1)
        for k in range(1, n + 1):
            cfg = PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order, priority=self.priority if k >= 24 else [])
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            yield k, sc
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=k, recalled=sc.meta["new_items"])
            day += timedelta(days=1)

    def test_a_destination_is_met_inside_its_phrase_and_not_introduced_again(self):
        for k, sc in self.course(26):
            if "a_flugvollinn_takk" in sc.meta["new_items"]:
                self.assertIn("a_flugvollinn", sc.meta["units_covered"])
                self.assertIn("a_flugvollinn", sc.meta["embedded_items"], "met inside the phrase: its next-day question asks the phrase")
                intros = [e.label for e in sc.exercises if e.kind == "intro" and "(á flugvöllinn)" in e.label]
                self.assertEqual(intros, [], "no «new: Á flugvöllinn, takk. (á flugvöllinn)»")
                return
        self.fail("the taxi phrase was not taught in the course")

    def test_the_patterns_come_and_say_the_other_destinations(self):
        said = set()
        for k, sc in self.course(40):
            said |= {e.label.split(": ", 1)[-1] for e in sc.exercises if "takk" in e.label or "strætó" in e.label}
        self.assertTrue({"Í miðbæinn, takk.", "Fer þessi strætó á flugvöllinn?"} & said, said)


class OneFillingTests(unittest.TestCase):
    """The review of #346: a pattern with one filling known can only be asked as the same sentence."""

    def lesson(self, fillers):
        from datetime import date

        from audiolesson.learner import LearnerState
        from audiolesson.planner import PlanConfig, Planner
        from audiolesson.prompts import Prompts
        from audiolesson.timing import Timing

        items = [{"id": f"f{k}", "kind": "vocab", "target": t, "meaning": m, "tags": ["dest"]} for k, (t, m) in enumerate(fillers)]
        items.append({"id": "c", "kind": "construction", "target": "Fer þessi strætó {dest}?", "meaning": "Does this bus go {dest}?", "slots": {"dest": "dest"},
                      "example": {"dest": "f0"}, "prereqs": ["f0"]})
        items += [{"id": f"w{n}", "kind": "phrase", "target": f"Ný lína {n}.", "meaning": f"New line {n}."} for n in range(12)]
        cur = cur_from(items)
        sc = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=3, max_new_items=3, seed=1, priority=[*(f"f{k}" for k in range(len(fillers))), "c"]), today=date(2026, 3, 1)).build()
        return cur, sc

    def test_with_one_filling_the_pattern_is_asked_a_few_times_not_fifteen(self):
        cur, sc = self.lesson([("á flugvöllinn", "to the airport")])
        asked = [e for e in sc.exercises if e.kind == "recall" and e.item_ids and e.item_ids[0] == "c"]
        self.assertLessEqual(len(asked), 5, "four by the cap and the closing one, not the ladder over and over")

    def test_no_sentence_of_the_pattern_is_asked_more_than_the_cap_whatever_the_path(self):
        """The re-review of #346: the ladder's asks of the example and the generated sentences count together, per sentence."""
        from audiolesson.planner import PlanConfig

        cur, sc = self.lesson([("á flugvöllinn", "to the airport"), ("í miðbæinn", "to the town centre")])
        counts: dict[str, int] = {}
        for e in sc.exercises:
            if e.kind in ("recall", "connect", "generative") and e.item_ids and e.item_ids[0] == "c":
                counts[e.label.split(": ", 1)[-1]] = counts.get(e.label.split(": ", 1)[-1], 0) + 1
        self.assertTrue(counts)
        self.assertLessEqual(max(counts.values()), PlanConfig().construction_asks_per_filling + 1, counts)

    def test_with_every_combination_used_the_ladder_asks_the_filling_asked_fewest_times(self):
        """The re-review of #346 (13 asks of one sentence): once every combination was used, the ladder asked the example again, whatever its count."""
        from audiolesson.exercises import Builder, _combo_key
        from audiolesson.learner import LearnerState
        from audiolesson.prompts import Prompts
        from audiolesson.script import Script
        from audiolesson.timing import Timing

        cur, _ = self.lesson([("á flugvöllinn", "to the airport"), ("í miðbæinn", "to the town centre")])
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        b.in_lesson.update({"f0", "f1"})
        c = cur.by_id["c"]
        options = b.filling_options(c)
        self.assertEqual(len(options), 2)
        for fills, _, _ in options:
            b.used_combos.add(_combo_key(c, fills))  # every combination used
        example, other = options[0][1], options[1][1]  # the example is f0
        asked = {example: 9, other: 1}
        b.ask_count = lambda text: asked[text]
        sc = Script(1, "t", cur.target_lang, cur.known_lang)
        ex = b.recall(sc, c, "meaning")
        self.assertEqual(ex.label, f"meaning: {other}", "not the example again")

    def test_combos_available_counts_the_fillings_that_can_be_said(self):
        from audiolesson.exercises import Builder
        from audiolesson.learner import LearnerState
        from audiolesson.prompts import Prompts
        from audiolesson.timing import Timing

        cur, _ = self.lesson([("á flugvöllinn", "to the airport"), ("í miðbæinn", "to the town centre")])
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        self.assertEqual(b.combos_available(cur.by_id["c"]), 0, "nothing is known or heard yet")
        b.in_lesson.update({"f0", "f1"})
        self.assertEqual(b.combos_available(cur.by_id["c"]), 2)


def cur_from(items):
    return curriculum_from_dict({**BASE, "items": items})


if __name__ == "__main__":
    unittest.main()
