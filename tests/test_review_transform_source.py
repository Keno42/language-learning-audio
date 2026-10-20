"""Transform reviews retain the exact input; legacy repairs preserve saved answers."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.review_wholes import refine_review
from audiolesson.review_wording import restore_transform_sources, reword_review
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class TransformReviewSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curricula = {lang: load_curriculum(ROOT / 'curricula/is-en', known_lang=lang) for lang in ('en', 'ja')}

    def build(self, lang, item, example, gender=None, hinted=False):
        prompts = Prompts.load(lang)
        builder = Builder(self.curricula[lang], prompts, Timing(level='A1'), LearnerState('is', lang, 'A1'))
        builder._gender_uses[item.id] = int(gender == 'm')
        sc = Script(31, 'Lesson 31', 'is', lang)
        ex = sc.new_exercise('recall', 'hinted' if hinted else 'meaning', [item.id], 'transform')
        builder._transform_prompt(sc, ex, item, example, hint=hinted)
        return sc

    def test_menu_question_is_complete_in_both_languages(self):
        for lang, cur in self.curricula.items():
            with self.subTest(lang=lang):
                item = cur.by_id['politeness_get_eg_fengid']
                example = next(e for e in item.examples if e.result == 'Get ég fengið matseðilinn?')
                sc = self.build(lang, item, example)
                qs = reword_review(sc.review_questions(), Prompts.load(lang), 'is')
                self.assertEqual(qs[0]['prompt'], item.instruction + '\nÉg ætla að fá matseðilinn.')
                self.assertEqual(qs[0]['answer'], example.result)
                self.assertNotIn(example.result, qs[0]['prompt'])

    def test_every_authored_example_keeps_its_source_and_gender(self):
        count = 0
        for lang, cur in self.curricula.items():
            for item in cur.items:
                if item.kind != 'transform':
                    continue
                for example in item.examples:
                    for gender in (('f', 'm') if example.source_m or example.result_m else (None,)):
                        with self.subTest(lang=lang, item=item.id, source=example.source, gender=gender):
                            q = self.build(lang, item, example, gender).review_questions()[0]
                            source = example.source_m if gender == 'm' and example.source_m else example.source
                            result = example.result_m if gender == 'm' and example.result_m else example.result
                            self.assertTrue(q['prompt'].endswith('\n' + source))
                            self.assertEqual(q['answer'], result)
                            count += 1
        self.assertGreater(count, 0)

    def test_hinted_recall_stays_out_of_written_review(self):
        cur = self.curricula['en']
        item = cur.by_id['politeness_get_eg_fengid']
        self.assertEqual(self.build('en', item, item.examples[0], hinted=True).review_questions(), [])

    def legacy(self, lang='en'):
        item = self.curricula[lang].by_id['politeness_get_eg_fengid']
        return {'items': [item.id], 'prompt': item.instruction, 'answer': 'Get ég fengið matseðilinn?'}

    def test_refinement_repairs_legacy_menu_questions(self):
        for lang, cur in self.curricula.items():
            old = self.legacy(lang)
            original = deepcopy(old)
            qs, rows = refine_review([old], cur, set(), Prompts.load(lang))
            self.assertEqual(qs[0]['prompt'], old['prompt'] + '\nÉg ætla að fá matseðilinn.')
            self.assertEqual(qs[0]['answer'], old['answer'])
            self.assertEqual(old, original)
            self.assertEqual(rows[0]['kind'], 'transform_source_restored')

    def test_merged_question_can_be_repaired_without_changing_items(self):
        old = self.legacy()
        old['items'].append('matsedilinn')
        qs, _ = restore_transform_sources([old], self.curricula['en'], Prompts.load('en'))
        self.assertEqual(qs[0]['items'], old['items'])
        self.assertTrue(qs[0]['prompt'].endswith('Ég ætla að fá matseðilinn.'))

    def test_repair_is_idempotent(self):
        qs, _ = restore_transform_sources([self.legacy()], self.curricula['en'], Prompts.load('en'))
        again, rows = restore_transform_sources(qs, self.curricula['en'], Prompts.load('en'))
        self.assertEqual(again, qs)
        self.assertEqual(rows, [])

    def test_gendered_legacy_question_uses_the_saved_answers_form(self):
        lang = 'en'
        cur, prompts = self.curricula[lang], Prompts.load(lang)
        item = next(i for i in cur.items if i.kind == 'transform' and any(e.source_m and e.result_m for e in i.examples))
        example = next(e for e in item.examples if e.source_m and e.result_m)
        q = {'items': [item.id], 'prompt': prompts.get('speak_as_m', prompt=item.instruction), 'answer': example.result_m}
        qs, _ = restore_transform_sources([q], cur, prompts)
        self.assertTrue(qs[0]['prompt'].endswith('\n' + example.source_m))

    def test_ambiguous_input_is_reported_without_guessing(self):
        example = lambda source: SimpleNamespace(source=source, result='Result.', source_m='', result_m='')
        item = SimpleNamespace(kind='transform', instruction='Transform:', examples=[example('Input A.'), example('Input B.')])
        cur = SimpleNamespace(by_id={'x': item})
        q = {'items': ['x'], 'prompt': 'Transform:', 'answer': 'Result.'}
        qs, rows = restore_transform_sources([q], cur, Prompts.load('en'))
        self.assertEqual(qs, [q])
        self.assertEqual(rows[0]['kind'], 'transform_source_unresolved')

    def test_missing_example_is_reported_without_changing_answer(self):
        q = self.legacy()
        q['answer'] = 'No longer in the authored examples.'
        qs, rows = restore_transform_sources([q], self.curricula['en'], Prompts.load('en'))
        self.assertEqual(qs, [q])
        self.assertEqual(rows[0]['matches'], 0)


if __name__ == '__main__':
    unittest.main()
