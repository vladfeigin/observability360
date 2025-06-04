variable "subscription_id" {
  description = "The subscription ID in which the resources will be created."
  sensitive   = true
}

variable "base_name" {
  description = "The base name for the resources (will be used for prefix)."
}

variable "email" {
  description = "The email address of the user who will be the owner of the resources."
}

variable "region" {
  description = "The region in which the resources will be created (example: swedencentral)."
  default     = "swedencentral"
}

variable "data_location" {
  description = "The data location for the communication service."
  default     = "Europe"
}

variable "adx_sku" {
  description = "Value of the sku for the Azure Data Explorer cluster."
  default     = "Dev(No SLA)_Standard_D11_v2"
}

variable "is_fabric" {
  description = "Boolean to indicate if the Storage backend are being created as part of Azure Fabric (EventHouse)."
  type        = bool
  default     = false
}
