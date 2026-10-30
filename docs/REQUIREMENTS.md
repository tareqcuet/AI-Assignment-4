# Assignment requirement checklist

| Source requirement | Implementation and verification |
|---|---|
| Python 3.8+ and `python3 main.py` | Standard-library CLI; Python 3.8 syntax check and Python 3.12 execution |
| Implement `can_fire(rule)` | All prerequisites with positive support and an improved consequence; equivalent to unknown-consequent checking at confidence 1 |
| Implement repeated forward chaining | Fixed-point loop; reverse-order multistep test, cycles, and repeat-run tests |
| Implement `conclusions()` | Sorted recommendations, specs, and other facts; category test |
| At least ten complete rules | Exactly the ten supplied DOCX rules in `kb/laptop_rules.json`; independent source-mapping test |
| Load rules with `load_rules()` | Called in `main()`; validation and missing-file tests |
| Collect user facts | All listed dimensions; budget and OS single-choice, remaining yes/no questions |
| Run engine and print results | CLI asserts facts, runs inference, prints categories and trace; subprocess test |
| Print fired rules | Rule, antecedents, consequent, and support updates in execution order |
| Add tests under `/tests` | `tests/test_project.py`, including explicit facts and expected outputs |
| Guideline premium-ultrabook example | Positive case with budget_high, portable, long_battery |
| Generic inference, no hardcoded domain logic | Engine handles arbitrary symbolic rules; synthetic multi-step and cycle tests |
| Code clarity and structure (10 points) | Original modular layout, docstrings, README, dependency declaration, and gitignore |
| Report/explanation (10 points) | `docs/REPORT.md` explains algorithm, rules, correctness, complexity, and limitations |
| Optional explanations | Derivation trace, nested strongest-proof explanations, and why-not diagnostics implemented and tested |
| Optional uncertainty handling | Input confidence and JSON rule weights; minimum-times-weight propagation, maximum over alternative proofs; 14 bonus tests |

The supplied PDF does not prescribe a separate report file format or student identification template. The report is provided as Markdown. Grading remains the instructor's decision; this checklist is an implementation audit, not a score claim.

Both named bonus areas are implemented. Run `python3 main.py --uncertain --why-not recommend:budget_ultrabook` to demonstrate them. Support scores are heuristic, not empirical probabilities. No flowchart is included, as requested.
