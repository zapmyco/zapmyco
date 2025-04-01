"""
Benchmark Runner - Runs performance benchmarks on the Home Agent
"""

import os
import json
import time
import logging
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime

from evaluation.framework.connectors.agent_connector import AgentConnector
from evaluation.framework.utils.dataset_loader import load_dataset

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Runs performance benchmarks on the Home Agent
    """

    def __init__(self, agent_config: Dict[str, Any], eval_config: Dict[str, Any]):
        """
        Initialize the benchmark runner

        Args:
            agent_config: Configuration for the agent
            eval_config: Evaluation configuration
        """
        self.agent_config = agent_config
        self.eval_config = eval_config

        # Initialize agent connector
        self.agent_connector = AgentConnector(agent_config)

        # Benchmark parameters
        self.iterations = eval_config.get("benchmark_iterations", 3)
        self.warmup_iterations = eval_config.get("warmup_iterations", 1)
        self.timeout = eval_config.get("timeout", 60)

        # Setup output directory
        self.output_dir = eval_config.get("benchmark_output_dir", "results/benchmarks")
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(
            f"Benchmark runner initialized with {self.iterations} iterations "
            f"({self.warmup_iterations} warmup)"
        )

    def run(self) -> Dict[str, Any]:
        """
        Run benchmarks

        Returns:
            Dict with benchmark results
        """
        start_time = time.time()

        # Load benchmark test cases
        benchmark_file = self.eval_config.get("benchmark_file", "benchmark_tests.jsonl")
        benchmark_dataset = self.eval_config.get("benchmark_dataset", "core")

        test_cases = load_dataset(
            dataset_name=benchmark_dataset,
            test_file=benchmark_file,
            datasets_dir=self.eval_config.get("datasets_dir", "datasets"),
        )

        if not test_cases:
            logger.warning("No benchmark test cases found")
            return {"error": "No benchmark test cases found"}

        logger.info(
            f"Running benchmarks with {len(test_cases)} test cases, "
            f"{self.iterations} iterations each"
        )

        # Run benchmarks
        benchmark_results = []

        for test_case in test_cases:
            test_id = test_case.get("test_id", "unknown")
            category = test_case.get("category", "unknown")

            logger.info(f"Benchmarking test {test_id} ({category})")

            # Run benchmark for this test case
            result = self._benchmark_test_case(test_case)
            benchmark_results.append(result)

        # Calculate overall statistics
        overall_stats = self._calculate_overall_stats(benchmark_results)

        # Prepare final results
        results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": time.time() - start_time,
            "config": {
                "agent": self.agent_config.get("name", "zapmyco"),
                "version": self.agent_config.get("version", "unknown"),
                "iterations": self.iterations,
                "warmup_iterations": self.warmup_iterations,
            },
            "overall": overall_stats,
            "test_results": benchmark_results,
        }

        # Save results
        self._save_results(results)

        logger.info(f"Benchmarks completed in {results['duration']:.2f} seconds")
        logger.info(f"Average response time: {overall_stats['mean_time']:.3f} seconds")

        return results

    def _benchmark_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run benchmark for a single test case

        Args:
            test_case: Test case to benchmark

        Returns:
            Dict with benchmark results for this test case
        """
        test_id = test_case.get("test_id", "unknown")
        input_data = test_case.get("input", {})

        # Results storage
        times = []
        responses = []
        errors = []

        # Warmup iterations
        for i in range(self.warmup_iterations):
            logger.debug(
                f"Warmup iteration {i+1}/{self.warmup_iterations} for {test_id}"
            )
            try:
                self.agent_connector.send_request(input_data, timeout=self.timeout)
            except Exception as e:
                logger.warning(f"Error during warmup: {e}")

        # Benchmark iterations
        for i in range(self.iterations):
            logger.debug(f"Benchmark iteration {i+1}/{self.iterations} for {test_id}")

            try:
                start_time = time.time()
                response = self.agent_connector.send_request(
                    input_data, timeout=self.timeout
                )
                end_time = time.time()

                duration = end_time - start_time
                times.append(duration)
                responses.append(response)

                logger.debug(f"Iteration {i+1} completed in {duration:.3f} seconds")

            except Exception as e:
                logger.warning(f"Error during benchmark iteration {i+1}: {e}")
                errors.append(str(e))

        # Calculate statistics
        stats = self._calculate_stats(times)

        return {
            "test_id": test_id,
            "category": test_case.get("category", "unknown"),
            "description": test_case.get("description", ""),
            "stats": stats,
            "success_rate": (
                (len(times) / self.iterations) * 100 if self.iterations > 0 else 0
            ),
            "errors": errors,
            "responses": (
                responses if self.eval_config.get("save_responses", False) else None
            ),
        }

    def _calculate_stats(self, times: List[float]) -> Dict[str, float]:
        """
        Calculate statistics from response times

        Args:
            times: List of response times

        Returns:
            Dict with statistics
        """
        if not times:
            return {
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "stdev": 0,
                "p90": 0,
                "p95": 0,
                "samples": 0,
            }

        times.sort()

        return {
            "min": round(min(times), 3),
            "max": round(max(times), 3),
            "mean": round(statistics.mean(times), 3),
            "median": round(statistics.median(times), 3),
            "stdev": round(statistics.stdev(times), 3) if len(times) > 1 else 0,
            "p90": round(times[int(len(times) * 0.9)], 3),
            "p95": round(times[int(len(times) * 0.95)], 3),
            "samples": len(times),
        }

    def _calculate_overall_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate overall statistics from all benchmark results

        Args:
            results: List of benchmark results

        Returns:
            Dict with overall statistics
        """
        # Collect all times
        all_times = []
        for result in results:
            times = [
                result["stats"].get("min", 0),
                result["stats"].get("max", 0),
                result["stats"].get("mean", 0),
            ]
            all_times.extend([t for t in times if t > 0])

        # Calculate success rate
        total_iterations = len(results) * self.iterations
        successful_iterations = sum(
            result["stats"].get("samples", 0) for result in results
        )
        success_rate = (
            (successful_iterations / total_iterations) * 100
            if total_iterations > 0
            else 0
        )

        return {
            "total_tests": len(results),
            "total_iterations": total_iterations,
            "successful_iterations": successful_iterations,
            "success_rate": round(success_rate, 2),
            "min_time": round(min(all_times), 3) if all_times else 0,
            "max_time": round(max(all_times), 3) if all_times else 0,
            "mean_time": round(statistics.mean(all_times), 3) if all_times else 0,
            "median_time": round(statistics.median(all_times), 3) if all_times else 0,
        }

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save benchmark results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/benchmark_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Benchmark results saved to {filename}")
