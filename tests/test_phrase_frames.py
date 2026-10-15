"""#336: fixed phrases of a scene that share a frame and differ in one stretch are found by their text, and the transport scene's frames are patterns."""
import unittest
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum, phrase_frames

ROOT = Path(__file__).resolve().parent.parent
BASE = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}


def cur(items):
    return curriculum_from_dict({**BASE, "items": items})


def phrase(i, target, topics=("transport",), **kw):
    return {"id": i, "kind": "phrase", "target": target, "meaning": target, "topics": list(topics), **kw}


class PhraseFrameTests(unittest.TestCase):
    def test_phrases_that_differ_in_one_stretch_are_a_frame_by_their_text(self):
        c = cur([
            phrase("a", "Fer þessi strætó í miðbæinn?"),
            phrase("b", "Fer þessi strætó á flugvöllinn?"),
            phrase("c", "Hvenær kemur strætó?"),
            phrase("d", "Á flugvöllinn, takk."),
            phrase("e", "Á þetta hótel, takk."),
        ])
        found = {frame: ids for frame, ids in phrase_frames(c)}
        self.assertEqual(found["fer þessi strætó … "], ["a", "b"])
        self.assertEqual(found["á … takk"], ["d", "e"])

    def test_a_subject_or_a_copula_alone_is_not_a_frame(self):
        c = cur([phrase("a", "Ég er hér."), phrase("b", "Ég er þreytt."), phrase("c", "Þetta er gott."), phrase("d", "Þetta er dýrt.")])
        self.assertEqual(phrase_frames(c), [])

    def test_phrases_of_other_scenes_are_not_compared(self):
        c = cur([phrase("a", "Fer þessi strætó í miðbæinn?"), phrase("b", "Fer þessi strætó á flugvöllinn?", topics=("weather",))])
        self.assertEqual(phrase_frames(c), [])

    def test_a_group_made_by_one_pattern_is_not_reported(self):
        c = cur([
            {"id": "dest_takk", "kind": "construction", "target": "{dest}, takk.", "meaning": "{dest}, please.", "slots": {"dest": "dest"}, "example": {"dest": "x"}, "prereqs": ["x"]},
            {"id": "x", "kind": "vocab", "target": "á flugvöllinn", "meaning": "to the airport", "tags": ["dest"]},
            {"id": "y", "kind": "vocab", "target": "á þetta hótel", "meaning": "to this hotel", "tags": ["dest"]},
            phrase("d", "Á flugvöllinn, takk.", instance_of="dest_takk", instance_fill={"dest": "x"}),
            phrase("e", "Á þetta hótel, takk.", instance_of="dest_takk", instance_fill={"dest": "y"}),
        ])
        self.assertEqual(phrase_frames(c), [])


class TransportFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_bus_and_taxi_phrases_are_instances_of_two_patterns_with_the_scenes_destinations(self):
        by = {i: self.cur.by_id[i] for i in ("fer_thessi_straeto_i_midbaeinn", "fer_thessi_straeto_a_flugvollinn", "a_flugvollinn_takk", "a_thetta_hotel_takk")}
        self.assertEqual({i.instance_of for i in list(by.values())[:2]}, {"fer_thessi_straeto_dest"})
        self.assertEqual({i.instance_of for i in list(by.values())[2:]}, {"dest_takk"})
        self.assertEqual(by["a_flugvollinn_takk"].instance_fill, {"dest": "a_flugvollinn"})

    def test_a_destination_shared_by_both_patterns_connects_them(self):
        shared = [c.id for c in self.cur.items if c.kind == "construction" and "dest" in c.slots.values() and "a_flugvollinn" in c.prereqs + list(c.example.values())]
        self.assertEqual(sorted(shared), ["dest_takk", "fer_thessi_straeto_dest"])

    def test_the_patterns_say_the_new_destinations(self):
        for ctor, fill, want in (
            ("fer_thessi_straeto_dest", "a_safnid", "Fer þessi strætó á safnið?"),
            ("dest_takk", "a_stoppistodina", "Á stoppistöðina, takk."),
            ("dest_takk", "i_midbaeinn", "Í miðbæinn, takk."),
        ):
            text, meaning = self.cur.resolve_slots(self.cur.by_id[ctor], {"dest": self.cur.by_id[fill]})
            self.assertEqual(text, want)
            self.assertNotIn("{", meaning)

    def test_no_frame_of_the_transport_scene_is_left_as_separate_phrases(self):
        transport = [(f, ids) for f, ids in phrase_frames(self.cur) if any("transport" in self.cur.by_id[i].topics for i in ids)]
        self.assertNotIn("fer þessi strætó … ", [f for f, _ in transport])
        self.assertNotIn("á … takk", [f for f, _ in transport])


if __name__ == "__main__":
    unittest.main()
