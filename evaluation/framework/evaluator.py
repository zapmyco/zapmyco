"""
Evaluator module - Core component that runs tests against the Home Agent
"""

import os
import json
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

from evaluation.framework.connectors.agent_connector import AgentConnector
from evaluation.framework.metrics.metric_calculator import MetricCalculator
from evaluation.framework.utils.dataset_loader import load_dataset
from evaluation.framework.utils.result_processor import process_results
from zapmyco.integrations.home_assistant.context_provider import MockContextProvider
from zapmyco.integrations.home_assistant.mcp import HomeAssistantMCP
from zapmyco.integrations.home_assistant.client import HomeAssistantClient
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Evaluator:
    """
    Evaluator class that runs tests against the Home Agent and evaluates the results
    """

    def __init__(self, agent_config: Dict, eval_config: Dict, metrics_config: Dict):
        """
        Initialize the evaluator with configuration

        Args:
            agent_config: Configuration for connecting to the agent
            eval_config: Configuration for the evaluation process
            metrics_config: Configuration for metrics calculation
        """
        self.agent_config = agent_config
        self.eval_config = eval_config
        self.metrics_config = metrics_config

        # Initialize connector to the agent
        self.agent_connector = AgentConnector(agent_config)

        # Initialize metric calculator
        self.metric_calculator = MetricCalculator(metrics_config)

        # Setup directories
        self.results_dir = eval_config.get("output_dir", "results/raw_results")
        os.makedirs(self.results_dir, exist_ok=True)

        # Evaluation parameters
        self.timeout = eval_config.get("timeout", 60)  # seconds
        self.parallel = eval_config.get("parallel", False)
        self.max_workers = eval_config.get("max_workers", 4)

        logger.info(
            f"Evaluator initialized with timeout={self.timeout}s, parallel={self.parallel}"
        )

    @asynccontextmanager
    async def _get_ha_client(self):
        """
        Context manager for handling HomeAssistantClient lifecycle
        """
        client = HomeAssistantClient()
        try:
            await client.connect()
            yield client
        finally:
            await client.disconnect()
            await asyncio.sleep(0.1)  # 给予一些时间让资源清理完成

    async def run_evaluation(self) -> Dict[str, Any]:
        """
        Run the full evaluation process

        Returns:
            Dict containing all evaluation results and metrics
        """
        start_time = time.time()

        # Determine which datasets to evaluate
        dataset_name = self.eval_config.get("dataset")
        test_file = self.eval_config.get("test_file")

        # Load datasets
        test_cases = load_dataset(
            dataset_name=dataset_name,
            test_file=test_file,
            datasets_dir=self.eval_config.get("datasets_dir", "datasets"),
        )

        logger.info(f"Loaded {len(test_cases)} test cases for evaluation")

        # Run tests
        if self.parallel and len(test_cases) > 1:
            results = await self._run_parallel(test_cases)
        else:
            results = await self._run_sequential(test_cases)

        # Process results
        processed_results = process_results(results)

        # Calculate metrics
        metrics = self.metric_calculator.calculate_all_metrics(processed_results)

        # Prepare final output
        evaluation_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": time.time() - start_time,
            "config": {
                "agent": self.agent_config.get("name", "zapmyco"),
                "version": self.agent_config.get("version", "unknown"),
                "timeout": self.timeout,
                "parallel": self.parallel,
            },
            "summary": {
                "total_tests": len(test_cases),
                "passed": metrics.get("overall_success_rate", {}).get("passed", 0),
                "failed": metrics.get("overall_success_rate", {}).get("failed", 0),
                "success_rate": metrics.get("overall_success_rate", {}).get("rate", 0),
            },
            "metrics": metrics,
            "results": processed_results,
        }

        # Save raw results
        self._save_results(evaluation_results)

        logger.info(
            f"Evaluation completed in {evaluation_results['duration']:.2f} seconds"
        )
        logger.info(
            f"Success rate: {evaluation_results['summary']['success_rate']:.2f}%"
        )

        return evaluation_results

    async def _run_sequential(self, test_cases: List[Dict]) -> List[Dict]:
        """Run test cases sequentially"""
        results = []

        for i, test_case in enumerate(test_cases):
            logger.info(
                f"Running test {i+1}/{len(test_cases)}: {test_case.get('test_id', 'unknown')}"
            )
            result = await self._execute_test(test_case)
            results.append(result)

        return results

    async def _run_parallel(self, test_cases: List[Dict]) -> List[Dict]:
        """Run test cases in parallel using ThreadPoolExecutor"""
        results = []
        workers = min(self.max_workers, len(test_cases))

        logger.info(
            f"Running {len(test_cases)} test cases in parallel with {workers} workers"
        )

        # 使用 asyncio.gather 来并行执行异步任务
        tasks = [self._execute_test(test_case) for test_case in test_cases]
        results = await asyncio.gather(*tasks)

        # 按原始测试顺序排序结果
        results.sort(
            key=lambda r: next(
                (
                    i
                    for i, tc in enumerate(test_cases)
                    if tc.get("test_id") == r.get("test_id")
                ),
                0,
            )
        )

        return results

    async def _execute_test(self, test_case: Dict) -> Dict:
        """
        Execute a single test case against the agent

        Args:
            test_case: The test case to execute

        Returns:
            Dict containing the test results
        """
        test_id = test_case.get("test_id", "unknown")
        category = test_case.get("category", "unknown")

        logger.debug(f"Executing test {test_id} from category {category}")

        start_time = time.time()

        try:
            # 设置模拟上下文
            mock_context = test_case.get("mock_context", {})
            mock_provider = MockContextProvider(mock_context)

            async with self._get_ha_client() as ha_client:
                # 更新 agent 的 MCP 实例
                self.agent_connector.agent.ha_mcp = HomeAssistantMCP(
                    ha_client, context_provider=mock_provider
                )

                # 执行测试
                actual_output = await self.agent_connector.send_request(
                    test_case["input"]
                )

                # 验证结果
                expected_output = test_case.get("expected_output", {})
                success, comparison = await self._compare_outputs(
                    expected_output, actual_output
                )

                result = {
                    "test_id": test_id,
                    "category": category,
                    "description": test_case.get("description", ""),
                    "status": "success" if success else "failed",
                    "duration": time.time() - start_time,
                    "input": test_case.get("input", {}),
                    "expected_output": expected_output,
                    "actual_output": actual_output,
                    "comparison": comparison,
                    "tags": test_case.get("tags", []),
                    "difficulty": test_case.get("difficulty", "medium"),
                }

        except Exception as e:
            logger.error(f"Error executing test {test_id}: {e}")
            result = {
                "test_id": test_id,
                "category": category,
                "description": test_case.get("description", ""),
                "status": "error",
                "duration": time.time() - start_time,
                "input": test_case.get("input", {}),
                "expected_output": test_case.get("expected_output", {}),
                "actual_output": None,
                "error": str(e),
                "tags": test_case.get("tags", []),
                "difficulty": test_case.get("difficulty", "medium"),
            }

        return result

    def _validate_output(self, actual: Dict, expected: Dict) -> bool:
        """验证输出结果是否符合预期"""
        # 这里可以根据具体需求实现更复杂的验证逻辑
        return actual == expected

    async def _compare_outputs(
        self, expected_output: Dict, actual_output: Dict
    ) -> Tuple[bool, Dict]:
        """
        Compare expected and actual outputs

        Args:
            expected_output: Expected output from test case
            actual_output: Actual output from agent

        Returns:
            Tuple of (success, comparison_details)
        """
        comparison = {}
        success = True

        # 比较字段
        for field, expected_value in expected_output.items():
            if field not in actual_output:
                comparison[field] = {
                    "status": "missing",
                    "expected": expected_value,
                    "actual": None,
                }
                success = False
                continue

            actual_value = actual_output[field]
            field_match = await self._compare_field_values(expected_value, actual_value)

            comparison[field] = {
                "status": "match" if field_match else "mismatch",
                "expected": expected_value,
                "actual": actual_value,
            }

            if not field_match:
                success = False

        return success, comparison

    async def _compare_field_values(self, expected: Any, actual: Any) -> bool:
        """
        Compare field values, handling different types appropriately

        Args:
            expected: Expected value
            actual: Actual value

        Returns:
            bool: True if values match, False otherwise
        """
        # Handle None values
        if expected is None:
            return actual is None

        # Type mismatch
        if not isinstance(actual, type(expected)):
            return False

        # Handle different types
        if isinstance(expected, dict):
            if set(expected.keys()) != set(actual.keys()):
                return False
            return all(
                await self._compare_field_values(expected[key], actual[key])
                for key in expected
            )
        elif isinstance(expected, list):
            if len(expected) != len(actual):
                return False
            # 使用asyncio.gather收集所有比较结果
            comparison_results = await asyncio.gather(
                *(
                    self._compare_field_values(exp, act)
                    for exp, act in zip(expected, actual)
                )
            )
            return all(comparison_results)
        else:
            # Direct comparison for basic types
            return expected == actual

    def _compare_execution(self, expected_exec: Dict, actual_exec: Dict) -> Dict:
        """
        Compare execution results in more detail

        Args:
            expected_exec: Expected execution results
            actual_exec: Actual execution results

        Returns:
            Dict with comparison details
        """
        # This would contain more sophisticated logic for comparing
        # execution results based on your specific format

        # Simplified version
        success = True
        details = {}

        for key, expected_value in expected_exec.items():
            if key in actual_exec:
                # For complex nested structures, you'd implement recursive comparison
                if isinstance(expected_value, dict) and isinstance(
                    actual_exec[key], dict
                ):
                    # Simplified - just check if all expected keys exist
                    missing_keys = [
                        k for k in expected_value if k not in actual_exec[key]
                    ]
                    if missing_keys:
                        success = False
                        details[key] = {"match": False, "missing_keys": missing_keys}
                    else:
                        details[key] = {"match": True}
                else:
                    # Direct comparison for non-dict values
                    match = expected_value == actual_exec[key]
                    details[key] = {
                        "match": match,
                        "expected": expected_value,
                        "actual": actual_exec[key],
                    }
                    if not match:
                        success = False
            else:
                details[key] = {"match": False, "error": "Missing in actual execution"}
                success = False

        return {"success": success, "details": details}

    def _save_results(self, results: Dict) -> None:
        """Save evaluation results to file"""
        filename = f"{self.results_dir}/evaluation.json"

        with open(filename, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {filename}")


if __name__ == "__main__":
    excepted_val = {
        "domain": "light",
        "service": "turn_on",
        "service_data": {"entity_id": "light.living_room"},
    }
    actual_val = {
        "domain": "light",
        "service": "turn_on",
        "service_data": {"entity_id": "light.living_room"},
    }

    def _compare_values(
        expected_val: Any, actual_val: Any, path: str = ""
    ) -> Tuple[bool, Dict]:
        """递归比较任意类型的值"""
        comparison = {
            "path": path,
            "expected": expected_val,
            "actual": actual_val,
        }

        # 处理 None 值
        if expected_val is None:
            comparison["match"] = actual_val is None
            return comparison["match"], comparison

        # 类型不同直接返回不匹配
        if not isinstance(actual_val, type(expected_val)):
            comparison["match"] = False
            comparison["error"] = (
                f"Type mismatch: expected {type(expected_val)}, got {type(actual_val)}"
            )
            return False, comparison

        # 根据类型分别处理
        if isinstance(expected_val, dict):
            nested_results = {}
            all_matched = True

            for key, exp_value in expected_val.items():
                new_path = f"{path}.{key}" if path else key
                if key not in actual_val:
                    nested_results[key] = {
                        "path": new_path,
                        "match": False,
                        "error": "Field missing in actual output",
                        "expected": exp_value,
                        "actual": None,
                    }
                    all_matched = False
                else:
                    matched, result = _compare_values(
                        exp_value, actual_val[key], new_path
                    )
                    nested_results[key] = result
                    all_matched = all_matched and matched

            comparison["nested"] = nested_results
            comparison["match"] = all_matched
            return all_matched, comparison

        elif isinstance(expected_val, list):
            if len(expected_val) != len(actual_val):
                comparison["match"] = False
                comparison["error"] = (
                    f"List length mismatch: expected {len(expected_val)}, got {len(actual_val)}"
                )
                return False, comparison

            nested_results = []
            all_matched = True

            for i, (exp_item, act_item) in enumerate(zip(expected_val, actual_val)):
                new_path = f"{path}[{i}]"
                matched, result = _compare_values(exp_item, act_item, new_path)
                nested_results.append(result)
                all_matched = all_matched and matched

            comparison["nested"] = nested_results
            comparison["match"] = all_matched
            return all_matched, comparison

        else:
            # 基本类型直接比较
            comparison["match"] = expected_val == actual_val
            return comparison["match"], comparison

    res = _compare_values(excepted_val, actual_val)
    print(res)
