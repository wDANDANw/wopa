###############################################################################
# main.tf
#
# Purpose:
# Define the Docker resources that Terraform creates. We create `emulator_count`
# instances of Docker containers, each running Docker-Android emulator images.
#
# Steps:
# 1. Use a for_each loop to create multiple emulator containers.
# 2. Each container exposes adb ports and runs budtmo/docker-android:emulator_11.0.
# 3. Attach them to `wopa_network` so `providers` container can resolve their hostnames.
#
# Maintainability:
# - If we change emulator image or device profile, update the image and env vars.
# - If we add VNC or WEB_VNC, add environment variables or ports here.
# - If we rename the network, update `networks_advanced` block.
###############################################################################

locals {
  # Create a map of emulator indexes so we can name them emulator1, emulator2, etc.
  emulator_instances = { for i in range(1, var.emulator_count + 1) : i => i }
}

# Instead of creating a network, we assume wopa_network is external and managed 
# by docker-compose. We'll reference it as a data source:
data "docker_network" "wopa_network" {
  name = "wopa_network"
}

resource "docker_container" "emulator" {
  for_each = local.emulator_instances
  name     = "emulator${each.value}" 
  image    = "budtmo/docker-android:emulator_11.0"
  restart  = "unless-stopped"

  # Attach to wopa_network so `emulatorX` can be resolved by providers container
  # If wopa_network is external and managed by docker-compose, use networks_advanced:
  networks_advanced {
    name = "wopa_network"
  }

  networks_advanced {
    name    = data.docker_network.wopa_network.name
    aliases = ["emulator${each.value}"]
  }

  # Expose ports for adb:
  # Typically emulator:5555 is used for adb connect
  # We map container 5555 to a random host port or a fixed scheme?
  # If random, just no "external" and rely on internal DNS. If we want direct access from providers:
  # Actually, providers container only needs DNS and internal port since same network.
  # If providers is on same network, it can use emulator1:5555 without host port mapping.
  # So we might not need port mapping. The name `emulator1` resolves inside network.
  
  # environment variables to configure emulator device
  env = [
    "EMULATOR_DEVICE=Samsung Galaxy S7",
    "WEB_VNC=true",
    "WEB_LOG=true",
    # If we want to access logs or VNC from outside, map ports or handle externally.
    # If needed:
    # "VNC_PASSWORD=secret"
  ]

  # ADB Ports
  ports {
    internal = 5555
    external = 5555
  }

  # VNC Ports
  ports {
    internal = 5900
    external = 5900
  }

  # Web VNC Ports
  ports {
    internal = 6080
    external = 6080
  }

  # Web Log Ports
  ports {
    internal = 9000
    external = 9000
  }

  # Pass KVM device to enable hardware acceleration
  # This is equivalent of `--device /dev/kvm` in docker run.
  devices {
    host_path      = "/dev/kvm"
    container_path = "/dev/kvm"
    permissions    = "rw"
  }

}
