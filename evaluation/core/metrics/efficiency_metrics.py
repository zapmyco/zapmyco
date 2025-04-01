"""
Efficiency Metrics - Implements performance and resource utilization metrics
"""

from typing import Dict, List, Any, Optional
import statistics
from datetime import datetime


class EfficiencyMetrics:
    """Calculates various efficiency and performance metrics"""

    @staticmethod
    def calculate_response_time_stats(
        results: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Calculate detailed response time statistics

        Args:
            results: List of test results containing duration information

        Returns:
            Dict containing response time statistics
        """
        durations = [r.get("duration", 0) for r in results if "duration" in r]

        if not durations:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "std_dev": 0.0}

        return {
            "min": round(min(durations), 3),
            "max": round(max(durations), 3),
            "mean": round(statistics.mean(durations), 3),
            "median": round(statistics.median(durations), 3),
            "std_dev": round(
                statistics.stdev(durations) if len(durations) > 1 else 0, 3
            ),
        }

    @staticmethod
    def calculate_throughput(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate system throughput metrics

        Args:
            results: List of test results with timestamps

        Returns:
            Dict containing throughput metrics
        """
        if not results:
            return {"requests_per_second": 0.0, "total_requests": 0}

        # Sort results by timestamp
        sorted_results = sorted(
            results,
            key=lambda x: datetime.fromisoformat(
                x.get("timestamp", "1970-01-01T00:00:00")
            ),
        )

        start_time = datetime.fromisoformat(
            sorted_results[0].get("timestamp", "1970-01-01T00:00:00")
        )
        end_time = datetime.fromisoformat(
            sorted_results[-1].get("timestamp", "1970-01-01T00:00:00")
        )

        duration = (end_time - start_time).total_seconds()
        if duration == 0:
            return {"requests_per_second": 0.0, "total_requests": len(results)}

        return {
            "requests_per_second": round(len(results) / duration, 2),
            "total_requests": len(results),
        }

    @staticmethod
    def calculate_resource_utilization(
        results: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Calculate resource utilization metrics

        Args:
            results: List of test results containing resource usage information

        Returns:
            Dict containing resource utilization metrics
        """
        memory_usage = [
            r.get("memory_usage", 0) for r in results if "memory_usage" in r
        ]
        cpu_usage = [r.get("cpu_usage", 0) for r in results if "cpu_usage" in r]

        metrics = {}

        if memory_usage:
            metrics["memory"] = {
                "avg": round(statistics.mean(memory_usage), 2),
                "max": round(max(memory_usage), 2),
                "min": round(min(memory_usage), 2),
            }

        if cpu_usage:
            metrics["cpu"] = {
                "avg": round(statistics.mean(cpu_usage), 2),
                "max": round(max(cpu_usage), 2),
                "min": round(min(cpu_usage), 2),
            }

        return metrics


if __name__ == "__main__":
    # Example usage of EfficiencyMetrics
    from datetime import datetime, timedelta

    # Create sample test results with timestamps
    base_time = datetime.now()
    example_results = [
        {
            "duration": 0.5,
            "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
            "memory_usage": 100 + i * 10,
            "cpu_usage": 50 + i * 5,
        }
        for i in range(5)
    ]

    # Calculate response time statistics
    response_stats = EfficiencyMetrics.calculate_response_time_stats(example_results)
    print("\nResponse Time Statistics:")
    print(f"Min: {response_stats['min']} seconds")
    print(f"Max: {response_stats['max']} seconds")
    print(f"Mean: {response_stats['mean']} seconds")
    print(f"Median: {response_stats['median']} seconds")
    print(f"Standard Deviation: {response_stats['std_dev']} seconds")

    # Calculate throughput metrics
    throughput = EfficiencyMetrics.calculate_throughput(example_results)
    print("\nThroughput Metrics:")
    print(f"Requests per second: {throughput['requests_per_second']}")
    print(f"Total requests: {throughput['total_requests']}")

    # Calculate resource utilization
    resource_metrics = EfficiencyMetrics.calculate_resource_utilization(example_results)
    print("\nResource Utilization:")
    if "memory" in resource_metrics:
        print("\nMemory Usage:")
        print(f"Average: {resource_metrics['memory']['avg']}MB")
        print(f"Maximum: {resource_metrics['memory']['max']}MB")
        print(f"Minimum: {resource_metrics['memory']['min']}MB")

    if "cpu" in resource_metrics:
        print("\nCPU Usage:")
        print(f"Average: {resource_metrics['cpu']['avg']}%")
        print(f"Maximum: {resource_metrics['cpu']['max']}%")
        print(f"Minimum: {resource_metrics['cpu']['min']}%")
