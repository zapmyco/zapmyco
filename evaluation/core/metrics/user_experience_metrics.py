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


if __name__ == "__main__":
    # Example usage of UserExperienceMetrics
    example_results = [
        {
            "interaction_time": 2.5,
            "interaction_steps": 3,
            "satisfaction_score": 4,
            "feedback": "easy to use",
            "task_completed": True,
            "user_errors": 0,
            "task_completion_time": 45,
            "accessibility": {
                "score": 90,
                "criteria": {
                    "keyboard_navigation": 95,
                    "screen_reader": 85,
                    "color_contrast": 90,
                },
            },
        },
        {
            "interaction_time": 3.8,
            "interaction_steps": 5,
            "satisfaction_score": 3,
            "feedback": "slightly confusing",
            "task_completed": True,
            "user_errors": 2,
            "task_completion_time": 65,
            "accessibility": {
                "score": 85,
                "criteria": {
                    "keyboard_navigation": 90,
                    "screen_reader": 80,
                    "color_contrast": 85,
                },
            },
        },
        {
            "interaction_time": 1.9,
            "interaction_steps": 2,
            "satisfaction_score": 5,
            "feedback": "excellent",
            "task_completed": True,
            "user_errors": 0,
            "task_completion_time": 30,
            "accessibility": {
                "score": 95,
                "criteria": {
                    "keyboard_navigation": 100,
                    "screen_reader": 90,
                    "color_contrast": 95,
                },
            },
        },
    ]

    # Calculate interaction metrics
    interaction_metrics = UserExperienceMetrics.calculate_interaction_metrics(
        example_results
    )
    print("\nInteraction Metrics:")
    if "response_times" in interaction_metrics:
        print("\nResponse Times:")
        print(f"Average: {interaction_metrics['response_times']['avg']} seconds")
        print(f"Median: {interaction_metrics['response_times']['median']} seconds")
        print(
            f"95th Percentile: {interaction_metrics['response_times']['p95']} seconds"
        )

    if "interaction_steps" in interaction_metrics:
        print("\nInteraction Steps:")
        print(f"Average: {interaction_metrics['interaction_steps']['avg']} steps")
        print(f"Min: {interaction_metrics['interaction_steps']['min']} steps")
        print(f"Max: {interaction_metrics['interaction_steps']['max']} steps")

    # Calculate satisfaction metrics
    satisfaction = UserExperienceMetrics.calculate_satisfaction_metrics(example_results)
    print("\nSatisfaction Metrics:")
    if "satisfaction" in satisfaction:
        print(f"Average Score: {satisfaction['satisfaction']['avg_score']}")
        print(f"Median Score: {satisfaction['satisfaction']['median_score']}")
        print("\nScore Distribution:")
        for score, count in satisfaction["satisfaction"]["score_distribution"].items():
            print(f"Score {score}: {count} responses")

    if "feedback" in satisfaction:
        print("\nFeedback Summary:")
        for feedback, count in satisfaction["feedback"].items():
            print(f"{feedback}: {count} responses")

    # Calculate usability metrics
    usability = UserExperienceMetrics.calculate_usability_metrics(example_results)
    print("\nUsability Metrics:")
    print(f"Task Completion Rate: {usability['task_completion_rate']}%")
    print(f"Error Rate: {usability['error_rate']}%")

    if "completion_time" in usability:
        print("\nCompletion Time:")
        print(f"Average: {usability['completion_time']['avg']} seconds")
        print(f"Median: {usability['completion_time']['median']} seconds")
        print(f"Standard Deviation: {usability['completion_time']['std_dev']} seconds")

    # Calculate accessibility metrics
    accessibility = UserExperienceMetrics.calculate_accessibility_score(example_results)
    print("\nAccessibility Metrics:")
    if "overall_score" in accessibility:
        print(f"Overall Score: {accessibility['overall_score']}")

    if "criteria_scores" in accessibility:
        print("\nCriteria Scores:")
        for criterion, score in accessibility["criteria_scores"].items():
            print(f"{criterion}: {score}")
