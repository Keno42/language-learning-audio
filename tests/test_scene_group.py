"""#327 part 1: the day's new material is a group of one scene (topic), and the scene played matches it where a theme exists."""
import unittest
from datetime import date
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import curriculum_from_dict, load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import Theme, load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


def cur():
    topics = {"a": ["social"], "b": ["cafe"], "c": ["social"], "d": ["social"], "e": ["cafe"], "f": ["cafe"]}
    items = [{"id": k, "kind": "phrase", "target": f"Lína {k}.", "meaning": f"Line {k}.", "topics": t} for k, t in topics.items()]
    return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})


def planner(learner=None, themes=(), **kw):
    learner = learner or LearnerState("is", "en", "A1")
    cfg = PlanConfig(minutes=10, new_items=3, max_new_items=3, seed=1, themes=list(themes), **kw)
    return Planner(cur(), learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)


def cafe_theme():
    return Theme(id="cafe", scenario="A4", title="Café", topics=["cafe"], levels=[])  # no levels: all of them are played


def just_played():
    l = LearnerState("is", "en", "A1")
    l.themes_done["cafe"] = 1
    l.themes_last["cafe"] = 6  # the lesson before: not to be played again yet
    l.lessons_completed = 6
    return l


class SceneGroupTests(unittest.TestCase):
    def ids(self, p, n=3):
        return [i.id for i in p.select_new(n)]

    def test_with_no_scene_to_play_the_first_items_topic_is_the_group(self):
        p = planner(just_played(), themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p, 4), ["a", "c", "d", "b"], "the social lines go ahead of the café line, but only two thirds of the places (3 of 4)")
        self.assertEqual(p.day_topic, "social")

    def test_a_scene_that_can_be_played_takes_the_group_even_when_the_first_item_is_elsewhere(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.themes_last["cafe"] = 1  # rested: next lesson is far past it
        l.lessons_completed = 6
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p), ["b", "e", "a"], "two of three places for the scene, the third in the course order")
        self.assertEqual(p.day_topic, "cafe")

    def test_a_scene_just_played_does_not_take_the_group(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.lessons_completed = 6
        l.themes_last["cafe"] = 6  # the lesson before
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p, 4), ["a", "c", "d", "b"])

    def test_the_trip_order_still_goes_first(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.themes_last["cafe"] = 1
        l.lessons_completed = 6
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"], priority=["d"])
        self.assertEqual(self.ids(p), ["d", "b", "e"])

    def test_a_first_course_keeps_the_course_order(self):
        self.assertEqual(self.ids(planner()), ["a", "b", "c"])
        self.assertEqual(self.ids(planner(just_played())), ["a", "b", "c"], "no themes configured")
        with_levels = Theme(id="cafe", scenario="A4", title="Café", topics=["cafe"], levels=[{"goal": "g", "turns": []}, {"goal": "h", "turns": []}])
        p = planner(just_played(), themes=[with_levels], theme_scenarios=["A4"])
        self.assertFalse(p.themes_exhausted())
        self.assertEqual(self.ids(p), ["a", "b", "c"], "a theme still has a level to play: the course order and the theme decide")

    def test_the_topic_is_set_once_a_lesson(self):
        p = planner(just_played(), themes=[cafe_theme()], theme_scenarios=["A4"])
        p.select_new(1)
        self.assertEqual(p.day_topic, "social")
        self.assertEqual([i.id for i in p.select_new(3, exclude={"a"})], ["c", "d", "b"], "the same topic in the next arc")


class ThemeMatchTests(unittest.TestCase):
    def setUp(self):
        self.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        self.themes = load_themes(IS_EN, self.cur, scen)
        self.order = scenario_order(scen)

    def planner(self, last: dict[str, int]):
        l = LearnerState("is", "en", "A1")
        for t in self.themes:
            l.themes_done[t.id] = len(t.levels)  # every level played: the lesson replays one
            l.themes_last[t.id] = last[t.id]
        l.lessons_completed = 20
        cfg = PlanConfig(minutes=10, new_items=3, seed=1, themes=self.themes, theme_scenarios=self.order)
        return Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def test_the_replayed_scene_is_the_days_topic_when_a_theme_has_it(self):
        last = {t.id: 10 for t in self.themes}
        last["cafe"] = 18  # rested two lessons: not by the old rule (3), by the match rule (2)
        p = self.planner(last)
        p.day_topic = "cafe"
        self.assertEqual(p.pick_theme()[0].id, "cafe")

    def test_without_a_match_the_rule_is_unchanged(self):
        last = {t.id: 10 for t in self.themes}
        last["cafe"] = 18
        p = self.planner(last)
        self.assertNotEqual(p.pick_theme()[0].id, "cafe")
        p.day_topic = "work"  # no theme plays it
        self.assertNotEqual(p.pick_theme()[0].id, "cafe")


def town_cur(known="en"):
    items = [
        {"id": "afsakid", "kind": "phrase", "target": "Afsakið.", "meaning": "Excuse me.", "topics": ["directions"]},
        {"id": "langt", "kind": "phrase", "target": "Er það langt?", "meaning": "Is it far?", "topics": ["directions"]},
        {"id": "takk", "kind": "phrase", "target": "Takk kærlega.", "meaning": "Thanks a lot.", "topics": ["social"]},
        {"id": "kaffi", "kind": "phrase", "target": "Kaffi, takk.", "meaning": "Coffee, please.", "topics": ["cafe"]},
    ]
    return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": known}, "items": items})


def town_theme():
    turns = [
        {"who": "you", "cue": "Stop someone.", "say": "Afsakið.", "items": ["afsakid"]},
        {"who": "partner", "say": "Já?", "meaning": "Yes?"},
        {"who": "you", "cue": "Ask if it's far.", "say": "Er það langt?", "items": ["langt"]},
        {"who": "partner", "say": "Nei.", "meaning": "No."},
        {"who": "you", "cue": "Thank them.", "say": "Takk kærlega.", "items": ["takk"]},
    ]
    return Theme(id="town", scenario="A8", title="Town", scene_line="You're in town.", topics=["directions"], levels=[{"goal": "Ask the way.", "turns": turns}])


class LevelInTheLessonThatTeachesItTests(unittest.TestCase):
    """#327: a level is played in the lesson that introduces its lines, not in a later lesson whose own new material is another scene's."""

    def learner(self):
        l = LearnerState("is", "en", "A1")
        l.lessons_completed = 6
        l.items["afsakid"] = ItemState(due="2026-03-20", successes=2, durable_successes=2, stage="meaning")
        return l

    def planner(self, minutes=10, new_items=3):
        cfg = PlanConfig(minutes=minutes, new_items=new_items, max_new_items=new_items, seed=1, themes=[town_theme()], theme_scenarios=["A8"])
        return Planner(town_cur(), self.learner(), Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def test_a_turn_whose_items_are_queued_today_counts_as_sayable_for_readiness(self):
        p = self.planner()
        self.assertTrue(p.learner.has_met("afsakid"))
        self.assertIsNone(p.pick_theme(), "two of three turns lack an item: not ready before the lesson")
        theme, level, heard = p.pick_theme(coming={"langt", "takk"})
        self.assertEqual((theme.id, level), ("town", 0))
        self.assertEqual(heard, {1, 2}, "the turns are still heard until their items are taught")
        self.assertIsNone(p.pick_theme(coming={"langt"}), "a turn whose item is not coming still keeps the level back")

    def test_a_level_whose_lines_come_today_beats_a_ready_level_that_teaches_nothing(self):
        """Lesson 40 of the lesson-33 replay: café 4 (every line known, scenario ranked first) and small talk 4 (its lines taught that lesson)
        were both ready at the same level; café 4 was played and small talk 4's lines, taught that day, had no scene until the next lesson."""
        known = Theme(id="cafe", scenario="A4", title="Café", scene_line="You're at a café.", topics=["cafe"], levels=[
            {"goal": "Say sorry.", "turns": [{"who": "you", "cue": "Say sorry.", "say": "Afsakið.", "items": ["afsakid"]}, {"who": "partner", "say": "Já?", "meaning": "Yes?"}]}])
        cfg = PlanConfig(minutes=10, new_items=3, max_new_items=3, seed=1, themes=[known, town_theme()], theme_scenarios=["A4", "A8"])
        p = Planner(town_cur(), self.learner(), Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        self.assertEqual(p.pick_theme()[0].id, "cafe", "nothing coming: the ranked scenario, as before")
        self.assertEqual(p.pick_theme(coming={"langt", "takk"})[0].id, "town", "the level whose lines this lesson teaches")

    def test_the_lesson_that_teaches_the_levels_lines_plays_it_and_asks_them_late(self):
        sc = self.planner(minutes=12, new_items=2).build()
        self.assertEqual((sc.meta["theme"]["id"], sc.meta["theme"]["level"]), ("town", 1))
        self.assertEqual(sorted(sc.meta["new_in_scene"]["in_turns"]), ["langt", "takk"])
        plays = [e for e in sc.exercises if e.kind == "dialogue" and "theme:town:1" in e.label]
        self.assertEqual(len(plays), 2)
        late = plays[-1]
        intros = {e.item_ids[0]: e.index for e in sc.exercises if e.kind == "intro" and e.item_ids}
        self.assertTrue(all(intros[i] < late.index for i in ("langt", "takk")), "both lines are taught before the late play")
        answers = [g.text for g in sc.segments if g.exercise == late.index and g.type == "answer"]
        self.assertIn("Er það langt?", answers, "the late play asks the line taught today")


class LessonGoalTests(unittest.TestCase):
    """#327: the goal of the level the lesson plays is said right after the opening, in the learner's language; a lesson with no theme has none."""

    def lesson(self, known="en", completed=6):
        theme = town_theme()
        theme.levels[0].goal_ja = "道を尋ねる。"
        l = LearnerState("is", known, "A1")
        l.lessons_completed = completed
        l.items["afsakid"] = ItemState(due="2026-03-20", successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=12, new_items=2, max_new_items=2, seed=1, themes=[theme], theme_scenarios=["A8"])
        return Planner(town_cur(known), l, Prompts.load(known), Timing(level="A1"), cfg, today=TODAY).build()

    def narrated(self, sc, ex):
        return [g.text for g in sc.segments if g.exercise == ex.index and g.type == "narrate"]

    def test_the_goal_is_said_right_after_the_opening(self):
        sc = self.lesson()
        self.assertEqual([e.label for e in sc.exercises[:2]], ["opening", "lesson goal"])
        self.assertEqual(self.narrated(sc, sc.exercises[1]), ["Today's goal: Ask the way."])
        self.assertEqual(sc.meta["theme"]["goal"], "Ask the way.")

    def test_the_goal_is_in_the_learners_language(self):
        sc = self.lesson("ja")
        self.assertEqual(self.narrated(sc, sc.exercises[1]), ["今日の目標：道を尋ねる。"])
        self.assertEqual(sc.meta["theme"]["goal"], "道を尋ねる。", "plan.json keeps the goal as it was said (review of #369)")

    def test_a_lesson_with_no_theme_has_no_goal(self):
        sc = self.lesson(completed=0)  # the first lesson keeps its rule: no theme, so no goal
        self.assertIsNone(sc.meta["theme"])
        self.assertFalse(any(e.label == "lesson goal" for e in sc.exercises))


class ClosingOrderTests(unittest.TestCase):
    """#327: the closing asks the items outside the scene first, hardest first, and ends on the played level's items in the order of its turns."""

    def test_the_order(self):
        cur = town_cur()
        by = cur.by_id
        kaffi, langt, takk = by["kaffi"], by["langt"], by["takk"]
        kaffi.difficulty, langt.difficulty, takk.difficulty = 1, 3, 1
        self.assertEqual([i.id for i in Planner.closing_order([takk, kaffi, langt], (town_theme(), 0, set()))], ["kaffi", "langt", "takk"],
                         "outside the scene first; then the turns' order, not the difficulty")
        self.assertEqual([i.id for i in Planner.closing_order([takk, kaffi, langt], None)], ["langt", "takk", "kaffi"], "no theme: hardest first, as before")

    def test_a_lesson_ends_on_its_scene(self):
        l = LearnerState("is", "en", "A1")
        l.lessons_completed = 6
        l.items["afsakid"] = ItemState(due="2026-03-20", successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=12, new_items=3, max_new_items=3, seed=1, themes=[town_theme()], theme_scenarios=["A8"])
        sc = Planner(town_cur(), l, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        start = next(e.index for e in sc.exercises if e.label == "final review")
        asked = [e.item_ids[0] for e in sc.exercises[start + 1:] if e.kind != "closing" and e.item_ids]
        self.assertTrue(asked, "the closing asked something")
        level_items = town_theme().levels[0].items
        self.assertIn(asked[-1], level_items, f"the last question is a line of the exchange: {asked}")
        inside = [i for i in asked if i in level_items]
        self.assertEqual(inside, sorted(inside, key=level_items.index), "in the order of the turns")


def bill_cur():
    """A café level whose second line is a linked phrase of a known pattern: it comes in as one sentence of the pattern (``embedded``), not
    through its own introduction (review of #365)."""
    items = [
        {"id": "afsakid", "kind": "phrase", "target": "Afsakið.", "meaning": "Excuse me.", "topics": ["cafe"]},
        {"id": "get_eg_fengid", "kind": "construction", "target": "Get ég fengið {thing}?", "meaning": "Could I have {thing}?", "topics": ["cafe"],
         "slots": {"thing": "acc_request"}, "example": {"thing": "matsedilinn"}},
        {"id": "matsedilinn", "kind": "vocab", "target": "matseðilinn", "meaning": "the menu", "tags": ["acc_request"], "topics": ["cafe"]},
        {"id": "reikninginn", "kind": "vocab", "target": "reikninginn", "meaning": "the bill", "tags": ["acc_request"], "topics": ["cafe"]},
        {"id": "get_eg_fengid_reikninginn", "kind": "phrase", "target": "Get ég fengið reikninginn?", "meaning": "Can I have the bill?", "topics": ["cafe"],
         "instance_of": "get_eg_fengid", "instance_fill": {"thing": "reikninginn"}},
    ]
    return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})


def bill_theme():
    turns = [
        {"who": "you", "cue": "Get the waiter's attention.", "say": "Afsakið.", "items": ["afsakid"]},
        {"who": "partner", "say": "Já?", "meaning": "Yes?"},
        {"who": "you", "cue": "Ask for the bill.", "say": "Get ég fengið reikninginn?", "items": ["get_eg_fengid_reikninginn"]},
        {"who": "partner", "say": "Já, auðvitað.", "meaning": "Yes, of course."},
    ]
    return Theme(id="bill", scenario="A4", title="Café", scene_line="You're at a café.", topics=["cafe"], levels=[{"goal": "Ask for the bill.", "turns": turns}])


class EmbeddedLineInTheExchangeTests(unittest.TestCase):
    """Review of #365: a line taught today inside a sentence of its pattern (``embedded``, not ``builder.in_lesson``) is asked in the late play,
    and the daily read counts it."""

    def build(self):
        l = LearnerState("is", "en", "A1")
        l.lessons_completed = 6
        for i in ("afsakid", "get_eg_fengid", "matsedilinn", "reikninginn"):
            l.items[i] = ItemState(due="2026-03-20", successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=12, new_items=1, max_new_items=1, seed=1, themes=[bill_theme()], theme_scenarios=["A4"])
        p = Planner(bill_cur(), l, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        return p, p.build()

    def test_an_embedded_line_is_asked_in_the_late_play_and_counted(self):
        p, sc = self.build()
        self.assertIn("get_eg_fengid_reikninginn", sc.meta["embedded_items"], "the phrase came in as a sentence of its pattern")
        self.assertEqual((sc.meta["theme"]["id"], sc.meta["theme"]["level"]), ("bill", 1))
        plays = [e for e in sc.exercises if e.kind == "dialogue" and "theme:bill:1" in e.label]
        self.assertEqual(len(plays), 2)
        self.assertIn("get_eg_fengid_reikninginn", plays[-1].item_ids, "asked in the late play, not only heard")
        self.assertNotIn("get_eg_fengid_reikninginn", plays[-1].heard_ids)
        self.assertEqual(sc.meta["new_in_scene"]["in_turns"], ["get_eg_fengid_reikninginn"])
        self.assertTrue(p.taught_today("get_eg_fengid_reikninginn"))

    def test_an_embedded_line_has_no_closing_recall_and_the_late_play_is_its_last_asking(self):
        """Review of #370: a linked phrase taught as a sentence of its pattern keeps #192's rule (no closing recall), so a lesson whose only new line of
        the exchange is one has no closing block; the exchange's late play is where the lesson last asks it."""
        p, sc = self.build()
        self.assertFalse(any(e.label == "final review" for e in sc.exercises), "nothing introduced on its own: no closing block")
        late = [e for e in sc.exercises if e.kind == "dialogue" and "theme:bill:1" in e.label][-1]
        self.assertIn("get_eg_fengid_reikninginn", late.item_ids)
        self.assertEqual([e.label for e in sc.exercises if e.index > late.index and "get_eg_fengid_reikninginn" in e.item_ids], [])

    def test_a_turn_only_heard_is_not_counted(self):
        p, sc = self.build()
        heard = {i for e in sc.exercises if e.kind == "dialogue" and "theme:bill:1" in e.label for i in e.heard_ids}
        self.assertFalse(heard & set(sc.meta["new_in_scene"]["in_turns"]))


if __name__ == "__main__":
    unittest.main()
