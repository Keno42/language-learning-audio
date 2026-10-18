"""Lesson 29: «Say: I love a piece of cake.» and «Say: I love a salad.». A food's meaning is worded for ordering («a piece of cake», «a hot dog»), which
is wrong where the sentence says what one likes or eats in general. «Ég elska {food}.» and «Ég borða ekki {food}.» ask for each food's generic
English (``meaning_forms.generic``): «I love cake.», «I don't eat hot dogs.». The Icelandic does not change."""
import re
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum

ROOT = Path(__file__).resolve().parent.parent


class GenericMeaningTests(unittest.TestCase):
    def test_a_food_one_loves_or_does_not_eat_has_no_article(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for pid in ("eg_elska", "eg_borda_ekki"):
            c = cur.by_id[pid]
            for food in cur.items_with_tag("acc_food", c):
                meaning = cur.resolve_slots(c, {"food": food})[1]
                self.assertNotRegex(meaning, r"\b(a|an|a piece of)\s", (pid, food.id))
        c = cur.by_id["eg_elska"]
        self.assertEqual(cur.resolve_slots(c, {"food": cur.by_id["koku"]}), ("Ég elska köku.", "I love cake."))
        self.assertEqual(cur.resolve_slots(cur.by_id["eg_aetla_ad_fa"], {"thing": cur.by_id["koku"]})[1], "I'll have a piece of cake.", "ordering keeps its wording")


if __name__ == "__main__":
    unittest.main()
