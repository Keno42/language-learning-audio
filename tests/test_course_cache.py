"""The guard on ``tests/course_cache.py``: a cached course is the course a test would have built itself.

Each recipe that goes through the cache is built through it short and then extended (as the tests take it, 9 lessons and then more), and
compared lesson by lesson with a fresh build read as it is handed out: the script, its meta and the learner. A recipe whose lessons stopped
being a pure function of their arguments fails here and not as a puzzling difference in another test.

The cache hands out each lesson as it stood when the recipe yielded it. A fresh build shares one learner between its steps, so a test that
kept a step's learner past the next step would read a later state; no test does (each reads it inside its own step), and a test that
needs the learner after a lesson takes the next step's.
"""
import json
import unittest

from tests import course_cache
from tests import test_parts_listening as listening  # the modules, not their classes: their tests run in their own files
from tests import test_sayable_forms as sayable

# (key, recipe, a short course, the longer one the tests take after it)
RECIPES = [
    ("listening-30", listening.ListeningTaskTests._fresh_course, 4, 9),
    ("short-items-30", sayable.ShortItemRepetitionTests._fresh_course, 3, 7),
]


def _seen(step) -> str:
    """What a test reads from one lesson: the script whole, and the learner where the recipe hands it out."""
    out = []
    for x in step[1:]:
        out.append(json.dumps(x.to_dict(), sort_keys=True, default=str))
        if hasattr(x, "transcript"):
            out.append(x.transcript())
    return "\n".join(out)


class CourseCacheTests(unittest.TestCase):
    def test_a_cached_course_extended_is_the_fresh_course(self):
        for key, recipe, short, longer in RECIPES:
            with self.subTest(key):
                course_cache._STORE.pop(key, None)  # from lesson 1, whatever ran before in this process
                list(course_cache.take(key, recipe, short))
                cached = list(course_cache.take(key, recipe, longer))
                fresh = [_seen(step) for step in recipe(longer)]  # each lesson as it is handed out
                self.assertEqual(len(cached), longer)
                for n, (a, b) in enumerate(zip(cached, fresh), 1):
                    self.assertEqual(_seen(a), b, f"{key}, lesson {n}")

    def test_what_one_test_changes_no_other_test_reads(self):
        key, recipe, short, _ = RECIPES[0]
        first = list(course_cache.take(key, recipe, short))
        before = _seen(first[-1])
        cur, learner, sc = first[-1]
        sc.exercises.clear()
        sc.segments.clear()
        learner.items.clear()
        cur.items.clear()
        again = list(course_cache.take(key, recipe, short))
        self.assertEqual(_seen(again[-1]), before)
        self.assertTrue(again[-1][0].items)

    def test_one_call_shares_its_curriculum_as_the_recipe_does(self):
        key, recipe, short, _ = RECIPES[0]
        lessons = list(course_cache.take(key, recipe, short))
        self.assertTrue(all(cur is lessons[0][0] for cur, _, _ in lessons))


if __name__ == "__main__":
    unittest.main()
