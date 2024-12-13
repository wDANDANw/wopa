###############################################################################
# config_loader.py
#
# Purpose:
# Provides a function `load_config(path)` that loads a YAML configuration file 
# and returns it as a Python dictionary. Other modules (like llm_client, sandbox_env, 
# emulator_env) rely on this to retrieve their settings.
#
# Key Responsibilities:
# 1. Given a file path (like "config.yaml"), load and parse the YAML.
# 2. Return a dictionary representing the config.
# 3. Handle file not found or YAML parsing errors gracefully.
#
# Requirements:
# - pyyaml (yaml.safe_load)
# - Return {} empty dict if file missing or error? Or raise exception?
#   Deciding the approach: It's safer to raise a ValueError if config is critical.
#
# Maintainability:
# - If config format changes (like switching from YAML to JSON), update here.
# - If we want defaults for missing keys, could implement them here.
###############################################################################

import os
import yaml


def load_config(path: str = f"config.yaml") -> dict:
    """
    Load a YAML configuration file and return it as a Python dict.

    Steps:
    1. Check if file exists.
       - If not, raise FileNotFoundError or return empty dict depending on design.
       Here, we raise FileNotFoundError because config is presumably essential.
    2. Open file, parse YAML with yaml.safe_load.
    3. If parsing fails (e.g., invalid YAML), raise ValueError.
    4. Return the parsed dictionary.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found at: {path}")

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                # If YAML is empty or doesn't result in a dict, return empty dict or raise ValueError
                raise ValueError(f"Invalid or empty config in: {path}")
            return data
    except yaml.YAMLError as e:
        # YAML parsing error
        raise ValueError(f"Failed to parse YAML config at {path}: {e}")
    except Exception as e:
        # Unexpected error reading file
        raise ValueError(f"Unexpected error loading config at {path}: {e}")

###############################################################################
# Explanation:
#
# - load_config(path):
#   - Checks file existence.
#   - Uses yaml.safe_load to parse. If YAML invalid, raises ValueError.
#   - If parsed data not a dict (like empty file or non-object), also ValueError.
#
# - Error Handling:
#   - Missing file: FileNotFoundError
#   - Invalid YAML: ValueError
#   - Unexpected IO error: ValueError
#
# Future Enhancements:
# - Could implement caching if performance becomes an issue.
# - Could merge multiple config files (like a base config and an environment-specific overlay).
# - If defaults needed, apply them here or in the calling modules.
###############################################################################
