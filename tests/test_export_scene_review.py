"""tools/export_scene_review.py (G10, #209): one scenario's cards as a packet a fluent speaker can review and correct by card and field."""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = ROOT / "curricula" / "is-en"


def tool():
    spec = importlib.util.spec_from_file_location("export_scene_review", ROOT / "tools" / "export_scene_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportSceneReviewTests(unittest.TestCase):
    def test_a_card_carries_its_context_and_keeps_the_source_wording(self):
        """#209's example: «a2_change» with «the cashier hands you your change», the partner's «Gjörðu svo vel.» and its replies."""
        data = tool().packet(CUR, "A2", rev="r")
        card = next(c for c in data["cards"] if c["card_id"] == "a2_change")
        self.assertEqual(card["situation"], "At the till, the cashier hands you your change.")
        self.assertEqual((card["partner"], card["partner_meaning"]), ("Gjörðu svo vel.", "Here you go."))
        self.assertEqual(card["replies"], ["Takk.", "Takk fyrir."])
        self.assertEqual(card["items"], [{"id": "takk", "target": "Takk.", "meaning": "Thanks."}])
        self.assertEqual((card["corrections"], card["reviewer_notes"]), ([], ""), "empty, for the reviewer")
        self.assertIn("awaiting review", data["status"])
        self.assertEqual(data["scenario"]["id"], "A2")
        self.assertTrue(data["scenario"]["purpose"])

    def test_every_correction_field_is_a_field_of_the_card_in_its_source_file(self):
        import tomllib

        data = tool().packet(CUR, "A2", rev="r")
        for card in data["cards"]:
            with (CUR / card["source_file"]).open("rb") as f:
                source = next(s for s in tomllib.load(f)["scenes"] if s["id"] == card["card_id"])
            for field in data["correction_fields"]:
                self.assertEqual(card[field], source.get(field, ""), (card["card_id"], field))

    def test_identical_inputs_give_an_identical_packet_and_the_limit_holds(self):
        t = tool()
        self.assertEqual(json.dumps(t.packet(CUR, "A3", rev="r"), sort_keys=True), json.dumps(t.packet(CUR, "A3", rev="r"), sort_keys=True))
        two = t.packet(CUR, "A3", limit=2, rev="r")
        self.assertEqual(len(two["cards"]), min(2, two["cards_in_scenario"]))

    def test_an_unknown_scenario_fails_and_names_the_scenarios(self):
        t = tool()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(t.main(["--scenario", "Z9"]), 2)
        self.assertIn("A2", err.getvalue())
        self.assertIn("Z9", err.getvalue())

    def test_exporting_writes_only_the_packet(self):
        before = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "curricula"], capture_output=True, text=True).stdout
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "review-A2.json"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tool().main(["--scenario", "A2", "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text("utf-8"))["scenario"]["id"], "A2")
        after = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "curricula"], capture_output=True, text=True).stdout
        self.assertEqual(before, after, "the curriculum is untouched")


if __name__ == "__main__":
    unittest.main()
