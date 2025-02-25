provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "docker" {
  registry_auth {
    address  = data.azurerm_container_registry.demo.login_server
    username = data.azurerm_container_registry.demo.admin_username
    password = data.azurerm_container_registry.demo.admin_password
  }
}

provider "azuread" {
  # Configuration options
}