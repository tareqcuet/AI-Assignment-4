"""Load and validate a JSON knowledge base without domain-specific logic."""
import json
from typing import List
from engine import Rule


def load_rules(path: str) -> List[Rule]:
    with open(path, "r", encoding="utf-8") as stream:
        raw = json.load(stream)
    if not isinstance(raw, list):
        raise ValueError("Knowledge base must be a JSON list of rules.")
    rules = []
    for i, item in enumerate(raw, start=1):
        label = "Rule #{}".format(i)
        if not isinstance(item, dict):
            raise ValueError(label + " must be an object.")
        antecedents = item.get("if")
        consequent = item.get("then")
        if not isinstance(antecedents, list) or not all(
            isinstance(fact, str) and fact.strip() for fact in antecedents
        ):
            raise ValueError(label + " needs an 'if' list of nonempty strings.")
        if not isinstance(consequent, str) or not consequent.strip():
            raise ValueError(label + " needs a nonempty 'then' string.")
        priority = item.get("priority", 0)
        name = item.get("name", label)
        if type(priority) is not int:
            raise ValueError(label + " priority must be an integer.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(label + " name must be a nonempty string.")
        rules.append(Rule(antecedents, consequent, priority, name,
                          item.get("confidence", 1.0)))
    return rules
