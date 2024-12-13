import os
import logging

###############################################################################
# File: core/config_loader.py
#
# Purpose:
# This module loads configuration values from environment variables, as per 
# previous discussions. We rely on docker-compose to supply these environment
# variables (e.g., MESSAGE_SERVICE_URL, REDIS_HOST, etc.).
#
# Design & Philosophy:
# - A simple get_env(key: str) function to retrieve required environment vars.
# - If a key is missing, we either raise an error or provide a default if 
#   appropriate. In our plan, it’s safer to raise an error because the system 
#   must know endpoints and redis configuration to run properly.
#
# Maintainability:
# - If new endpoints or config values are added, just update get_env or 
#   add specialized getter functions.
# - If we want defaults for some vars, we can easily add them here.
#
# Testing:
# - Unit tests can mock os.environ and verify behavior of get_env.
# - If environment variables are not found, system should fail early, providing 
#   a clear error message.
###############################################################################

logger = logging.getLogger(__name__)


def get_env(key: str) -> str:
    """
    Retrieve a configuration value from environment variables.

    If the variable is not set, raise a ValueError. This ensures that all critical 
    configuration values are explicitly provided.

    Args:
        key (str): The name of the environment variable to retrieve.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not found.
    """
    value = os.environ.get(key)
    if value is None:
        # We could log an error and raise
        logger.error(f"Missing required environment variable: {key}")
        raise ValueError(f"Environment variable {key} not set.")
    return value


def get_redis_config():
    """
    Retrieve redis connection details from environment variables.
    Typically:
    - REDIS_HOST
    - REDIS_PORT

    Returns:
        (host: str, port: int)
    """
    host = get_env("REDIS_HOST")
    port_str = get_env("REDIS_PORT")
    # Convert port_str to int
    try:
        port = int(port_str)
    except ValueError:
        logger.error("REDIS_PORT must be an integer.")
        raise ValueError("REDIS_PORT must be an integer.")

    return host, port


def get_service_urls():
    """
    Retrieve all service endpoints from env vars:
    MESSAGE_SERVICE_URL
    LINK_SERVICE_URL
    FILE_SERVICE_URL
    APP_SERVICE_URL
    SANDBOX_PROVIDER_URL
    EMULATOR_PROVIDER_URL

    Returns:
        dict: A dictionary with all service endpoints.
    """
    return {
        "MESSAGE_SERVICE_URL": get_env("MESSAGE_SERVICE_URL"),
        "LINK_SERVICE_URL": get_env("LINK_SERVICE_URL"),
        "FILE_SERVICE_URL": get_env("FILE_SERVICE_URL"),
        "APP_SERVICE_URL": get_env("APP_SERVICE_URL"),
        "SANDBOX_PROVIDER_URL": get_env("SANDBOX_PROVIDER_URL"),
        "EMULATOR_PROVIDER_URL": get_env("EMULATOR_PROVIDER_URL"),
    }


###############################################################################
# Future changes:
# If we add new configuration keys, we can create specialized functions or just 
# reuse get_env. For sensitive defaults, we could add optional parameters to get_env.
#
# Not the last file:
# We will continue with other core files (e.g., request_handler.py, orchestrator.py),
# api routes, admin_ui, and connectors. We will notify when we provide the last file.
###############################################################################
