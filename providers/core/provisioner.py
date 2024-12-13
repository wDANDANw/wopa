###############################################################################
# core/provisioner.py
#
# Purpose:
# This module manages Terraform-based provisioning of emulator and sandbox instances
# for the Providers subsystem. It can be called by other Python code (e.g., emulator_env.py)
# when additional resources are needed.
#
# Key Responsibilities:
# 1. Run Terraform commands in non-interactive mode from within the container.
# 2. Parse Terraform outputs and update instances.json to reflect new endpoints.
# 3. Provide functions like provision_emulators() or provision_sandbox() that:
#    - Run `terraform init` and `terraform apply -auto-approve`.
#    - Parse outputs (sandbox/emulator URLs).
#    - Write them to instances.json.
#
# Requirements:
# - Terraform installed in the providers container.
# - A terraform/ directory with main.tf, variables.tf, outputs.tf, etc.
# - Docker socket mounted so Terraform can create docker containers.
#
# Future Enhancements:
# - Add arguments to provision_emulators() to specify the count dynamically.
# - Add separate functions for sandbox provisioning or more granular control.
#
###############################################################################

import subprocess
import json
import sys
import os

import logging
logger = logging.getLogger(__name__)
# Terraform working directory, relative to /providers
TERRAFORM_DIR = "./terraform"

def run_terraform_command(cmd_list):
    """
    Run a terraform command and handle errors gracefully.

    Parameters:
    - cmd_list: List of strings representing the terraform command and arguments.
                We'll inject the '-chdir' argument to run in TERRAFORM_DIR.

    Returns:
    - The stdout output if successful.

    On failure:
    - Print error and sys.exit(1).

    Note:
    - If you prefer exceptions, raise a custom Exception instead of sys.exit().
    """
    # Insert '-chdir' argument so terraform runs in the terraform/ directory
    full_cmd = ["terraform", f"-chdir={TERRAFORM_DIR}"] + cmd_list
    try:
        logger.info(f"Provisioner: run_terraform_command: Running: {' '.join(full_cmd)}")
        result = subprocess.run(full_cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Provisioner: run_terraform_command: Terraform command failed: {e.stderr}")
        sys.exit(1)


def parse_terraform_outputs():
    """
    Parse `terraform output -json` to extract sandbox and emulator endpoints.

    Expected Terraform outputs (example):
    {
      "sandbox_urls": { "value": ["http://sandbox1:8002"] },
      "emulator_urls": { "value": ["http://emulator1:5555"] }
    }

    Returns a dict like:
    {
      "sandbox": [...],
      "emulator": [...]
    }

    If keys are missing, return empty lists.
    """
    output_json = run_terraform_command(["output", "-json"])
    data = json.loads(output_json)

    sandbox_endpoints = data.get("sandbox_urls", {}).get("value", [])
    emulator_endpoints = data.get("emulator_urls", {}).get("value", [])

    return {
        "sandbox": sandbox_endpoints,
        "emulator": emulator_endpoints
    }


def write_instances_file(instances_data):
    """
    Write the parsed endpoints to instances.json.

    Parameters:
    - instances_data: dict with "sandbox" and "emulator" keys.

    instances.json example:
    {
      "sandbox": ["http://sandbox1:8002","http://sandbox2:8003"],
      "emulator": ["http://emulator1:5555","http://emulator2:5555"]
    }

    On error:
    - Print message and sys.exit(1).
    """

    instances_file = "/providers/instances.json"
    try:
        with open(instances_file, "w") as f:
            json.dump(instances_data, f, indent=2)
        logger.info(f"Provisioner: write_instances_file: Wrote endpoints to {instances_file}: {instances_data}")
    except Exception as e:
        print(f"Failed to write {instances_file}: {e}")
        sys.exit(1)


def apply_terraform_changes():
    """
    Run 'terraform init' and 'terraform apply -auto-approve' to ensure TF config is applied.

    On failure:
    - sys.exit(1)
    """
    logger.info("Provisioner: apply_terraform_changes: Terraform init started")
    # terraform init
    run_terraform_command(["init"])
    # terraform apply
    run_terraform_command(["apply", "-auto-approve"])
    logger.info("Provisioner: apply_terraform_changes: Terraform apply completed")


def provision_emulators():
    """
    Provision emulator instances by calling Terraform. This function can be triggered
    by emulator_env.py when no emulator endpoints exist or scaling is needed.

    Steps:
    1. apply_terraform_changes() to apply current TF config.
    2. parse_terraform_outputs() to get updated endpoints.
    3. write_instances_file() to store them in instances.json.

    If we need to scale, set TF_VAR_emulator_count in os.environ before calling this.
    """
    logger.info("Provisioner: provision_emulators: Provisioning emulator(s) via Terraform...")
    apply_terraform_changes()
    instances_data = parse_terraform_outputs()
    write_instances_file(instances_data)
    logger.info("Provisioner: provision_emulators: Emulator provisioning complete. Updated instances.json with new endpoints.")


def provision_sandbox():
    """
    Provision sandbox instance(s) if needed, similar to provision_emulators().

    Steps:
    1. apply_terraform_changes()
    2. parse_terraform_outputs()
    3. write_instances_file()

    If sandbox not needed now, just a placeholder.
    """
    logger.info("Provisioner: provision_sandbox: Provisioning sandbox instance(s) via Terraform...")
    apply_terraform_changes()
    instances_data = parse_terraform_outputs()
    write_instances_file(instances_data)
    logger.info("Provisioner: provision_sandbox: Sandbox provisioning complete.")

