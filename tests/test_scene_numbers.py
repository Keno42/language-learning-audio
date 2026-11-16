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

    def test_every_number_a_partner_says_in_an_exchange_has_another_value(self):
        """#451's remaining data: eighteen partner turns said one value in every play («Það gera tvö þúsund krónur.», «svona tíu mínútur», «klukkan
        átta»), so the rotation of #520 had nothing to rotate outside the hotel desk and the bus. Every partner turn that says a number has a line
        with another, except the one that says the learner's own order back (three hot dogs stay three); a `repeat` says the line before it,
        as picked."""
        echo = {("cafe", 5, "Þrjár með öllu. Eitthvað að drekka?")}
        one_value = [
            (t.id, n + 1, turn.say) for t in self.themes for n, level in enumerate(t.levels) for turn in level.turns
            if turn.who == "partner" and not turn.repeat and number_words(turn.say)
            and len({tuple(number_words(ln.say)) for ln in turn.lines()}) < 2
        ]
        self.assertEqual(set(one_value), echo)

    def test_the_cheaper_hat_is_cheaper_whatever_the_two_prices_said(self):
        """The clothes shop's two prices rotate apart: «Þessi er ódýrari» must hold for every pair, so the first hat is six thousand or more and the
        second under four."""
        level = self.level("clothes", 0)
        first = next(t for t in level.turns if "mjög hlý" in t.say)
        second = next(t for t in level.turns if "ódýrari" in t.say)
        thousands = {"tvö": 2, "þrjú": 3, "sex": 6, "átta": 8, "níu": 9}
        for a in first.lines():
            for b in second.lines():
                self.assertGreater(thousands[number_words(a.say)[0]], thousands[number_words(b.say)[0]] + 1, (a.say, b.say))

    def test_a_turns_number_as_written_rests_behind_its_values_never_said(self):
        """On the replay of lesson 54's export seven of the ten number lines the heard exchanges said kept the old value: the record of the
        exchanges' lines began with #520, so a value never said tied with the one every late play had said. The lines that say their turn's number
        as written are known (the line as written, its other wordings; «hálf sjö» is not «sjö»), and the planner ranks one with no record
        behind the turn's other values."""
        from audiolesson.themes import written_value_lines

        written = written_value_lines(self.themes)
        self.assertIn("Það gera tvö þúsund krónur.", written)
        self.assertIn("Tvö þúsund krónur, takk.", written)
        self.assertNotIn("Það gera níu hundruð og fimmtíu krónur.", written)
        self.assertIn("Frábært. Klukkan sjö, við sundlaugina.", written)
        self.assertNotIn("Frábært. Klukkan hálf sjö, við sundlaugina.", written)
        level = self.level("supermarket", 0)
        k = next(k for k, t in enumerate(level.turns) if "tvö þúsund" in t.say)
        tired = lambda say: (0, say in written, 0)  # noqa: E731  (the planner's key for lines with no record and rested words)
        for seed in range(20):
            say = level.turns[k].lines()[pick_variants(level, random.Random(seed), tired=tired, as_written_too=True)[k]].say
            self.assertNotIn("tvö þúsund", say.lower(), seed)

    def test_every_answer_of_a_scene_line_is_made_of_words_the_course_teaches(self):
        """Review of #520: the second code said «núll», a word of no item, so `partner_pick_out` could never ask it. An answer the learner is to say
        back holds only words some item teaches, in every line of every scene (as written, a variant, a listening line)."""
        from audiolesson.text import WORD

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        taught = {w.lower() for i in cur.items for text in (i.target, i.target_m or "") for w in WORD.findall(text)}
        untaught = [
            (t.id, n + 1, p["answer"]) for t in self.themes for n, level in enumerate(t.levels) for turn in level.turns if turn.who == "partner"
            for ln in [*turn.lines(), *turn.listen_lines()] for p in ln.probes if any(w.lower() not in taught for w in WORD.findall(p["answer"]))
        ]
        self.assertEqual(untaught, [])

    def test_an_exchange_says_the_number_whose_words_have_rested(self):
        level = self.level("hotel", 0)
        for seed in range(8):
            self.assertIn("hundrað og fimmtán", self.room(pick_variants(level, random.Random(seed), tired=tired_of("þrjú", "sex"))), seed)
            self.assertIn("þrjú hundruð og sex", self.room(pick_variants(level, random.Random(seed), tired=tired_of("hundrað", "fimmtán"))), seed)

    def test_a_turns_own_last_value_rests_before_its_words_are_weighed(self):
        """On the replay of lesson 53's export with words alone, «herbergi hundrað og fimmtán» came four lessons running: «þrjú», «hundruð» and
        «sex» are said all through a lesson, «fimmtán» hardly. The line an exchange said longest ago comes first, then the words."""
        level = self.level("hotel", 0)
        last = {"fimmtán": 54, "sex": 53, "tólf": 55}  # the lesson an exchange last said each room
        words = tired_of("þrjú", "hundruð", "sex")
        tired = lambda say: (next((at for w, at in last.items() if w in say), 0), words(say))
        for seed in range(8):
            self.assertIn("þrjú hundruð og sex", self.room(pick_variants(level, random.Random(seed), tired=tired, as_written_too=True)), seed)

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
