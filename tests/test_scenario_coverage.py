"""The scenarios' outcome in `validate` (#327): what of a Tier A/B scenario a theme level's learner line says, and the cards that
ask a level's goal."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.cli import main
from audiolesson.content import load_curriculum
from audiolesson.scenes import load_scenes, unasked_levels, unknown_levels
from audiolesson.themes import load_themes, scenario_coverage, unranked_themes

COURSE = '[curriculum]\nname = "x"\ntarget_lang = "is"\nknown_lang = "en"\n' + "".join(
    f'\n[[items]]\nid = "{i}"\nkind = "vocab"\ntarget = "{t}"\nmeaning = "{m}"\n'
    for i, t, m in (("kaffi", "kaffi", "coffee"), ("takk", "takk", "thanks"), ("hae", "hæ", "hi"), ("bless", "bless", "bye"))
)
SCENARIOS = """
[[scenarios]]
id = "A1"
tier = "A"
title = "Café"
items = ["kaffi", "takk"]

[[scenarios]]
id = "B1"
tier = "B"
title = "Greet"
items = ["hae"]

[[scenarios]]
id = "C1"
tier = "C"
title = "Farewell"
items = ["bless"]
"""
ORDER = '{ who = "you", cue = "Order a coffee.", say = "Kaffi.", items = ["kaffi"] }'
THANK = '{ who = "you", cue = "Thank her.", say = "Takk.", items = ["takk"] }'
LEAVE = '{ who = "you", cue = "Say hi and bye.", say = "Hæ, bless.", items = ["hae", "bless"] }'


def themes_toml(cafe_levels: list[str]) -> str:
    levels = "".join(f'\n[[themes.levels]]\ngoal = "Level {n}."\nturns = [{turn}]\n' for n, turn in enumerate(cafe_levels, 1))
    return (
        '[[themes]]\nid = "cafe"\nscenario = "A1"\ntitle = "Café"\nscene_line = "You\'re at a café."\n' + levels
        + '\n[[themes]]\nid = "farewell"\nscenario = "C1"\ntitle = "Farewell"\nscene_line = "You\'re leaving."\n'
        + f'\n[[themes.levels]]\ngoal = "Leave."\nturns = [{LEAVE}]\n'
    )


def card(level: str) -> str:
    return (
        '[[scenes]]\nid = "a1_order"\nscenario = "A1"\nkind = "initiate"\nsituation = "Order a coffee."\nreplies = ["Kaffi."]\n'
        f'items = ["kaffi"]\nlevel = "{level}"\n'
    )


def course(d: Path, cafe_levels: list[str], level: str = "cafe:1") -> Path:
    (d / "cando").mkdir(exist_ok=True)
    (d / "course.toml").write_text(COURSE, "utf-8")
    (d / "cando" / "travel.toml").write_text(SCENARIOS, "utf-8")
    (d / "cando" / "themes.toml").write_text(themes_toml(cafe_levels), "utf-8")
    (d / "cando" / "scenes.toml").write_text(card(level), "utf-8")
    return d


def validate(d: Path) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["validate", str(d)])
    return code, out.getvalue(), err.getvalue()


class ScenarioCoverageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def load(self):
        cur = load_curriculum(self.dir)
        scenarios = load_cando(self.dir, cur)
        return scenarios, load_themes(self.dir, cur, scenarios), load_scenes(self.dir, cur, scenarios)

    def test_coverage_rises_when_a_level_says_the_scenarios_items(self):
        """A scenario item counts once a learner's line of a played level says it. «hæ» is said only in a Tier C scenario's theme,
        which is never played without a trip profile boosting it: it does not count, and the theme is named."""
        course(self.dir, [ORDER])
        scenarios, themes, _ = self.load()
        self.assertEqual(scenario_coverage(themes, scenarios), [("A1", ["kaffi"], ["takk"]), ("B1", [], ["hae"])])
        self.assertEqual([t.id for t in unranked_themes(themes, scenarios)], ["farewell"])
        code, out, err = validate(self.dir)
        self.assertEqual(code, 0, err)
        self.assertIn("1 of 3 Tier A/B scenario items said in a theme level; none yet: B1", out)
        self.assertIn("farewell (C1)", err)

        course(self.dir, [ORDER, THANK])
        scenarios, themes, _ = self.load()
        self.assertEqual(scenario_coverage(themes, scenarios)[0], ("A1", ["kaffi", "takk"], []))
        self.assertIn("2 of 3 Tier A/B scenario items said in a theme level; none yet: B1", validate(self.dir)[1])

    def test_a_card_whose_level_does_not_exist_fails(self):
        for level in ("cafe:2", "cafe:0", "museum:1", "cafe"):
            with self.subTest(level=level):
                course(self.dir, [ORDER], level)
                _, themes, scenes = self.load()
                self.assertEqual(unknown_levels(scenes, themes), [("a1_order", level)])
                code, _, err = validate(self.dir)
                self.assertEqual(code, 1)
                self.assertIn("theme levels that do not exist", err)
                self.assertIn(repr(level), err)

    def test_a_level_no_card_asks_is_listed(self):
        course(self.dir, [ORDER, THANK])
        _, themes, scenes = self.load()
        self.assertEqual(unasked_levels(scenes, themes), ["cafe:2", "farewell:1"])
        code, out, _ = validate(self.dir)
        self.assertEqual(code, 0)
        self.assertIn("2 theme levels have no scenario card asking their goal (a card's `level`, #327): cafe:2, farewell:1", out)

    def test_the_cards_level_reaches_the_bots_json(self):
        """`audiolesson scenes` passes the card's level to the bot, which reads only the keys it knows."""
        course(self.dir, [ORDER])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(["scenes", str(self.dir)]), 0)
        self.assertEqual([c["level"] for c in json.loads(buf.getvalue())], ["cafe:1"])


if __name__ == "__main__":
    unittest.main()
