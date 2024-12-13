###############################################################################
# versions.tf
#
# Purpose:
# This file pins Terraform and provider versions to ensure consistent builds.
#
# Maintainability:
# If Terraform or providers need updates, adjust version constraints here.
###############################################################################

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
