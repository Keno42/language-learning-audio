"""The owner, 2026-11-26: «a question whose answer I could not have known» still comes up in the written review. The audit of lessons 50–68's
review found the cue fixed by its «Literally:» line almost everywhere; what was left were two right lines, one of them shown: «Mig vantar
símkort.» where every other «need» is «Ég þarf …», «Ég vil sjá lunda.» beside «Mig langar að sjá eldfjall.». A question now carries the other
answers it accepts (``also``), and the bot shows them beside the answer."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.review_wholes import also_answers, with_also

ROOT = Path(__file__).resolve().parent.parent
IS_EN = ROOT / "curricula" / "is-en"


class ReviewAlsoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)

    def test_an_item_s_alternatives_go_with_its_line(self):
        self.assertEqual(also_answers(self.cur, ["eg_tharf_simkort"], "Mig vantar símkort."), ["Ég þarf símkort."])
        self.assertEqual(also_answers(self.cur, ["eg_tharf_simkort"], "Something else."), [], "only for the item's own line")
        self.assertEqual(also_answers(self.cur, ["eg_datt"], "Ég datt."), [], "an item with none")

    def test_a_pattern_s_alternative_is_filled_with_the_answer_s_own_words(self):
        self.assertEqual(also_answers(self.cur, ["mig_langar_ad_sja", "eldfjall"], "Mig langar að sjá eldfjall."), ["Ég vil sjá eldfjall."])

    def test_the_review_carries_them_and_leaves_the_rest_as_it_was(self):
        review = [{"items": ["eg_vil_sja_lunda"], "prompt": "p", "answer": "Ég vil sjá lunda."}, {"items": ["eg_datt"], "prompt": "q", "answer": "Ég datt."}]
        out = with_also(self.cur, review)
        self.assertEqual(out[0]["also"], ["Mig langar að sjá lunda."])
        self.assertNotIn("also", out[1])

    def test_a_part_asked_through_its_whole_gets_the_whole_s_alternatives(self):
        """Review of #613: «eldfjall» reviewed through «Mig langar að sjá eldfjall.» names the pattern in ``through``, not in ``items``."""
        from audiolesson.prompts import Prompts
        from audiolesson.review_wholes import refine_review

        met = {"mig_langar_ad_sja", "eldfjall"}
        review, _ = refine_review([{"items": ["eldfjall"], "prompt": "How do you say: A volcano.", "answer": "eldfjall"}], self.cur, met, Prompts.load("en"))
        q = next(q for q in review if "eldfjall" in q["items"])
        self.assertEqual(q.get("through"), "mig_langar_ad_sja", q)
        self.assertEqual(with_also(self.cur, [q])[0]["also"], ["Ég vil sjá eldfjall."])

    def test_one_scene_one_frame(self):
        """«Say you want to see puffins.» → «Ég vil …», so the volcano's «Mig langar …» is asked with «you'd like to», as its meaning says."""
        q = json.loads(subprocess.run([sys.executable, "-m", "audiolesson.cli", "questions", str(IS_EN), "--ids", "eg_tharf_simkort"],
                                      capture_output=True, text=True, cwd=ROOT, check=True).stdout)
        self.assertEqual(q["eg_tharf_simkort"]["also"], ["Ég þarf símkort."])
        c = self.cur.by_id["mig_langar_ad_sja"]
        self.assertIn("you'd like to see", c.situation)


if __name__ == "__main__":
    unittest.main()
