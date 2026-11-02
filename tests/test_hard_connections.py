"""#326: an item reported hard is practised through its connections (a line of its scene, another pattern, the same pattern with other
words), not as the same sentence again."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
IS_EN = ROOT / "curricula" / "is-en"


class HardConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, scen)
        cls.order = scenario_order(scen)

    def planner(self, learner, **kw):
        cfg = PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order, **kw)
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def test_hard_items_are_the_open_and_the_hesitated(self):
        l = LearnerState("is", "en", "A1")
        l.items["a"] = ItemState(stage="meaning", last_outcome="not_recalled")
        l.items["kaffi"] = ItemState(stage="meaning", last_outcome="hesitated")
        l.items["te"] = ItemState(stage="meaning", last_outcome="recalled", durable_successes=2)
        l.items["afsakid"] = ItemState(stage="meaning", last_outcome="not_recalled")
        self.assertEqual(sorted(self.planner(l).hard_items()), ["afsakid", "kaffi"], "«a» is not in the curriculum; a recalled item is not hard")

    def known(self, *ids):
        l = LearnerState("is", "en", "A1")
        for i in ids:
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, interval_days=7, recalled=3, last_outcome="recalled",
                                   due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
        l.lessons_completed = 8
        return l

    def test_the_phrases_built_on_a_word_and_its_other_forms_connect_it(self):
        """The review of #330: «lundi» has «Ég vil sjá lunda.» (a phrase built on it), heard in the whale-watching dialogue."""
        p = self.planner(self.known("lundi", "eg_vil_sja_lunda"))
        self.assertEqual([c.id for c in p.related_items(self.cur.by_id["lundi"])], ["eg_vil_sja_lunda"])
        self.assertEqual(self.planner(self.known("lundi")).related_items(self.cur.by_id["lundi"]), [], "a phrase never met connects nothing")
        recent = self.known("lundi", "eg_vil_sja_lunda")
        recent.items["eg_vil_sja_lunda"].durable_successes = 0  # met in the lesson before: not yet «known»
        recent.items["eg_vil_sja_lunda"].successes = 1
        self.assertEqual([c.id for c in self.planner(recent).related_items(self.cur.by_id["lundi"])], ["eg_vil_sja_lunda"], "met is enough (the review of #332)")
        recent.items["eg_vil_sja_lunda"].last_outcome = "not_recalled"
        self.assertEqual(self.planner(recent).related_items(self.cur.by_id["lundi"]), [], "a failed one is open: not used")

    def test_a_word_reported_hard_is_a_hard_item_for_two_weeks_or_until_recalled(self):
        l = self.known("kaffi", "te", "mjolk")
        l.report([], [], TODAY, sooner=["kaffi"], hard=["te"])
        self.assertEqual((l.items["kaffi"].reported_hard, l.items["te"].reported_hard), (TODAY.isoformat(), TODAY.isoformat()))
        self.assertEqual(l.items["te"].last_outcome, "recalled", "no outcome is recorded")
        self.assertLessEqual(l.items["te"].due, (TODAY + timedelta(days=4)).isoformat(), "it comes back sooner, as a «sooner» does")
        self.assertEqual(l.reported, [], "a report of hardness alone does not mark the lesson reported")
        p = self.planner(l)
        p.today = TODAY + timedelta(days=3)
        self.assertEqual(sorted(p.hard_items()), ["kaffi", "te"])
        p.today = TODAY + timedelta(days=20)
        self.assertEqual(p.hard_items(), [], "two weeks later it is not hard any more")
        l.report([], [], TODAY + timedelta(days=4), recalled=["te"])
        self.assertEqual(l.items["te"].reported_hard, "", "a confirmed recall settles it")

    def test_the_cli_reports_hard_items(self):
        import io, tempfile
        from contextlib import redirect_stdout

        from audiolesson.cli import main

        l = self.known("kaffi")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            l.save(path)
            with redirect_stdout(io.StringIO()) as out:
                main(["report", "-l", str(path), "--hard", "kaffi,nope", "--date", TODAY.isoformat()])
            back = LearnerState.load(path)
        self.assertEqual(back.items["kaffi"].reported_hard, TODAY.isoformat())
        self.assertIn("reported hard", out.getvalue())

    def test_a_line_of_the_scene_is_found_for_an_item_a_theme_level_needs(self):
        l = LearnerState("is", "en", "A1")
        p = self.planner(l)
        found = p.scene_line_of(self.cur.by_id["er_thetta_saeti_laust"], set())
        self.assertIsNotNone(found)
        dlg, turn_items, key, _, _ = found
        self.assertEqual(turn_items, {0: ["er_thetta_saeti_laust"]})
        self.assertTrue(key.startswith("cafe:"))
        self.assertEqual(dlg.id, "theme:" + key.rsplit(":", 1)[0], "the exchange is named by the level the line is from, so the daily read counts the scene once")
        self.assertEqual(len(dlg.turns), 1)
        self.assertEqual(dlg.turns[0].expect_text, "Er þetta sæti laust?")
        again = p.scene_line_of(self.cur.by_id["er_thetta_saeti_laust"], {key})
        self.assertTrue(again is None or again[2] != key, "a line used for this item is not used again")

    def test_the_allergy_line_has_a_scene(self):
        """Lesson 33: «Ég er með ofnæmi fyrir hnetum.» was asked five times a lesson as one sentence, with nothing connecting it (#326's
        content gap). The café's fourth level holds it, with the partner's line before it and the reply after it; the request that line answers
        («Án hnetna?» after «Get ég fengið köku án hnetna?», the owner's order after lesson 44: one asks first, and says why) leads in (#427)."""
        found = self.planner(LearnerState("is", "en", "A1")).scene_line_of(self.cur.by_id["eg_er_med_ofnaemi_fyrir_hnetum"], set())
        self.assertIsNotNone(found)
        dlg, turn_items, key, asked, lead = found
        self.assertEqual((dlg.id, turn_items), ("theme:cafe:4", {0: ["get_eg_fengid_koku_an_hnetna"], 1: ["eg_er_med_ofnaemi_fyrir_hnetum"]}))
        self.assertEqual(lead, {0: False}, "the request, never met by this learner: heard, not asked")
        self.assertTrue(asked, "the line holds no other item, so it is asked, not only heard")
        self.assertEqual([t.expect_text for t in dlg.turns], ["Get ég fengið köku án hnetna?", "Ég er með ofnæmi fyrir hnetum."])
        self.assertTrue(dlg.turns[0].partner and dlg.turns[1].partner, "the partner's line before it and the reply after it")

    def test_a_lead_in_line_comes_after_the_question_it_answers(self):
        """Lesson 45: the exchange cut out of smalltalk's fifth level for «Hvar býrð þú?» opened with the learner's «Já, ég hef verið hér áður.», an
        answer to a question no one had asked. The learner's line that leads in (#427) comes after the partner's line it answers, when there is one."""
        p, used = self.planner(LearnerState("is", "en", "A1")), set()
        while (found := p.scene_line_of(self.cur.by_id["hvar_byrd_thu"], used)) is not None and found[0].id != "theme:smalltalk:5":
            used.add(found[2])
        self.assertIsNotNone(found)
        dlg, turn_items, _, _, lead = found
        self.assertEqual(turn_items, {0: ["ja", "eg_hef_verid_her_adur"], 1: ["hvar_byrd_thu"]})
        self.assertEqual(dlg.turns[0].opener, "Fallegt, er það ekki? Hefurðu komið hingað áður?", "the question comes first")
        self.assertEqual([t.expect_text for t in dlg.turns], ["Já, ég hef verið hér áður.", "Hvar býrð þú?"])
        self.assertEqual(set(lead), {0})

    def test_a_scene_line_is_asked_as_line_role_decides_on_its_other_items(self):
        """#265: one rule decides every learner line. «Ég ætla að fá kaffi.» for an open «kaffi»: the pattern met but not yet known is enough
        to ask it, as the theme's own play does (#263); never met, the line is heard with its meaning (#240)."""
        l = self.known("kaffi")
        l.items["kaffi"].last_outcome = "not_recalled"
        _, turn_items, key, asked, _ = self.planner(l).scene_line_of(self.cur.by_id["kaffi"], set())
        self.assertEqual((key, turn_items), ("cafe:1:1", {0: ["eg_aetla_ad_fa", "kaffi"]}))
        self.assertFalse(asked, "the pattern never met: heard")
        l.items["eg_aetla_ad_fa"] = ItemState(stage="meaning", successes=1, last_outcome="recalled", due=(TODAY + timedelta(days=1)).isoformat(),
                                               last_practiced=(TODAY - timedelta(days=1)).isoformat())
        self.assertFalse(l.knows("eg_aetla_ad_fa"))
        _, _, _, asked, _ = self.planner(l).scene_line_of(self.cur.by_id["kaffi"], set())
        self.assertTrue(asked, "met, not known: asked")

    def test_the_open_allergy_line_goes_through_its_pattern_unless_the_review_asked_the_pattern_today(self):
        """«Ég er með ofnæmi fyrir hnetum.» is a sentence of «Ég er með ofnæmi fyrir {allergen}.» (#326): once the pattern is known, a connection
        practice of the open line is another allergen. Not on a day the learner's own review asked the pattern (#238)."""
        def lesson(reviewed: bool):
            l = self.known("ofnaemi_fyrir", "hnetum", "fiski", "eg_er_med_ofnaemi_fyrir_hnetum", "eg_aetla_ad_fa", "koku", "ja", "takk")
            l.items["eg_er_med_ofnaemi_fyrir_hnetum"].last_outcome = "not_recalled"
            if reviewed:
                l.items["ofnaemi_fyrir"].last_reviewed = TODAY.isoformat()
            return self.planner(l).build().meta
        free = lesson(False)
        self.assertIn("pattern", free["hard_connections"]["eg_er_med_ofnaemi_fyrir_hnetum"]["kinds"])
        asked = lesson(True)
        self.assertNotIn("pattern", asked["hard_connections"]["eg_er_med_ofnaemi_fyrir_hnetum"]["kinds"])
        self.assertNotIn("ofnaemi_fyrir", asked["asked_after_review"])

    def test_the_pattern_connection_avoids_the_patterns_it_was_in(self):
        l = LearnerState("is", "en", "A1")
        for i in ("eg_aetla_ad_fa", "kaffi", "te", "mjolk", "sykur"):
            if i in self.cur.by_id:
                l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, interval_days=7, recalled=3, due=(TODAY + timedelta(days=5)).isoformat())
        b = self.planner(l).builder
        homes = {c.id for c, _ in b.homes_of(self.cur.by_id["kaffi"])}
        self.assertTrue(homes)
        gen = b.generate_with(self.cur.by_id["kaffi"], avoid=frozenset(homes))
        self.assertIsNone(gen, "no home left when all are avoided")

    def test_a_course_practises_hard_items_through_their_connections(self):
        """A course with failures: hard items are asked through a scene line, another pattern or a sibling, and the report says so;
        no connection practice is the first practice of the item in its lesson."""
        l = LearnerState("is", "en", "A1")
        day = TODAY
        kinds: set[str] = set()
        with_two = 0
        for n in range(1, 13):
            sc = self.planner(l).build()
            m = sc.meta
            for item_id, row in m["hard_connections"].items():
                kinds |= set(row["kinds"])
                with_two += row["practices"] >= 3 and row["connections"] >= 2
                for t in row["connection_times_s"]:
                    first = min((e.start for e in sc.exercises if item_id in e.item_ids and e.kind in ("recall", "generative", "connect")), default=0)
                    self.assertGreaterEqual(t + 1, first, f"lesson {n}: {item_id}: the first practice is the ladder's own")
            apply_to_learner(sc, l, day)
            new = m["new_items"]
            failed = new[:2] if n % 2 == 1 else []
            l.report(failed, [], day + timedelta(days=1), lesson_number=n, recalled=[i for i in new if i not in failed])
            day += timedelta(days=1)
        self.assertIn("scene", kinds)
        self.assertTrue(kinds & {"pattern", "sibling"}, kinds)
        self.assertGreater(with_two, 0, "some hard item went through two connections in a lesson")


if __name__ == "__main__":
    unittest.main()
