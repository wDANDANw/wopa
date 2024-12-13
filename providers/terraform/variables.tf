###############################################################################
# variables.tf
#
# Purpose:
# Define variables for emulator_count and possibly other future scaling parameters.
#
# Maintainability:
# If adding sandbox_count or other resources, define similar variables.
###############################################################################

variable "emulator_count" {
  type        = number
  description = "Number of emulator instances to create"
  default     = 1
}
