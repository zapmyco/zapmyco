"""
Robustness Metrics - Implements system stability and reliability metrics
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict


class RobustnessMetrics:
    """Calculates various robustness and reliability metrics"""

    @staticmethod
    def calculate_error_distribution(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate distribution of different types of errors

        Args:
            results: List of test results

        Returns:
            Dict containing error distribution metrics
        """
        error_types = defaultdict(int)
        total_tests = len(results)

        for result in results:
            if result.get("status") in ["failed", "error"]:
                error_type = result.get("error_type", "unknown")
                error_types[error_type] += 1

        # Calculate percentages
        error_distribution = {
            error_type: {
                "count": count,
                "percentage": round((count / total_tests) * 100, 2),
            }
            for error_type, count in error_types.items()
        }

        return {
            "total_errors": sum(error_types.values()),
            "error_types": error_distribution,
        }

    @staticmethod
    def calculate_stability_score(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate system stability metrics

        Args:
            results: List of test results

        Returns:
            Dict containing stability metrics
        """
        total_tests = len(results)
        if total_tests == 0:
            return {
                "stability_score": 0.0,
                "consistency_score": 0.0,
                "recovery_rate": 0.0,
            }

        # Calculate consecutive failures
        max_consecutive_failures = 0
        current_consecutive_failures = 0

        for result in results:
            if result.get("status") in ["failed", "error"]:
                current_consecutive_failures += 1
                max_consecutive_failures = max(
                    max_consecutive_failures, current_consecutive_failures
                )
            else:
                current_consecutive_failures = 0

        # Calculate recovery rate (successful tests after failures)
        recoveries = 0
        for i in range(1, len(results)):
            if (
                results[i - 1].get("status") in ["failed", "error"]
                and results[i].get("status") == "passed"
            ):
                recoveries += 1

        failure_count = sum(
            1 for r in results if r.get("status") in ["failed", "error"]
        )
        recovery_rate = (
            round(recoveries / failure_count, 3) if failure_count > 0 else 1.0
        )

        # Calculate stability score (weighted combination of metrics)
        success_rate = (total_tests - failure_count) / total_tests
        consistency = 1.0 - (max_consecutive_failures / total_tests)

        stability_score = round(
            0.4 * success_rate + 0.3 * consistency + 0.3 * recovery_rate, 3
        )

        return {
            "stability_score": stability_score,
            "consistency_score": round(consistency, 3),
            "recovery_rate": recovery_rate,
            "max_consecutive_failures": max_consecutive_failures,
        }

    @staticmethod
    def calculate_load_tolerance(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate system's tolerance to varying load conditions

        Args:
            results: List of test results with load information

        Returns:
            Dict containing load tolerance metrics
        """
        # Group results by load level
        load_groups = defaultdict(list)
        for result in results:
            load_level = result.get("load_level", "normal")
            load_groups[load_level].append(result)

        tolerance_metrics = {}

        for load_level, group_results in load_groups.items():
            success_rate = sum(1 for r in group_results if r.get("status") == "passed")
            total = len(group_results)

            if total > 0:
                tolerance_metrics[load_level] = {
                    "success_rate": round((success_rate / total) * 100, 2),
                    "total_tests": total,
                    "avg_response_time": round(
                        sum(r.get("duration", 0) for r in group_results) / total, 3
                    ),
                }

        return tolerance_metrics


if __name__ == "__main__":
    # Example usage of RobustnessMetrics
    example_results = [
        {"status": "passed", "error_type": None, "load_level": "normal"},
        {"status": "failed", "error_type": "timeout", "load_level": "high"},
        {"status": "error", "error_type": "connection", "load_level": "normal"},
        {"status": "passed", "error_type": None, "load_level": "low"},
        {"status": "failed", "error_type": "validation", "load_level": "high"},
        {"status": "passed", "error_type": None, "load_level": "normal"},
        {"status": "error", "error_type": "connection", "load_level": "high"},
        {"status": "passed", "error_type": None, "load_level": "normal"},
    ]

    # Calculate error distribution
    error_dist = RobustnessMetrics.calculate_error_distribution(example_results)
    print("\nError Distribution:")
    print(f"Total Errors: {error_dist['total_errors']}")
    print("\nError Types:")
    for error_type, stats in error_dist["error_types"].items():
        print(f"{error_type}: {stats['count']} occurrences ({stats['percentage']}%)")

    # Calculate stability metrics
    stability = RobustnessMetrics.calculate_stability_score(example_results)
    print("\nStability Metrics:")
    print(f"Overall Stability Score: {stability['stability_score']}")
    print(f"Consistency Score: {stability['consistency_score']}")
    print(f"Recovery Rate: {stability['recovery_rate']}")
    print(f"Max Consecutive Failures: {stability['max_consecutive_failures']}")

    # Calculate load tolerance
    load_tolerance = RobustnessMetrics.calculate_load_tolerance(example_results)
    print("\nLoad Tolerance by Level:")
    for level, metrics in load_tolerance.items():
        print(f"\n{level.upper()} Load:")
        print(f"Success Rate: {metrics['success_rate']}%")
        print(f"Total Tests: {metrics['total_tests']}")
        print(f"Average Response Time: {metrics['avg_response_time']} seconds")
