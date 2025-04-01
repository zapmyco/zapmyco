"""
Dataset Loader - Utility for loading test datasets
"""

import os
import json
import logging
import glob
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_dataset(
    dataset_name: Optional[str] = None,
    test_file: Optional[str] = None,
    datasets_dir: str = "datasets",
) -> List[Dict[str, Any]]:
    """
    Load test cases from datasets

    Args:
        dataset_name: Optional name of dataset to load (core, scenario, stress)
        test_file: Optional specific test file to load
        datasets_dir: Directory containing datasets

    Returns:
        List of test cases
    """
    test_cases = []

    try:
        if test_file:
            # Load specific test file
            if not os.path.exists(test_file):
                # Try to find it in datasets directory
                potential_paths = [
                    test_file,
                    os.path.join(datasets_dir, test_file),
                    os.path.join(datasets_dir, "core_tests", test_file),
                    os.path.join(datasets_dir, "scenario_tests", test_file),
                    os.path.join(datasets_dir, "stress_tests", test_file),
                ]

                for path in potential_paths:
                    if os.path.exists(path):
                        test_file = path
                        break
                else:
                    raise FileNotFoundError(f"Test file not found: {test_file}")

            logger.info(f"Loading test file: {test_file}")
            test_cases.extend(_load_test_file(test_file))

        elif dataset_name:
            # Load specific dataset
            dataset_path = os.path.join(datasets_dir, dataset_name)
            if not os.path.exists(dataset_path):
                # Try with _tests suffix
                dataset_path = os.path.join(datasets_dir, f"{dataset_name}_tests")

            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Dataset not found: {dataset_name}")

            logger.info(f"Loading dataset: {dataset_path}")
            test_cases.extend(_load_dataset_dir(dataset_path))

        else:
            # Load all datasets
            logger.info(f"Loading all datasets from {datasets_dir}")

            # Load core tests
            core_path = os.path.join(datasets_dir, "core_tests")
            if os.path.exists(core_path):
                test_cases.extend(_load_dataset_dir(core_path))

            # Load scenario tests
            scenario_path = os.path.join(datasets_dir, "scenario_tests")
            if os.path.exists(scenario_path):
                test_cases.extend(_load_dataset_dir(scenario_path))

            # Load stress tests
            stress_path = os.path.join(datasets_dir, "stress_tests")
            if os.path.exists(stress_path):
                test_cases.extend(_load_dataset_dir(stress_path))

        logger.info(f"Loaded {len(test_cases)} test cases")
        return test_cases

    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        raise


def _load_dataset_dir(directory: str) -> List[Dict[str, Any]]:
    """
    Load all test files from a directory

    Args:
        directory: Directory containing test files

    Returns:
        List of test cases
    """
    test_cases = []

    # Find all JSON and JSONL files
    json_files = glob.glob(os.path.join(directory, "*.json"))
    jsonl_files = glob.glob(os.path.join(directory, "*.jsonl"))

    # Load each file
    for file_path in json_files + jsonl_files:
        try:
            test_cases.extend(_load_test_file(file_path))
        except Exception as e:
            logger.warning(f"Error loading file {file_path}: {e}")

    return test_cases


def _load_test_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load test cases from a file

    Args:
        file_path: Path to test file

    Returns:
        List of test cases
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    with open(file_path, "r", encoding="utf-8") as f:
        if file_ext == ".json":
            # Regular JSON file - could be a single test or an array
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                return [data]
        elif file_ext == ".jsonl":
            # JSONL file - one test per line
            return [json.loads(line) for line in f if line.strip()]
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
