"""#220: ease learns from a recall confirmed after a long gap; the confirmed recall rate is read by gap."""
import unittest
from datetime import date, timedelta

from audiolesson.learner import ItemState, LearnerState, retention_report

TODAY = date(2026, 3, 1)


def learner(**kw):
    l = LearnerState("is", "en", "A1")
    base = dict(stage="meaning", ease=2.3, interval_days=7.0, due=(TODAY - timedelta(days=1)).isoformat(), last_practiced=(TODAY - timedelta(days=14)).isoformat(),
                successes=3, durable_successes=2, recalled=2, last_outcome="recalled")
    base.update(kw)
    l.items["a"] = ItemState(**base)
    l.items["b"] = ItemState(**base)
    return l


class LongGapTests(unittest.TestCase):
    def test_a_recall_confirmed_after_a_week_raises_the_ease_and_extends_the_interval(self):
        l = learner()
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 14})
        st = l.items["a"]
        self.assertAlmostEqual(st.ease, 2.4)
        self.assertGreaterEqual(st.interval_days, 14 * 2.4 - 0.1, "at least the gap bridged, times the ease")
        self.assertGreaterEqual(date.fromisoformat(st.due), TODAY + timedelta(days=int(st.interval_days)))

    def test_the_bots_gap_is_capped_by_the_lessons_own_practice(self):
        """#298 review: an item a lesson practised 2 days ago with a bot gap of 14 counts as 2: the ease does not rise by the long-gap rule."""
        l = learner(last_practiced=(TODAY - timedelta(days=2)).isoformat())
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 14})
        self.assertEqual(l.items["a"].ease, 2.3, "one confirmation at a real gap: the interval extends, the ease waits for the second")
        self.assertEqual(l.items["a"].interval_days, round(7 * 2.3, 1), "a 2-day gap is a real gap on a due item (below)")
        self.assertEqual(l.retention, {}, "2 days: in no bucket")

    def test_a_gap_shorter_than_the_practice_is_kept(self):
        l = learner()  # practised 14 days ago
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 8})
        self.assertAlmostEqual(l.items["a"].ease, 2.4)
        self.assertIn("7", l.retention)

    def test_no_gap_changes_nothing_but_the_count(self):
        l = learner()
        l.report([], [], TODAY, recalled=["a", "b"], gaps={"a": 3})
        self.assertEqual((l.items["b"].ease, l.items["b"].interval_days), (2.3, 7.0), "no gap: as before")

    def test_a_failure_at_any_gap_lowers_the_ease_as_before(self):
        l = learner()
        l.report(["a"], [], TODAY, gaps={"a": 21})
        self.assertAlmostEqual(l.items["a"].ease, 2.1)
        self.assertEqual(l.items["a"].interval_days, 1)

    def test_the_ease_never_passes_its_ceiling(self):
        l = learner(ease=2.98)
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 30})
        self.assertEqual(l.items["a"].ease, 3.0)


class RealGapTests(unittest.TestCase):
    """#220, the owner's rule: a 言えた at a real gap extends the interval, and two in a row raise the ease."""

    def test_a_first_confirmation_on_a_one_day_interval_moves_it_to_three_days(self):
        l = learner(interval_days=1.0, due=TODAY.isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat(), recalled=0)
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 1})
        st = l.items["a"]
        self.assertEqual((st.interval_days, st.due, st.ease, st.gap_streak), (3.0, (TODAY + timedelta(days=3)).isoformat(), 2.3, 1))

    def test_a_due_item_grows_by_the_gap_and_the_ease_and_two_in_a_row_raise_the_ease(self):
        l = learner(interval_days=7.0, last_practiced=(TODAY - timedelta(days=5)).isoformat())
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 5})
        st = l.items["a"]
        self.assertEqual((st.interval_days, st.ease, st.gap_streak), (round(7 * 2.3, 1), 2.3, 1))
        day2 = TODAY + timedelta(days=int(st.interval_days))
        st.last_practiced = TODAY.isoformat()
        l.report([], [], day2, recalled=["a"], gaps={"a": int(st.interval_days)})
        self.assertEqual(st.gap_streak, 2)
        self.assertAlmostEqual(st.ease, 2.4, msg="the second one is at a long gap: the long-gap rule raises the ease once")

    def test_two_short_gaps_in_a_row_raise_the_ease_once(self):
        l = learner(interval_days=1.0, due=TODAY.isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 1})
        st = l.items["a"]
        day2 = TODAY + timedelta(days=3)
        st.last_practiced = TODAY.isoformat()
        l.report([], [], day2, recalled=["a"], gaps={"a": 3})
        self.assertEqual((st.gap_streak, round(st.ease, 2)), (2, 2.4))
        self.assertGreater(st.interval_days, 3)

    def test_a_failure_or_a_hesitation_resets_the_streak(self):
        l = learner(interval_days=1.0, due=TODAY.isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        l.report([], [], TODAY, recalled=["a", "b"], gaps={"a": 1, "b": 1})
        l.report(["a"], [], TODAY, hesitated=["b"])
        self.assertEqual((l.items["a"].gap_streak, l.items["b"].gap_streak), (0, 0))

    def test_an_early_check_of_an_item_not_due_on_a_long_interval_changes_nothing(self):
        l = learner(interval_days=14.0, due=(TODAY + timedelta(days=9)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 2})
        st = l.items["a"]
        self.assertEqual((st.interval_days, st.ease, st.gap_streak), (14.0, 2.3, 0))

    def test_a_same_day_answer_is_not_a_gap(self):
        l = learner(interval_days=1.0, due=TODAY.isoformat(), last_practiced=TODAY.isoformat())
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 0})
        self.assertEqual(l.items["a"].interval_days, 1.0)


class RetentionCountTests(unittest.TestCase):
    def test_outcomes_are_counted_by_the_longest_bucket_the_gap_reached(self):
        l = learner()
        l.items["c"] = ItemState(**{**l.items["a"].__dict__})
        l.items["d"] = ItemState(**{**l.items["a"].__dict__})
        l.report(["d"], [], TODAY, recalled=["a", "b"], hesitated=["c"], gaps={"a": 3, "b": 8, "c": 14, "d": 15})
        self.assertEqual(l.retention, {"3": [1, 1], "7": [1, 1], "14": [0, 2]})
        report = retention_report(l)
        self.assertEqual(report["3–6 days"], "1/1 (100%)")
        self.assertEqual(report["14+ days"], "0/2 (0%)")

    def test_it_is_saved_and_loaded_and_an_old_file_reads_empty(self):
        import tempfile
        from pathlib import Path

        l = learner()
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 10})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            l.save(path)
            self.assertEqual(LearnerState.load(path).retention, {"7": [1, 1]})
            fresh = LearnerState("is", "en", "A1")
            fresh.save(path)
            self.assertEqual(LearnerState.load(path).retention, {})
            self.assertEqual(retention_report(fresh)["7–13 days"], "–")

    def test_the_cli_reads_gaps(self):
        from audiolesson.cli import _gaps

        self.assertEqual(_gaps("a=14, b=7,bad,c=x"), {"a": 14, "b": 7})


if __name__ == "__main__":
    unittest.main()
