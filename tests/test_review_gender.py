"""The written review names the speaker's form it expects, as the lesson does (lesson-30 feedback round: «I'm hungry» asked with no word of
whose answer is wanted, when «Ég er svöng.» and «Ég er svangur.» are both right).

The lesson says «As a woman: …» / «As a man: …» before every gendered answer. The review's own questions did not: an item's cue for the bot's
rewording (`audiolesson questions`) and for an open item, and a part asked through the sentence that holds it (`whole_for`)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from audiolesson.cli import _review_cue, _review_cues
from audiolesson.content import load_curriculum
from audiolesson.exercises import answer_gender, speak_as
from audiolesson.prompts import Prompts
from audiolesson.review_wholes import refine_review, whole_for
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


    def test_a_stored_whole_sentence_question_gets_its_form_when_the_review_is_refined(self):
        """Review of #375: a question kept from an earlier lesson as a whole sentence («How do you say: I'm hungry.» → «Ég er svöng.», items
        `svong_state`) never goes back through `whole_for`, and the bot's wording refresh does not match it (its answer is not the bare word). Refining
        the review names the form, the woman's and the man's alike, and corrects a wrong one; one already named, or with one form for both, is left as it is."""
        met = {"svong_state", "eg_er_state", "eg_er_svong", "bankinn", "hvar_er"}
        for prompt, answer, items, expected in (
            ("How do you say: I'm hungry.", "Ég er svöng.", ["svong_state"], "As a woman: How do you say: I'm hungry."),
            ("How do you say: I'm hungry.", "Ég er svangur.", ["svong_state"], "As a man: How do you say: I'm hungry."),
            ("As a man: Say: I'm hungry.", "Ég er svöng.", ["eg_er_svong"], "As a woman: Say: I'm hungry."),
            ("As a woman: Say: I'm hungry.", "Ég er svöng.", ["eg_er_svong"], "As a woman: Say: I'm hungry."),
            ("How do you say: Where is the bank?", "Hvar er bankinn?", ["bankinn"], "How do you say: Where is the bank?"),
        ):
            out, report = refine_review([{"items": items, "prompt": prompt, "answer": answer}], self.cur, met, self.prompts)
            self.assertEqual(out[0]["prompt"], expected, (prompt, answer))
            self.assertEqual(any(r["kind"] == "speaker_form" for r in report), expected != prompt, report)

    def test_a_pattern_sentence_stored_with_the_pattern_alone_gets_its_form(self):
        """Lesson 34: «svangur» was the answer and the question did not say a man's answer was wanted. A sentence of a pattern is stored with the
        pattern alone (items `eg_er_state`, as the plan stores «Mér finnst þetta dýrt.» under `mer_finnst_thetta`): the form is read from the
        pattern's fillers the answer holds. A filler with one form for both («einmana») names none."""
        for answer, expected in (
            ("Ég er svangur.", "As a man: In a sentence. Say: I'm hungry."),
            ("Ég er svöng.", "As a woman: In a sentence. Say: I'm hungry."),
            ("Ég er einmana.", "In a sentence. Say: I'm hungry."),
        ):
            out, _ = refine_review([{"items": ["eg_er_state"], "prompt": "In a sentence. Say: I'm hungry.", "answer": answer}], self.cur, {"eg_er_state"}, self.prompts)
            self.assertEqual(out[0]["prompt"], expected, answer)

    def test_the_bots_refine_review_command_names_the_form_of_its_stored_questions(self):
        stdin = json.dumps({"review": [{"items": ["svong_state"], "prompt": "How do you say: I'm hungry.", "answer": "Ég er svangur."}], "met": ["svong_state", "eg_er_state"]})
        with tempfile.TemporaryDirectory() as tmp:  # the bot passes its learner file; a missing one adds nothing to what `met` says
            out = subprocess.run([sys.executable, "-m", "audiolesson.cli", "refine-review", str(ROOT / "curricula" / "is-en"), "--learner", str(Path(tmp) / "learner.json")],
                                 input=stdin, capture_output=True, text=True, check=True, cwd=ROOT)
        data = json.loads(out.stdout)
        self.assertEqual(data["review"][0]["prompt"], "As a man: How do you say: I'm hungry.")
        self.assertIn("speaker_form", [r["kind"] for r in data["refined"]])

if __name__ == "__main__":
    unittest.main()
