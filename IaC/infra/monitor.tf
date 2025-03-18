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

resource "azurerm_eventhub_namespace_authorization_rule" "monitor" {
  name                = "authorization_rule"
  namespace_name      = azurerm_eventhub_namespace.monitor.name
  resource_group_name = azurerm_resource_group.demo.name

  listen = true
  send   = true
  manage = true
}

resource "azurerm_eventhub_consumer_group" "logs_adx" {
  name                = "logs-adx-consumergroup"
  namespace_name      = azurerm_eventhub_namespace.monitor.name
  eventhub_name       = azurerm_eventhub.logs.name
  resource_group_name = azurerm_resource_group.demo.name
}



# resource "azurerm_kusto_eventhub_data_connection" "logs_connection" {
#   name                = "logs-eventhub-data-connection"
#   resource_group_name = azurerm_resource_group.demo.name
#   location            = var.region
#   cluster_name        = azurerm_kusto_cluster.demo.name
#   database_name       = azurerm_kusto_database.otel.name

#   eventhub_id    = azurerm_eventhub.logs.id
#   consumer_group = azurerm_eventhub_consumer_group.logs_adx.name

#   table_name        = "my-table"         #(Optional)
#   mapping_rule_name = "my-table-mapping" #(Optional)
#   data_format       = "JSON"             #(Optional)
# }