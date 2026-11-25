"""#281 finding 1: the two searches for a part's sentence, in one place (``audiolesson/wholes.py``)."""
import unittest
from pathlib import Path

from audiolesson import wholes
from audiolesson.content import load_curriculum

IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


class WholesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)

    def test_a_line_holds_a_part_s_words_in_order_and_together(self):
        self.assertTrue(wholes.holds(wholes.words("Takk fyrir hjálpina."), ["hjálpina"]))
        self.assertTrue(wholes.holds(["þúsund", "krónur"], ["þúsund", "krónur"]), "the review counts a line as long as the part")
        self.assertFalse(wholes.holds(["þúsund", "krónur"], ["þúsund", "krónur"], longer=True), "an introduction needs a longer line")
        self.assertFalse(wholes.holds(["krónur", "þúsund"], ["þúsund", "krónur"]))
        self.assertFalse(wholes.holds(["takk"], []))

    def test_a_pattern_takes_the_part_and_fills_its_other_slots(self):
        part = self.cur.by_id["koku"] if "koku" in self.cur.by_id else next(i for i in self.cur.items if i.kind == "vocab" and i.tags)
        found = [(c.id, f) for c in self.cur.items if c.kind == "construction" and c.slots and (f := wholes.fill_slots(self.cur, c, part, lambda _: True))]
        self.assertTrue(found, "some pattern takes it")
        for cid, fills in found:
            c = self.cur.by_id[cid]
            self.assertEqual(set(fills), set(c.slots))
            self.assertIn(part, fills.values())
        self.assertFalse([c for c in self.cur.items if c.kind == "construction" and c.slots and len(c.slots) > 1
                          and wholes.fill_slots(self.cur, c, part, lambda _: False) is not None],
                         "a pattern with another slot and nothing accepted for it has no sentence")


if __name__ == "__main__":
    unittest.main()
