"""``Curriculum.takes`` is ``item in items_with_tag(tag, construction)`` asked of the item alone, without the list: the planner asks it of every
pattern of the course for every part it places, and the list (every item read, then compared field by field) was most of a lesson's build time.
The answer is the list's, for every slot and item of the real courses, for an equal copy of an item and for one that differs."""
import copy
import dataclasses
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum

ROOT = Path(__file__).resolve().parent.parent


class SlotTakesTests(unittest.TestCase):
    def test_every_slot_of_the_courses_takes_what_its_list_holds(self):
        for path, lang in ((ROOT / "curricula" / "is-en", None), (ROOT / "curricula" / "is-en", "ja"), (ROOT / "curricula" / "fr-en-a1.toml", None)):
            cur = load_curriculum(path, known_lang=lang)
            patterns = [c for c in cur.items if c.kind == "construction" and c.slots]
            self.assertTrue(patterns)
            for c in patterns:
                for tag in c.slots.values():
                    for of in (c, None):  # the pattern's own fills (``exclude_fills``, the reflexive ones of a line said to someone), and the tag's
                        listed = {i.id for i in cur.items_with_tag(tag, of)}
                        self.assertEqual({i.id for i in cur.items if cur.takes(tag, of, i)}, listed, (path.name, lang, c.id, tag, of is None))

    def test_an_equal_copy_is_taken_and_a_changed_one_is_not(self):
        """What ``in`` does with a list of items: equal by every field, not by identity or by id alone."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        c = cur.by_id["eg_vil"]
        tag = c.slots["inf"]
        fills = cur.items_with_tag(tag, c)
        fill = fills[0]
        other = next(i for i in cur.items if tag not in i.tags)
        changed = dataclasses.replace(fill, meaning=fill.meaning + ", changed")
        stranger = dataclasses.replace(fill, id="not_in_the_course")
        for item in (fill, copy.copy(fill), other, changed, stranger):
            self.assertEqual(cur.takes(tag, c, item), item in fills, item.id)
        self.assertTrue(cur.takes(tag, c, copy.copy(fill)))
        self.assertFalse(cur.takes(tag, c, changed))
        self.assertFalse(cur.takes(tag, c, stranger))


if __name__ == "__main__":
    unittest.main()
