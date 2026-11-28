"""#627: an item's own words where they differ from its meaning («Ég hef það gott.»: "I have it good" for "I'm doing well"), authored as
``Item.literal``. The introduction says them once after the first model; the written review carries them beside the answer (``literal``), for
the bot to show once the answer is shown, not before: before, they would give the answer away. ``validate`` lists the candidates."""
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum, validate
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.literal import candidates, with_literal_words
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
LITERAL = {"en": "I miss the family.", "ja": "家族を恋しく思う。"}


def course(lang: str, literal_ja: bool = True):
    cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
    it = cur.by_id["eg_sakna_fjolskyldunnar"]
    it.literal = LITERAL[lang] if lang == "en" or literal_ja else ""
    return cur, it


class LiteralTests(unittest.TestCase):
    def test_the_introduction_says_it_once_after_the_first_model(self):
        for lang in ("en", "ja"):
            cur, it = course(lang)
            prompts = Prompts.load(lang)
            sc = Script(1, "t", "is", lang)
            Builder(cur, prompts, Timing(level="A1"), LearnerState("is", lang, "A1")).intro(sc, it)
            said = [(g.type, g.text) for g in sc.segments if g.type in ("narrate", "speak")]
            line = prompts.get("literal_intro", literal=LITERAL[lang])
            self.assertEqual([t for _, t in said].count(line), 1, lang)
            at = said.index(("narrate", line))
            self.assertEqual(said[at - 1], ("speak", it.target), "right after the first model")

    def test_an_item_without_one_says_nothing_new(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        prompts = Prompts.load("en")
        sc = Script(1, "t", "is", "en")
        Builder(cur, prompts, Timing(level="A1"), LearnerState("is", "en", "A1")).intro(sc, cur.by_id["eg_sakna_fjolskyldunnar"])
        self.assertFalse(any(g.text.startswith("Word for word") for g in sc.segments if g.type == "narrate"))

    def test_the_review_carries_it_beside_the_answer_not_in_the_prompt(self):
        cur, it = course("en")
        q = {"items": [it.id], "prompt": "Say you miss your family.", "answer": it.target}
        out = with_literal_words(cur, [q, {**q, "answer": "Ég sakna fjölskyldunnar minnar heima."}, {**q, "items": [it.id, "takk"]}])
        self.assertEqual(out[0]["literal"], LITERAL["en"])
        self.assertEqual(out[0]["prompt"], q["prompt"], "the prompt is unchanged: the literal words would give the answer away")
        self.assertEqual(out[1]["literal"], "", "a longer answer is not the item's words")
        self.assertEqual(out[2]["literal"], "")

    def test_a_question_that_came_in_with_one_is_worked_out_afresh(self):
        """Review of #640: a queued question carrying a literal, refined to a longer answer or after the literal was removed, kept the old one."""
        cur, it = course("en")
        old = {"items": [it.id], "prompt": "Say you miss your family.", "answer": it.target, "literal": "stale words"}
        self.assertEqual(with_literal_words(cur, [old])[0]["literal"], LITERAL["en"])
        self.assertEqual(with_literal_words(cur, [{**old, "answer": "Ég sakna fjölskyldunnar minnar."}])[0]["literal"], "")
        it.literal = ""
        self.assertEqual(with_literal_words(cur, [old])[0]["literal"], "", "removed: \"\" tells the bot to drop the stored one")

    def test_a_japanese_lesson_without_its_own_literal_says_none(self):
        """A literal authored only in English is not said in a Japanese lesson: none rather than English in Japanese."""
        raw = {"curriculum": {"name": "t", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "phrase", "target": "Ég hef það gott.", "meaning": "I'm doing well.", "meaning_ja": "元気です。",
                          "literal": "I have it good."}]}
        self.assertEqual(curriculum_from_dict(raw).by_id["a"].literal, "I have it good.")
        self.assertEqual(curriculum_from_dict(raw, known_lang="ja").by_id["a"].literal, "")
        raw["items"][0]["literal_ja"] = "それを良く持っている。"
        self.assertEqual(curriculum_from_dict(raw, known_lang="ja").by_id["a"].literal, "それを良く持っている。")

    def test_validate_takes_it_on_a_phrase_or_a_word_only(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        cur.by_id["hvad_kostar"].literal = "What costs {item}?"
        with self.assertRaises(CurriculumError):
            validate(cur)
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        it = cur.by_id["eg_hef_thad_gott"]
        it.literal = it.meaning
        with self.assertRaises(CurriculumError, msg="the same words as the meaning are no literal"):
            validate(cur)

    def test_the_candidates_are_the_items_whose_meaning_says_words_the_target_lacks(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        found = {it.id: lack for it, lack in candidates(cur)}
        self.assertEqual(found.get("eg_hef_thad_gott"), ["i'm"])
        self.assertEqual(found.get("eg_sakna_fjolskyldunnar"), ["my"])
        self.assertNotIn("eg_er_svong", found, "«Ég er svöng.» says «I'm»")
        self.assertNotIn("eg_skil_ekki", found, "«Ég skil ekki.» says «don't»")
        cur.by_id["eg_hef_thad_gott"].literal = "I have it good."
        self.assertNotIn("eg_hef_thad_gott", {it.id for it, _ in candidates(cur)}, "an authored one is no longer a candidate")
        self.assertEqual(candidates(load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")), [], "the rules read English meanings")


if __name__ == "__main__":
    unittest.main()
