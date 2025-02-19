resource "azurerm_container_registry" "demo" {
  name                = "${var.base_name}acr"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  sku                 = "Basic"
  admin_enabled       = true
}