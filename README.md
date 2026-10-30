# Assignment 4 — Laptop Advisor Expert System

Bonus edition: explanations and uncertainty handling are implemented.

A completed version of the supplied teaching project. It uses forward chaining to infer laptop categories and specifications from user facts, using the ten rules in `Assignment 4_rules.docx`.

## Requirements and quick start

Python 3.8 or newer. All code and tests use the Python standard library; no packages need to be installed.

Unzip the project, open a terminal inside `assignment4_laptop_advisor`, and run:

```bash
python3 main.py
```

On Windows, use `py main.py` if `python3` is unavailable. Answer the budget and OS questions with the displayed options and other questions with `y`, `yes`, `n`, or `no`. Answers ignore capitalization and surrounding spaces. Invalid answers prompt again. Ctrl+C or end-of-input exits cleanly with status 1.

The knowledge-base path is relative to `main.py`, so running the script by absolute path from another directory also works.

## Run the bonus features

```bash
python3 main.py --uncertain --why-not recommend:budget_ultrabook
```

Answer the normal questions, then enter a score from 0 to 1 for each positive input fact. Enter defaults to 1. A score of 0 means unknown/no positive support. The program displays confidence scores, rule calculations, nested explanations, and missing requirements for the requested target. `--why-not` also works without `--uncertain`. Use `python3 main.py --help` for options.

For a reproducible example, choose high budget, any OS, yes for portability and battery, and no for every other question. Enter confidence values 1, 0.8, 0.6 for budget, portability, and battery. The premium ultrabook result has 60% support. This is a heuristic support score, not a measured probability.

The rule calculation is `min(antecedent scores) * rule confidence`. Alternative proofs use maximum support. All ten assignment rules default to confidence 1.0; their meanings are unchanged. Detailed assumptions and calculations are in `docs/REPORT.md`.

## Project structure

| Path | Purpose |
|---|---|
| `main.py` | User questions, execution, results, and explanations |
| `engine.py` | Rule representation and generic forward-chaining engine |
| `kb_loader.py` | JSON loading and schema validation |
| `kb/laptop_rules.json` | All ten required laptop rules |
| `tests/test_project.py` | Input/output, engine, loader, and CLI tests |
| `tests/test_bonus.py` | Fourteen tests of confidence and explanations |
| `tests/__init__.py` | Test discovery support |
| `docs/REPORT.md` | Design, algorithm, rule table, assumptions, and limitations |
| `docs/REQUIREMENTS.md` | Assignment requirement-to-implementation checklist |
| `docs/TEST_RESULTS.txt` | Captured test run and runtime version |
| `docs/EXAMPLE_RUN.txt` | Captured interactive program example |
| `requirements.txt` | Documents that no external dependencies are needed |
| `.gitignore` | Excludes virtual environments and Python-generated files |

## Example

Choose `high` budget and `windows` OS; answer yes to portability, long battery, and office-only usage, and no to gaming, creative work, AI acceleration, large screen, and frequent travel. The output includes:

```text
Results
> Recommendation: premium_ultrabook (support 100.0%)
No additional specifications matched the supplied rules.

Fired rules (in execution order)
1. Budget Ultra-portable: IF budget_high AND portable AND long_battery THEN recommend:premium_ultrabook
```

`docs/EXAMPLE_RUN.txt` contains the complete captured session with its input sequence.

## Run tests

From the project folder:

```bash
python3 -m unittest discover -s tests -v
```

On Windows, use `py -m unittest discover -s tests -v`. The suite contains 39 test methods, with subtests for all ten rules, each missing antecedent, and malformed knowledge bases. It also verifies multi-step chaining, priority, ties, cycles, duplicates, input validation, and execution from another directory. The captured run used Python 3.12; Python 3.8 compatibility was checked syntactically, not by running a separate 3.8 interpreter.

## How reasoning works

1. Collect facts and insert them into a set (working memory).
2. Calculate each rule's support; a rule is eligible only if it improves its consequent.
3. Fire the eligible rule with highest priority; equal priorities use JSON order.
4. Add or improve its consequent and record the rule, prerequisites, scores, and priority.
5. Recheck the rules until no confidence score improves.
6. Print recommendations, specifications, confidence scores, the trace, and proof trees.

`conclusions()` returns a dictionary with `recommendations`, `specs`, and `other`. The first two contain values without their `recommend:` or `spec:` prefix. `other` contains all remaining known facts, including the user's original facts. The trace identifies which facts were derived.

## Extend the knowledge base

Add an object to the JSON list using the same schema:

```json
{
  "name": "Example additional rule",
  "if": ["some_fact", "another_fact"],
  "then": "recommend:example_category",
  "priority": 0,
  "confidence": 1.0
}
```

Add a corresponding test. New user facts also need CLI questions if they cannot be derived. No laptop-specific logic belongs in `engine.py`. An empty `if` list is an unconditional rule; missing `if` is invalid. Names, priorities, and confidence default to `Rule #N`, `0`, and `1.0` when omitted.

## Scope

All ten supplied rules are preserved without adding invented product advice. Multiple matching recommendations are displayed. Priority controls firing order, not a ranking of laptop quality. There is no price database or compatibility solver. Confidence scores express positive support, not calibrated probabilities. Read `docs/REPORT.md` for the precise assumptions and limitations.
