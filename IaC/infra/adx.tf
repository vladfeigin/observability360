resource "azurerm_kusto_cluster" "demo" {
  count = var.is_fabric ? 0 : 1

  name                = "${var.base_name}-adx"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name

  sku {
    name     = var.adx_sku
    capacity = 2
  }
}

resource "azurerm_kusto_database" "otel" {
  count = var.is_fabric ? 0 : 1

  name                = "observabilitydb"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = azurerm_kusto_cluster.demo[0].name
}

# Monitoring
data "azurerm_monitor_diagnostic_categories" "adx" {
  count = var.is_fabric ? 0 : 1

  resource_id = azurerm_kusto_cluster.demo[0].id
}

resource "azurerm_monitor_diagnostic_setting" "adx" {
  count = var.is_fabric ? 0 : 1

  name               = "adx-diagnostic-setting"
  target_resource_id = azurerm_kusto_cluster.demo[0].id

  eventhub_name                  = azurerm_eventhub.diagnostic.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx[0].log_category_types
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx[0].metrics
    content {
      category = metric.value
      enabled  = true
    }
  }
}