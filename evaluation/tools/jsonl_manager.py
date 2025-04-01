import json
import os
from typing import List, Dict, Any


class JsonlDatasetManager:
    """JSONL格式评测数据集管理工具"""

    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir

    def add_test_case(self, file_path, test_case):
        """添加新的测试案例到指定JSONL文件"""
        full_path = os.path.join(self.dataset_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(test_case, ensure_ascii=False) + "\n")

    def filter_dataset(self, file_path, filter_func):
        """根据过滤函数筛选测试案例"""
        full_path = os.path.join(self.dataset_dir, file_path)
        filtered_cases = []

        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                test_case = json.loads(line)
                if filter_func(test_case):
                    filtered_cases.append(test_case)

        return filtered_cases

    def merge_datasets(self, output_path, input_paths):
        """合并多个JSONL数据集"""
        full_output = os.path.join(self.dataset_dir, output_path)
        os.makedirs(os.path.dirname(full_output), exist_ok=True)

        with open(full_output, "w", encoding="utf-8") as out_f:
            for input_path in input_paths:
                full_input = os.path.join(self.dataset_dir, input_path)
                with open(full_input, "r", encoding="utf-8") as in_f:
                    for line in in_f:
                        if line.strip():
                            out_f.write(line)

    def generate_stats(self, file_path):
        """生成数据集统计信息"""
        full_path = os.path.join(self.dataset_dir, file_path)
        stats = {"total_count": 0, "categories": {}, "difficulties": {}, "tags": {}}

        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                test_case = json.loads(line)
                stats["total_count"] += 1

                # 统计分类
                category = test_case.get("category", "unknown")
                stats["categories"][category] = stats["categories"].get(category, 0) + 1

                # 统计难度
                difficulty = test_case.get("difficulty", "unknown")
                stats["difficulties"][difficulty] = (
                    stats["difficulties"].get(difficulty, 0) + 1
                )

                # 统计标签
                for tag in test_case.get("tags", []):
                    stats["tags"][tag] = stats["tags"].get(tag, 0) + 1

        return stats
