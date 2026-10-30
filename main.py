"""Interactive laptop advisor. Run with Python 3.8 or newer."""
import argparse
from pathlib import Path
import sys
from engine import ForwardChainingEngine, validate_confidence
from kb_loader import load_rules

KB_PATH = Path(__file__).resolve().parent / "kb" / "laptop_rules.json"


def ask_choice(prompt, choices):
    """Reprompt until a complete valid answer is supplied."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return answer
        print("Please enter one of: {}.".format(", ".join(choices)))


def ask_yes_no(prompt):
    return ask_choice(prompt + " (y/n): ", ("y", "yes", "n", "no")) in ("y", "yes")


def collect_initial_facts():
    facts = []
    budget = ask_choice("Budget (low/medium/high): ", ("low", "medium", "high"))
    facts.append("budget_" + budget)
    os_choice = ask_choice("Preferred OS (windows/macos/linux/any): ",
                           ("windows", "macos", "linux", "any"))
    if os_choice != "any":
        facts.append("pref_os_" + os_choice)
    for fact, question in (
        ("portable", "Is portability important?"),
        ("long_battery", "Do you need long battery life?"),
        ("gaming", "Will you use the laptop for gaming?"),
        ("creative_work", "Will you do creative work?"),
    ):
        if ask_yes_no(question):
            facts.append(fact)
    # 'Office only' excludes gaming and creative work by its meaning.
    if "gaming" not in facts and "creative_work" not in facts:
        if ask_yes_no("Is your usage office work only?"):
            facts.append("office_only")
    for fact, question in (
        ("needs_ai_accel", "Do you need AI acceleration?"),
        ("large_screen", "Do you want a large screen?"),
        ("travel_often", "Do you travel often?"),
    ):
        if ask_yes_no(question):
            facts.append(fact)
    return facts


def collect_confidences(facts):
    """Let the user express uncertainty about each positive input fact."""
    scores = {}
    print("\nEnter support from 0 to 1 for each fact; Enter means 1.")
    print("0 means unknown/no positive support, not a negative fact.")
    for fact in facts:
        while True:
            raw = input("Confidence for {} [1]: ".format(fact)).strip()
            try:
                scores[fact] = validate_confidence(float(raw) if raw else 1.0)
                break
            except ValueError:
                print("Please enter a finite number from 0 to 1.")
    return scores


def print_proof(proof, indent=0):
    if proof is None:
        return
    prefix = "  " * indent
    if proof["source"] == "user":
        print("{}{}: {:.1%} (user input)".format(prefix, proof["fact"], proof["confidence"]))
    else:
        scores = [p["confidence"] for p in proof["premises"]]
        print("{}{}: {:.1%} via '{}' (min support {:.1%} x rule {:.1%})".format(
            prefix, proof["fact"], proof["confidence"], proof["rule"],
            min(scores, default=1.0), proof["rule_confidence"]))
        for premise in proof["premises"]:
            print_proof(premise, indent + 1)


def print_why_not(engine, fact):
    print("\nWhy / why not: " + fact)
    if fact in engine.facts:
        print("This fact is supported; its strongest explanation is:")
        print_proof(engine.explain(fact))
        return
    candidates = engine.why_not(fact)
    if not candidates:
        print("No rule derives this fact and no positive user support was supplied.")
    for candidate in candidates:
        if candidate["missing"]:
            print("{}: missing positive support for {}.".format(
                candidate["rule"], ", ".join(candidate["missing"])))
        elif candidate["rule_confidence"] == 0:
            print("{}: rule confidence is zero (disabled).".format(candidate["rule"]))
        else:
            print("{}: available support {:.1%}.".format(
                candidate["rule"], candidate["available_support"]))


def print_results(engine):
    results = engine.conclusions()
    print("\nResults")
    for category, label in (("recommendations", "Recommendation"), ("specs", "Specification")):
        for value in results[category]:
            fact = ("recommend:" if category == "recommendations" else "spec:") + value
            print("> {}: {} (support {:.1%})".format(label, value, engine.confidence[fact]))
    if not results["recommendations"]:
        print("No laptop recommendation matched the supplied rules.")
    if not results["specs"]:
        print("No additional specifications matched the supplied rules.")
    print("\nFired rules (in execution order)")
    if not engine.trace:
        print("None. No rule had all required facts.")
    for step, event in enumerate(engine.trace, start=1):
        print("{}. {}: IF {} THEN {}".format(
            step, event["rule"], " AND ".join(event["antecedents"]) or "TRUE",
            event["consequent"]))
        print("   Support: {:.1%} -> {:.1%}".format(
            event["previous_confidence"], event["confidence"]))
    print("\nHow the results were derived (strongest support)")
    for fact in sorted(engine.facts):
        if fact.startswith(("recommend:", "spec:")):
            print_proof(engine.explain(fact))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Forward-chaining laptop advisor")
    parser.add_argument("--uncertain", action="store_true",
                        help="ask for confidence in each positive input fact")
    parser.add_argument("--why-not", metavar="FACT",
                        help="explain a target such as recommend:premium_ultrabook")
    args = parser.parse_args(argv)
    try:
        rules = load_rules(str(KB_PATH))
        print("Laptop Advisor - rule-based expert system")
        engine = ForwardChainingEngine(rules)
        facts = collect_initial_facts()
        scores = collect_confidences(facts) if args.uncertain else None
        engine.assert_facts(facts, scores)
        print("Support scores express rule-based confidence, not measured probabilities.")
        engine.run()
        print_results(engine)
        if args.why_not:
            print_why_not(engine, args.why_not)
        return 0
    except (OSError, ValueError) as error:
        print("Unable to load knowledge base: {}".format(error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled; no advice generated.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
