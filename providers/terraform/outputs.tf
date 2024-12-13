###############################################################################
# outputs.tf
#
# Purpose:
# Define outputs for emulator endpoints so `provisioner.py` can parse them.
# We return a list of emulator URLs like ["http://emulator1:5555", "http://emulator2:5555"].
#
# Maintainability:
# If we change how we form endpoints (different port or protocol), update the expression.
###############################################################################

output "emulator_urls" {
  description = "List of emulator endpoints"
  # Build a list of URLs based on the container names and port 5555.
  # All containers are named "emulatorX" and accessible on wopa_network as "emulatorX".
  # The emulator listens on port 5555 for adb.
  # We'll return "http://emulatorX:5555" for each container.
  
  value = [
    for c in docker_container.emulator :
    "http://${c.name}:5555"
  ]
}
