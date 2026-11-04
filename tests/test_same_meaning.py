"""Lesson 47: «It's raining.» cued both «Það rignir.» and the weather pattern's «Það er rigning.», and «I'm coming …» both «Ég er að koma!» and
«Ég kem …»: from the English the learner could not tell which answer was asked. Two different answers never share a meaning, in any language of the
curriculum (`content.same_meaning_answers`, checked by `validate`)."""
import unittest
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum, same_meaning_answers

ROOT = Path(__file__).resolve().parent.parent


def cur(items):
    return curriculum_from_dict({"curriculum": {"name": "t", "target_lang": "is", "known_lang": "en"}, "items": items})


WEATHER = [
    {"id": "thad_rignir", "kind": "phrase", "target": "Það rignir.", "meaning": "It's raining."},
    {"id": "thad_er_weather", "kind": "construction", "target": "Það er {weather}.", "meaning": "It's {weather}.", "slots": {"weather": "weather"},
     "example": {"weather": "kalt"}},
    {"id": "kalt", "kind": "vocab", "target": "kalt", "meaning": "cold", "tags": ["weather"]},
    {"id": "rigning", "kind": "vocab", "target": "rigning", "meaning": "raining", "tags": ["weather"]},
]


class SameMeaningTests(unittest.TestCase):
    def test_a_pattern_sentence_and_a_phrase_with_one_meaning_are_found(self):
        found = same_meaning_answers(cur(WEATHER))
        self.assertEqual([m for m, _ in found], ["it's raining"])
        self.assertEqual(len(found[0][1]), 2, found)

    def test_a_meaning_that_tells_them_apart_or_an_excluded_fill_passes(self):
        apart = [dict(i) for i in WEATHER]
        apart[3]["meaning_forms"] = {"in_sentence": "rainy"}
        self.assertEqual(same_meaning_answers(cur(apart)), [])
        excluded = [dict(i) for i in WEATHER]
        excluded[1]["exclude_fills"] = ["rigning"]
        self.assertEqual(same_meaning_answers(cur(excluded)), [])

    def test_a_spoken_meaning_is_the_cue_and_is_compared_too(self):
        """Review of #484: two phrases with different written glosses and one ``meaning_spoken`` were both cued «Say: It's raining.»."""
        spoken = [
            {"id": "a", "kind": "phrase", "target": "Það rignir.", "meaning": "It's raining (now).", "meaning_spoken": "It's raining."},
            {"id": "b", "kind": "phrase", "target": "Það er rigning.", "meaning": "It's raining (rain).", "meaning_spoken": "It's raining."},
        ]
        found = same_meaning_answers(cur(spoken))
        self.assertEqual([m for m, _ in found], ["it's raining"], found)

    def test_the_same_answer_twice_is_not_a_clash(self):
        twice = WEATHER[:3] + [{"id": "thad_er_kalt", "kind": "phrase", "target": "Það er kalt.", "meaning": "It's cold."}]
        self.assertEqual(same_meaning_answers(cur(twice)), [])

    def test_the_curriculum_has_none_in_any_of_its_languages(self):
        path = ROOT / "curricula" / "is-en"
        for lang in load_curriculum(path).known_langs:
            self.assertEqual(same_meaning_answers(load_curriculum(path, known_lang=lang)), [], lang)


if __name__ == "__main__":
    unittest.main()
