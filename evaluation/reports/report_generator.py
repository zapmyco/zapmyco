from asyncio.log import logger
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class ReportGenerator:
    def __init__(self, results: Dict[str, Any], eval_config: Dict[str, Any]):
        """
        Initialize the report generator

        Args:
            results: Dictionary containing evaluation results
            eval_config: Dictionary containing evaluation configuration
        """
        self.results = results
        self.eval_config = eval_config

    def generate(self) -> str:
        """
        Generate and save the evaluation report to a file

        Returns:
            str: Path to the generated report file
        """
        # Generate report data
        report_data = self.generate_report()

        # Create output directory if it doesn't exist
        output_dir = self.eval_config.get("report_dir")
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename
        report_path = os.path.join(output_dir, "evaluation_report.json")

        # Save report to file
        try:
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Report generated successfully: {report_path}")
            return report_path
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            raise

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate the evaluation report

        Returns:
            Dict containing the complete report data
        """
        if not self.results:
            self.results = self._load_latest_results()
            if not self.results:
                raise ValueError("No evaluation results available")

        return self._prepare_report_data()

    def _prepare_report_data(self) -> Dict[str, Any]:
        """
        Prepare data for the report template

        Returns:
            Dict containing all data needed for the report
        """
        # Extract summary metrics
        summary = self.results.get("summary", {})
        metrics = self.results.get("metrics", {})

        # Calculate category-specific success rates
        category_results = self._calculate_category_results()

        # Prepare test case details
        test_details = self._prepare_test_details()

        # Prepare data for charts
        chart_data = self._prepare_chart_data()

        return {
            "title": "Zapmyco Home Agent Evaluation Report",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": {
                "name": self.results.get("config", {}).get("agent", "Zapmyco"),
                "version": self.results.get("config", {}).get("version", "unknown"),
            },
            "summary": summary,
            "metrics": metrics,
            "category_results": category_results,
            "test_details": test_details,
            "chart_data": chart_data,
            "duration": self._format_duration(self.results.get("duration", 0)),
        }

    def _calculate_category_results(self) -> List[Dict[str, Any]]:
        """
        Calculate success rates by test category

        Returns:
            List of dicts with category stats
        """
        # Group results by category
        categories = {}
        for result in self.results.get("results", []):
            category = result.get("category", "unknown")
            if category not in categories:
                categories[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "error": 0,
                }

            categories[category]["total"] += 1
            status = result.get("status", "unknown")
            if status in categories[category]:
                categories[category][status] += 1

        # Calculate success rates
        category_results = []
        for category, stats in categories.items():
            success_rate = 0
            if stats["total"] > 0:
                success_rate = (stats["passed"] / stats["total"]) * 100

            category_results.append(
                {
                    "name": category,
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "error": stats.get("error", 0),
                    "success_rate": round(success_rate, 2),
                }
            )

        # Sort by category name
        category_results.sort(key=lambda x: x["name"])

        return category_results

    def _prepare_test_details(self) -> List[Dict[str, Any]]:
        """
        Prepare detailed test results for the report

        Returns:
            List of test details
        """
        test_details = []

        for result in self.results.get("results", []):
            # Extract key information for the report
            test_detail = {
                "test_id": result.get("test_id", "unknown"),
                "category": result.get("category", "unknown"),
                "description": result.get("description", ""),
                "status": result.get("status", "unknown"),
                "duration": result.get("duration", 0),
                "tags": result.get("tags", []),
                "difficulty": result.get("difficulty", "medium"),
                # "input_summary": self._summarize_input(result.get("input", {})),
                "input_summary": result.get("input", {}),
                # "comparison_summary": self._summarize_comparison(
                #     result.get("comparison", {})
                # ),
                "comparison_summary": result.get("comparison", {}),
                "has_error": "error" in result,
            }

            if test_detail["has_error"]:
                test_detail["error"] = result.get("error", "Unknown error")

            test_details.append(test_detail)

        # Sort by test_id
        test_details.sort(key=lambda x: x["test_id"])

        return test_details

    def _prepare_chart_data(self) -> Dict[str, Any]:
        """
        Prepare data for charts in the report

        Returns:
            Dict with chart data
        """
        # Success rate by category
        category_results = self._calculate_category_results()

        # Success rate by difficulty
        difficulty_stats = self._calculate_difficulty_stats()

        # Success rate by tags
        tag_stats = self._calculate_tag_stats()

        return {
            "categories": {
                "labels": [cat["name"] for cat in category_results],
                "success_rates": [cat["success_rate"] for cat in category_results],
            },
            "difficulties": {
                "labels": [diff["name"] for diff in difficulty_stats],
                "success_rates": [diff["success_rate"] for diff in difficulty_stats],
                "counts": [diff["total"] for diff in difficulty_stats],
            },
            "tags": {
                "labels": [tag["name"] for tag in tag_stats[:10]],  # Top 10 tags
                "success_rates": [tag["success_rate"] for tag in tag_stats[:10]],
                "counts": [tag["total"] for tag in tag_stats[:10]],
            },
        }

    def _calculate_difficulty_stats(self) -> List[Dict[str, Any]]:
        """Calculate success rates by difficulty level"""
        difficulties = {}

        for result in self.results.get("results", []):
            difficulty = result.get("difficulty", "medium")
            if difficulty not in difficulties:
                difficulties[difficulty] = {"total": 0, "passed": 0}

            difficulties[difficulty]["total"] += 1
            if result.get("status") == "passed":
                difficulties[difficulty]["passed"] += 1

        # Calculate success rates
        difficulty_stats = []
        for difficulty, stats in difficulties.items():
            success_rate = 0
            if stats["total"] > 0:
                success_rate = (stats["passed"] / stats["total"]) * 100

            difficulty_stats.append(
                {
                    "name": difficulty,
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "success_rate": round(success_rate, 2),
                }
            )

        # Sort by difficulty (easy, medium, hard)
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        difficulty_stats.sort(key=lambda x: difficulty_order.get(x["name"].lower(), 99))

        return difficulty_stats

    def _calculate_tag_stats(self) -> List[Dict[str, Any]]:
        """Calculate success rates by tags"""
        tags = {}

        for result in self.results.get("results", []):
            for tag in result.get("tags", []):
                if tag not in tags:
                    tags[tag] = {"total": 0, "passed": 0}

                tags[tag]["total"] += 1
                if result.get("status") == "passed":
                    tags[tag]["passed"] += 1

        # Calculate success rates
        tag_stats = []
        for tag, stats in tags.items():
            success_rate = 0
            if stats["total"] > 0:
                success_rate = (stats["passed"] / stats["total"]) * 100

            tag_stats.append(
                {
                    "name": tag,
                    "total": stats["total"],
                    "passed": stats["passed"],
                    "success_rate": round(success_rate, 2),
                }
            )

        # Sort by frequency (most common first)
        tag_stats.sort(key=lambda x: x["total"], reverse=True)

        return tag_stats

    def _summarize_input(self, input_data: Dict[str, Any]) -> str:
        """Create a summary of the test input"""
        if "text" in input_data:
            # For text-based inputs, return the text (truncated if needed)
            text = input_data["text"]
            if len(text) > 100:
                return f"{text[:100]}..."
            return text
        else:
            # For structured inputs, return a summary
            return f"Structured input with {len(input_data)} fields"

    def _summarize_comparison(self, comparison: Dict[str, Any]) -> str:
        """Create a summary of the comparison results"""
        if not comparison:
            return "No comparison data available"

        success = comparison.get("success", False)

        if "fields" in comparison:
            matched_fields = sum(
                1
                for field in comparison["fields"].values()
                if field.get("match", False)
            )
            total_fields = len(comparison["fields"])

            if success:
                return f"All {total_fields} expected fields matched"
            else:
                return f"{matched_fields}/{total_fields} expected fields matched"

        return "Success" if success else "Failed"

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to a readable string"""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.2f} hours"

    def _load_latest_results(self) -> Optional[Dict[str, Any]]:
        """
        Load the latest evaluation results from file

        Returns:
            Dict with results or None if not found
        """
        results_dir = self.eval_config.get("output_dir", "results/raw_results")

        try:
            # Get list of result files
            result_files = [f for f in os.listdir(results_dir) if f.endswith(".json")]

            if not result_files:
                logger.warning(f"No result files found in {results_dir}")
                return None

            # Sort by modification time (newest first)
            result_files.sort(
                key=lambda f: os.path.getmtime(os.path.join(results_dir, f)),
                reverse=True,
            )

            # Load the newest file
            latest_file = os.path.join(results_dir, result_files[0])
            logger.info(f"Loading latest results from {latest_file}")

            with open(latest_file, "r") as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return None
