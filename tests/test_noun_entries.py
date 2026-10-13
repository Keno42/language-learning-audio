"""#270 step 1: the nouns of the curriculum carry their gender and form."""
import re
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum

ROOT = Path(__file__).resolve().parent.parent
CASE = re.compile(r"^(nom|acc|dat|gen)_")
# vocab items with a case tag that are not nouns (counts and times that agree with a noun) or are not declined (borrowed words), authored on purpose
NOT_NOUNS = {"latte", "sushi", "pasta", "tokyo_dat", "osaka_dat"}


class NounDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def case_nouns(self):
        return [it for it in self.cur.items if it.kind == "vocab" and any(CASE.match(t) for t in it.tags)]

    def test_every_case_tagged_noun_has_a_noun_a_form_and_a_gender(self):
        bare = [it.id for it in self.case_nouns() if it.id not in NOT_NOUNS and not (it.noun and it.form and it.gender)]
        self.assertEqual(bare, [], "add noun, form and gender (#270 step 1), or list it as not a noun on purpose")

    def test_a_forms_case_is_one_of_its_tags_cases(self):
        wrong = []
        for it in self.case_nouns():
            if not it.form or it.form.startswith("pl"):  # the pilot's plural forms (krónur, norðurljósin) name number, not case
                continue
            tag_cases = {CASE.match(t).group(1) for t in it.tags if CASE.match(t)}
            if it.form.split("_")[0] not in tag_cases:
                wrong.append((it.id, it.form, sorted(tag_cases)))
        self.assertEqual(wrong, [])

    def test_a_nouns_forms_agree_about_its_gender_and_each_form_is_once(self):
        self.assertTrue(self.cur.nouns)
        for noun, entry in self.cur.nouns.items():
            self.assertIn(entry["gender"], ("masc", "fem", "neut"), noun)
            self.assertEqual(len(set(entry["forms"])), len(entry["forms"]))

    def test_the_forms_that_go_together_are_one_noun(self):
        for noun, forms in {"bill": {"nom", "acc"}, "kaffi": {"acc", "acc_def"}, "lykill": {"acc", "nom_def"}, "simi": {"acc", "nom_def"}, "hotel": {"nom_def", "dat_def"}}.items():
            self.assertEqual(set(self.cur.nouns[noun]["forms"]), forms, noun)

    def test_old_ids_resolve_to_their_noun_and_form(self):
        self.assertEqual(self.cur.noun_form("ulpu"), ("ulpa", "acc"))
        self.assertEqual(self.cur.noun_form("hotelinu"), ("hotel", "dat_def"))
        self.assertEqual(self.cur.noun_form("bil"), ("bill", "acc"))


if __name__ == "__main__":
    unittest.main()
