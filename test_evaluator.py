#!/usr/bin/env python3
"""
测试评测器的并发功能
"""

import asyncio
import logging
import time
import yaml
import os

from evaluation.core.evaluator import Evaluator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_evaluation_test(parallel=True, max_workers=2):
    """运行评测测试"""
    start_time = time.time()

    # 加载配置
    with open("config/evaluation_config.yaml", "r") as f:
        eval_config = yaml.safe_load(f)
    
    # 修改并发设置
    eval_config["parallel"] = parallel
    eval_config["max_workers"] = max_workers
    
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


async def main():
    """主函数"""
    logger.info("开始测试评测器的并发功能")
    
    # 测试串行执行
    logger.info("测试串行执行...")
    serial_duration, _ = await run_evaluation_test(parallel=False)
    
    # 测试并行执行 (2个工作线程)
    logger.info("测试并行执行 (2个工作线程)...")
    parallel_duration_2, _ = await run_evaluation_test(parallel=True, max_workers=2)
    
    # 测试并行执行 (4个工作线程)
    logger.info("测试并行执行 (4个工作线程)...")
    parallel_duration_4, _ = await run_evaluation_test(parallel=True, max_workers=4)
    
    # 输出比较结果
    logger.info(f"串行执行耗时: {serial_duration:.2f}秒")
    logger.info(f"并行执行耗时 (2个工作线程): {parallel_duration_2:.2f}秒")
    logger.info(f"并行执行耗时 (4个工作线程): {parallel_duration_4:.2f}秒")
    logger.info(f"加速比 (2个工作线程): {serial_duration/parallel_duration_2:.2f}x")
    logger.info(f"加速比 (4个工作线程): {serial_duration/parallel_duration_4:.2f}x")


if __name__ == "__main__":
    asyncio.run(main())
