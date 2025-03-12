resource "azurerm_eventhub_namespace" "monitor" {
  name                = "${var.base_name}-monitor-eventhub"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  sku                 = "Standard"
  capacity            = 1
}

resource "azurerm_eventhub" "logs" {
  name              = "logging-eventhub"
  namespace_id      = azurerm_eventhub_namespace.monitor.id
  partition_count   = 2
  message_retention = 1
}

resource "azurerm_eventhub" "metrics" {
  name              = "metrics-eventhub"
  namespace_id      = azurerm_eventhub_namespace.monitor.id
  partition_count   = 2
  message_retention = 1
}