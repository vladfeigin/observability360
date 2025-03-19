resource "azurerm_kusto_eventhub_data_connection" "diagnostic" {
  name                = "diagnostic-eventhub-data-connection"
  resource_group_name = data.azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = data.azurerm_kusto_cluster.demo.name
  database_name       = data.azurerm_kusto_database.otel.name

  eventhub_id    = data.azurerm_eventhub.diagnostic.id
  consumer_group = data.azurerm_eventhub_consumer_group.diagnostic_adx.name

  table_name        = "DiagnosticRawRecords"
  mapping_rule_name = "DiagnosticRawRecordsMapping"
  data_format       = "JSON"
}

resource "azurerm_kusto_eventhub_data_connection" "activitylog" {
  name                = "activityloh-eventhub-data-connection"
  resource_group_name = data.azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = data.azurerm_kusto_cluster.demo.name
  database_name       = data.azurerm_kusto_database.otel.name

  eventhub_id    = data.azurerm_eventhub.activitylog.id
  consumer_group = data.azurerm_eventhub_consumer_group.activitylog_adx.name

  table_name        = "ActivityLogsRawRecords"
  mapping_rule_name = "ActivityLogsRawRecordsMapping"
  data_format       = "JSON"
}