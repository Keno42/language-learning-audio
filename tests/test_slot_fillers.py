"""#579 step 2 (H5; the owner, 2026-11-22: «similar lines apart»): lessons 62–65 taught the illness fillers of «Ég er með {…}» three to five a
lesson («höfuðverk», «hita», «flensu», «magaverk» …), and they were the next-day failures (6 of lesson 63's 7 weak items). On the replay of lesson
66's export, lesson 68 would teach seven family fillers of «Þetta er {person}.» together. At most ``PlanConfig.max_slot_fillers`` (2) new fillers
of one slot come in a lesson, counting its earlier arcs, unless the theme's next level wants them; the rest wait a lesson, and other items take
the places."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import Level, Theme, Turn
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class SlotFillerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.people = [i for i in cls.cur.items if "person" in i.tags and i.kind != "construction"]
        first = min(i.order for i in cls.people)
        cls.learner = LearnerState("is", "en", "A1")
        for i in cls.cur.items:  # everything before the family module known, so its fillers are next in the course
            if i.order < first and "person" not in i.tags and not i.command:
                cls.learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                    recalled=2, last_outcome="recalled", interval_days=3,
                                                    last_practiced=(TODAY - timedelta(days=1)).isoformat())

    def _pick(self, exclude=None, **cfg) -> list[str]:
        cfg = {"minutes": 30, "new_items": 8, "seed": 1, "priority": ["thetta_er_person"] + [i.id for i in self.people], **cfg}
        planner = Planner(self.cur, self.learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(**cfg), today=TODAY)
        return [i.id for i in planner.select_new(8, exclude=exclude)]

    def _people(self, ids) -> list[str]:
        return [i for i in ids if "person" in self.cur.by_id[i].tags and self.cur.by_id[i].kind != "construction"]

    def test_at_most_two_fillers_of_one_slot_a_lesson(self):
        self.assertGreaterEqual(len(self.people), 7, "the family module has a slot's worth of fillers")
        ids = self._pick()
        self.assertEqual(len(self._people(ids)), 2, ids)
        self.assertIn("thetta_er_person", ids, "the pattern comes with its two fillers")
        self.assertGreaterEqual(len(ids), 8, "the pace is unchanged: other items take the places")
        self.assertGreater(len(self._people(self._pick(max_slot_fillers=99))), 2, "without the limit, the slot's fillers come together")

    def test_the_lesson_s_earlier_arcs_count(self):
        two = self._people(self._pick())
        self.assertEqual(self._people(self._pick(exclude=set(two))), [], "a later arc of the same lesson takes no third")

    def test_the_fillers_a_theme_level_wants_are_exempt(self):
        """A level that asks for three family members gets all three: the scene holds them apart (H4, «unless the played level asks»)."""
        wanted = [i.id for i in self.people[:3]]
        level = Level(goal="g", partner_speaker="native_c",
                      turns=[Turn(who="you", say=self.cur.by_id[w].target, cue="Introduce them.", items=[w]) for w in wanted])
        theme = Theme(scene_line="At a family dinner.", id="family_test", scenario="A1", title="Family", levels=[level])
        ids = self._pick(themes=[theme], theme_scenarios=["A1"])
        self.assertTrue(set(wanted) <= set(ids), ids)


if __name__ == "__main__":
    unittest.main()
