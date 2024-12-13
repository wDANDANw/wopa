###############################################################################
# config_loader.py
#
# Purpose:
# The config_loader.py provides a central function, load_config(), to load 
# configuration settings for the Services subsystem of WOPA. By centralizing 
# configuration loading, we ensure maintainability, clarity, and a single source 
# of truth for environment variables, file-based configurations, and defaults.
#
# Design & Approach:
# - We load configuration from a YAML file (e.g., "config/services_config.yaml") 
#   and then merge environment variables and defaults.
# - Environment variables can override certain settings (like WORKER_SERVER_URL).
# - If the config file is missing or empty, we fallback to a default dictionary.
# - The idea is to provide maximum flexibility:
#   - YAML file for stable defaults and structured configs.
#   - Environment variables for dynamic overrides in different environments (dev, test, prod).
#
# Process:
# 1. Attempt to read "config/services_config.yaml" (or a known config path).
# 2. Parse YAML into a Python dict (using pyyaml).
# 3. If file not found or empty, use a default empty dict.
# 4. Check environment variables that might override keys.
# 5. Return the final merged config dictionary.
#
# Keys of interest:
# - WORKER_SERVER_URL: The base URL for the Worker subsystem.
#   We allow environment variable WORKER_SERVER_URL to override it.
#
# Future Extensibility:
# - If we add new config keys (thresholds, timeouts, debug flags), we 
#   just add them to the YAML and read them here.
# - If we add different config files per environment, we can detect ENV mode 
#   and load from different files.
#
# Testing:
# - Unit tests can mock open() and yaml.safe_load to test fallback logic.
# - Integration tests can run with real config files and environment vars.
#
###############################################################################

import os
import yaml
import logging

logger = logging.getLogger("services")

def load_config() -> dict:
    """
    Load configuration from 'config/services_config.yaml' and merge with environment variables.

    Steps:
    - Try to open 'config/services_config.yaml'.
    - If found, parse with yaml.safe_load(). If empty, use empty dict.
    - Apply environment variable overrides (like WORKER_SERVER_URL).
    - Return the final dict.

    Returns:
        dict: The configuration dictionary.
    """
    config_file_path = "config/services_config.yaml"
    base_config = {}
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                base_config = yaml.safe_load(f) or {}
                logger.info("Loaded configuration from services_config.yaml.")
        except Exception as e:
            logger.warning(f"Failed to read config file {config_file_path}: {e}. Using empty config.")
            base_config = {}
    else:
        logger.info(f"No config file found at {config_file_path}, using defaults.")

    # Example environment overrides:
    # If we define more keys in the future, handle them similarly.
    env_worker_url = os.environ.get("WORKER_SERVER_URL")
    if env_worker_url:
        base_config["WORKER_SERVER_URL"] = env_worker_url

    # If we want defaults for WORKER_SERVER_URL if not set anywhere:
    if "WORKER_SERVER_URL" not in base_config:
        base_config["WORKER_SERVER_URL"] = "http://workers:8002"

    return base_config
