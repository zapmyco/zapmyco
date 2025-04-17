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

    async def run(self) -> Dict[str, Any]:
        """
        Run benchmarks on all test cases

        Returns:
            Dict containing benchmark results
        """
        # Load test cases
        test_cases = load_dataset(
            dataset_name=self.eval_config.get("dataset"),
            test_file=self.eval_config.get("test_file"),
            datasets_dir=self.eval_config.get("datasets_dir", "datasets"),
        )

        start_time = time.time()
        results = []

        # Run benchmarks for each test case
        for test_case in test_cases:
            result = await self._benchmark_test_case(test_case)
            results.append(result)

        # Calculate overall statistics
        all_times = []
        for result in results:
            all_times.extend(result.get("times", []))

        overall_stats = self._calculate_stats(all_times)

        # Prepare results
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": time.time() - start_time,
            "config": {
                "iterations": self.iterations,
                "warmup_iterations": self.warmup_iterations,
                "timeout": self.timeout,
            },
            "overall_stats": overall_stats,
            "test_results": results,
        }

        # Save results
        self._save_results(results)

        logger.info(f"Benchmarks completed in {results['duration']:.2f} seconds")
        logger.info(f"Average response time: {overall_stats['mean_time']:.3f} seconds")

        return results

    async def _benchmark_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
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
                await self.agent_connector.send_request(
                    input_data, timeout=self.timeout
                )
            except Exception as e:
                logger.warning(f"Error during warmup: {e}")

        # Benchmark iterations
        for i in range(self.iterations):
            logger.debug(f"Benchmark iteration {i+1}/{self.iterations} for {test_id}")

            try:
                start_time = time.time()
                response = await self.agent_connector.send_request(
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
            "times": times,
            "responses": responses,
            "errors": errors,
            "stats": stats,
        }

    def _calculate_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate statistics from a list of times"""
        if not times:
            return {
                "mean_time": 0,
                "median_time": 0,
                "min_time": 0,
                "max_time": 0,
                "std_dev": 0,
            }

        return {
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save benchmark results to file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/benchmark_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Benchmark results saved to {filename}")
