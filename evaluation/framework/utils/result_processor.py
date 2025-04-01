"""
Result Processor - Processes raw evaluation results
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def process_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process raw evaluation results

    Args:
        results: List of raw test results

    Returns:
        List of processed results
    """
    processed_results = []

    for result in results:
        # Make a copy to avoid modifying the original
        processed = result.copy()

        # Add any additional processing here
        # For example, you might want to:
        # - Extract specific fields from complex outputs
        # - Normalize response formats
        # - Add derived metrics

        # Example: Add a simplified output summary
        if "actual_output" in processed:
            processed["output_summary"] = processed["actual_output"]
            # _summarize_output(processed["actual_output"])

        # Example: Add a simplified comparison summary
        if "comparison" in processed:
            processed["comparison_summary"] = processed["comparison"]
            # _summarize_comparison(
            #     processed["comparison"]
            # )

        processed_results.append(processed)

    logger.debug(f"Processed {len(processed_results)} test results")
    return processed_results


def _summarize_output(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of the output for easier analysis

    Args:
        output: The raw output

    Returns:
        Dict with summarized output
    """
    summary = {}

    # Example: Extract execution status
    if "execution" in output:
        execution = output["execution"]
        if isinstance(execution, dict):
            # Extract success status from each action
            actions = {}
            for key, value in execution.items():
                if isinstance(value, dict):
                    actions[key] = value.get("success", False)
                else:
                    actions[key] = value
            summary["execution"] = actions

    # Example: Count fields in the output
    summary["field_count"] = len(output) if isinstance(output, dict) else 0

    return summary


def _summarize_comparison(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of the comparison results

    Args:
        comparison: The comparison results

    Returns:
        Dict with summarized comparison
    """
    summary = {"success": comparison.get("success", False), "match_rate": 0}

    # Calculate field match rate
    if "fields" in comparison:
        fields = comparison["fields"]
        if fields:
            matched = sum(1 for field in fields.values() if field.get("match", False))
            total = len(fields)
            if total > 0:
                summary["match_rate"] = round((matched / total) * 100, 2)
                summary["matched_fields"] = matched
                summary["total_fields"] = total

    return summary
