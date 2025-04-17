"""
Accuracy Metrics - Implements various accuracy measurement metrics
"""

from typing import Dict, List, Any, Optional
import numpy as np


class AccuracyMetrics:
    """Calculates various accuracy metrics for evaluation results"""

    @staticmethod
    def calculate_precision(true_positives: int, false_positives: int) -> float:
        """Calculate precision metric"""
        if true_positives + false_positives == 0:
            return 0.0
        return true_positives / (true_positives + false_positives)

    @staticmethod
    def calculate_recall(true_positives: int, false_negatives: int) -> float:
        """Calculate recall metric"""
        if true_positives + false_negatives == 0:
            return 0.0
        return true_positives / (true_positives + false_negatives)

    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """Calculate F1 score"""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def calculate_accuracy(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate accuracy metrics from test results

        Args:
            results: List of test results containing expected and actual outputs

        Returns:
            Dict containing various accuracy metrics
        """
        true_positives = sum(
            1
            for r in results
            if r.get("status") == "passed"
            and r.get("expected_output") == r.get("actual_output")
        )
        false_positives = sum(
            1
            for r in results
            if r.get("status") == "passed"
            and r.get("expected_output") != r.get("actual_output")
        )
        false_negatives = sum(
            1
            for r in results
            if r.get("status") == "failed"
            and r.get("expected_output") == r.get("actual_output")
        )

        precision = AccuracyMetrics.calculate_precision(true_positives, false_positives)
        recall = AccuracyMetrics.calculate_recall(true_positives, false_negatives)
        f1_score = AccuracyMetrics.calculate_f1_score(precision, recall)

        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }

    @staticmethod
    def calculate_error_rate(results: List[Dict[str, Any]]) -> float:
        """Calculate error rate from test results"""
        total = len(results)
        if total == 0:
            return 0.0
        errors = sum(1 for r in results if r.get("status") in ["failed", "error"])
        return round(errors / total, 3)


if __name__ == "__main__":
    # Example usage of AccuracyMetrics
    example_results = [
        {"status": "passed", "expected_output": "Hello", "actual_output": "Hello"},
        {
            "status": "passed",
            "expected_output": "World",
            "actual_output": "world",  # Case mismatch
        },
        {"status": "failed", "expected_output": "Test", "actual_output": "Error"},
        {"status": "error", "expected_output": "Data", "actual_output": None},
    ]

    # Calculate accuracy metrics
    accuracy_metrics = AccuracyMetrics.calculate_accuracy(example_results)
    print("\nAccuracy Metrics:")
    print(f"Precision: {accuracy_metrics['precision']}")
    print(f"Recall: {accuracy_metrics['recall']}")
    print(f"F1 Score: {accuracy_metrics['f1_score']}")
    print(f"True Positives: {accuracy_metrics['true_positives']}")
    print(f"False Positives: {accuracy_metrics['false_positives']}")
    print(f"False Negatives: {accuracy_metrics['false_negatives']}")

    # Calculate error rate
    error_rate = AccuracyMetrics.calculate_error_rate(example_results)
    print(f"\nError Rate: {error_rate}")
