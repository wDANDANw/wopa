###############################################################################
# config_loader.py
#
# Purpose:
# This module provides a function to load configuration for the Workers subsystem 
# from a `config.yaml` file. It returns a dictionary that other parts of the system 
# can rely on. If `config.yaml` is missing or invalid, it returns a default 
# configuration to keep the system running in a known state.
#
# Design & Steps:
# 1. Define a default_config dictionary with minimal and safe defaults.
# 2. Attempt to load `config.yaml` from a known path (e.g. `workers/config/config.yaml`).
# 3. Parse the YAML, ensuring it returns a dict. If not, log an error and return default_config.
# 4. Merge or just return the loaded config. If any keys are missing, rely on defaults.
#
# Keys in config.yaml:
# - mode: "local"|"online" indicates whether to use local providers or external APIs.
# - providers_server_url: The base URL for local providers if mode=local. E.g. "http://providers:8003"
# - Additional keys can be added later (like timeouts, logging levels, etc.)
#
# Maintainability:
# - If we add new config fields, update default_config and the YAML template.
# - If we move `config.yaml`, update the path.
# - If we need environment variable overrides, we can add that logic here.
#
# Testing:
# - Unit tests can mock open() and yaml.safe_load() to test fallback logic.
# - Integration tests can run with a real config.yaml.
#
###############################################################################

import logging
import os
import yaml

logger = logging.getLogger(__name__)

def load_config() -> dict:
    """
    load_config():
    Attempts to load configuration from 'config/config.yaml'.
    If missing or invalid, returns default_config.

    Returns:
      config (dict)
    """
    config_path = os.path.join("config", "config.yaml")

    default_config = {
        "mode": "local",  # Default to local mode if not specified
        "providers_server_url": "http://providers:8003",  # Default URL for local providers
        # Add any other default keys if needed
    }

    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}, using default config.")
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            conf = yaml.safe_load(f)
            if not isinstance(conf, dict):
                logger.error("Config file format invalid, expected a dictionary at the root. Using default config.")
                return default_config

            # Merge defaults with loaded conf (if we want to ensure defaults):
            # For now, if keys missing in conf, we rely on defaults where needed:
            final_config = default_config.copy()
            final_config.update(conf)
            logger.info("Configuration loaded successfully.")
            return final_config

    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}. Using default config.")
        return default_config
