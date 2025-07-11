resource "azurerm_kusto_eventhub_data_connection" "diagnostic" {
  count = var.is_fabric ? 0 : 1

  name                = "diagnostic-eventhub-data-connection"
  resource_group_name = data.azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = data.azurerm_kusto_cluster.demo[0].name
  database_name       = data.azurerm_kusto_database.observability[0].name

  eventhub_id    = data.azurerm_eventhub.diagnostic.id
  consumer_group = data.azurerm_eventhub_consumer_group.diagnostic.name

  table_name        = "DiagnosticRawRecords"
  mapping_rule_name = "DiagnosticRawRecordsMapping"
  data_format       = "JSON"
}

resource "azurerm_kusto_eventhub_data_connection" "operatinoal" {
  count = var.is_fabric ? 0 : 1

  name                = "operational-eventhub-data-connection"
  resource_group_name = data.azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = data.azurerm_kusto_cluster.demo[0].name
  database_name       = data.azurerm_kusto_database.observability[0].name

  eventhub_id    = data.azurerm_eventhub.operational.id
  consumer_group = data.azurerm_eventhub_consumer_group.operational.name

  table_name        = "ActivityLogsRawRecords"
  mapping_rule_name = "ActivityLogsRawRecordsMapping"
  data_format       = "JSON"
}