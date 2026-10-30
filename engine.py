"""Domain-independent, monotonic forward chaining over symbolic facts."""
from dataclasses import dataclass
from copy import deepcopy
import math
from typing import Any, Dict, List, Set


def validate_confidence(value):
    """Accept only finite numeric support scores between zero and one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Confidence must be a number between 0 and 1.")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Confidence must be finite and between 0 and 1.")
    return float(value)


@dataclass
class Rule:
    antecedents: List[str]
    consequent: str
    priority: int = 0
    name: str = ""
    confidence: float = 1.0

    def __post_init__(self):
        self.confidence = validate_confidence(self.confidence)


class ForwardChainingEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = list(rules)
        self.facts: Set[str] = set()
        self.trace: List[Dict[str, Any]] = []
        self.confidence: Dict[str, float] = {}
        self.proofs: Dict[str, Dict[str, Any]] = {}

    def assert_facts(self, initial: List[str], confidences=None) -> None:
        """Add positive support; omitted scores default to 1.0.

        Zero means no positive support, not evidence of falsehood. Updates
        only increase support; create a new engine to retract facts.
        """
        confidences = {} if confidences is None else confidences
        scores = [(fact, validate_confidence(confidences.get(fact, 1.0)))
                  for fact in initial]
        for fact, score in scores:
            if score > self.confidence.get(fact, 0.0):
                self.facts.add(fact)
                self.confidence[fact] = score
                self.proofs[fact] = {"fact": fact, "confidence": score,
                                    "source": "user", "premises": []}

    def rule_support(self, rule: Rule) -> float:
        """AND uses minimum support, then multiplies by rule reliability."""
        return min((self.confidence.get(f, 0.0) for f in rule.antecedents),
                   default=1.0) * rule.confidence

    def can_fire(self, rule: Rule) -> bool:
        """Fire only if positive support would improve the conclusion."""
        return self.rule_support(rule) > self.confidence.get(rule.consequent, 0.0)

    def run(self) -> None:
        """Reach a support fixed point, highest priority first, stable ties.

        Multiple proofs use max, not addition, so repeated or correlated
        evidence cannot inflate confidence. Improved facts propagate again.
        """
        ordered_rules = sorted(self.rules, key=lambda rule: -rule.priority)
        while True:
            for rule in ordered_rules:
                if self.can_fire(rule):
                    support = self.rule_support(rule)
                    previous = self.confidence.get(rule.consequent, 0.0)
                    premises = [self.proofs[f] for f in rule.antecedents]
                    proof = {"fact": rule.consequent, "confidence": support,
                             "source": "rule", "rule": rule.name,
                             "rule_confidence": rule.confidence,
                             "premises": premises}
                    self.facts.add(rule.consequent)
                    self.confidence[rule.consequent] = support
                    # Proof nodes are replaced, never mutated. Earlier proofs
                    # remain accurate snapshots even after confidence updates.
                    self.proofs[rule.consequent] = proof
                    self.trace.append({
                        "rule": rule.name, "antecedents": list(rule.antecedents),
                        "consequent": rule.consequent, "priority": rule.priority,
                        "confidence": support, "previous_confidence": previous,
                        "rule_confidence": rule.confidence,
                        "antecedent_confidences": [p["confidence"] for p in premises],
                    })
                    break
            else:
                return

    def explain(self, fact: str):
        """Return an independent copy of the strongest recorded proof tree."""
        return deepcopy(self.proofs.get(fact))

    def why_not(self, fact: str):
        """Describe immediate rule requirements and their available support."""
        return [{"rule": rule.name,
                 "missing": [f for f in rule.antecedents if f not in self.facts],
                 "rule_confidence": rule.confidence,
                 "available_support": self.rule_support(rule)}
                for rule in self.rules if rule.consequent == fact]

    def conclusions(self) -> Dict[str, List[str]]:
        """Return sorted, deduplicated results; strip category prefixes."""
        result: Dict[str, List[str]] = {
            "recommendations": [], "specs": [], "other": []
        }
        for fact in sorted(self.facts):
            if fact.startswith("recommend:"):
                result["recommendations"].append(fact[len("recommend:"):])
            elif fact.startswith("spec:"):
                result["specs"].append(fact[len("spec:"):])
            else:
                result["other"].append(fact)
        return result
