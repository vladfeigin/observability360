data "azuread_client_config" "current" {}

data "azurerm_resource_group" "demo" {
  name = "${var.base_name}-rg"
}

data "azurerm_container_registry" "demo" {
  name                = "${var.base_name}acr"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_kusto_cluster" "demo" {
  name                = "${var.base_name}-adx"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_kusto_database" "otel" {
  name                = "openteldb"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo.name
}

data "azurerm_kubernetes_cluster" "demo" {
  name                = "${var.base_name}-aks"
  resource_group_name = data.azurerm_resource_group.demo.name
}