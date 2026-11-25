"""Review of #610: the visit's host could ask «Viltu kaffi eða te?» and the learner's reply was «Já, takk.», which picks neither. A partner line
a learner's yes or no answers asks a yes/no question in every wording: no «eða» (or) in any of its lines."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.themes import load_themes

IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


class SceneReplyTests(unittest.TestCase):
    def test_a_yes_or_no_answers_a_yes_no_question_in_every_variant(self):
        cur = load_curriculum(IS_EN)
        found, checked = [], 0
        for t in load_themes(IS_EN, cur, load_cando(IS_EN, cur)):
            for n, level in enumerate(t.levels, 1):
                for k in range(len(level.turns) - 1):
                    turn, reply = level.turns[k], level.turns[k + 1]
                    if turn.who != "partner" or reply.who != "you" or not reply.say.split()[0].strip(",.!") in ("Já", "Nei"):
                        continue
                    checked += 1
                    found += [(t.id, n, ln.say) for ln in turn.lines() if " eða " in f" {ln.say} "]
        self.assertGreater(checked, 5, "the check reads the yes/no replies")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
