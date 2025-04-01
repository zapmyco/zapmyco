#!/usr/bin/env python3
"""
测试评测器的并发性能
"""

import asyncio
import logging
import time
import yaml
import os
import json
import copy
from typing import List, Dict

from evaluation.core.evaluator import Evaluator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def duplicate_test_cases(test_cases: List[Dict], target_count: int) -> List[Dict]:
    """复制测试用例，直到达到目标数量"""
    result = []
    original_count = len(test_cases)
    
    # 计算需要复制的次数
    full_copies = target_count // original_count
    remainder = target_count % original_count
    
    # 完整复制
    for i in range(full_copies):
        for j, test_case in enumerate(test_cases):
            # 创建深拷贝
            new_case = copy.deepcopy(test_case)
            # 修改ID以避免重复
            new_case["test_id"] = f"{new_case['test_id']}_{i+1}_{j+1}"
            result.append(new_case)
    
    # 复制剩余部分
    for j in range(remainder):
        new_case = copy.deepcopy(test_cases[j])
        new_case["test_id"] = f"{new_case['test_id']}_remainder_{j+1}"
        result.append(new_case)
    
    return result


async def run_evaluation_test(parallel=True, max_workers=2, test_count=20):
    """运行评测测试"""
    start_time = time.time()

    # 加载配置
    with open("config/evaluation_config.yaml", "r") as f:
        eval_config = yaml.safe_load(f)
    
    # 修改并发设置
    eval_config["parallel"] = parallel
    eval_config["max_workers"] = max_workers
    
    # 加载原始测试用例
    with open("evaluation/datasets/core_tests/intent_understanding.jsonl", "r") as f:
        original_test_cases = [json.loads(line) for line in f if line.strip()]
    
    # 创建临时测试文件
    temp_test_file = "evaluation/datasets/core_tests/temp_performance_test.jsonl"
    
    # 复制测试用例以达到目标数量
    expanded_test_cases = duplicate_test_cases(original_test_cases, test_count)
    
    # 保存到临时文件
    with open(temp_test_file, "w") as f:
        for test_case in expanded_test_cases:
            f.write(json.dumps(test_case) + "\n")
    
    # 修改配置以使用临时测试文件
    eval_config["test_file"] = "core_tests/temp_performance_test.jsonl"
    
    try:
        # 创建评测器
        evaluator = Evaluator(
            agent_config={"name": "zapmyco", "version": "test"},
            eval_config=eval_config,
            metrics_config={},
        )
        
        # 运行评测
        results = await evaluator.run_evaluation()
        
        # 输出结果
        duration = time.time() - start_time
        logger.info(f"评测完成，耗时: {duration:.2f}秒")
        logger.info(f"成功率: {results['summary']['success_rate']:.2f}%")
        
        return duration, results
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_test_file):
            os.remove(temp_test_file)


async def main():
    """主函数"""
    logger.info("开始测试评测器的并发性能")
    
    # 测试用例数量
    test_count = 16  # 使用16个测试用例，足够测试并发性能但不会耗时太长
    
    # 测试串行执行
    logger.info(f"测试串行执行 ({test_count}个测试用例)...")
    serial_duration, _ = await run_evaluation_test(parallel=False, test_count=test_count)
    
    # 测试并行执行 (2个工作线程)
    logger.info(f"测试并行执行 (2个工作线程, {test_count}个测试用例)...")
    parallel_duration_2, _ = await run_evaluation_test(parallel=True, max_workers=2, test_count=test_count)
    
    # 测试并行执行 (4个工作线程)
    logger.info(f"测试并行执行 (4个工作线程, {test_count}个测试用例)...")
    parallel_duration_4, _ = await run_evaluation_test(parallel=True, max_workers=4, test_count=test_count)
    
    # 测试并行执行 (8个工作线程)
    logger.info(f"测试并行执行 (8个工作线程, {test_count}个测试用例)...")
    parallel_duration_8, _ = await run_evaluation_test(parallel=True, max_workers=8, test_count=test_count)
    
    # 输出比较结果
    logger.info(f"串行执行耗时: {serial_duration:.2f}秒")
    logger.info(f"并行执行耗时 (2个工作线程): {parallel_duration_2:.2f}秒")
    logger.info(f"并行执行耗时 (4个工作线程): {parallel_duration_4:.2f}秒")
    logger.info(f"并行执行耗时 (8个工作线程): {parallel_duration_8:.2f}秒")
    logger.info(f"加速比 (2个工作线程): {serial_duration/parallel_duration_2:.2f}x")
    logger.info(f"加速比 (4个工作线程): {serial_duration/parallel_duration_4:.2f}x")
    logger.info(f"加速比 (8个工作线程): {serial_duration/parallel_duration_8:.2f}x")
    
    # 计算理论最大加速比
    theoretical_max_2 = min(2, test_count)
    theoretical_max_4 = min(4, test_count)
    theoretical_max_8 = min(8, test_count)
    
    logger.info(f"理论最大加速比 (2个工作线程): {theoretical_max_2:.2f}x")
    logger.info(f"理论最大加速比 (4个工作线程): {theoretical_max_4:.2f}x")
    logger.info(f"理论最大加速比 (8个工作线程): {theoretical_max_8:.2f}x")
    
    logger.info(f"效率 (2个工作线程): {(serial_duration/parallel_duration_2)/theoretical_max_2*100:.2f}%")
    logger.info(f"效率 (4个工作线程): {(serial_duration/parallel_duration_4)/theoretical_max_4*100:.2f}%")
    logger.info(f"效率 (8个工作线程): {(serial_duration/parallel_duration_8)/theoretical_max_8*100:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
