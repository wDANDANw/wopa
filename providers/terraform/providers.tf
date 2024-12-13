###############################################################################
# providers.tf
#
# Purpose:
# Configure the Docker provider. Assumes DOCKER_HOST is set to connect to host daemon.
#
# Maintainability:
# If docker host changes (like a remote daemon), adjust host field or rely on env vars.
###############################################################################

provider "docker" {
  # Usually the docker provider picks up DOCKER_HOST from env.
  # If needed, specify here: 
  # host = "unix:///var/run/docker.sock"
}
