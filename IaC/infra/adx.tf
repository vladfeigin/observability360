resource "azurerm_kusto_cluster" "demo" {
  name                = "${var.base_name}-adx"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name

  sku {
    name     = var.adx_sku
    capacity = 1
  }
}

resource "azurerm_kusto_database" "otel" {
  name                = "openteldb"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = azurerm_kusto_cluster.demo.name
}