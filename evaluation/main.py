#!/usr/bin/env python3
"""
Main entry point for running evaluations
"""

import argparse
import os
import sys
import logging
from datetime import datetime
import asyncio

from evaluation.core.evaluator import Evaluator
from evaluation.core.utils.config_loader import load_config
from evaluation.reports.report_generator import ReportGenerator

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 创建logs目录（如果不存在）
os.makedirs("logs", exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger(__name__)


def setup_argparser():
    """设置命令行参数解析"""
    parser = argparse.ArgumentParser(description="Zapmyco Home Agent Evaluation System")

    # 配置选项
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(ROOT_DIR, "config", "evaluation_config.yaml"),
        help="Path to evaluation configuration file",
    )
    parser.add_argument(
        "--agent-config",
        type=str,
        default=os.path.join(ROOT_DIR, "config", "agent_config.yaml"),
        help="Path to agent configuration file",
    )
    parser.add_argument(
        "--metrics-config",
        type=str,
        default=os.path.join(ROOT_DIR, "config", "metrics_config.yaml"),
        help="Path to metrics configuration file",
    )

    # 数据集选项
    parser.add_argument(
        "--dataset",
        type=str,
        help="Specific dataset to evaluate (core, scenario, stress)",
    )
    parser.add_argument("--test-file", type=str, help="Specific test file to run")

    # 输出选项
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/raw_results",
        help="Directory to store evaluation results",
    )
    parser.add_argument(
        "--report-format",
        type=str,
        choices=["html", "pdf", "json", "all"],
        default="html",
        help="Format for the evaluation report",
    )

    # 其他选项
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Run tests in parallel where possible"
    )
    parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout in seconds for each test case"
    )

    return parser


async def main():
    """主函数"""
    # 解析命令行参数
    parser = setup_argparser()
    args = parser.parse_args()

    # 设置日志级别
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)

    # 加载配置
    try:
        eval_config = load_config(args.config)
        agent_config = load_config(args.agent_config)
        metrics_config = load_config(args.metrics_config)

        # 命令行参数覆盖配置文件
        if args.dataset:
            eval_config["dataset"] = args.dataset
        if args.test_file:
            eval_config["test_file"] = args.test_file
        if args.output_dir:
            eval_config["output_dir"] = args.output_dir
        if args.timeout:
            eval_config["timeout"] = args.timeout
        if args.parallel:
            eval_config["parallel"] = args.parallel

        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # 执行请求的操作
    try:
        # 运行完整评测
        logger.info("Starting evaluation...")

        # 创建评测器
        evaluator = Evaluator(
            agent_config=agent_config,
            eval_config=eval_config,
            metrics_config=metrics_config,
        )

        try:
            # 运行评测
            results = await evaluator.run_evaluation()

            # 生成报告
            logger.info("Generating evaluation report...")
            report_generator = ReportGenerator(
                results,
                eval_config,
            )
            report_path = report_generator.generate()

            logger.info(f"Evaluation completed. Report saved to: {report_path}")
        finally:
            # 确保资源被正确关闭
            await evaluator.cleanup()

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
