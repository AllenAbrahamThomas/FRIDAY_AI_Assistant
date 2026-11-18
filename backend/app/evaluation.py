import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.intent_classifier import intent_classifier


CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "cases.json"


def load_evaluation_cases() -> List[Dict[str, Any]]:
    with CASES_PATH.open("r", encoding="utf-8") as cases_file:
        return json.load(cases_file)["cases"]


def evaluate_routing(cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    evaluation_cases = cases if cases is not None else load_evaluation_cases()
    mismatches = []
    per_intent: Dict[str, Dict[str, int]] = {}

    for case in evaluation_cases:
        actual = intent_classifier.classify(case["prompt"])
        intent_stats = per_intent.setdefault(
            case["expected_intent"],
            {"total": 0, "correct": 0}
        )
        intent_stats["total"] += 1
        is_correct = (
            actual.intent == case["expected_intent"]
            and actual.requires_tools == case["requires_tools"]
        )
        if is_correct:
            intent_stats["correct"] += 1
        else:
            mismatches.append({
                "id": case["id"],
                "expected_intent": case["expected_intent"],
                "actual_intent": actual.intent,
                "expected_requires_tools": case["requires_tools"],
                "actual_requires_tools": actual.requires_tools
            })

    total = len(evaluation_cases)
    correct = total - len(mismatches)
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "per_intent": per_intent,
        "mismatches": mismatches
    }


def main() -> None:
    report = evaluate_routing()
    print(f"Routing accuracy: {report['correct']}/{report['total']} ({report['accuracy']:.1%})")
    for intent, counts in sorted(report["per_intent"].items()):
        print(f"{intent}: {counts['correct']}/{counts['total']}")
    for mismatch in report["mismatches"]:
        print(f"Mismatch {mismatch['id']}: {mismatch['actual_intent']}")


if __name__ == "__main__":
    main()
