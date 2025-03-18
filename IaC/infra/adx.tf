resource "azurerm_kusto_cluster" "demo" {
  name                = "${var.base_name}-adx"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name

  sku {
    name     = var.adx_sku
    capacity = 2
  }
}

resource "azurerm_kusto_database" "otel" {
  name                = "openteldb"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = azurerm_kusto_cluster.demo.name
}

# Monitoring
data "azurerm_monitor_diagnostic_categories" "adx" {
  resource_id = azurerm_kusto_cluster.demo.id
}

resource "azurerm_monitor_diagnostic_setting" "adx_logs" {
  name               = "adx-logs-diagnostic-setting"
  target_resource_id = azurerm_kusto_cluster.demo.id

  eventhub_name                  = azurerm_eventhub.logs.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx.log_category_types
    content {
      category = enabled_log.value
    }
  }

  lifecycle {
    ignore_changes = [metric]
  }
}

resource "azurerm_monitor_diagnostic_setting" "adx_metrics" {
  name               = "adx-metrics-diagnostic-setting"
  target_resource_id = azurerm_kusto_cluster.demo.id

  eventhub_name                  = azurerm_eventhub.metrics.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "metric" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx.metrics
    content {
      category = metric.value
      enabled  = true
    }
  }
}