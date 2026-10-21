"""The written review names the speaker's form it expects, as the lesson does (lesson-30 feedback round: «I'm hungry» asked with no word of
whose answer is wanted, when «Ég er svöng.» and «Ég er svangur.» are both right).

The lesson says «As a woman: …» / «As a man: …» before every gendered answer. The review's own questions did not: an item's cue for the bot's
rewording (`audiolesson questions`) and for an open item, and a part asked through the sentence that holds it (`whole_for`)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from audiolesson.cli import _review_cue, _review_cues
from audiolesson.content import load_curriculum
from audiolesson.exercises import answer_gender, speak_as
from audiolesson.prompts import Prompts
from audiolesson.review_wholes import whole_for
from audiolesson.review_wording import lesson_cue_count, review_prompt

ROOT = Path(__file__).resolve().parent.parent


class ReviewNamesTheSpeakersFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.prompts = Prompts.load("en")

    def test_the_answer_gender_is_read_from_the_items_it_was_made_of(self):
        by = self.cur.by_id
        self.assertEqual(answer_gender("Ég er svöng.", by["eg_er_svong"]), "f")
        self.assertEqual(answer_gender("Ég er svangur.", by["eg_er_svong"]), "m")
        self.assertEqual(answer_gender("Ég er svangur.", by["eg_er_state"], by["svong_state"]), "m", "a fill's man's form")
        self.assertIsNone(answer_gender("Ég er frá Japan.", by["eg_er_svong"]), "the item's words are not in it")
        self.assertIsNone(answer_gender("Hvar er bankinn?", by["bankinn"]), "a word with one form for both")

    def test_an_items_review_cue_names_the_womans_form_it_expects(self):
        by = self.cur.by_id
        cue = _review_cue(self.cur, self.prompts, by["eg_er_svong"])
        self.assertEqual(cue, speak_as(self.prompts, "f", by["eg_er_svong"].situation_for(0)))
        self.assertTrue(cue.startswith("As a woman: "), cue)
        self.assertFalse(_review_cue(self.cur, self.prompts, by["bankinn"]).startswith("As a "), "no form to name")

    def test_every_current_cue_names_it_so_the_bot_rewords_a_stored_question_without_it(self):
        """The bot replaces a stored one-item question whose prompt is none of the current cues (site_update_notifier `refresh_wording`): the
        lesson's own «As a woman: Say: I'm hungry.» is one of them now, and a stored «Say: I'm hungry.» is not."""
        cues = _review_cues(self.cur, self.prompts, self.cur.by_id["eg_er_svong"])
        self.assertTrue(cues and all(c.startswith("As a woman: ") for c in cues), cues)
        self.assertIn("As a woman: Say: I'm hungry.", cues)
        self.assertNotIn("Say: I'm hungry.", cues)

    def test_the_questions_command_gives_the_bot_the_named_form(self):
        out = subprocess.run([sys.executable, "-m", "audiolesson.cli", "questions", str(ROOT / "curricula" / "is-en"), "--ids", "eg_er_svong,bankinn"],
                             capture_output=True, text=True, check=True, cwd=ROOT)
        data = json.loads(out.stdout)
        self.assertTrue(data["eg_er_svong"]["prompt"].startswith("As a woman: "))
        self.assertEqual(data["eg_er_svong"]["answer"], "Ég er svöng.")
        self.assertFalse(data["bankinn"]["prompt"].startswith("As a "))

    def test_a_part_asked_through_its_sentence_names_the_form(self):
        by = self.cur.by_id
        whole = whole_for(self.cur, by["svong_state"], {"eg_er_state", "svong_state"}, self.prompts)
        self.assertEqual(whole["answer"], "Ég er svöng.")
        self.assertTrue(whole["prompt"].startswith("As a woman: "), whole)
        taught = {"through": "eg_er_state", "answer": "Ég er svangur.", "meaning": "I'm hungry."}
        as_taught = whole_for(self.cur, by["svong_state"], {"svong_state"}, self.prompts, taught)
        self.assertEqual(as_taught["answer"], "Ég er svangur.")
        self.assertTrue(as_taught["prompt"].startswith("As a man: "), as_taught)

    def test_a_lesson_cue_behind_the_form_is_reworded_and_counted_and_the_form_stays(self):
        self.assertEqual(review_prompt("As a man: In a sentence. Say: I'm full.", self.prompts, "is"), "As a man: How do you say: I'm full.")
        self.assertEqual(review_prompt("As a woman: Your host offers a third helping. Say you're full.", self.prompts, "is"),
                         "As a woman: Your host offers a third helping. Say you're full.", "a situation stays")
        self.assertEqual(lesson_cue_count([{"prompt": "As a man: In a sentence. Say: I'm full."}], self.prompts), 1)


if __name__ == "__main__":
    unittest.main()
