provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "docker" {
  registry_auth {
    address  = azurerm_container_registry.demo.login_server
    username = azurerm_container_registry.demo.admin_username
    password = azurerm_container_registry.demo.admin_password
  }
}

provider "azuread" {
  # Configuration options
}