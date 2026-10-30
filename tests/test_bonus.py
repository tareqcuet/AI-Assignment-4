"""Bonus tests: numeric uncertainty, proof trees, and user-visible explanations."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine import ForwardChainingEngine, Rule, validate_confidence
from kb_loader import load_rules
from main import KB_PATH, collect_confidences, print_why_not


class BonusTests(unittest.TestCase):
    def test_minimum_times_rule_confidence(self):
        e = ForwardChainingEngine([Rule(['a', 'b'], 'c', confidence=0.9)])
        e.assert_facts(['a', 'b'], {'a': 0.8, 'b': 0.6})
        e.run()
        self.assertAlmostEqual(e.confidence['c'], 0.54)

    def test_chained_confidence(self):
        e = ForwardChainingEngine([Rule(['b'], 'c', confidence=0.5),
                                  Rule(['a'], 'b', confidence=0.8)])
        e.assert_facts(['a'], {'a': 0.75})
        e.run()
        self.assertAlmostEqual(e.confidence['c'], 0.3)
        proof = e.explain('c')
        self.assertEqual(proof['premises'][0]['premises'][0]['source'], 'user')

    def test_improvement_propagates_and_trace_retains_old_values(self):
        e = ForwardChainingEngine([Rule(['a'], 'b', 5, 'weak', 0.4),
                                  Rule(['b'], 'c', 4, 'downstream', 0.5),
                                  Rule(['a'], 'b', 0, 'strong', 0.9)])
        e.assert_facts(['a'])
        e.run()
        self.assertAlmostEqual(e.confidence['c'], 0.45)
        self.assertEqual([t['rule'] for t in e.trace], ['weak', 'downstream', 'strong', 'downstream'])
        self.assertAlmostEqual(e.trace[1]['confidence'], 0.2)
        self.assertEqual(e.explain('c')['premises'][0]['rule'], 'strong')

    def test_multiple_evidence_uses_max_not_sum(self):
        e = ForwardChainingEngine([Rule(['a'], 'c', confidence=0.6),
                                  Rule(['b'], 'c', confidence=0.7),
                                  Rule(['b'], 'c', confidence=0.7)])
        e.assert_facts(['a', 'b'])
        e.run()
        self.assertEqual(e.confidence['c'], 0.7)
        self.assertEqual(len(e.trace), 2)

    def test_weighted_cycle_terminates_without_inflation(self):
        e = ForwardChainingEngine([Rule(['a'], 'b', confidence=0.9),
                                  Rule(['b'], 'a', confidence=1)])
        e.assert_facts(['a'], {'a': 0.6})
        e.run()
        self.assertEqual(e.confidence['a'], 0.6)
        self.assertAlmostEqual(e.confidence['b'], 0.54)
        self.assertEqual(len(e.trace), 1)
        e.run()
        self.assertEqual(len(e.trace), 1)

    def test_missing_unknown_and_disabled_rules(self):
        e = ForwardChainingEngine([Rule(['a'], 'b'), Rule([], 'c', confidence=0)])
        e.assert_facts(['a'], {'a': 0})
        e.run()
        self.assertEqual(e.facts, set())
        self.assertEqual(e.why_not('b')[0]['missing'], ['a'])
        self.assertIsNone(e.explain('b'))

    def test_increased_input_confidence_and_no_retraction(self):
        e = ForwardChainingEngine([Rule(['a'], 'b', confidence=0.5)])
        e.assert_facts(['a'], {'a': 0.4})
        e.run()
        old = e.explain('b')
        e.assert_facts(['a'], {'a': 0.8})
        e.run()
        self.assertEqual(old['confidence'], 0.2)
        self.assertEqual(e.confidence['b'], 0.4)
        e.assert_facts(['a'], {'a': 0.1})
        self.assertEqual(e.confidence['a'], 0.8)

    def test_proof_cannot_be_mutated_by_caller(self):
        e = ForwardChainingEngine([Rule(['a'], 'b')])
        e.assert_facts(['a'])
        e.run()
        proof = e.explain('b')
        proof['premises'][0]['confidence'] = 0
        self.assertEqual(e.explain('b')['premises'][0]['confidence'], 1)

    def test_invalid_confidence_rejected(self):
        for value in (-0.1, 1.1, float('nan'), float('inf'), True, '0.5', None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): validate_confidence(value)
                with self.assertRaises(ValueError): Rule([], 'a', confidence=value)
                with self.assertRaises(ValueError):
                    ForwardChainingEngine([]).assert_facts(['a'], {'a': value})

    def test_loader_weights_and_invalid_weights(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'rules.json'
            for value in (0, 0.8, 1, -1, 2, True, 'bad', None):
                p.write_text(json.dumps([{'if': ['a'], 'then': 'b', 'confidence': value}]))
                with self.subTest(value=value):
                    if type(value) in (int, float) and 0 <= value <= 1:
                        self.assertEqual(load_rules(str(p))[0].confidence, value)
                    else:
                        with self.assertRaises(ValueError): load_rules(str(p))

    def test_confidence_prompt_retries_and_default(self):
        with patch('builtins.input', side_effect=['nan', '2', 'bad', '0.6', '']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(collect_confidences(['a', 'b']), {'a': 0.6, 'b': 1})

    def test_why_not_missing_disabled_unknown_and_supported(self):
        e = ForwardChainingEngine([Rule(['a', 'b'], 'c', name='needs_b'),
                                  Rule([], 'disabled', name='off', confidence=0)])
        e.assert_facts(['a'])
        e.run()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            for fact in ('c', 'disabled', 'unlisted', 'a'): print_why_not(e, fact)
        for phrase in ('missing positive support for b', 'zero (disabled)',
                       'No rule derives', 'user input'):
            self.assertIn(phrase, output.getvalue())

    def test_uncertain_cli_end_to_end(self):
        answers = 'high\nany\ny\ny\nn\nn\nn\nn\nn\nn\n1\n0.8\n0.6\n'
        r = subprocess.run([sys.executable, str(KB_PATH.parent.parent / 'main.py'),
                            '--uncertain', '--why-not', 'recommend:budget_ultrabook'],
                           input=answers, text=True, capture_output=True, timeout=5)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('premium_ultrabook (support 60.0%)', r.stdout)
        self.assertIn('min support 60.0% x rule 100.0%', r.stdout)
        self.assertIn('missing positive support for budget_low, office_only', r.stdout)

    def test_unconditional_weight(self):
        e = ForwardChainingEngine([Rule([], 'a', confidence=0.3)])
        e.run()
        self.assertEqual(e.confidence['a'], 0.3)


if __name__ == '__main__':
    unittest.main()
