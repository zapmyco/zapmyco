"""
User Experience Metrics - Implements metrics for evaluating user experience
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics


class UserExperienceMetrics:
    """Calculates various user experience related metrics"""

    @staticmethod
    def calculate_interaction_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate metrics related to user interactions

        Args:
            results: List of test results containing interaction data

        Returns:
            Dict containing interaction metrics
        """
        interaction_times = [
            r.get("interaction_time", 0) for r in results if "interaction_time" in r
        ]
        interaction_steps = [
            r.get("interaction_steps", 0) for r in results if "interaction_steps" in r
        ]

        metrics = {}

        if interaction_times:
            metrics["response_times"] = {
                "avg": round(statistics.mean(interaction_times), 3),
                "median": round(statistics.median(interaction_times), 3),
                "p95": round(
                    sorted(interaction_times)[int(len(interaction_times) * 0.95)], 3
                ),
            }

        if interaction_steps:
            metrics["interaction_steps"] = {
                "avg": round(statistics.mean(interaction_steps), 2),
                "min": min(interaction_steps),
                "max": max(interaction_steps),
            }

        return metrics

    @staticmethod
    def calculate_satisfaction_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate user satisfaction related metrics

        Args:
            results: List of test results containing satisfaction scores

        Returns:
            Dict containing satisfaction metrics
        """
        satisfaction_scores = [
            r.get("satisfaction_score", 0) for r in results if "satisfaction_score" in r
        ]
        feedback = defaultdict(int)

        for result in results:
            if "feedback" in result:
                feedback[result["feedback"]] += 1

        metrics = {}

        if satisfaction_scores:
            metrics["satisfaction"] = {
                "avg_score": round(statistics.mean(satisfaction_scores), 2),
                "median_score": round(statistics.median(satisfaction_scores), 2),
                "score_distribution": {
                    score: satisfaction_scores.count(score)
                    for score in set(satisfaction_scores)
                },
            }

        if feedback:
            metrics["feedback"] = dict(feedback)

        return metrics

    @staticmethod
    def calculate_usability_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate system usability metrics

        Args:
            results: List of test results containing usability data

        Returns:
            Dict containing usability metrics
        """
        success_rate = (
            sum(1 for r in results if r.get("task_completed", False)) / len(results)
            if results
            else 0
        )
        error_rate = (
            sum(1 for r in results if r.get("user_errors", 0) > 0) / len(results)
            if results
            else 0
        )

        completion_times = [
            r.get("task_completion_time", 0)
            for r in results
            if "task_completion_time" in r
        ]

        metrics = {
            "task_completion_rate": round(success_rate * 100, 2),
            "error_rate": round(error_rate * 100, 2),
        }

        if completion_times:
            metrics["completion_time"] = {
                "avg": round(statistics.mean(completion_times), 2),
                "median": round(statistics.median(completion_times), 2),
                "std_dev": round(
                    (
                        statistics.stdev(completion_times)
                        if len(completion_times) > 1
                        else 0
                    ),
                    2,
                ),
            }

        return metrics

    @staticmethod
    def calculate_accessibility_score(
        results: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Calculate accessibility related metrics

        Args:
            results: List of test results containing accessibility data

        Returns:
            Dict containing accessibility metrics
        """
        accessibility_scores = []
        criteria_scores = defaultdict(list)

        for result in results:
            if "accessibility" in result:
                acc_data = result["accessibility"]
                if "score" in acc_data:
                    accessibility_scores.append(acc_data["score"])

                # Collect scores for different criteria
                for criterion, score in acc_data.get("criteria", {}).items():
                    criteria_scores[criterion].append(score)

        metrics = {}

        if accessibility_scores:
            metrics["overall_score"] = round(statistics.mean(accessibility_scores), 2)

        if criteria_scores:
            metrics["criteria_scores"] = {
                criterion: round(statistics.mean(scores), 2)
                for criterion, scores in criteria_scores.items()
            }

        return metrics
