"""#439 (lesson 41: «kem/fer, í kvöld/á morgun の組み合わせ4種はただの入れ替えだから学習量としては４つ合わせてもとても軽い感じ»): four new items that make
four sentences got 20 asks, each item running its own ladder. A recall whose sentence says another of today's new items is that item's practice
too, and a pattern whose sentences its fillers' practice already said is practised as a substitution: their later timed recalls are not asked
again. Each item keeps its introduction, its first recall and the closing's; a phrase keeps its whole ladder."""
import unittest

import tests.test_parts_listening as course

FAMILY = {"eg_fer", "a_morgun", "i_kvold"}


class SharedPracticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = [(cur, sc) for cur, _, sc in cls._course(9)]

    @staticmethod
    def _course(lessons):
        """The listening course (``ListeningTaskTests._fresh_course``) with the trust check (#631) is off: this pins a substitution family's shared recalls, not which lines the table lets through."""
        import dataclasses
        from datetime import timedelta

        from audiolesson.cando import load_cando
        from audiolesson.content import load_curriculum
        from audiolesson.learner import LearnerState
        from audiolesson.planner import PlanConfig, Planner, apply_to_learner
        from audiolesson.prompts import Prompts
        from audiolesson.themes import load_themes, scenario_order
        from audiolesson.timing import Timing

        path = course.ROOT / "curricula" / "is-en"
        cur = dataclasses.replace(load_curriculum(path), trust=None)
        scenarios = load_cando(path)
        themes = load_themes(path, cur, scenarios)
        learner, day, out = LearnerState("is", "en", "A1"), course.TODAY, []
        for n in range(1, lessons + 1):
            cfg = PlanConfig(minutes=30, new_target=8, themes=themes, theme_scenarios=scenario_order(scenarios))
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            out.append((cur, learner, sc))
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        return out

    def test_a_substitution_family_is_not_asked_item_by_item(self):
        """The course's lesson 9 introduces «á morgun», «í kvöld» and «Ég fer {time}.»: 14 of its exercises asked their sentences before #439."""
        cur, sc = self.lessons[-1]
        family = [e for e in sc.exercises if FAMILY & set(e.item_ids) and e.kind in ("intro", "recall", "generative")]
        self.assertLessEqual(len(family), 10, [e.label for e in family])
        self.assertIn("eg_fer", sc.meta["shared_recalls"])
        own = [e for e in sc.exercises if e.item_ids and e.item_ids[0] == "eg_fer" and e.kind == "recall"]
        self.assertTrue(own and own[0].stage == "hinted", "the pattern's first recall is asked")
        self.assertTrue(any(e.stage == "meaning" for e in own[1:]), "and a later unhinted one")

    def test_plan_json_lists_the_shared_recalls(self):
        """Review of #442: the field reached the script's metadata only; ``plan.json`` is built field by field (``cli._plan``)."""
        from audiolesson.cli import _plan

        cur, sc = self.lessons[-1]
        self.assertEqual(_plan(sc, cur)["shared_recalls"], sc.meta["shared_recalls"])
        self.assertIn("eg_fer", _plan(sc, cur)["shared_recalls"])

    def test_a_phrase_is_passed_over_only_when_another_recall_said_it(self):
        """A phrase's own rungs are its spaced practice: no sentence count passes them; only a recall that said it for another item does
        («Hvenær?» inside «Hvenær leggjum við af stað?», as the closing counts it, #280)."""
        for cur, sc in self.lessons:
            new = set(sc.meta["new_items"])
            self.assertLessEqual(set(sc.meta["shared_recalls"]), new, "only today's new items")
            for i in set(sc.meta["shared_recalls"]):
                if cur.by_id[i].kind == "construction":
                    continue
                said_by_other = any(i in e.item_ids and e.item_ids[0] != i for e in sc.exercises if e.kind in ("recall", "generative"))
                self.assertTrue(said_by_other, f"lesson {sc.lesson_number}: {i}")

if __name__ == "__main__":
    unittest.main()
