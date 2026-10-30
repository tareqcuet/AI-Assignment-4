"""Behavioral tests with explicit input facts and expected conclusions."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from engine import ForwardChainingEngine, Rule
from kb_loader import load_rules
from main import KB_PATH, collect_initial_facts, main

# Independently transcribed from Assignment 4_rules.docx.
CASES = [
    (["budget_high", "portable", "long_battery"], "recommend:premium_ultrabook"),
    (["budget_low", "office_only", "portable"], "recommend:budget_ultrabook"),
    (["gaming", "budget_medium"], "recommend:midrange_gaming_laptop"),
    (["gaming", "budget_high"], "recommend:high_end_gaming_laptop"),
    (["creative_work", "portable"], "spec:ram_16_plus"),
    (["creative_work", "large_screen"], "spec:display_15_plus_color_accurate"),
    (["travel_often", "long_battery"], "spec:battery_60wh_plus"),
    (["pref_os_macos"], "spec:macos_required"),
    (["needs_ai_accel"], "spec:gpu_with_tensor_cores"),
    (["pref_os_linux", "office_only"], "spec:linux_friendly_hw"),
]


def infer(facts, rules=None):
    engine = ForwardChainingEngine(load_rules(str(KB_PATH)) if rules is None else rules)
    engine.assert_facts(facts)
    engine.run()
    return engine


class LaptopRuleTests(unittest.TestCase):
    def test_all_ten_rules_match_source(self):
        rules = load_rules(str(KB_PATH))
        self.assertEqual(len(rules), 10)
        self.assertEqual({(tuple(r.antecedents), r.consequent) for r in rules},
                         {(tuple(facts), expected) for facts, expected in CASES})

    def test_each_rule_positive(self):
        for facts, expected in CASES:
            with self.subTest(expected=expected):
                self.assertEqual(infer(facts).facts - set(facts), {expected})

    def test_each_required_antecedent(self):
        for facts, expected in CASES:
            for missing in facts:
                with self.subTest(expected=expected, missing=missing):
                    self.assertNotIn(expected, infer([f for f in facts if f != missing]).facts)

    def test_combined_profile(self):
        engine = infer(["budget_high", "portable", "long_battery", "creative_work",
                        "large_screen", "travel_often", "pref_os_macos", "needs_ai_accel"])
        self.assertEqual(engine.conclusions()["recommendations"], ["premium_ultrabook"])
        self.assertEqual(engine.conclusions()["specs"], ["battery_60wh_plus",
                         "display_15_plus_color_accurate", "gpu_with_tensor_cores",
                         "macos_required", "ram_16_plus"])
        self.assertEqual(len(engine.trace), 6)

    def test_multiple_recommendations_are_preserved(self):
        self.assertEqual(infer(["budget_high", "gaming", "portable", "long_battery"])
                         .conclusions()["recommendations"],
                         ["high_end_gaming_laptop", "premium_ultrabook"])

    def test_no_match(self):
        self.assertEqual(infer(["budget_low", "pref_os_windows"]).trace, [])


class EngineTests(unittest.TestCase):
    def test_multistep_reverse_order(self):
        engine = infer(["seed"], [Rule(["middle"], "recommend:result", name="second"),
                                  Rule(["seed"], "middle", name="first")])
        self.assertIn("recommend:result", engine.facts)
        self.assertEqual([event["rule"] for event in engine.trace], ["first", "second"])

    def test_all_antecedents_and_unknown_consequent(self):
        rule = Rule(["a", "b"], "c")
        engine = ForwardChainingEngine([rule])
        engine.assert_facts(["a"])
        self.assertFalse(engine.can_fire(rule))
        engine.assert_facts(["b"])
        self.assertTrue(engine.can_fire(rule))
        engine.assert_facts(["c"])
        self.assertFalse(engine.can_fire(rule))

    def test_priority_and_stable_ties(self):
        rules = [Rule(["a"], "b", 0, "first"), Rule(["a"], "c", 5, "high"),
                 Rule(["a"], "d", 0, "last")]
        self.assertEqual([e["rule"] for e in infer(["a"], rules).trace],
                         ["high", "first", "last"])

    def test_cycles_duplicate_consequents_and_reruns(self):
        engine = infer(["a", "a"], [Rule(["a"], "b"), Rule(["b"], "a"), Rule(["a"], "b")])
        self.assertEqual(engine.facts, {"a", "b"})
        self.assertEqual(len(engine.trace), 1)
        engine.run()
        self.assertEqual(len(engine.trace), 1)

    def test_unsupported_cycle_derives_nothing(self):
        self.assertEqual(infer([], [Rule(["a"], "b"), Rule(["b"], "a")]).facts, set())

    def test_unconditional_rule_and_empty_kb(self):
        self.assertEqual(infer([], [Rule([], "a")]).facts, {"a"})
        self.assertEqual(infer([], []).conclusions(),
                         {"recommendations": [], "specs": [], "other": []})

    def test_add_facts_after_run(self):
        engine = infer([], [Rule(["a"], "b")])
        engine.assert_facts(["a"])
        engine.run()
        self.assertIn("b", engine.facts)

    def test_conclusion_categories(self):
        engine = infer(["plain", "spec:z", "recommend:b", "spec:a"], [])
        self.assertEqual(engine.conclusions(), {"recommendations": ["b"],
                         "specs": ["a", "z"], "other": ["plain"]})

    def test_trace_explains_derivation(self):
        engine = infer(["a"], [Rule(["a"], "b", 3, "explanation")])
        self.assertEqual(engine.trace, [{"rule": "explanation", "antecedents": ["a"],
                                        "consequent": "b", "priority": 3,
                                        "confidence": 1.0, "previous_confidence": 0.0,
                                        "rule_confidence": 1.0, "antecedent_confidences": [1.0]}])


class LoaderTests(unittest.TestCase):
    def load_payload(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_rules(str(path))

    def test_defaults(self):
        self.assertEqual(self.load_payload([{"if": [], "then": "a"}]),
                         [Rule([], "a", 0, "Rule #1")])

    def test_invalid_structures(self):
        for payload in ({}, [None], [{"then": "a"}], [{"if": "a", "then": "b"}],
                        [{"if": [1], "then": "a"}], [{"if": [], "then": ""}],
                        [{"if": [], "then": "a", "priority": True}],
                        [{"if": [], "then": "a", "name": ""}]):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.load_payload(payload)

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rules(str(path))


class CLITests(unittest.TestCase):
    def test_normalized_and_invalid_answers(self):
        answers = ["invalid", " LOW ", "wrong", "Linux", "maybe", " YES ",
                   "n", "no", "n", "yes", "n", "n", "n"]
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(collect_initial_facts(),
                             ["budget_low", "pref_os_linux", "portable", "office_only"])

    def test_office_only_excluded_for_gaming(self):
        with patch("builtins.input", side_effect=["high", "any", "n", "n", "y", "n", "n", "n", "n"]):
            self.assertEqual(collect_initial_facts(), ["budget_high", "gaming"])

    def test_every_boolean_can_be_collected(self):
        with patch("builtins.input", side_effect=["high", "macos"] + ["y"] * 7):
            self.assertEqual(set(collect_initial_facts()), {"budget_high", "pref_os_macos",
                             "portable", "long_battery", "gaming", "creative_work",
                             "needs_ai_accel", "large_screen", "travel_often"})

    def test_complete_cli_from_other_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(KB_PATH.parent.parent / "main.py")],
                                    input="high\nwindows\ny\ny\nn\nn\ny\nn\nn\nn\n",
                                    text=True, capture_output=True, cwd=folder, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Recommendation: premium_ultrabook", result.stdout)
        self.assertIn("Budget Ultra-portable: IF budget_high AND portable AND long_battery", result.stdout)

    def test_no_match_message(self):
        output = io.StringIO()
        with patch("main.collect_initial_facts", return_value=["budget_low"]), contextlib.redirect_stdout(output):
            self.assertEqual(main([]), 0)
        self.assertIn("No laptop recommendation matched", output.getvalue())
        self.assertIn("None. No rule had all required facts.", output.getvalue())

    def test_missing_file_handled(self):
        with patch("main.load_rules", side_effect=FileNotFoundError("missing")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 1)

    def test_cancelled_input_handled(self):
        for exception in (EOFError, KeyboardInterrupt):
            with self.subTest(exception=exception), patch("builtins.input", side_effect=exception), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
