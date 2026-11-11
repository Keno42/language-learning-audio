"""#451 step 3d: the number a scene's exchange says rotates, as a pick-out's does (step 3)."""
import random
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.numbers import number_words
from audiolesson.themes import Level, Turn, load_themes, pick_variants

ROOT = Path(__file__).resolve().parent.parent


def tired_of(*words):
    return lambda say: sum(w in words for w in number_words(say))


class SceneNumberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cur, load_cando(ROOT / "curricula" / "is-en", cur))

    def level(self, theme, n):
        return next(t for t in self.themes if t.id == theme).levels[n]

    def room(self, picks):
        level = self.level("hotel", 0)
        k = next(k for k, t in enumerate(level.turns) if "herbergi" in t.say)
        return level.turns[k].lines()[picks.get(k, 0)].say

    def test_the_hotel_desk_and_the_bus_have_other_numbers_to_say(self):
        """Lesson 53: «herbergi tvö hundruð og tólf» in each of the hotel desk's three exchanges, and on the replay in each of the next four
        lessons. The room, the breakfast hours, check-out, the code and the fare each have another value the exchange can say."""
        for theme, n, word in (("hotel", 0, "herbergi"), ("hotel", 0, "Morgunmatur"), ("hotel", 1, "Klukkan"), ("hotel", 1, "Lykilorðið"), ("bus", 0, "krónur")):
            turn = next(t for t in self.level(theme, n).turns if t.who == "partner" and word in t.say)
            values = {tuple(number_words(ln.say)) for ln in turn.lines()}
            self.assertGreater(len(values), 1, (theme, n, word))
            for ln in turn.lines():
                self.assertTrue(ln.probes and ln.meaning and ln.meaning_ja, ln.say)

    def test_an_exchange_says_the_number_whose_words_have_rested(self):
        level = self.level("hotel", 0)
        for seed in range(8):
            self.assertIn("hundrað og fimmtán", self.room(pick_variants(level, random.Random(seed), tired=tired_of("þrjú", "sex"))), seed)
            self.assertIn("þrjú hundruð og sex", self.room(pick_variants(level, random.Random(seed), tired=tired_of("hundrað", "fimmtán"))), seed)

    def test_the_early_play_never_says_the_line_as_written_and_a_play_heard_again_may(self):
        """The lesson's late play says the lines as written (#134), so its early play takes another value however tired; a level heard again as
        spare time has no late play, and says the line as written when its numbers have rested longest."""
        level = self.level("hotel", 0)
        tired = tired_of("þrjú", "sex", "hundrað", "fimmtán")
        for seed in range(8):
            self.assertNotIn("tólf", self.room(pick_variants(level, random.Random(seed), tired=tired)), seed)
            self.assertIn("tólf", self.room(pick_variants(level, random.Random(seed), tired=tired, as_written_too=True)), seed)
        self.assertEqual(pick_variants(level, random.Random(0), canonical=True, tired=tired), {}, "the late play: as written")

    def test_a_replays_early_play_takes_the_rested_one_of_the_wordings_heard(self):
        level = self.level("hotel", 0)
        k = next(k for k, t in enumerate(level.turns) if "herbergi" in t.say)
        heard = {(k, 1), (k, 2)}
        for seed in range(8):
            self.assertEqual(pick_variants(level, random.Random(seed), heard=heard, tired=tired_of("þrjú", "sex"))[k], 2, seed)

    def test_a_turn_whose_lines_say_the_same_number_or_none_is_picked_as_before(self):
        same = Level(goal="g", turns=[
            Turn("partner", "Klukkan ellefu.", variants=[{"say": "Útritun er klukkan ellefu."}, {"say": "Það er klukkan ellefu."}]),
            Turn("partner", "Já.", variants=[{"say": "Já, já."}, {"say": "Jú."}]),
        ])
        for seed in range(8):
            self.assertEqual(pick_variants(same, random.Random(seed), tired=tired_of("ellefu")), pick_variants(same, random.Random(seed)), seed)


if __name__ == "__main__":
    unittest.main()
