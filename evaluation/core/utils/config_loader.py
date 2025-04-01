"""
Config Loader - Utility for loading configuration files
"""

import os
import yaml
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file

    Args:
        config_path: Path to configuration file

    Returns:
        Dict containing configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file format is not supported
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    file_ext = os.path.splitext(config_path)[1].lower()

    try:
        with open(config_path, "r") as f:
            if file_ext in [".yaml", ".yml"]:
                config = yaml.safe_load(f)
            elif file_ext == ".json":
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {file_ext}")

        logger.debug(f"Loaded configuration from {config_path}")
        return config

    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        raise
