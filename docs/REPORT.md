# Assignment 4 project report — bonus edition

## Objective and sources

Complete the supplied expert-system teaching project using the guidance PDF and all ten Laptop Advisor rules in the rules DOCX. This revision implements both bonus areas: explanations and uncertainty handling. The original module structure and rule meanings are retained. No flowchart is included, as requested.

## Knowledge base

Facts are symbolic strings. Every rule has an AND-list of antecedents, a consequent, a priority, a name, and a confidence weight in [0, 1]. All ten assignment rules have weight 1.0 because the supplied rules are categorical and provide no empirical reliability estimates. Weights can be configured in JSON without changing the engine.

| Rule | Required facts (AND) | Consequent |
|---|---|---|
| Budget Ultra-portable | budget_high, portable, long_battery | recommend:premium_ultrabook |
| Student light office | budget_low, office_only, portable | recommend:budget_ultrabook |
| Gaming | gaming, budget_medium | recommend:midrange_gaming_laptop |
| Pro gaming | gaming, budget_high | recommend:high_end_gaming_laptop |
| Creative work (portable) | creative_work, portable | spec:ram_16_plus |
| Creative work (display) | creative_work, large_screen | spec:display_15_plus_color_accurate |
| Travel + battery | travel_often, long_battery | spec:battery_60wh_plus |
| OS preference mapping | pref_os_macos | spec:macos_required |
| AI acceleration | needs_ai_accel | spec:gpu_with_tensor_cores |
| Linux suitability | pref_os_linux, office_only | spec:linux_friendly_hw |

The first rule uses the DOCX name, “Budget Ultra-portable,” even though its condition is `budget_high`. Its logic matches the starter's “Premium Ultrabook” rule. The starter's priority 5 is preserved; the other rules have priority 0. Neither rule meaning nor output tokens are changed.

## Uncertainty model

This is a positive-support certainty model, not Bayesian inference or a complete MYCIN implementation. Scores are transparent heuristic support values, not measured probabilities of laptop suitability.

For a rule with antecedents A1 ... An and rule weight w:

`candidate = min(confidence(A1), ..., confidence(An)) * w`

For multiple ways to derive the same conclusion:

`new_confidence = max(previous_confidence, candidate)`

Missing facts have support 0. An unconditional rule uses antecedent support 1. A zero-weight rule is disabled. Scores must be finite numbers from 0 to 1; booleans, NaN, infinity, and out-of-range values are rejected. Default scores are 1.0, reproducing ordinary Boolean inference.

Example: budget_high=1.0, portable=0.8, long_battery=0.6 gives premium_ultrabook support `min(1.0, 0.8, 0.6) * 1.0 = 0.6`. A synthetic rule with weight 0.9 and antecedent support 0.6 yields 0.54; this weighted-rule behavior is tested separately without inventing weights for the instructor's rules.

Minimum models the weakest prerequisite in an AND rule. Maximum selects the strongest available justification instead of summing correlated evidence. Repeating a rule therefore cannot inflate confidence. The model deliberately does not combine independent evidence probabilistically. A score of 0 means no positive support; it is not a negative fact. There is no confidence threshold: every strictly positive result is printed with its score.

## Inference and termination

The engine scans rules in descending priority, preserving JSON order for ties. An eligible rule must strictly increase its consequent's support. It adds or updates that fact, records the calculation, and restarts the scan until no support improves. With all weights and inputs equal to 1, this is exactly the original unknown-consequent forward-chaining behavior.

In uncertainty mode an already-known fact can improve, so its dependent rules are reconsidered. For example, `a -> b` at 0.4 followed by `b -> c` at 0.5 first gives c=0.2. If another rule improves b to 0.9, c becomes 0.45. The trace preserves both computations.

Rules have weights no greater than 1, so a conclusion cannot exceed the support of its prerequisites. A cycle cannot provide a strictly stronger proof than the same proof without that cycle. In a finite knowledge base there are finitely many useful acyclic proof trees, so strictly improving updates terminate. Unsupported cycles derive nothing. The tests cover both ordinary and weighted cycles, duplicate rules, and repeated runs.

If R is the number of rules, A the largest antecedent count, and U the number of successful updates, inference scanning costs O(R log R + (U+1)R(A+1)). In Boolean mode U is at most R; weighted mode may update a rule's conclusion more than once. The trace and retained proof nodes take O(U(A+1)) space in addition to the rules and initial facts. Exporting a nested explanation may expand shared proof branches. This small teaching engine is intended for the assignment, not very large knowledge bases.

## Explanations

Every firing records the rule, prerequisite names and scores, rule weight, old consequent score, and new score. Output prints this chronological trace and a nested explanation for every recommendation/specification. The strongest proof tree ends at user-supplied facts and shows minimum support multiplied by rule weight at every inference step.

Proof nodes are snapshots: later confidence improvements do not rewrite previous derivations. `explain(fact)` returns a deep copy so callers cannot alter the engine's record. Equal-strength alternative proofs are not enumerated; the first strongest proof is retained deterministically.

`--why-not FACT` explains a supported target or lists the immediate missing prerequisites for every rule that could derive an unsupported target. It also identifies disabled rules and targets with no rule. This is a diagnostic of current support, not backward-chaining inference or an automatic question-generation system.

## Input behavior

Normal execution collects categorical facts and assumes confidence 1. In `--uncertain` mode, the same questions are followed by a confidence prompt for each positively selected fact. Enter accepts 1; 0 withdraws positive support for this run. Budget and OS choices are exclusive. The office-only question is skipped when gaming or creative work is selected. All other source facts are collected individually. OS `any` asserts no OS preference.

The API is monotonic: repeated `assert_facts` calls can increase support but cannot decrease it. Start a new engine to retract or revise a fact downward. Directly editing internal working-memory dictionaries is unsupported. The CLI constructs a fresh engine for each run.

## Validation and limits

The suite contains 39 test methods with additional subtests. The original tests verify every supplied rule and every missing prerequisite, combined profiles, multistep reasoning, priorities, ties, cycles, loading, input validation, and CLI behavior. Fourteen bonus tests verify weighted calculations, propagation of stronger evidence, duplicate-proof handling, weighted cycles, unknown facts, disabled rules, score validation, proof snapshots, confidence prompts, why-not diagnostics, and a complete uncertainty-mode session. See TEST_RESULTS.txt for the captured results. Python 3.8 syntax is checked; executable tests use the available Python 3.12 interpreter.

Windows preference still has no rule in the supplied knowledge base. Some profiles yield specifications only or no result. Multiple recommendations are preserved. The rules do not resolve product compatibility conflicts or identify actual laptop models. Priorities select firing order, not recommendation quality. Confidence does not repair incomplete or conflicting domain rules. These limits are disclosed rather than hidden behind artificial scores.

## Attribution

The supplied ZIP provided the initial module structure, Rule fields, engine signatures, loading pattern, and ultrabook example. The assignment documents provided the project requirements and domain rules.

I designed and implemented the core logic and functionality of the project and performed testing to verify the implementation. I used AI assistance to help organize the project structure, improve the overall completeness and clarity of the implementation, prepare documentation, and write some of the tests. I reviewed the resulting work and refined it to ensure that it aligned with the assignment requirements.
