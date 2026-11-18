import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.evaluation import evaluate_routing, load_evaluation_cases


def test_routing_evaluation_dataset_is_repeatable_and_measurable():
    cases = load_evaluation_cases()
    report = evaluate_routing(cases)

    assert len(cases) == 15
    assert report["total"] == 15
    assert report["correct"] == 15
    assert report["accuracy"] == 1.0
    assert report["mismatches"] == []
