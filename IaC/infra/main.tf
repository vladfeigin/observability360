data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "demo" {
  name     = "${var.base_name}-rg"
  location = var.region
}

locals {
  assets_directory_path = "../../assets"
  # initialize_kql_queries_file_name = 
}