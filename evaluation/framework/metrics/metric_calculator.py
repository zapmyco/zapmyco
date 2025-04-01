"""
Metric Calculator - Calculates evaluation metrics from test results
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MetricCalculator:
    """
    Calculates evaluation metrics from test results
    """

    def __init__(self, metrics_config: Dict[str, Any]):
        """
        Initialize the metric calculator

        Args:
            metrics_config: Configuration for metrics calculation
        """
        self.metrics_config = metrics_config
        self.enabled_metrics = metrics_config.get("enabled_metrics", [])

        # If no specific metrics are enabled, enable all
        if not self.enabled_metrics:
            self.enabled_metrics = [
                "overall_success_rate",
                "category_success_rates",
                "response_times",
                "accuracy_metrics",
                "feature_coverage",
            ]

        logger.info(
            f"Metric calculator initialized with {len(self.enabled_metrics)} enabled metrics"
        )

    def calculate_all_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate all enabled metrics from test results

        Args:
            results: List of test results

        Returns:
            Dict containing all calculated metrics
        """
        metrics = {}

        if "overall_success_rate" in self.enabled_metrics:
            metrics["overall_success_rate"] = self.calculate_success_rate(results)

        if "category_success_rates" in self.enabled_metrics:
            metrics["category_success_rates"] = self.calculate_category_success_rates(
                results
            )

        if "response_times" in self.enabled_metrics:
            metrics["response_times"] = self.calculate_response_times(results)

        # if "accuracy_metrics" in self.enabled_metrics:
        #     metrics["accuracy_metrics"] = self.calculate_accuracy_metrics(results)

        if "feature_coverage" in self.enabled_metrics:
            metrics["feature_coverage"] = self.calculate_feature_coverage(results)

        # Calculate any custom metrics defined in the config
        for custom_metric in self.metrics_config.get("custom_metrics", []):
            metric_name = custom_metric.get("name")
            if metric_name:
                try:
                    metrics[metric_name] = self.calculate_custom_metric(
                        results, custom_metric
                    )
                except Exception as e:
                    logger.error(
                        f"Error calculating custom metric '{metric_name}': {e}"
                    )

        return metrics

    def calculate_success_rate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate overall success rate

        Args:
            results: List of test results

        Returns:
            Dict with success rate metrics
        """
        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        errors = sum(1 for r in results if r.get("status") == "error")

        success_rate = 0
        if total > 0:
            success_rate = (passed / total) * 100

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "rate": round(success_rate, 2),
        }

    def calculate_category_success_rates(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate success rates by category

        Args:
            results: List of test results

        Returns:
            Dict with category-specific success rates
        """
        categories = {}

        # Group results by category
        for result in results:
            category = result.get("category", "unknown")
            if category not in categories:
                categories[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                }

            categories[category]["total"] += 1
            status = result.get("status", "unknown")
            if status == "passed":
                categories[category]["passed"] += 1
            elif status == "failed":
                categories[category]["failed"] += 1
            elif status == "error":
                categories[category]["errors"] += 1

        # Calculate success rates
        for category, stats in categories.items():
            if stats["total"] > 0:
                stats["rate"] = round((stats["passed"] / stats["total"]) * 100, 2)
            else:
                stats["rate"] = 0

        return categories

    def calculate_response_times(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate response time metrics

        Args:
            results: List of test results

        Returns:
            Dict with response time metrics
        """
        durations = [r.get("duration", 0) for r in results if "duration" in r]

        if not durations:
            return {"min": 0, "max": 0, "avg": 0, "median": 0}

        durations.sort()

        return {
            "min": round(min(durations), 3),
            "max": round(max(durations), 3),
            "avg": round(sum(durations) / len(durations), 3),
            "median": round(durations[len(durations) // 2], 3),
            "p90": round(durations[int(len(durations) * 0.9)], 3),
            "p95": round(durations[int(len(durations) * 0.95)], 3),
            "total_count": len(durations),
        }

    def calculate_accuracy_metrics(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate accuracy-related metrics

        Args:
            results: List of test results

        Returns:
            Dict with accuracy metrics
        """
        # Count tests with different types of expected outputs
        total_with_execution = sum(
            1 for r in results if "execution" in r.get("expected_output", {})
        )
        passed_execution = sum(
            1
            for r in results
            if "execution" in r.get("expected_output", {})
            and r.get("comparison", {}).get("execution", {}).get("success", False)
        )

        # Calculate execution success rate
        execution_rate = 0
        if total_with_execution > 0:
            execution_rate = (passed_execution / total_with_execution) * 100

        # Calculate field match rates
        field_matches = []
        for result in results:
            comparison = result.get("comparison", {})
            fields = comparison.get("fields", {})

            if fields:
                matched = sum(1 for f in fields.values() if f.get("match", False))
                total = len(fields)

                if total > 0:
                    field_matches.append(matched / total)

        # Calculate average field match rate
        avg_field_match = 0
        if field_matches:
            avg_field_match = sum(field_matches) / len(field_matches) * 100

        return {
            "execution_success_rate": round(execution_rate, 2),
            "field_match_rate": round(avg_field_match, 2),
            "total_with_execution": total_with_execution,
            "passed_execution": passed_execution,
        }

    def calculate_feature_coverage(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate feature coverage metrics based on tags

        Args:
            results: List of test results

        Returns:
            Dict with feature coverage metrics
        """
        # Collect all unique tags
        all_tags = set()
        for result in results:
            tags = result.get("tags", [])
            all_tags.update(tags)

        # Count tests and passed tests per tag
        tag_stats = {}
        for tag in all_tags:
            tag_tests = [r for r in results if tag in r.get("tags", [])]
            passed = sum(1 for r in tag_tests if r.get("status") == "passed")

            tag_stats[tag] = {
                "total": len(tag_tests),
                "passed": passed,
                "rate": round((passed / len(tag_tests)) * 100, 2) if tag_tests else 0,
            }

        # Sort tags by frequency
        sorted_tags = sorted(
            tag_stats.items(), key=lambda x: x[1]["total"], reverse=True
        )

        return {"total_features": len(all_tags), "features": dict(sorted_tags)}

    def calculate_custom_metric(
        self, results: List[Dict[str, Any]], metric_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate a custom metric as defined in the config

        Args:
            results: List of test results
            metric_config: Configuration for the custom metric

        Returns:
            Dict with custom metric results
        """
        metric_type = metric_config.get("type", "unknown")

        if metric_type == "filter_count":
            # Count tests matching a filter
            filter_field = metric_config.get("filter_field", "status")
            filter_value = metric_config.get("filter_value")

            if filter_value is not None:
                count = sum(1 for r in results if r.get(filter_field) == filter_value)
                total = len(results)

                return {
                    "count": count,
                    "total": total,
                    "percentage": round((count / total) * 100, 2) if total > 0 else 0,
                }

        elif metric_type == "average_field":
            # Calculate average of a numeric field
            field = metric_config.get("field")

            if field:
                values = [r.get(field, 0) for r in results if field in r]

                if values:
                    return {
                        "average": round(sum(values) / len(values), 3),
                        "min": round(min(values), 3),
                        "max": round(max(values), 3),
                        "count": len(values),
                    }

        # Default return if metric type not recognized
        return {"error": f"Unknown metric type: {metric_type}"}
