data "azuread_client_config" "current" {}

data "azurerm_resource_group" "demo" {
  name = "${var.base_name}-rg"
}

data "azurerm_container_registry" "demo" {
  name                = "${var.base_name}acr"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_kusto_cluster" "demo" {
  count = var.is_fabric ? 0 : 1

  name                = "${var.base_name}-adx"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_kusto_database" "observability" {
  count = var.is_fabric ? 0 : 1

  name                = "observabilitydb"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo[0].name
}

data "azurerm_kubernetes_cluster" "demo" {
  name                = "${var.base_name}-aks"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_eventhub_namespace" "monitor" {
  name                = "${var.base_name}-monitor-eventhub"
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_eventhub" "diagnostic" {
  name                = "DiagnosticData"
  namespace_name      = data.azurerm_eventhub_namespace.monitor.name
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_eventhub" "operational" {
  name                = "OperationalData"
  namespace_name      = data.azurerm_eventhub_namespace.monitor.name
  resource_group_name = data.azurerm_resource_group.demo.name

}

data "azurerm_eventhub_consumer_group" "diagnostic" {
  name                = "KustoConsumerGroup"
  namespace_name      = data.azurerm_eventhub_namespace.monitor.name
  eventhub_name       = data.azurerm_eventhub.diagnostic.name
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "azurerm_eventhub_consumer_group" "operational" {
  name                = "KustoConsumerGroup"
  namespace_name      = data.azurerm_eventhub_namespace.monitor.name
  eventhub_name       = data.azurerm_eventhub.operational.name
  resource_group_name = data.azurerm_resource_group.demo.name
}

data "fabric_workspace" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = "${var.base_name}-workspace"
}


data "fabric_kql_database" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = "observabilitydb"
  workspace_id = data.fabric_workspace.demo[0].id
}