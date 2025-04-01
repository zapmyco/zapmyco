"""
Dataset Validator - Validates test datasets for correct format
"""

import os
import json
import logging
import glob
import jsonschema
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Schema for validating test cases
TEST_CASE_SCHEMA = {
    "type": "object",
    "required": ["test_id", "category", "input", "expected_output"],
    "properties": {
        "test_id": {"type": "string"},
        "category": {"type": "string"},
        "description": {"type": "string"},
        "input": {"type": "object"},
        "expected_output": {"type": "object"},
        "evaluation_criteria": {"type": "object"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


def validate_datasets(datasets_dir: str = "datasets") -> Dict[str, Any]:
    """
    Validate all test datasets

    Args:
        datasets_dir: Directory containing datasets

    Returns:
        Dict with validation results
    """
    validation_results = {
        "valid_files": 0,
        "invalid_files": 0,
        "valid_tests": 0,
        "invalid_tests": 0,
        "errors": [],
    }

    logger.info(f"Validating datasets in {datasets_dir}")

    # Check if directory exists
    if not os.path.exists(datasets_dir):
        error = f"Datasets directory not found: {datasets_dir}"
        logger.error(error)
        validation_results["errors"].append(error)
        return validation_results

    # Find all dataset directories
    dataset_dirs = [
        os.path.join(datasets_dir, "core_tests"),
        os.path.join(datasets_dir, "scenario_tests"),
        os.path.join(datasets_dir, "stress_tests"),
    ]

    # Add the main directory itself
    dataset_dirs.append(datasets_dir)

    # Validate each directory
    for directory in dataset_dirs:
        if os.path.exists(directory):
            dir_results = _validate_directory(directory)

            # Aggregate results
            validation_results["valid_files"] += dir_results["valid_files"]
            validation_results["invalid_files"] += dir_results["invalid_files"]
            validation_results["valid_tests"] += dir_results["valid_tests"]
            validation_results["invalid_tests"] += dir_results["invalid_tests"]
            validation_results["errors"].extend(dir_results["errors"])

    # Log summary
    logger.info(
        f"Validation complete: {validation_results['valid_files']} valid files, "
        f"{validation_results['invalid_files']} invalid files"
    )
    logger.info(
        f"Test cases: {validation_results['valid_tests']} valid, "
        f"{validation_results['invalid_tests']} invalid"
    )

    if validation_results["errors"]:
        logger.warning(f"Found {len(validation_results['errors'])} validation errors")

    return validation_results


def _validate_directory(directory: str) -> Dict[str, Any]:
    """
    Validate all test files in a directory

    Args:
        directory: Directory to validate

    Returns:
        Dict with validation results
    """
    results = {
        "valid_files": 0,
        "invalid_files": 0,
        "valid_tests": 0,
        "invalid_tests": 0,
        "errors": [],
    }

    logger.info(f"Validating directory: {directory}")

    # Find all JSON and JSONL files
    json_files = glob.glob(os.path.join(directory, "*.json"))
    jsonl_files = glob.glob(os.path.join(directory, "*.jsonl"))

    # Validate each file
    for file_path in json_files + jsonl_files:
        file_results = _validate_file(file_path)

        if file_results["is_valid"]:
            results["valid_files"] += 1
        else:
            results["invalid_files"] += 1

        results["valid_tests"] += file_results["valid_tests"]
        results["invalid_tests"] += file_results["invalid_tests"]
        results["errors"].extend(file_results["errors"])

    return results


def _validate_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a test file

    Args:
        file_path: Path to the test file

    Returns:
        Dict with validation results
    """
    results = {
        "file": file_path,
        "is_valid": True,
        "valid_tests": 0,
        "invalid_tests": 0,
        "errors": [],
    }

    try:
        # Load test cases from file
        test_cases = _load_test_file(file_path)

        # Validate each test case
        for i, test_case in enumerate(test_cases):
            try:
                jsonschema.validate(test_case, TEST_CASE_SCHEMA)
                results["valid_tests"] += 1
            except jsonschema.exceptions.ValidationError as e:
                results["invalid_tests"] += 1
                results["is_valid"] = False
                error = (
                    f"Validation error in {file_path}, test case #{i+1}: {e.message}"
                )
                results["errors"].append(error)
                logger.warning(error)

    except Exception as e:
        results["is_valid"] = False
        error = f"Error processing file {file_path}: {str(e)}"
        results["errors"].append(error)
        logger.error(error)

    # Log result
    if results["is_valid"]:
        logger.info(f"✓ Valid: {file_path} ({results['valid_tests']} test cases)")
    else:
        logger.warning(
            f"✗ Invalid: {file_path} ({results['valid_tests']} valid, {results['invalid_tests']} invalid)"
        )

    return results


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
