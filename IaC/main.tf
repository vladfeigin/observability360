resource "azurerm_resource_group" "demo" {
  name     = "${var.base_name}-rg"
  location = var.region
}

resource "azurerm_service_plan" "demo" {
  name                = "${var.base_name}-serviceplan"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  os_type             = "Linux"
  sku_name            = "B2"
}