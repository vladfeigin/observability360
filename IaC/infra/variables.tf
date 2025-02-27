variable "subscription_id" {
  description = "The subscription ID in which the resources will be created."
  sensitive   = true
}

variable "base_name" {
  description = "The base name for the resources (will be used for prefix)."
}

variable "region" {
  description = "The region in which the resources will be created (example: swedencentral)."
  default     = "swedencentral"
}

variable "adx_sku" {
  description = "Value of the sku for the Azure Data Explorer cluster."
  default     = "Standard_E2d_v4"
}